import asyncio
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REPO_DIR = Path(__file__).parent.parent.parent
REPORTS_DIR = REPO_DIR / "arb-reports"
DB_PATH = REPO_DIR / "web" / "arb.db"

# ── DB ────────────────────────────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id      TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                account_id  TEXT NOT NULL,
                region      TEXT NOT NULL,
                prompt      TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                full_log    TEXT,
                created_at  TEXT NOT NULL,
                started_at  TEXT,
                finished_at TEXT
            )
        """)
        # 서버 재시작 시 24시간 이상 running 상태인 job을 error로 정리
        con.execute("""
            UPDATE jobs SET status='error', finished_at=?, full_log='서버 재시작 또는 24시간 초과로 인한 중단'
            WHERE status='running'
            AND started_at < datetime('now', '-24 hours')
        """, (now_kst().isoformat(),))

init_db()

@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def db_create_job(job: dict):
    with get_db() as con:
        con.execute(
            "INSERT INTO jobs (job_id,service_name,account_id,region,prompt,status,created_at) VALUES (?,?,?,?,?,?,?)",
            (job["job_id"], job["service_name"], job["account_id"], job["region"],
             job["prompt"], "pending", job["created_at"])
        )

def db_update(job_id: str, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with get_db() as con:
        con.execute(f"UPDATE jobs SET {sets} WHERE job_id=?", (*kwargs.values(), job_id))

def db_get(job_id: str) -> Optional[dict]:
    with get_db() as con:
        row = con.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

def db_list() -> list[dict]:
    with get_db() as con:
        rows = con.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

# ── In-memory log buffer (per running job) ────────────────────────────────────
LOG_BUFFERS: dict[str, list[str]] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)

# ── Background task ───────────────────────────────────────────────────────────

async def run_kiro(job_id: str, prompt: str, agent: str = "arb-orchestrator"):
    db_update(job_id, status="running", started_at=now_kst().isoformat())
    LOG_BUFFERS[job_id] = []
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(mode='wb', suffix='.log', delete=False)
    tmp_path = tmp.name
    tmp.close()
    # DB 전용 점검은 database-summary.md 생성을 완료 트리거로 사용
    is_db_only = (agent == "arb-database")
    try:
        with open(tmp_path, 'wb') as out_f:
            proc = await asyncio.create_subprocess_exec(
                "kiro-cli", "chat", "--agent", agent,
                stdin=asyncio.subprocess.PIPE,
                stdout=out_f,
                stderr=out_f,
                cwd=str(REPO_DIR),
            )
            proc_start = __import__('time').time()
            loop_start_time = asyncio.get_event_loop().time()
            proc.stdin.write((prompt + "\n").encode())
            await proc.stdin.drain()
            proc.stdin.close()

            # 파일 tail로 실시간 로그 스트리밍 (pipe 버퍼 포화 방지)
            offset = 0
            trigger_found_at = None
            AUTO_KILL_AFTER = 300  # 완료 기준 파일 생성 후 5분
            while True:
                await asyncio.sleep(0.5)
                with open(tmp_path, 'rb') as f:
                    f.seek(offset)
                    chunk = f.read()
                    if chunk:
                        lines = strip_ansi(chunk.decode(errors="replace")).splitlines(keepends=True)
                        LOG_BUFFERS[job_id].extend(lines)
                        offset += len(chunk)
                if proc.returncode is not None:
                    break
                # 완료 트리거 감지
                # - DB 전용 점검: database-summary.md 생성 → 즉시 종료
                # - Infra/전체 점검: improvement-plan.md 생성 → 5분 후 종료
                if trigger_found_at is None:
                    if is_db_only:
                        has_trigger = any(
                            md.stat().st_mtime >= proc_start
                            for md in REPORTS_DIR.rglob("database-summary.md")
                        )
                        if has_trigger:
                            proc.kill()
                            LOG_BUFFERS[job_id].append("\n[자동 종료] database-summary.md 생성 확인으로 프로세스를 종료합니다.\n")
                            break
                    else:
                        has_improvement = any(
                            md.stat().st_mtime >= proc_start
                            for md in REPORTS_DIR.rglob("improvement-plan.md")
                        )
                        if has_improvement:
                            trigger_found_at = asyncio.get_event_loop().time()
                # improvement-plan.md 생성 후 5분 경과 시 자동 종료 (Infra/전체 전용)
                if trigger_found_at and (asyncio.get_event_loop().time() - trigger_found_at) > AUTO_KILL_AFTER:
                    proc.kill()
                    LOG_BUFFERS[job_id].append("\n[자동 종료] improvement-plan.md 생성 후 5분 경과로 프로세스를 종료합니다.\n")
                    break
                try:
                    await asyncio.wait_for(proc.wait(), timeout=0.1)
                    break
                except asyncio.TimeoutError:
                    pass

            await proc.wait()
            # 남은 출력 flush
            with open(tmp_path, 'rb') as f:
                f.seek(offset)
                chunk = f.read()
                if chunk:
                    LOG_BUFFERS[job_id].extend(
                        strip_ansi(chunk.decode(errors="replace")).splitlines(keepends=True))

        full_log = strip_ansi(Path(tmp_path).read_text(errors="replace"))
        db_update(job_id, status="done", full_log=full_log,
                  finished_at=now_kst().isoformat())
    except Exception as e:
        db_update(job_id, status="error", full_log=f"ERROR: {e}",
                  finished_at=now_kst().isoformat())
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        await asyncio.sleep(30)
        LOG_BUFFERS.pop(job_id, None)

# ── API ───────────────────────────────────────────────────────────────────────

class ArbRequest(BaseModel):
    service_name: str
    account_id: str
    region: str
    regions: list = []  # 멀티 리전 선택 시 사용
    scope: str = "all"  # "all" = 전체 점검, "database" = DB만 점검
    engines: list = []  # scope=database 시 점검할 엔진 목록

# DB 엔진 ID → 표시명 매핑
ENGINE_LABELS = {
    "aurora-mysql":    "Aurora MySQL",
    "aurora-postgres": "Aurora PostgreSQL",
    "rds-mysql":       "RDS MySQL",
    "rds-postgres":    "RDS PostgreSQL",
    "dynamodb":        "DynamoDB",
    "elasticache":     "ElastiCache",
}

@app.post("/api/arb/run")
async def arb_run(req: ArbRequest):
    # scope에 따라 에이전트와 프롬프트 분기
    if req.scope == "database":
        agent = "arb-database"
        engines = req.engines if req.engines else list(ENGINE_LABELS.keys())
        engine_names = ", ".join(ENGINE_LABELS.get(e, e) for e in engines)
        def make_prompt(region):
            return (
                f"다음 정보로 DB ARB 점검을 수행하세요.\n\n"
                f"- 서비스명: {req.service_name}\n"
                f"- 계정 ID: {req.account_id}\n"
                f"- 리전: {region}\n"
                f"- 점검 엔진: {engine_names}\n\n"
                f"다음 DB 엔진만 점검하세요: {engine_names}. "
                f"목록에 없는 DB 엔진(sub-agent)은 호출하지 마세요."
            )
    else:
        agent = "arb-orchestrator"
        def make_prompt(region):
            return (
                f"{req.service_name} 환경 ({req.account_id}) {region} 리전 ARB 점검. "
                f"대상 계정 Role ARN: arn:aws:iam::{req.account_id}:role/ARB-ReadOnly-Role. "
                f"setup-arb-profile.sh를 실행하여 arb-target 프로파일을 세팅하세요. "
                f"setup이 실패하면 기존 arb-target 프로파일(~/.aws/credentials)을 그대로 사용하세요."
            )

    # 멀티 리전: regions 배열이 있으면 리전별 개별 job 순차 생성
    target_regions = req.regions if req.regions else [req.region]
    job_ids = []
    for region in target_regions:
        job_id = str(uuid.uuid4())
        prompt = make_prompt(region)
        job = {
            "job_id": job_id,
            "service_name": req.service_name,
            "account_id": req.account_id,
            "region": region,
            "prompt": prompt,
            "created_at": now_kst().isoformat(),
        }
        db_create_job(job)
        job_ids.append(job_id)
    # 순차 실행 (리전별 충돌 방지)
    async def run_sequential():
        for jid in job_ids:
            j = db_get(jid)
            await run_kiro(jid, j["prompt"], agent=agent)
    asyncio.create_task(run_sequential())
    return {"job_id": job_ids[0], "job_ids": job_ids}


@app.get("/api/arb/stream/{job_id}")
async def arb_stream(job_id: str):
    if not db_get(job_id):
        raise HTTPException(404, "job not found")

    async def generator() -> AsyncGenerator[dict, None]:
        sent = 0
        while True:
            buf = LOG_BUFFERS.get(job_id, [])
            while sent < len(buf):
                yield {"data": json.dumps({"line": buf[sent]})}
                sent += 1

            job = db_get(job_id)
            if job and job["status"] in ("done", "error"):
                # flush any remaining lines from DB log if buffer already gone
                if job_id not in LOG_BUFFERS and job.get("full_log"):
                    db_lines = job["full_log"].splitlines(keepends=True)
                    while sent < len(db_lines):
                        yield {"data": json.dumps({"line": db_lines[sent]})}
                        sent += 1
                yield {"data": json.dumps({"status": job["status"]})}
                break
            await asyncio.sleep(0.3)

    return EventSourceResponse(generator())


@app.get("/api/arb/jobs")
async def list_jobs():
    return [{k: v for k, v in j.items() if k != "full_log"} for j in db_list()]


@app.get("/api/arb/jobs/{job_id}")
async def get_job(job_id: str):
    job = db_get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {k: v for k, v in job.items() if k != "full_log"}


@app.get("/api/arb/jobs/{job_id}/log")
async def get_job_log(job_id: str):
    job = db_get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {"log": job.get("full_log") or ""}


def _parse_summary(path: Path) -> Optional[dict]:
    """summary.md에서 PASS/FAIL/Critical FAIL 숫자 파싱"""
    try:
        text = path.read_text(errors="replace")
        import re
        # 합계 행: | **24** | **39** | **51** | **19** | (숫자 앞에 ~ 허용)
        m = re.search(r'\*\*합계\*\*\s*\|\s*\*\*~?(\d+)\*\*\s*\|\s*\*\*~?(\d+)\*\*\s*\|\s*\*\*[~\d/]+\*\*\s*\|\s*\*\*~?(\d+)\*\*', text)
        if m:
            return {"pass": int(m.group(1)), "fail": int(m.group(2)), "critical": int(m.group(3))}
        # fallback: | 24 | 39 | 51 | 19 |
        m = re.search(r'합계[^\n]*\|\s*~?(\d+)\s*\|\s*~?(\d+)\s*\|\s*[~\d]+\s*\|\s*~?(\d+)', text)
        if m:
            return {"pass": int(m.group(1)), "fail": int(m.group(2)), "critical": int(m.group(3))}
    except Exception:
        pass
    return None


def _account_groups() -> dict:
    """account_id 기준으로 jobs를 그룹핑. 표시명은 가장 최근 service_name 사용"""
    from collections import defaultdict
    groups: dict = defaultdict(lambda: {"service_name": "", "last_date": "", "jobs": []})
    for j in db_list():
        acct = j["account_id"]
        groups[acct]["jobs"].append(j)
        if j["created_at"] > groups[acct]["last_date"]:
            groups[acct]["last_date"] = j["created_at"]
            groups[acct]["service_name"] = j["service_name"]
    return dict(groups)


@app.get("/api/dashboard/projects")
async def dashboard_projects():
    """계정 ID 기준으로 프로젝트 목록 반환 (done + running 포함)"""
    result = []
    for acct, g in _account_groups().items():
        active_jobs = [j for j in g["jobs"] if j["status"] in ("done", "running")]
        if active_jobs:
            result.append({"account_id": acct, "service_name": g["service_name"]})
    # 최근 점검일 내림차순 정렬
    for item in result:
        g = _account_groups().get(item["account_id"], {})
        item["_last_date"] = g.get("last_date", "")
    return sorted(result, key=lambda x: x.pop("_last_date"), reverse=True)


@app.get("/api/dashboard/trend")
async def dashboard_trend(account_id: str):
    """계정 ID 기준 점검 이력 (각 점검 개별 표시)"""
    result = []
    for j in db_list():
        if j["account_id"] != account_id or j["status"] != "done":
            continue
        date = j["created_at"][:10]
        time_str = j["created_at"][11:16]
        summary = _parse_job_summary(j) or {}
        result.append({
            "date": date,
            "time": time_str,
            "label": f"{date} {time_str}",
            "region": j["region"],
            "service_name": j["service_name"],
            "pass": summary.get("pass", 0),
            "fail": summary.get("fail", 0),
            "critical": summary.get("critical", 0),
        })
    return sorted(result, key=lambda x: x["label"])


@app.get("/api/dashboard/cost")
async def dashboard_cost(months: int = 3):
    """계정 ID 기준 점검 횟수 + 월별 AWS 비용"""
    import boto3, calendar
    from collections import defaultdict

    # 계정별 점검 횟수 집계
    project_list = []
    for acct, g in _account_groups().items():
        done = [j for j in g["jobs"] if j["status"] == "done"]
        if done:
            project_list.append({
                "project": g["service_name"],
                "account_id": acct,
                "count": len(done),
                "last_date": max(j["created_at"][:10] for j in done),
            })
    project_list.sort(key=lambda x: -x["count"])

    # 월별 비용 조회 (최근 N개월)
    monthly_cost = []
    try:
        from botocore.credentials import InstanceMetadataProvider, InstanceMetadataFetcher
        provider = InstanceMetadataProvider(iam_role_fetcher=InstanceMetadataFetcher(timeout=1000, num_attempts=2))
        creds = provider.load()
        ce = boto3.client("ce", region_name="us-east-1",
            aws_access_key_id=creds.access_key,
            aws_secret_access_key=creds.secret_key,
            aws_session_token=creds.token)
        now = now_kst()
        year = now.year
        # 해당 연도 1월 ~ 현재 월까지만 조회 (CE는 미래 날짜 불가)
        import datetime as _dt
        end_dt = (now.replace(day=1) + _dt.timedelta(days=32)).replace(day=1)
        start_str = f"{year}-01-01"
        end_str = end_dt.strftime("%Y-%m-%d")
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start_str, "End": end_str},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        cost_by_month = {r["TimePeriod"]["Start"][:7]: round(float(r["Total"]["UnblendedCost"]["Amount"]), 2)
                         for r in resp["ResultsByTime"]}
        for mon in range(1, 13):
            key = f"{year:04d}-{mon:02d}"
            monthly_cost.append({
                "month": key,
                "cost": cost_by_month.get(key, 0),
                "estimated": mon == now.month,
            })
    except Exception as e:
        print(f"[cost API error] {e}")

    return {"projects": project_list, "monthly_cost": monthly_cost}


@app.get("/api/dashboard/monthly")
async def dashboard_monthly(month: str = ""):
    """일별 점검 현황 + AWS 일별 비용 (계정 ID 기준 중복 제거)"""
    from collections import defaultdict
    import calendar, boto3
    # account_id → 최신 service_name 매핑
    acct_name = {acct: g["service_name"] for acct, g in _account_groups().items()}
    daily: dict = defaultdict(lambda: {"count": 0, "accounts": set()})
    for j in db_list():
        if j["status"] not in ("done", "running"):
            continue
        day = j["created_at"][:10]
        if month and not day.startswith(month):
            continue
        daily[day]["count"] += 1
        daily[day]["accounts"].add(j["account_id"])

    if not month:
        month = now_kst().strftime("%Y-%m")
    year, mon = int(month[:4]), int(month[5:7])
    _, days_in_month = calendar.monthrange(year, mon)

    # Cost Explorer 조회 (월 전체)
    cost_by_day: dict = {}
    try:
        ce = boto3.client("ce", region_name="us-east-1")
        next_month = datetime(year, mon, days_in_month) + __import__('datetime').timedelta(days=1)
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": f"{month}-01", "End": next_month.strftime("%Y-%m-%d")},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        for r in resp["ResultsByTime"]:
            day = r["TimePeriod"]["Start"]
            cost_by_day[day] = round(float(r["Total"]["UnblendedCost"]["Amount"]), 2)
    except Exception:
        pass

    result = []
    for d in range(1, days_in_month + 1):
        day_str = f"{month}-{d:02d}"
        v = daily.get(day_str, {"count": 0, "accounts": set()})
        result.append({
            "day": day_str,
            "count": v["count"],
            "projects": sorted(acct_name.get(a, a) for a in v["accounts"]),
            "cost": cost_by_day.get(day_str, 0),
        })
    return result


def _parse_job_summary(job: dict) -> Optional[dict]:
    """job과 연관된 리포트에서 PASS/FAIL/Critical 합계 파싱"""
    if not job.get("started_at"):
        return None
    try:
        import re, datetime as dt
        started = datetime.fromisoformat(job["started_at"])
        # finished_at이 비정상(재시작으로 덮어써진 경우)이면 started + 3시간으로 대체
        if job.get("finished_at"):
            finished = datetime.fromisoformat(job["finished_at"])
            if (finished - started).total_seconds() > 7200:
                finished = started + dt.timedelta(hours=3)
        else:
            finished = started + dt.timedelta(hours=3)

        window_end = finished + dt.timedelta(hours=1)

        if not REPORTS_DIR.exists():
            return None

        # 파일 mtime을 KST로 변환 (서버가 UTC, DB는 KST)
        def mtime_kst(p):
            return datetime.fromtimestamp(p.stat().st_mtime) + dt.timedelta(hours=9)

        # 1순위: summary.md (통합 리포트)
        for md in REPORTS_DIR.rglob("summary.md"):
            mtime = mtime_kst(md)
            if started <= mtime <= window_end:
                parsed = _parse_summary(md)
                if parsed:
                    return parsed

        # 2순위: database-summary.md (DB 전용 점검 시, summary.md 없을 때만)
        for md in REPORTS_DIR.rglob("database-summary.md"):
            mtime = mtime_kst(md)
            if started <= mtime <= window_end:
                parsed = _parse_summary(md)
                if parsed:
                    return parsed

        # 3순위: 개별 md 파일에서 PASS/FAIL 합산 (테이블 행 패턴)
        total = {"pass": 0, "fail": 0, "critical": 0}
        found = False
        for md in REPORTS_DIR.rglob("*.md"):
            if md.name in ("summary.md", "database-summary.md", "diagram.md", "improvement-plan.md"):
                continue
            mtime = mtime_kst(md)
            if not (started <= mtime <= window_end):
                continue
            text = md.read_text(errors="replace")
            # 테이블 행에서 PASS/FAIL 카운트 (✅ PASS, ❌ FAIL 포함)
            pass_count = len(re.findall(r'\|\s*(?:✅\s*)?PASS\s*\|', text))
            fail_count = len(re.findall(r'\|\s*(?:❌\s*)?FAIL\s*\|', text))
            crit_count = len(re.findall(r'\|\s*critical\s*\|\s*(?:❌\s*)?FAIL', text, re.IGNORECASE))
            if pass_count or fail_count:
                found = True
                total["pass"] += pass_count
                total["fail"] += fail_count
                total["critical"] += crit_count
        return total if found else None
    except Exception:
        return None


@app.get("/api/arb/jobs/{job_id}/summary")
async def get_job_summary(job_id: str):
    job = db_get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return _parse_job_summary(job) or {}


INFRA_FILES = {"architecture", "devops", "operation", "service-stability", "system-stability", "diagram", "improvement-plan"}
DB_FILES = {"aurora-mysql", "aurora-postgres", "rds-mysql", "rds-postgres", "dynamodb", "elasticache", "verify-result"}

def _classify_report(name: str) -> str:
    stem = name.replace(".md", "")
    if stem in ("summary", "database-summary"):
        return "summary"
    if stem in INFRA_FILES:
        return "infra"
    if stem in DB_FILES or stem.startswith("aurora-") or stem.startswith("rds-"):
        return "database"
    return "infra"  # 기타는 infra로


@app.get("/api/arb/reports/tree")
async def reports_tree():
    """프로젝트 > 날짜 > summary + infra/database 분류 트리"""
    from collections import defaultdict
    import re as _re

    # 계정 ID → 최신 서비스명 매핑
    acct_to_name = {acct: g["service_name"] for acct, g in _account_groups().items()}

    # date_dir별 job_id 폴더 존재 여부 캐싱 (성능 최적화)
    job_dir_cache: dict = {}
    def has_job_dir_cached(date_dir_path):
        key = str(date_dir_path)
        if key not in job_dir_cache:
            try:
                job_dir_cache[key] = any(
                    d.is_dir() and _re.match(r"^[0-9a-f]{8}$", d.name)
                    for d in date_dir_path.iterdir()
                )
            except Exception:
                job_dir_cache[key] = False
        return job_dir_cache[key]

    tree: dict = defaultdict(lambda: defaultdict(lambda: {"summary": None, "infra": [], "database": []}))
    if REPORTS_DIR.exists():
        for md in sorted(REPORTS_DIR.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            parts = md.relative_to(REPORTS_DIR).parts
            if len(parts) < 3:
                continue
            service = parts[0]
            if any(service.startswith(p) for p in ("ap-", "us-", "eu-", "sa-", "ca-", "me-", "af-")):
                continue
            region = parts[1]
            date = parts[2]

            # 신구조: job_id 폴더(8자리 hex) 감지
            if len(parts) >= 5 and _re.match(r"^[0-9a-f]{8}$", parts[3]):
                date = parts[2]
            elif len(parts) == 4:
                # 구구조 date/file — job_id 폴더 있으면 중복이므로 스킵
                date_dir = REPORTS_DIR / service / region / date
                if has_job_dir_cached(date_dir):
                    continue

            # 계정 ID 폴더(12자리 숫자)면 서비스명으로 표시
            if _re.match(r"^\d{12}$", service):
                service = acct_to_name.get(service, service)

            display_name = md.name if region == "ap-northeast-2" else f"[{region}] {md.name}"
            entry = {"path": str(md.relative_to(REPORTS_DIR)), "name": display_name,
                     "modified": (datetime.fromtimestamp(md.stat().st_mtime) + __import__("datetime").timedelta(hours=9)).isoformat()}
            cat = _classify_report(md.name)
            if cat == "summary":
                if tree[service][date]["summary"] is None:
                    tree[service][date]["summary"] = entry
            else:
                tree[service][date][cat].append(entry)
    result = []
    for service in sorted(tree.keys()):
        dates = []
        for date in sorted(tree[service].keys(), reverse=True):
            d = tree[service][date]
            dates.append({
                "date": date,
                "summary": d["summary"],
                "infra": sorted(d["infra"], key=lambda x: x["name"]),
                "database": sorted(d["database"], key=lambda x: x["name"]),
            })
        result.append({"service": service, "dates": dates})
    return result


@app.get("/api/arb/jobs/{job_id}/reports")
async def get_job_reports(job_id: str):
    job = db_get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    reports = []
    if REPORTS_DIR.exists() and job.get("finished_at"):
        import datetime as _dt
        finished = datetime.fromisoformat(job["finished_at"])
        started = datetime.fromisoformat(job["started_at"]) if job.get("started_at") else finished
        for md in REPORTS_DIR.rglob("*.md"):
            # 파일 mtime은 UTC → KST로 변환하여 비교
            mtime_kst = datetime.fromtimestamp(md.stat().st_mtime) + _dt.timedelta(hours=9)
            if started <= mtime_kst <= finished + _dt.timedelta(minutes=3):
                reports.append({
                    "path": str(md.relative_to(REPORTS_DIR)),
                    "name": md.name,
                    "size": md.stat().st_size,
                    "modified": mtime_kst.isoformat(),
                })
    return sorted(reports, key=lambda r: r["modified"])


@app.get("/api/arb/reports")
async def list_reports():
    reports = []
    if REPORTS_DIR.exists():
        for md in sorted(REPORTS_DIR.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            reports.append({
                "path": str(md.relative_to(REPORTS_DIR)),
                "name": md.name,
                "size": md.stat().st_size,
                "modified": (datetime.fromtimestamp(md.stat().st_mtime) + __import__("datetime").timedelta(hours=9)).isoformat(),
            })
    return reports


def _translate_markdown(text: str, target_lang: str = "en") -> str:
    """마크다운 구조를 유지하며 Amazon Translate로 번역 (코드블록 제외)"""
    import boto3, re
    from botocore.credentials import InstanceMetadataProvider, InstanceMetadataFetcher
    # EC2 인스턴스 메타데이터에서 직접 credential 가져오기 (profile 우회)
    provider = InstanceMetadataProvider(iam_role_fetcher=InstanceMetadataFetcher(timeout=1000, num_attempts=2))
    creds = provider.load()
    client = boto3.client("translate", region_name="ap-northeast-2",
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.token)
    result = []
    state = {"buffer": [], "in_code": False}

    def flush():
        buf = state["buffer"]
        if not buf:
            return
        chunk = '\n'.join(buf)
        resp = client.translate_text(Text=chunk, SourceLanguageCode="ko", TargetLanguageCode=target_lang)
        result.extend(resp["TranslatedText"].split('\n'))
        state["buffer"] = []

    for line in text.split('\n'):
        if line.strip().startswith('```'):
            flush()
            state["in_code"] = not state["in_code"]
            result.append(line)
            continue
        if state["in_code"]:
            result.append(line)
            continue
        if re.match(r'^[\|\s\-:]+$', line) and '|' in line:
            flush()
            result.append(line)
            continue
        state["buffer"].append(line)
        if sum(len(l) for l in state["buffer"]) > 4000:
            flush()

    flush()
    return '\n'.join(result)


@app.get("/api/arb/reports/content")
async def get_report(path: str = Query(...), lang: str = "ko"):
    import json as _j2
    target = (REPORTS_DIR / path).resolve()
    if not str(target).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(403, "forbidden")
    if not target.exists():
        raise HTTPException(404, "not found")
    content = target.read_text(errors="replace")

    # summary.md인 경우 사전 서베이 내용을 접힌 상태로 상단에 추가
    if Path(path).name == "summary.md":
        is_en = lang == "en"
        parts = Path(path).parts
        acct_id = parts[0] if parts else None
        if acct_id and re.match(r"^\d{12}$", acct_id):
            survey_file = SURVEY_DIR / f"{acct_id}.json"
            if survey_file.exists():
                sv = _j2.loads(survey_file.read_text())
                data = sv.get("data", {})
                saved_at = sv.get("submitted_at", "")[:16]
                if data:
                    rows = []
                    for sec_key, sec in SURVEY_SCHEMA.items():
                        sec_label = sec.get("label_en", sec["label"]) if is_en else sec["label"]
                        for f in sec["fields"]:
                            val = data.get(f["key"])
                            if val is None:
                                continue
                            f_label = f.get("label_en", f["label"]) if is_en else f["label"]
                            if isinstance(val, bool):
                                disp = "✅ Y" if val else "❌ N"
                            else:
                                disp = str(val)
                            rows.append(f"| {sec_label} — {f_label} | {disp} |")
                    if rows:
                        hdr = "| Item | Answer |" if is_en else "| 항목 | 응답 |"
                        table = hdr + "\n|------|------|\n" + "\n".join(rows)
                        title = f"📋 Pre-Survey (submitted: {saved_at}) — click to expand" if is_en else f"📋 사전 서베이 (제출: {saved_at}) — 클릭하여 펼치기"
                        survey_section = (
                            f"<details>\n"
                            f"<summary>{title}</summary>\n\n"
                            f"{table}\n\n"
                            f"</details>\n\n"
                        )
                        content = survey_section + content

        # DB 사전 서베이 파일들(스크립트 결과 + 수동 설문)도 접힌 상태로 추가
        import datetime as _dt3
        db_sections = []

        # 1) 스크립트 결과 .md 파일
        db_survey_dir = DB_PRESUVEY_DIR / acct_id if acct_id else None
        if db_survey_dir and db_survey_dir.exists():
            db_files = sorted(db_survey_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            for db_file in db_files:
                mtime = (datetime.fromtimestamp(db_file.stat().st_mtime) + _dt3.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
                engine_name = db_file.stem
                db_content = db_file.read_text(errors="replace")[:3000]
                title = f"🗄️ DB Script Result — {engine_name} (uploaded: {mtime}) — click to expand" if is_en else f"🗄️ DB 스크립트 결과 — {engine_name} (업로드: {mtime}) — 클릭하여 펼치기"
                db_sections.append(
                    f"<details>\n"
                    f"<summary>{title}</summary>\n\n"
                    f"```\n{db_content}\n```\n\n"
                    f"</details>\n\n"
                )

        # 2) DB 수동 설문 (.json → 테이블로 변환)
        import json as _j3
        db_manual_dir = DB_MANUAL_SURVEY_DIR / acct_id if acct_id else None
        if db_manual_dir and db_manual_dir.exists():
            for json_file in sorted(db_manual_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                engine = json_file.stem
                try:
                    sv = _j3.loads(json_file.read_text())
                    data = sv.get("data", {})
                    saved_at = sv.get("submitted_at", "")[:16]
                    schema_entry = DB_MANUAL_SCHEMA.get(engine)
                    if not schema_entry or not data:
                        continue
                    rows = []
                    for sec in schema_entry["sections"]:
                        sec_label = sec.get("label_en", sec["label"]) if is_en else sec["label"]
                        for f in sec["fields"]:
                            val = data.get(f["key"])
                            if val is None:
                                continue
                            f_label = f.get("label_en", f["label"]) if is_en else f["label"]
                            if isinstance(val, bool):
                                disp = "✅ Y" if val else "❌ N"
                            else:
                                disp = str(val)
                            rows.append(f"| {sec_label} — {f_label} | {disp} |")
                    if rows:
                        hdr = "| Item | Answer |" if is_en else "| 항목 | 응답 |"
                        table = hdr + "\n|------|------|\n" + "\n".join(rows)
                        eng_label = schema_entry.get("label_en", schema_entry.get("label", engine)) if is_en else schema_entry.get("label", engine)
                        title = f"📋 DB Manual Survey — {eng_label} (submitted: {saved_at}) — click to expand" if is_en else f"📋 DB 수동 설문 — {eng_label} (제출: {saved_at}) — 클릭하여 펼치기"
                        db_sections.append(
                            f"<details>\n"
                            f"<summary>{title}</summary>\n\n"
                            f"{table}\n\n"
                            f"</details>\n\n"
                        )
                except Exception:
                    pass

        if db_sections:
            content = "".join(db_sections) + "---\n\n" + content

    if lang == "en":
        content = _translate_markdown(content, "en")
    return {"content": content, "path": path}


# ── Knowledge Guide API ───────────────────────────────────────────────────────
import json as _json

_KNOWLEDGE_INDEX: Optional[dict] = None
_KNOWLEDGE_PATH = Path(__file__).parent / "knowledge_index.json"

def _load_knowledge():
    global _KNOWLEDGE_INDEX
    if _KNOWLEDGE_INDEX is None and _KNOWLEDGE_PATH.exists():
        _KNOWLEDGE_INDEX = _json.loads(_KNOWLEDGE_PATH.read_text())
    return _KNOWLEDGE_INDEX


@app.get("/api/guide/summary-fails")
async def guide_summary_fails(path: str = Query(...)):
    """summary.md의 카테고리별 FAIL 판정에서 관련 Check ID와 가이드 문서 반환"""
    import re as _re
    target = (REPORTS_DIR / path).resolve()
    if not str(target).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(403, "forbidden")
    if not target.exists():
        raise HTTPException(404, "not found")

    text = target.read_text(errors="replace")
    idx = _load_knowledge()
    check_map = idx.get("check_map", {}) if idx else {}

    # 카테고리 → 관련 Check ID 매핑
    CATEGORY_CHECKS = {
        "아키텍처": ["ARCH-011","ARCH-005","ARCH-010","ARCH-012","ARCH-013","ARCH-014","ARCH-015","ARCH-019","ARCH-022","ARCH-023","ARCH-026","ARCH-027","ARCH-028","ARCH-029","ARCH-031"],
        "architecture": ["ARCH-011","ARCH-005","ARCH-010","ARCH-014","ARCH-015","ARCH-019","ARCH-022","ARCH-023","ARCH-026","ARCH-027","ARCH-028","ARCH-029","ARCH-031"],
        "devops": ["DEV-001","DEV-005","DEV-011","DEV-012"],
        "devops 자동화": ["DEV-001","DEV-005","DEV-011","DEV-012"],
        "운영": ["OPS-002","OPS-006","OPS-007","OPS-011","OPS-012","OPS-013"],
        "운영 적합성": ["OPS-002","OPS-006","OPS-007","OPS-011","OPS-012","OPS-013"],
        "서비스 안정성": ["SYS-001","SYS-002","SYS-003","SYS-004"],
        "시스템 안정성": ["SYS-001","SYS-002","SYS-003","SYS-004"],
        "rds postgresql": ["RDS-HA-001","RDS-SEC-002","COM-BR-001","COM-BR-002","COM-NI-001","COM-AC-001","COM-MON-001"],
        "rds mysql": ["RDS-HA-001","RDS-SEC-002","COM-BR-001","COM-BR-002","COM-NI-001"],
        "aurora mysql": ["AUR-MY-003","AUR-MY-006","AUR-MON-003","COM-BR-001","COM-BR-002","COM-NI-001"],
        "aurora postgresql": ["AUR-MON-003","COM-BR-001","COM-BR-002","COM-NI-001"],
        "dynamodb": ["DDB-SEC-002","DDB-SEC-004"],
    }

    results = []
    for line in text.split('\n'):
        if '❌ FAIL' not in line and '❌ fail' not in line.lower():
            continue
        # 테이블 행: | 1 | 아키텍처 | ... | ❌ FAIL |
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) < 2:
            continue
        # 카테고리명은 2번째 셀
        cat_name = cells[1].lower().strip()
        check_ids = CATEGORY_CHECKS.get(cat_name, [])
        if not check_ids:
            # 부분 매칭
            for key in CATEGORY_CHECKS:
                if key in cat_name or cat_name in key:
                    check_ids = CATEGORY_CHECKS[key]
                    break
        if not check_ids:
            continue
        # 해당 카테고리의 관련 문서 수집
        docs = []
        seen_files = set()
        for cid in check_ids:
            for doc in check_map.get(cid, []):
                if doc["file"] not in seen_files:
                    seen_files.add(doc["file"])
                    docs.append({"check_id": cid, "title": doc["title"], "file": doc["file"]})
        if docs:
            results.append({
                "category": cells[1],
                "check_ids": check_ids,
                "docs": docs[:8],
            })

    return results


@app.get("/api/guide/arb-tree")
async def guide_arb_tree(lang: str = "ko"):
    """ARB 체크리스트 기반 카테고리 트리 + 관련 Knowledge 문서"""
    idx = _load_knowledge()
    check_map = idx.get("check_map", {}) if idx else {}

    tree = [
        {"category": "인프라 아키텍처" if lang=="ko" else "Infrastructure Architecture", "icon": "🏗️", "children": [
            {"id": "ARCH-011", "label": "Multi-AZ HA 구성" if lang=="ko" else "Multi-AZ HA Configuration"},
            {"id": "ARCH-005", "label": "Multi-Region 아키텍처" if lang=="ko" else "Multi-Region Architecture"},
            {"id": "ARCH-012", "label": "VPC 구성" if lang=="ko" else "VPC Configuration"},
            {"id": "ARCH-013", "label": "Public/Private Subnet 분리" if lang=="ko" else "Public/Private Subnet Separation"},
            {"id": "ARCH-028", "label": "SPOF 제거" if lang=="ko" else "SPOF Elimination"},
            {"id": "ARCH-023", "label": "마이크로서비스 장애 격리" if lang=="ko" else "Microservice Fault Isolation"},
        ]},
        {"category": "Auto Scaling / 컨테이너" if lang=="ko" else "Auto Scaling / Container", "icon": "📈", "children": [
            {"id": "ARCH-014", "label": "Auto Scaling Group 구성" if lang=="ko" else "Auto Scaling Group"},
            {"id": "ARCH-015", "label": "Scaling Policy" },
            {"id": "ARCH-029", "label": "트래픽 급증 대비" if lang=="ko" else "Traffic Surge Handling"},
            {"id": "ARCH-026", "label": "컨테이너 오케스트레이션 (EKS/ECS)" if lang=="ko" else "Container Orchestration (EKS/ECS)"},
            {"id": "ARCH-019", "label": "이미지 기반 배포" if lang=="ko" else "Image-based Deployment"},
        ]},
        {"category": "모니터링 / 운영" if lang=="ko" else "Monitoring / Operations", "icon": "📊", "children": [
            {"id": "ARCH-010", "label": "CloudWatch 모니터링" if lang=="ko" else "CloudWatch Monitoring"},
            {"id": "ARCH-022", "label": "분산 추적 (X-Ray)" if lang=="ko" else "Distributed Tracing (X-Ray)"},
            {"id": "OPS-002", "label": "장애 에스컬레이션 / SNS" if lang=="ko" else "Incident Escalation / SNS"},
            {"id": "OPS-006", "label": "CloudWatch Dashboard"},
            {"id": "OPS-007", "label": "Alarm 임계값 설정" if lang=="ko" else "Alarm Threshold Settings"},
        ]},
        {"category": "백업 / DR" if lang=="ko" else "Backup / DR", "icon": "💾", "children": [
            {"id": "OPS-011", "label": "AWS Backup Plan"},
            {"id": "OPS-012", "label": "데이터 분류별 백업 정책" if lang=="ko" else "Data Classification Backup Policy"},
            {"id": "OPS-013", "label": "인프라별 백업 방식" if lang=="ko" else "Infrastructure Backup Methods"},
            {"id": "ARCH-031", "label": "DR 전략" if lang=="ko" else "DR Strategy"},
            {"id": "SYS-003", "label": "HA 테스트" if lang=="ko" else "HA Testing"},
            {"id": "SYS-004", "label": "DR 전환 테스트" if lang=="ko" else "DR Failover Testing"},
        ]},
        {"category": "DevOps / 배포" if lang=="ko" else "DevOps / Deployment", "icon": "🚀", "children": [
            {"id": "DEV-001", "label": "IaC (Terraform)"},
            {"id": "DEV-005", "label": "CI 빌드 자동화" if lang=="ko" else "CI Build Automation"},
            {"id": "DEV-011", "label": "배포 파이프라인" if lang=="ko" else "Deployment Pipeline"},
            {"id": "DEV-012", "label": "Rollback 지원" if lang=="ko" else "Rollback Support"},
        ]},
        {"category": "DB 공통" if lang=="ko" else "DB Common", "icon": "🗄️", "children": [
            {"id": "COM-BR-001", "label": "자동 백업 / Retention" if lang=="ko" else "Auto Backup / Retention"},
            {"id": "COM-BR-002", "label": "삭제 방지" if lang=="ko" else "Deletion Protection"},
            {"id": "COM-NI-001", "label": "DB 서브넷 망분리" if lang=="ko" else "DB Subnet Isolation"},
            {"id": "COM-AC-001", "label": "SBC 경유 접근" if lang=="ko" else "SBC Access Control"},
            {"id": "COM-MON-001", "label": "CloudWatch 알람" if lang=="ko" else "CloudWatch Alarm"},
        ]},
        {"category": "Aurora MySQL", "icon": "🐬", "children": [
            {"id": "AUR-MY-003", "label": "파라미터 권장 설정" if lang=="ko" else "Recommended Parameters"},
            {"id": "AUR-MY-006", "label": "비밀번호 정책" if lang=="ko" else "Password Policy"},
            {"id": "AUR-MON-003", "label": "CloudWatch Logs Export"},
        ]},
        {"category": "RDS / DynamoDB", "icon": "📋", "children": [
            {"id": "RDS-HA-001", "label": "RDS Multi-AZ"},
            {"id": "RDS-SEC-002", "label": "기본 포트 변경" if lang=="ko" else "Change Default Port"},
            {"id": "DDB-SEC-002", "label": "IAM 정책 와일드카드" if lang=="ko" else "IAM Policy Wildcard"},
            {"id": "DDB-SEC-004", "label": "DynamoDB VPC Endpoint"},
        ]},
    ]
    for cat in tree:
        for item in cat["children"]:
            docs = check_map.get(item["id"], [])
            item["doc_count"] = len(docs)
            item["top_doc"] = docs[0]["title"] if docs else None
    return tree

    tree = [
        {
            "category": "인프라 아키텍처",
            "icon": "🏗️",
            "children": [
                {"id": "ARCH-011", "label": "Multi-AZ HA 구성"},
                {"id": "ARCH-005", "label": "Multi-Region 아키텍처"},
                {"id": "ARCH-012", "label": "VPC 구성"},
                {"id": "ARCH-013", "label": "Public/Private Subnet 분리"},
                {"id": "ARCH-028", "label": "SPOF 제거"},
                {"id": "ARCH-023", "label": "마이크로서비스 장애 격리"},
            ]
        },
        {
            "category": "Auto Scaling / 컨테이너",
            "icon": "📈",
            "children": [
                {"id": "ARCH-014", "label": "Auto Scaling Group 구성"},
                {"id": "ARCH-015", "label": "Scaling Policy"},
                {"id": "ARCH-029", "label": "트래픽 급증 대비"},
                {"id": "ARCH-026", "label": "컨테이너 오케스트레이션 (EKS/ECS)"},
                {"id": "ARCH-019", "label": "이미지 기반 배포"},
            ]
        },
        {
            "category": "모니터링 / 운영",
            "icon": "📊",
            "children": [
                {"id": "ARCH-010", "label": "CloudWatch 모니터링"},
                {"id": "ARCH-022", "label": "분산 추적 (X-Ray)"},
                {"id": "OPS-002", "label": "장애 에스컬레이션 / SNS"},
                {"id": "OPS-006", "label": "CloudWatch Dashboard"},
                {"id": "OPS-007", "label": "Alarm 임계값 설정"},
            ]
        },
        {
            "category": "백업 / DR",
            "icon": "💾",
            "children": [
                {"id": "OPS-011", "label": "AWS Backup Plan"},
                {"id": "OPS-012", "label": "데이터 분류별 백업 정책"},
                {"id": "OPS-013", "label": "인프라별 백업 방식"},
                {"id": "ARCH-031", "label": "DR 전략"},
                {"id": "SYS-003", "label": "HA 테스트"},
                {"id": "SYS-004", "label": "DR 전환 테스트"},
            ]
        },
        {
            "category": "DevOps / 배포",
            "icon": "🚀",
            "children": [
                {"id": "DEV-001", "label": "IaC (Terraform)"},
                {"id": "DEV-005", "label": "CI 빌드 자동화"},
                {"id": "DEV-011", "label": "배포 파이프라인"},
                {"id": "DEV-012", "label": "Rollback 지원"},
            ]
        },
        {
            "category": "DB 공통",
            "icon": "🗄️",
            "children": [
                {"id": "COM-BR-001", "label": "자동 백업 / Retention"},
                {"id": "COM-BR-002", "label": "삭제 방지"},
                {"id": "COM-NI-001", "label": "DB 서브넷 망분리"},
                {"id": "COM-AC-001", "label": "SBC 경유 접근"},
                {"id": "COM-MON-001", "label": "CloudWatch 알람"},
            ]
        },
        {
            "category": "Aurora MySQL",
            "icon": "🐬",
            "children": [
                {"id": "AUR-MY-003", "label": "파라미터 권장 설정"},
                {"id": "AUR-MY-006", "label": "비밀번호 정책"},
                {"id": "AUR-MON-003", "label": "CloudWatch Logs Export"},
            ]
        },
        {
            "category": "RDS / DynamoDB",
            "icon": "📋",
            "children": [
                {"id": "RDS-HA-001", "label": "RDS Multi-AZ"},
                {"id": "RDS-SEC-002", "label": "기본 포트 변경"},
                {"id": "DDB-SEC-002", "label": "IAM 정책 와일드카드"},
                {"id": "DDB-SEC-004", "label": "DynamoDB VPC Endpoint"},
            ]
        },
    ]

    # 각 항목에 관련 문서 수 추가
    for cat in tree:
        for item in cat["children"]:
            docs = check_map.get(item["id"], [])
            item["doc_count"] = len(docs)
            item["top_doc"] = docs[0]["title"] if docs else None

    return tree


@app.get("/api/guide/index")
async def guide_index():
    """Knowledge 문서 브레드크럼 기반 목차 반환"""
    idx = _load_knowledge()
    if not idx:
        raise HTTPException(503, "knowledge index not loaded")
    from collections import defaultdict
    tree: dict = defaultdict(list)
    for doc in idx.get("docs", []):
        bc = doc.get("breadcrumb", [])
        # 최상위 카테고리 (breadcrumb 2번째 또는 1번째)
        if len(bc) >= 2:
            cat = bc[1]
        elif len(bc) == 1:
            cat = bc[0]
        else:
            cat = "기타"
        tree[cat].append({"file": doc["file"], "title": doc["title"]})
    return [{"category": k, "docs": v} for k, v in sorted(tree.items()) if k]


@app.get("/api/guide/check/{check_id}")
async def guide_by_check(check_id: str):
    """Check ID 기반 관련 Knowledge 문서 반환"""
    idx = _load_knowledge()
    if not idx:
        raise HTTPException(503, "knowledge index not loaded")
    docs = idx.get("check_map", {}).get(check_id.upper(), [])
    return {"check_id": check_id, "docs": docs}


@app.get("/api/guide/search")
async def guide_search(q: str):
    """다중 키워드(공백 구분) Knowledge 문서 검색 — AND 조건"""
    idx = _load_knowledge()
    if not idx:
        raise HTTPException(503, "knowledge index not loaded")
    keywords = [k.lower() for k in q.split() if k.strip()]
    if not keywords:
        return []
    results = []
    for doc in idx.get("docs", []):
        search_text = doc["keywords_raw"] + " " + doc["body_preview"].lower()
        if all(kw in search_text for kw in keywords):
            results.append({
                "file": doc["file"],
                "title": doc["title"],
                "breadcrumb": doc["breadcrumb"],
                "body_preview": doc["body_preview"][:600],
            })
    return results[:20]


GUIDE_BASE = Path("/home/noboru78.lee/repo/aiops-arb-guide/OPSPROCESS_MD")


def _preprocess_guide_doc(text: str) -> str:
    """이미지 경로를 API URL로 변환, details 블록 간소화"""
    import re as _re
    # frontmatter 제거
    text = _re.sub(r'^---[\s\S]+?---\n', '', text, count=1).strip()
    # ./attachments/xxx/yyy.png → /api/guide/attachment/xxx/yyy.png
    text = _re.sub(
        r'\./attachments/(\d+/[^\)"\s]+)',
        r'/api/guide/attachment/\1',
        text
    )
    # <details><summary>📝 이미지 텍스트 내용...</summary> 블록을 간결하게 축약
    def shorten_details(m):
        # 이미지 유형/구조 설명만 남기고 OCR 텍스트 제거
        content = m.group(1)
        type_m = _re.search(r'## 이미지 유형\n(.+)', content)
        desc_m = _re.search(r'### 구조 설명\n(.+?)(?=###|\Z)', content, _re.DOTALL)
        summary = ""
        if type_m:
            summary += f"**유형**: {type_m.group(1).strip()}\n\n"
        if desc_m:
            desc = desc_m.group(1).strip()[:200]
            summary += f"{desc}{'...' if len(desc_m.group(1).strip()) > 200 else ''}"
        return f"<details>\n<summary>📝 이미지 설명 보기</summary>\n\n{summary}\n\n</details>"

    text = _re.sub(
        r'<details>\s*<summary>📝 이미지 텍스트 내용[^<]*</summary>([\s\S]+?)</details>',
        shorten_details,
        text
    )
    return text


@app.get("/api/guide/attachment/{path:path}")
async def guide_attachment(path: str):
    """Knowledge 문서 첨부파일(이미지 등) 서빙"""
    from fastapi.responses import FileResponse
    target = (GUIDE_BASE / "attachments" / path).resolve()
    if not str(target).startswith(str((GUIDE_BASE / "attachments").resolve())):
        raise HTTPException(403, "forbidden")
    if not target.exists():
        raise HTTPException(404, "not found")
    return FileResponse(str(target))


@app.get("/api/guide/doc")
async def guide_doc(file: str, lang: str = "ko"):
    """특정 Knowledge 문서 전체 내용 반환"""
    docs_dir = GUIDE_BASE / "docs"
    target = (docs_dir / file).resolve()
    if not str(target).startswith(str(docs_dir.resolve())):
        raise HTTPException(403, "forbidden")
    if not target.exists():
        raise HTTPException(404, "not found")
    content = _preprocess_guide_doc(target.read_text(errors="replace"))
    if lang == "en":
        try:
            content = _translate_markdown(content, "en")
        except Exception:
            pass
    return {"file": file, "content": content}


@app.get("/api/guide/report-fails")
async def guide_report_fails(path: str = Query(...)):
    """리포트 경로(파일 또는 디렉토리)에서 FAIL Check ID 추출 후 관련 가이드 반환"""
    import re as _re
    idx = _load_knowledge()
    check_map = idx.get("check_map", {}) if idx else {}

    target = (REPORTS_DIR / path).resolve()
    if not str(target).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(403, "forbidden")

    # 파일이면 해당 파일, 디렉토리면 하위 모든 md, summary.md면 같은 폴더 전체 스캔
    if target.is_dir():
        md_files = list(target.rglob("*.md"))
    elif target.is_file():
        # summary.md인 경우 같은 폴더 전체 스캔
        if target.name == "summary.md":
            md_files = list(target.parent.rglob("*.md"))
        else:
            md_files = [target]
    else:
        raise HTTPException(404, "not found")

    seen = set()
    fails = []
    for md in md_files:
        if md.name in ("diagram.md", "improvement-plan.md", "verify-result.md"):
            continue
        text = md.read_text(errors="replace")
        for line in text.split('\n'):
            if '❌' not in line and ('FAIL' not in line):
                continue
            ids = _re.findall(r'[A-Z]+-[A-Z]+-\d+|[A-Z]+-\d+', line)
            for cid in ids:
                if cid in check_map and check_map[cid] and cid not in seen:
                    seen.add(cid)
                    item_text = _re.sub(r'\|', '', line).strip()[:120]
                    fails.append({
                        "check_id": cid,
                        "description": item_text,
                        "guide_count": len(check_map[cid]),
                        "top_doc": check_map[cid][0]["title"] if check_map[cid] else None,
                    })
    return fails


# ── Chat API ──────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    report_path: Optional[str] = None
    history: list = []
    lang: str = "ko"


def _get_bedrock_client():
    from botocore.credentials import InstanceMetadataProvider, InstanceMetadataFetcher
    import boto3
    provider = InstanceMetadataProvider(iam_role_fetcher=InstanceMetadataFetcher(timeout=1000, num_attempts=2))
    creds = provider.load()
    return boto3.client("bedrock-runtime", region_name="us-east-1",
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.token)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """운영가이드 + 리포트 컨텍스트 기반 질의응답 (Amazon Nova Lite)"""
    import json as _json, sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    try:
        from slack_bot import check_small_talk
        small_talk = check_small_talk(req.question)
        if small_talk:
            async def _st():
                yield {"data": _json.dumps({"text": small_talk})}
                yield {"data": _json.dumps({"done": True})}
            return EventSourceResponse(_st())
    except Exception:
        pass

    idx = _load_knowledge()
    docs_data = idx.get("docs", []) if idx else []

    # 1. Knowledge 인덱스에서 관련 문서 검색 (상위 3개)
    q_lower = req.question.lower()
    keywords = q_lower.split()
    scored = [(sum(1 for kw in keywords if kw in doc["keywords_raw"] + " " + doc["body_preview"].lower()), doc)
              for doc in docs_data]
    top_docs = [d for s, d in sorted(scored, key=lambda x: -x[0]) if s > 0][:3]

    # 2. 리포트 내용 발췌
    report_excerpt = ""
    if req.report_path and REPORTS_DIR.exists():
        rf = (REPORTS_DIR / req.report_path).resolve()
        if str(rf).startswith(str(REPORTS_DIR.resolve())) and rf.exists():
            report_excerpt = rf.read_text(errors="replace")[:3000]

    # 3. 컨텍스트 + 시스템 프롬프트
    knowledge_context = "\n\n".join([
        f"[운영가이드: {d['title']}]\n{d['body_preview'][:800]}" for d in top_docs
    ]) or "(관련 가이드 없음)"

    reply_lang = "Korean" if req.lang == "ko" else "English"
    system_text = f"""You are an AWS ARB (Architecture Review Board) expert assistant.
Answer in {reply_lang}.

Answer priority:
1. If the provided [Operations Guide] or [ARB Report] contains relevant content, present that first and cite the document name.
2. If the provided documents do not cover the question, supplement with AWS official best practices — prefix with "일반적인 Best Practice는:" (Korean) or "General Best Practice:" (English), and cite the AWS service/documentation name (e.g., "AWS RDS User Guide", "AWS Well-Architected Framework").
3. Do not fabricate specific figures or facts not present in the provided report.
4. No greetings or honorifics. Be concise and practical."""

    user_text = f"""질문: {req.question}

--- 참조 운영가이드 ---
{knowledge_context}

--- ARB 점검 리포트 ---
{report_excerpt or '(리포트 미선택)'}"""

    # 4. 대화 히스토리 (Converse API 포맷)
    messages = [{"role": h["role"], "content": [{"text": h["content"]}]}
                for h in req.history[-6:]]
    messages.append({"role": "user", "content": [{"text": user_text}]})

    # 5. Nova Lite 스트리밍
    async def stream_response():
        try:
            client = _get_bedrock_client()
            try:
                resp = client.converse_stream(
                    modelId="amazon.nova-lite-v1:0",
                    system=[{"text": system_text}],
                    messages=messages,
                    inferenceConfig={"maxTokens": 1500},
                )
                for event in resp["stream"]:
                    if "contentBlockDelta" in event:
                        text = event["contentBlockDelta"]["delta"].get("text", "")
                        if text:
                            yield {"data": _json.dumps({"text": text})}
            except Exception:
                resp = client.converse(
                    modelId="amazon.nova-lite-v1:0",
                    system=[{"text": system_text}],
                    messages=messages,
                    inferenceConfig={"maxTokens": 1500},
                )
                text = resp["output"]["message"]["content"][0]["text"]
                for i in range(0, len(text), 30):
                    yield {"data": _json.dumps({"text": text[i:i+30]})}
                    await asyncio.sleep(0.02)
            yield {"data": _json.dumps({"done": True})}
        except Exception as e:
            yield {"data": _json.dumps({"error": str(e)})}

    return EventSourceResponse(stream_response())



# ── Pre-Survey API ────────────────────────────────────────────────────────────
import json as _json

SURVEY_DIR = Path(__file__).parent.parent / "surveys"
SURVEY_DIR.mkdir(parents=True, exist_ok=True)

SURVEY_SCHEMA = {
    "infra_selection": {
        "label": "인프라 선정", "label_en": "Infra Selection", "fields": [
        {"key": "cloud_provider", "label": "Cloud 인프라 선정 (AWS/GCP/Azure/OnPrem/Hybrid)", "label_en": "Cloud Provider (AWS/GCP/Azure/OnPrem/Hybrid)", "type": "select",
         "options": ["AWS", "GCP", "Azure", "On-Prem", "Multi-Cloud", "Hybrid"]},
        {"key": "cost_comparison_done", "label": "인프라별 비용 비교 수행 여부", "label_en": "Cost comparison across infra options", "type": "bool"},
        {"key": "cloud_constraint_reviewed", "label": "Cloud 강점/제약 검토 여부", "label_en": "Cloud strengths/constraints reviewed", "type": "bool"},
    ]},
    "account_setup": {
        "label": "인프라 계정", "label_en": "Account Setup", "fields": [
        {"key": "account_created", "label": "호스팅 계정 생성 완료", "label_en": "Hosting account created", "type": "bool"},
        {"key": "env_separation", "label": "DEV/STG/PROD 계정 분리 여부", "label_en": "DEV/STG/PROD account separation", "type": "select",
         "options": ["분리됨", "일부 분리", "미분리"]},
        {"key": "billing_integrated", "label": "Cloud Billing 계정 통합 여부", "label_en": "Cloud Billing account integrated", "type": "bool"},
    ]},
    "budget": {
        "label": "예산", "label_en": "Budget", "fields": [
        {"key": "hosting_budget_secured", "label": "인프라 호스팅 예산 경영계획 반영 여부", "label_en": "Hosting budget in business plan", "type": "bool"},
        {"key": "ops_staff_budget_secured", "label": "운영 인력 예산 확보 여부", "label_en": "Ops staff budget secured", "type": "bool"},
        {"key": "ops_model", "label": "운영 방식 (DevOps 직접/위탁)", "label_en": "Operations model (DevOps/Outsourced)", "type": "select",
         "options": ["DevOps 직접 운영", "위탁 운영", "혼합"]},
    ]},
    "system_stability": {
        "label": "시스템 안정성", "label_en": "System Stability", "fields": [
        {"key": "api_functional_test_done", "label": "API 기능 검증 테스트 PASS 여부", "label_en": "API functional test passed", "type": "bool"},
        {"key": "performance_test_done", "label": "성능 검증 테스트 PASS 여부", "label_en": "Performance test passed", "type": "bool"},
        {"key": "rto_rpo_defined", "label": "RTO/RPO 수립 여부", "label_en": "RTO/RPO defined", "type": "bool"},
        {"key": "rto_value", "label": "RTO 목표 (분)", "label_en": "RTO target (min)", "type": "text"},
        {"key": "rpo_value", "label": "RPO 목표 (분)", "label_en": "RPO target (min)", "type": "text"},
        {"key": "ha_test_done", "label": "HA 테스트 수행 여부", "label_en": "HA test performed", "type": "bool"},
        {"key": "dr_test_done", "label": "DR 전환 테스트 수행 여부", "label_en": "DR failover test performed", "type": "bool"},
        {"key": "disaster_drill_planned", "label": "DR 훈련 계획 수립 여부", "label_en": "DR drill plan established", "type": "bool"},
    ]},
    "operation": {
        "label": "운영 적합성", "label_en": "Operations", "fields": [
        {"key": "incident_grade_defined", "label": "장애 등급 정의서 수립 여부", "label_en": "Incident severity levels defined", "type": "bool"},
        {"key": "escalation_list_defined", "label": "장애 에스컬레이션/전파 명단 정의 여부", "label_en": "Incident escalation contacts defined", "type": "bool"},
        {"key": "cs_process_ready", "label": "CS 프로세스 및 고객지원 채널 준비 여부", "label_en": "CS process and support channel ready", "type": "bool"},
        {"key": "change_process_established", "label": "시스템 변경 프로세스 수립 여부", "label_en": "Change management process established", "type": "bool"},
        {"key": "ops_tool", "label": "운영 관리 Tool (JIRA 등)", "label_en": "Ops management tool (JIRA etc.)", "type": "text"},
        {"key": "ops_documents_ready", "label": "운영 산출물 준비 여부", "label_en": "Ops documentation ready", "type": "bool"},
        {"key": "admin_implemented", "label": "운영 Admin 구현 여부", "label_en": "Admin console implemented", "type": "bool"},
    ]},
    "service_stability": {
        "label": "서비스 안정성", "label_en": "Service Stability", "fields": [
        {"key": "change_sharing_process", "label": "서비스 변경 계획/결과 공유 프로세스 여부", "label_en": "Change plan/result sharing process", "type": "bool"},
        {"key": "release_manager_assigned", "label": "RM 담당자 지정 및 R&R 정의 여부", "label_en": "Release Manager assigned with R&R", "type": "bool"},
        {"key": "dependency_analysis_doc", "label": "타 서비스 연동/영향도 분석 정의 여부", "label_en": "Service dependency analysis documented", "type": "bool"},
        {"key": "failure_scenario_doc", "label": "장애 시나리오 및 처리 방안 정의 여부", "label_en": "Failure scenarios and handling defined", "type": "bool"},
        {"key": "aging_test_done", "label": "앱 에이징 테스트 수행 여부", "label_en": "App aging test performed", "type": "bool"},
        {"key": "deploy_strategy", "label": "배포 전략 (Blue/Green/Canary 등)", "label_en": "Deployment strategy (Blue/Green/Canary etc.)", "type": "select",
         "options": ["none", "blue-green", "canary", "rolling", "in-place"]},
        {"key": "deploy_monitoring", "label": "점진 배포 모니터링 방안 확보 여부", "label_en": "Progressive deploy monitoring in place", "type": "bool"},
    ]},
    "devops": {
        "label": "DevOps 자동화", "label_en": "DevOps Automation", "fields": [
        {"key": "build_tool", "label": "빌드 시스템 (Jenkins/CodeBuild/GitHub Actions 등)", "label_en": "Build system (Jenkins/CodeBuild/GitHub Actions etc.)", "type": "text"},
        {"key": "build_url", "label": "빌드 시스템 URL", "label_en": "Build system URL", "type": "text"},
        {"key": "deploy_tool", "label": "배포 파이프라인 도구 (ArgoCD/CodeDeploy 등)", "label_en": "Deployment tool (ArgoCD/CodeDeploy etc.)", "type": "text"},
        {"key": "rollback_supported", "label": "빠른 Rollback 지원 여부", "label_en": "Fast rollback supported", "type": "bool"},
        {"key": "image_registry", "label": "이미지 레지스트리 (ECR/DockerHub 등)", "label_en": "Image registry (ECR/DockerHub etc.)", "type": "text"},
        {"key": "image_lifecycle_policy", "label": "이미지 보관 정책 수립 여부", "label_en": "Image lifecycle policy established", "type": "bool"},
    ]},
}


@app.get("/api/survey/schema")
async def get_survey_schema():
    return SURVEY_SCHEMA


@app.get("/api/survey/{account_id}")
async def get_survey(account_id: str):
    survey_file = SURVEY_DIR / f"{account_id}.json"
    if not survey_file.exists():
        return {"account_id": account_id, "data": {}, "submitted_at": None}
    data = _json.loads(survey_file.read_text())
    return data


@app.post("/api/survey/{account_id}")
async def save_survey(account_id: str, body: dict):
    survey_file = SURVEY_DIR / f"{account_id}.json"
    payload = {"account_id": account_id, "data": body, "submitted_at": now_kst().isoformat()}
    survey_file.write_text(_json.dumps(payload, ensure_ascii=False, indent=2))
    return {"status": "saved", "submitted_at": payload["submitted_at"]}


# ── DB Pre-Survey Upload API ──────────────────────────────────────────────────
from fastapi import UploadFile, File as FastAPIFile

DB_PRESUVEY_DIR = Path(__file__).parent.parent / "db-presurveys"
DB_PRESUVEY_DIR.mkdir(parents=True, exist_ok=True)

# pre-survey 파일 위치: database/arb-automation/pre-survey + service-guide/database
PRESUVEY_SOURCES = [
    Path("/opt/web/aiops-arb-kiro/database/arb-automation/pre-survey"),
    Path("/opt/web/aiops-arb-kiro/service-guide/database"),
]

# DB 엔진별 수동 입력 서베이 스키마
DB_MANUAL_SCHEMA = {
    "aurora-mysql": {
        "label": "Aurora MySQL", "label_en": "Aurora MySQL",
        "sections": [
            {
                "key": "account", "label": "계정 관리", "label_en": "Account Management",
                "fields": [
                    {"key": "acc_1person1account", "label": "개인 사용자 계정 1인 1계정 원칙 준수 (공용 계정 사용 금지)", "label_en": "1 person 1 account (no shared accounts)", "type": "bool"},
                    {"key": "acc_admin_unused", "label": "기본 마스터(admin) 계정 서비스 미사용", "label_en": "Default master (admin) account not used for service", "type": "bool"},
                    {"key": "acc_dba_manages", "label": "DB 계정 관리 DBA 담당", "label_en": "DB accounts managed by DBA", "type": "bool"},
                    {"key": "acc_process_doc", "label": "DB 계정 신규/변경/삭제 프로세스 문서 존재", "label_en": "Account change process documented", "type": "bool"},
                    {"key": "acc_perm_doc_updated", "label": "DB 계정 권한 리스트 문서 최신 유지", "label_en": "Account permission list kept up-to-date", "type": "bool"},
                    {"key": "acc_5yr_retention", "label": "DB 계정 내역 5년 보관", "label_en": "Account change history retained for 5 years", "type": "bool"},
                    {"key": "acc_naming_rule", "label": "Instance 네이밍 규칙 준수", "label_en": "Instance naming rule compliant", "type": "bool"},
                ]
            },
            {
                "key": "schema", "label": "스키마 설계", "label_en": "Schema Design",
                "fields": [
                    {"key": "sch_fk_intentional", "label": "FK 미사용 또는 FK 사용이 의도된 설계", "label_en": "No FK, or FK usage is intentional", "type": "bool"},
                    {"key": "sch_procedure_reviewed", "label": "Procedure/Function 제약사항 검토 완료 (없으면 O)", "label_en": "Procedure/Function constraints reviewed (O if none)", "type": "bool"},
                    {"key": "sch_pk_autoincrement", "label": "테이블 PK가 int/bigint + AUTO_INCREMENT 사용", "label_en": "Table PK uses int/bigint + AUTO_INCREMENT", "type": "bool"},
                    {"key": "sch_uk_or_logic_dedup", "label": "중복 방지를 UK 또는 로직단에서 처리", "label_en": "Deduplication handled by UK or application logic", "type": "bool"},
                    {"key": "sch_index_naming", "label": "인덱스 네이밍룰 준수", "label_en": "Index naming rule compliant", "type": "bool"},
                ]
            }
        ]
    },
    "aurora-postgres": {
        "label": "Aurora PostgreSQL", "label_en": "Aurora PostgreSQL",
        "sections": [
            {
                "key": "account", "label": "계정 관리", "label_en": "Account Management",
                "fields": [
                    {"key": "acc_1person1account", "label": "개인 사용자 계정 1인 1계정 원칙 준수 (공용 계정 사용 금지)", "label_en": "1 person 1 account (no shared accounts)", "type": "bool"},
                    {"key": "acc_postgres_unused", "label": "postgres 기본 마스터 계정 서비스 미사용 (관리 목적으로만 사용)", "label_en": "postgres master account not used for service", "type": "bool"},
                    {"key": "acc_dba_manages", "label": "DB 계정 관리 DBA 담당", "label_en": "DB accounts managed by DBA", "type": "bool"},
                    {"key": "acc_process_doc", "label": "DB 계정 신규/변경/삭제 프로세스 문서 존재", "label_en": "Account change process documented", "type": "bool"},
                    {"key": "acc_perm_doc_updated", "label": "DB 계정 권한 리스트 문서 최신 유지", "label_en": "Account permission list kept up-to-date", "type": "bool"},
                    {"key": "acc_5yr_retention", "label": "DB 계정 내역 5년 보관", "label_en": "Account change history retained for 5 years", "type": "bool"},
                    {"key": "acc_naming_rule", "label": "Instance 네이밍 규칙 준수", "label_en": "Instance naming rule compliant", "type": "bool"},
                ]
            },
            {
                "key": "schema", "label": "스키마 설계", "label_en": "Schema Design",
                "fields": [
                    {"key": "sch_fk_intentional", "label": "FK 미사용 또는 FK 사용이 의도된 설계 (성능 영향 검토 완료)", "label_en": "No FK, or FK usage intentional with performance review", "type": "bool"},
                    {"key": "sch_procedure_reviewed", "label": "Function/Procedure 제약사항 검토 완료 (없으면 O)", "label_en": "Function/Procedure constraints reviewed (O if none)", "type": "bool"},
                    {"key": "sch_pk_type", "label": "테이블 PK가 SERIAL/BIGSERIAL/IDENTITY 또는 UUID 사용", "label_en": "Table PK uses SERIAL/BIGSERIAL/IDENTITY or UUID", "type": "bool"},
                    {"key": "sch_uk_or_logic_dedup", "label": "중복 방지를 UK 또는 로직단에서 처리", "label_en": "Deduplication handled by UK or application logic", "type": "bool"},
                    {"key": "sch_index_naming", "label": "인덱스 네이밍룰 준수", "label_en": "Index naming rule compliant", "type": "bool"},
                ]
            }
        ]
    },
    "dynamodb": {
        "label": "DynamoDB", "label_en": "DynamoDB",
        "sections": [
            {
                "key": "table_design", "label": "테이블 설계", "label_en": "Table Design",
                "fields": [
                    {"key": "ddb_design_type", "label": "설계 방식", "label_en": "Design pattern", "type": "select",
                     "options": ["Single Table Design", "Multi Table Design", "혼합"]},
                    {"key": "ddb_pk_cardinality", "label": "파티션 키(PK) 카디널리티가 높은지 검토 완료", "label_en": "Partition key high cardinality reviewed", "type": "bool"},
                    {"key": "ddb_access_patterns_defined", "label": "모든 Read/Write 액세스 패턴 사전 정의 완료", "label_en": "All Read/Write access patterns pre-defined", "type": "bool"},
                    {"key": "ddb_lsi_gsi_based_on_patterns", "label": "LSI/GSI가 실제 액세스 패턴 기반으로 설계됨", "label_en": "LSI/GSI designed based on actual access patterns", "type": "bool"},
                    {"key": "ddb_design_rationale", "label": "Single/Multi Table 설계 방식 선택 근거 명확", "label_en": "Single/Multi Table design rationale documented", "type": "bool"},
                    {"key": "ddb_attr_naming", "label": "어트리뷰트 네이밍 컨벤션 정의 및 일관 적용", "label_en": "Attribute naming convention defined and consistent", "type": "bool"},
                    {"key": "ddb_attr_short_names", "label": "어트리뷰트 이름이 불필요하게 길지 않게 설계", "label_en": "Attribute names are concise", "type": "bool"},
                    {"key": "ddb_schema_doc_submitted", "label": "스키마 모델링 문서 제출", "label_en": "Schema modeling document submitted", "type": "bool"},
                    {"key": "ddb_access_pattern_doc_submitted", "label": "액세스 패턴 정리 문서 제출", "label_en": "Access pattern document submitted", "type": "bool"},
                ]
            },
            {
                "key": "index_design", "label": "인덱스 설계", "label_en": "Index Design",
                "fields": [
                    {"key": "ddb_lsi_vs_gsi_reviewed", "label": "LSI 사용 전 GSI 대체 가능성 검토", "label_en": "Checked if GSI can replace LSI before using LSI", "type": "bool"},
                    {"key": "ddb_lsi_400kb_aware", "label": "LSI 사용 시 아이템 400KB 제한 인지", "label_en": "Aware of 400KB item limit with LSI", "type": "bool"},
                    {"key": "ddb_lsi_10gb_aware", "label": "LSI 사용 시 파티션 컬렉션 10GB 제한 인지", "label_en": "Aware of 10GB partition collection limit with LSI", "type": "bool"},
                    {"key": "ddb_gsi_pk_cardinality", "label": "GSI 파티션 키 카디널리티 검토 완료", "label_en": "GSI partition key cardinality reviewed", "type": "bool"},
                    {"key": "ddb_sparse_index_reviewed", "label": "Sparse Index 패턴 적용 검토 완료", "label_en": "Sparse Index pattern considered", "type": "bool"},
                    {"key": "ddb_gsi_pk_update_aware", "label": "GSI PK 값 변경 시 동작 방식 인지 및 앱 로직 반영", "label_en": "GSI PK update behavior understood and in app logic", "type": "bool"},
                ]
            },
            {
                "key": "capacity_infra", "label": "용량 및 인프라", "label_en": "Capacity & Infrastructure",
                "fields": [
                    {"key": "ddb_partition_limit_aware", "label": "파티션당 처리량 한도 인지 (3,000 RCU / 1,000 WCU)", "label_en": "Aware of per-partition limits (3,000 RCU / 1,000 WCU)", "type": "bool"},
                    {"key": "ddb_ondemand_reserved_aware", "label": "On-Demand 모드에서 Reserved Capacity 구매 불가 인지", "label_en": "On-Demand mode cannot use Reserved Capacity", "type": "bool"},
                    {"key": "ddb_iac_deletion_protection", "label": "IaC에서 테이블 삭제 방지 설정", "label_en": "Table deletion protection in IaC", "type": "bool"},
                    {"key": "ddb_global_tables_reviewed", "label": "Global Tables 사용 시 특성/주의사항 검토 완료", "label_en": "Global Tables reviewed if used (N/A if not)", "type": "select",
                     "options": ["N/A (미사용)", "O (검토완료)", "X (미검토)"]},
                ]
            }
        ]
    },
    "elasticache": {
        "label": "ElastiCache", "label_en": "ElastiCache",
        "sections": [
            {
                "key": "design", "label": "설계 검토", "label_en": "Design Review",
                "fields": [
                    {"key": "ec_data_type_reviewed", "label": "사용 중인 Redis Data Type이 용도에 적합한지 검토 완료", "label_en": "Redis Data Type suitability reviewed", "type": "bool"},
                    {"key": "ec_cache_pattern", "label": "Cache Design Pattern 선택 및 근거 정리", "label_en": "Cache Design Pattern selected with rationale", "type": "select",
                     "options": ["Cache-Aside", "Write-Through", "Write-Behind", "Read-Through", "혼합", "미정"]},
                    {"key": "ec_client_official", "label": "공식 권장 Redis Client 사용", "label_en": "Official recommended Redis client in use", "type": "bool"},
                    {"key": "ec_ttl_defined", "label": "모든 Key에 TTL 정책 정의 완료", "label_en": "TTL policy defined for all keys", "type": "bool"},
                    {"key": "ec_cluster_mode_aware", "label": "Cluster Mode 사용 시 특성 및 제약사항 인지", "label_en": "Cluster Mode constraints understood if enabled", "type": "select",
                     "options": ["N/A (미사용)", "O (인지완료)", "X (미인지)"]},
                    {"key": "ec_naming_rule", "label": "클러스터/Key 네이밍 규칙 준수", "label_en": "Cluster/Key naming rule compliant", "type": "bool"},
                ]
            }
        ]
    }
}

PRESUVEY_SCRIPTS = {
    "aurora-mysql": {
        "label": "Aurora MySQL", "script": "aurora-mysql-survey.sh", "sample": "aurora-mysql-survey-mock.md",
        "description": "Aurora MySQL 클러스터의 계정/권한/스키마/FK/인덱스 등 DB 내부 정보를 수집합니다.",
        "description_en": "Collects DB internal info (accounts, permissions, schema, FK, indexes) from Aurora MySQL cluster.",
        "guide_en": ["Run this script on a DB Bastion host with mysql client installed.",
                     "The script auto-collects DB info and generates a .md file.",
                     "Fill in the white (non-comment) lines, then upload the result."],
    },
    "aurora-postgres": {
        "label": "Aurora PostgreSQL", "script": "aurora-postgres-survey.sh", "sample": "aurora-postgres-pre-survey.md",
        "description": "Aurora PostgreSQL 클러스터의 계정/권한/스키마/인덱스 등 DB 내부 정보를 수집합니다.",
        "description_en": "Collects DB internal info (accounts, permissions, schema, indexes) from Aurora PostgreSQL cluster.",
        "guide_en": ["Run this script on a DB Bastion host with psql client installed.",
                     "The script auto-collects DB info and generates a .md file.",
                     "Fill in the white (non-comment) lines, then upload the result."],
    },
    "dynamodb": {
        "label": "DynamoDB", "script": None, "sample": "dynamodb-pre-survey.md",
        "description": "DynamoDB 테이블의 구조 및 설정 정보를 수집합니다.",
        "description_en": "Collects table structure and configuration info from DynamoDB.",
        "guide_en": ["No script available. Fill in the sample file manually.",
                     "Refer to the sample file format below.",
                     "Upload the completed .md file."],
    },
    "elasticache": {
        "label": "ElastiCache", "script": None, "sample": "elasticache-pre-survey.md",
        "description": "ElastiCache 클러스터의 설정 정보를 수집합니다.",
        "description_en": "Collects configuration info from ElastiCache cluster.",
        "guide_en": ["No script available. Fill in the sample file manually.",
                     "Refer to the sample file format below.",
                     "Upload the completed .md file."],
    },
}

def _find_presurvey_file(filename):
    """여러 소스 폴더에서 파일 검색"""
    for base in PRESUVEY_SOURCES:
        p = base / filename
        if p.exists():
            return p
    return None

PRESUVEY_BASE = PRESUVEY_SOURCES[0]  # 하위 호환

@app.get("/api/db-presurvey/info")
async def db_presurvey_info():
    result = {}
    for key, info in PRESUVEY_SCRIPTS.items():
        header_lines = []
        if info["script"]:
            sp = _find_presurvey_file(info["script"])
            if sp:
                for line in sp.read_text().split("\n"):
                    if line.startswith("#"):
                        header_lines.append(line.lstrip("#").strip())
                    elif line.strip() == "" and header_lines:
                        continue
                    elif not line.startswith("#"):
                        break
        result[key] = {
            "label": info["label"],
            "description": info["description"],
            "description_en": info.get("description_en", info["description"]),
            "guide_en": info.get("guide_en", []),
            "has_script": info["script"] is not None, "script_name": info["script"],
            "header_lines": [l for l in header_lines if l],
            "has_sample": _find_presurvey_file(info["sample"]) is not None if info["sample"] else False,
            "sample_name": info["sample"],
        }
    return result

@app.get("/api/db-presurvey/script/{engine}")
async def download_script(engine: str):
    info = PRESUVEY_SCRIPTS.get(engine)
    if not info or not info["script"]: raise HTTPException(404, "script not found")
    path = _find_presurvey_file(info["script"])
    if not path: raise HTTPException(404, "file not found")
    return {"filename": info["script"], "content": path.read_text()}

@app.get("/api/db-presurvey/sample/{engine}")
async def download_sample(engine: str):
    info = PRESUVEY_SCRIPTS.get(engine)
    if not info or not info["sample"]: raise HTTPException(404, "sample not found")
    path = _find_presurvey_file(info["sample"])
    if not path: raise HTTPException(404, "file not found")
    return {"filename": info["sample"], "content": path.read_text()}

@app.post("/api/db-presurvey/upload/{account_id}/{engine}")
async def upload_presurvey(account_id: str, engine: str, file: UploadFile = FastAPIFile(...)):
    import datetime as _dt
    if not account_id.isdigit() or len(account_id) != 12: raise HTTPException(400, "invalid account_id")
    content = await file.read()
    dest_dir = DB_PRESUVEY_DIR / account_id; dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_kst().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{engine}-{timestamp}.md"; dest.write_bytes(content)
    return {"status": "uploaded", "path": str(dest.relative_to(DB_PRESUVEY_DIR)), "size": len(content)}

@app.get("/api/db-presurvey/files/{account_id}")
async def list_presurvey_files(account_id: str):
    import datetime as _dt2
    acct_dir = DB_PRESUVEY_DIR / account_id
    if not acct_dir.exists(): return []
    files = []
    for f in sorted(acct_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        mtime = datetime.fromtimestamp(f.stat().st_mtime) + _dt2.timedelta(hours=9)
        files.append({"name": f.name, "size": f.stat().st_size, "uploaded_at": mtime.isoformat()})
    return files


# ── DB Manual Survey API ──────────────────────────────────────────────────────
DB_MANUAL_SURVEY_DIR = Path(__file__).parent.parent / "db-manual-surveys"
DB_MANUAL_SURVEY_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/api/db-manual-survey/schema")
async def get_db_manual_schema():
    return DB_MANUAL_SCHEMA

@app.get("/api/db-manual-survey/{account_id}/{engine}")
async def get_db_manual_survey(account_id: str, engine: str):
    f = DB_MANUAL_SURVEY_DIR / account_id / f"{engine}.json"
    if not f.exists():
        return {"data": {}, "submitted_at": None}
    import json as _json
    data = _json.loads(f.read_text())
    return data

@app.post("/api/db-manual-survey/{account_id}/{engine}")
async def save_db_manual_survey(account_id: str, engine: str, request: Request):
    import json as _json
    answers = await request.json()
    acct_dir = DB_MANUAL_SURVEY_DIR / account_id
    acct_dir.mkdir(parents=True, exist_ok=True)
    import datetime as _dt3
    kst_now = (datetime.utcnow() + _dt3.timedelta(hours=9)).isoformat()
    payload = {"data": answers, "submitted_at": kst_now}
    (acct_dir / f"{engine}.json").write_text(_json.dumps(payload, ensure_ascii=False, indent=2))
    return {"submitted_at": kst_now}

# Serve manual docs (before React catch-all)
docs_dir = Path(__file__).parent.parent.parent / "docs"
if docs_dir.exists():
    app.mount("/docs", StaticFiles(directory=str(docs_dir)), name="docs")

# Serve React build
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
