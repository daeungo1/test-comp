"""
ARB Slack Bot — Socket Mode
- 일반 질의: Knowledge 인덱스 + Bedrock Nova Lite RAG
- 점검 요청: kiro-cli arb-orchestrator 비동기 호출
"""
import os, sys, json, re, asyncio, subprocess, threading
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent
BACKEND_DIR = REPO_DIR / "web" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

env_file = Path(__file__).parent.parent / ".env.slack"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

app = App(token=SLACK_BOT_TOKEN)

# ── 점검 요청 키워드 ────────────────────────────────────────────────────────
def is_inspection_request(text: str) -> bool:
    """실제 점검 요청인지 판별 — 12자리 계정 ID 필수 + 명시적 실행 의도"""
    lower = text.lower()

    # 계정 ID(12자리)가 없으면 무조건 일반 질의
    has_account = bool(re.search(r'\b\d{12}\b', text))
    if not has_account:
        return False

    # 조회/질의 키워드가 있으면 점검 아님 (결과 확인, 가이드 질문 등)
    query_keywords = ['결과', '리포트', '보여', '알려', '어디야', '뭐야', '어때', '요약',
                      '확인해', '무엇', '어떻게', '방법', '의뢰', '가이드', '?', '？']
    if any(kw in lower for kw in query_keywords):
        return False

    # 계정 ID + 명시적 실행 의도
    action_keywords = ['점검해줘', '점검 요청', '점검해', '점검 시작', 'arb 점검', 'inspect', 'review 해줘']
    return any(kw in lower for kw in action_keywords)


# ── Knowledge 인덱스 ────────────────────────────────────────────────────────
_INDEX = None
def load_index():
    global _INDEX
    if _INDEX is None:
        idx_path = BACKEND_DIR / "knowledge_index.json"
        if idx_path.exists():
            _INDEX = json.loads(idx_path.read_text())
    return _INDEX


def md_to_slack(text: str) -> str:
    """마크다운 → Slack mrkdwn 변환"""
    import re
    # 헤더 → 굵게
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # **굵게** → *굵게*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # _이탤릭_ 유지
    # - 목록 → • 목록
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    # 수평선 제거
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    # 링크 [텍스트](url) → <url|텍스트>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)
    return text.strip()


def get_bedrock_client():
    from botocore.credentials import InstanceMetadataProvider, InstanceMetadataFetcher
    import boto3
    provider = InstanceMetadataProvider(iam_role_fetcher=InstanceMetadataFetcher(timeout=1000, num_attempts=2))
    creds = provider.load()
    return boto3.client("bedrock-runtime", region_name="us-east-1",
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.token)


# ── RAG 답변 ────────────────────────────────────────────────────────────────
REPORTS_DIR = Path(__file__).parent.parent.parent / "arb-reports"

# 일상 대화 패턴 → 간단 응답 (RAG 불필요)
_SMALL_TALK = {
    "greeting": {
        "patterns": ["안녕", "hello", "hi ", "반가워", "방가"],
        "ko": "안녕하세요! ARB 자동화 어시스턴트입니다.\n무엇을 도와드릴까요?\n\n💡 사용 예시:\n• `ARB가 뭐야?` — 시스템 소개\n• `Multi-AZ 구성 방법` — 기술 가이드\n• `myservice 123456789012 점검해줘` — ARB 점검 요청",
        "en": "Hello! I'm the ARB automation assistant.\nHow can I help you?\n\n💡 Examples:\n• `What is ARB?` — System intro\n• `Multi-AZ configuration guide` — Technical guide\n• `myservice 123456789012 inspect` — ARB inspection request",
    },
    "what_can_you_do": {
        "patterns": ["어떤 일", "어떤일", "뭐해", "뭐 해", "무슨 일", "무슨일", "what do you", "what can you", "what are you"],
        "ko": "저는 AWS 인프라 ARB(Architecture Review Board) 자동화 어시스턴트입니다.\n\n✅ 할 수 있는 것:\n• ARB 체크리스트 기반 인프라 자동 점검 (인프라 75항목 + DB 214항목)\n• 점검 결과 리포트 분석 및 개선 방향 안내\n• 내부 운영 가이드(645개 문서) 기반 기술 질의응답\n• 점검 이력 관리 및 FAIL 추이 대시보드\n\n점검 요청: `서비스명 계정ID 리전 점검해줘`",
        "en": "I'm an AWS ARB (Architecture Review Board) automation assistant.\n\n✅ What I can do:\n• Auto-inspect infrastructure based on ARB checklists (75 infra + 214 DB items)\n• Analyze inspection reports and recommend improvements\n• Answer technical questions based on internal ops guide (645 docs)\n• Manage inspection history and FAIL trend dashboard\n\nTo request inspection: `servicename accountID region inspect`",
    },
    "can_inspect": {
        "patterns": ["점검 가능", "점검가능", "can you inspect", "점검 할 수 있", "점검해줄 수"],
        "ko": "네, 가능합니다! AWS 인프라를 ARB 체크리스트 기준으로 자동 점검합니다.\n\n점검 요청 방법:\n`서비스명 계정ID 리전 점검해줘`\n예) `myservice 123456789012 ap-northeast-2 점검해줘`\n\n완료까지 30~60분 소요됩니다.",
        "en": "Yes! I can auto-inspect AWS infrastructure based on ARB checklists.\n\nHow to request:\n`servicename accountID region inspect`\nExample: `myservice 123456789012 ap-northeast-2 inspect`\n\nTakes 30~60 minutes to complete.",
    },
    "how_to_inspect": {
        "patterns": ["점검은 어떻게", "점검 어떻게", "점검 방법", "의뢰 방법", "의뢰는 어떻게", "어떻게 하면", "어떤식으로", "어떤 식으로", "점검 요청", "how to inspect", "how to request"],
        "ko": "ARB 점검 의뢰 방법:\n\n`서비스명 계정ID 리전 점검해줘`\n예) `myservice 123456789012 ap-northeast-2 점검해줘`\n\n• 리전 생략 시 전체 리전 자동 탐지\n• 완료까지 30~60분 소요\n• 완료 후 Slack으로 결과 전송 + Web UI 히스토리 기록",
        "en": "How to request ARB inspection:\n\n`servicename accountID region inspect`\nExample: `myservice 123456789012 ap-northeast-2 inspect`\n\n• Omit region for auto-detect all regions\n• Takes 30~60 minutes\n• Results sent to Slack + recorded in Web UI history",
    },
}

def check_small_talk(text: str) -> str:
    """일상 대화 감지 후 템플릿 응답 반환. 없으면 빈 문자열."""
    lower = text.lower().strip()
    is_en = not any(ord(c) > 127 for c in text)

    # small talk 패턴 매칭
    for key, data in _SMALL_TALK.items():
        if any(p in lower for p in data["patterns"]):
            return data["en"] if is_en else data["ko"]

    # ARB/AWS/인프라와 무관한 질문 감지 → 범위 안내
    arb_keywords = ['arb', 'aws', '인프라', '점검', '리포트', 'rds', 'ec2', 'eks', 's3',
                    'multi-az', '백업', '모니터링', '보안', '아키텍처', '서버', '클라우드',
                    'cloudwatch', 'vpc', 'iam', 'backup', 'inspect', 'architecture',
                    '가이드', '체크리스트', '개선', 'fail', 'pass', '서비스']
    if not any(kw in lower for kw in arb_keywords):
        if is_en:
            return "ARB Assistant only handles AWS infrastructure inspection and related guidance.\nFor other topics, please use a general assistant."
        return "ARB 점검 범위를 벗어나는 질문에는 답드릴 수 없습니다.\nAWS 인프라 점검, 운영 가이드 조회, ARB 관련 질문을 해주세요."

    return ""


def find_recent_report(account_id: str) -> str:
    """계정 ID와 연관된 가장 최근 리포트 디렉토리에서 summary.md 내용 반환"""
    if not REPORTS_DIR.exists():
        return ""
    candidates = []
    for summary in REPORTS_DIR.rglob("summary.md"):
        try:
            content = summary.read_text(errors="replace")
            if account_id in content:
                candidates.append((summary.stat().st_mtime, summary))
        except Exception:
            pass
    if not candidates:
        return ""
    _, latest = max(candidates, key=lambda x: x[0])
    return latest.read_text(errors="replace")[:4000]


def rag_answer(question: str) -> str:
    # 일상 대화는 RAG 없이 즉시 응답
    small_talk = check_small_talk(question)
    if small_talk:
        return small_talk

    idx = load_index()
    docs_data = idx.get("docs", []) if idx else []

    keywords = question.lower().split()
    scored = [(sum(1 for kw in keywords if kw in doc["keywords_raw"] + " " + doc["body_preview"].lower()), doc)
              for doc in docs_data]
    top_docs = [d for s, d in sorted(scored, key=lambda x: -x[0]) if s > 0][:3]

    knowledge_context = "\n\n".join([
        f"[운영가이드: {d['title']}]\n{d['body_preview'][:800]}"
        for d in top_docs
    ]) or "(관련 가이드 없음)"

    # 계정 ID가 언급되면 최근 리포트 자동 포함
    import re as _re
    account_match = _re.search(r'\b(\d{12})\b', question)
    report_context = ""
    if account_match:
        report_context = find_recent_report(account_match.group(1))

    system_text = """You are an AWS ARB (Architecture Review Board) expert assistant.
Detect the language of the question and reply in the same language.

Answer priority:
1. If the provided [Operations Guide] or [ARB Report] contains relevant content, present that first and cite the document name.
2. If the provided documents do not cover the question, supplement with AWS official best practices — prefix with "일반적인 Best Practice는:" (Korean) or "General Best Practice:" (English), and cite the AWS service/documentation name (e.g., "AWS RDS User Guide", "AWS Well-Architected Framework").
3. Do not fabricate specific figures or facts not present in the provided report.
4. No greetings or honorifics. Be concise and Slack-friendly."""

    user_text = f"""질문: {question}

--- 참조 운영가이드 ---
{knowledge_context}

--- ARB 점검 리포트 ---
{report_context if report_context else "(리포트 없음)"}"""

    try:
        client = get_bedrock_client()
        resp = client.converse(
            modelId="amazon.nova-lite-v1:0",
            system=[{"text": system_text}],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig={"maxTokens": 1200},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"오류: {e}"


# ── DB 연동 ─────────────────────────────────────────────────────────────────
import sqlite3 as _sqlite3, uuid
from datetime import datetime, timezone, timedelta
_KST = timezone(timedelta(hours=9))
def _now_kst(): return datetime.now(_KST).replace(tzinfo=None)

DB_PATH = REPO_DIR / "web" / "arb.db"

def db_create_job(job_id, service_name, account_id, region, prompt):
    with _sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO jobs (job_id,service_name,account_id,region,prompt,status,created_at,started_at) VALUES (?,?,?,?,?,?,?,?)",
            (job_id, service_name, account_id, region, prompt, "running",
             _now_kst().isoformat(), _now_kst().isoformat())
        )

def db_finish_job(job_id, status, log=""):
    with _sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE jobs SET status=?, finished_at=?, full_log=? WHERE job_id=?",
            (status, _now_kst().isoformat(), log[:50000], job_id)
        )

def parse_inspection_params(text: str) -> dict:
    account = re.search(r'\b(\d{12})\b', text)
    region = re.search(r'\b(ap-northeast-[12]|ap-southeast-[12]|us-east-[12]|us-west-[12]|eu-west-[123]|eu-central-1|ca-central-1|ap-south-1)\b', text, re.I)

    # 서비스명: 불필요한 토큰 제거 (단어 단위 정확 매칭)
    service = text
    service = re.sub(r'\b\d{12}\b', '', service)
    service = re.sub(r'\b(ap-northeast-[12]|ap-southeast-[12]|us-east-[12]|us-west-[12]|eu-west-[12])\b', '', service, flags=re.I)
    # 불필요 키워드 — 단어 경계 기반 제거 (부분 매칭 방지)
    noise_words = [
        r'\bID\s*:\s*', r'\b서비스\b', r'\b계정\b', r'\b계정에\b', r'\b대해\b', r'\b전체\b',
        r'\b리전\b', r'\b모든\b', r'\b자동\b', r'\b탐지\b', r'\b주요\b', r'\bDB영역\b',
        r'\b전체리전\b', r'\b모든리전\b', r'\barb\b', r'\b점검해줘\b', r'\b점검해\b',
        r'\b점검\s*요청\b', r'\b점검\s*시작\b', r'\barb\s*점검\b', r'\b점검\b',
        r'\b해줘\b', r'\b요청\b', r'\b검토\b', r'\b리뷰\b', r'\bauto\b',
        r'\binspect\b', r'\breview\b', r'\b서울\b', r'\b부산\b',
    ]
    for p in noise_words:
        service = re.sub(p, '', service, flags=re.I)
    service = re.sub(r"['\"\(\)\[\]:]+", '', service)
    service = re.sub(r'\b(에|의|을|를|이|가|은|는|으로|로|에서|과|와|및|에서의)\b', '', service)
    service = re.sub(r'\s+', ' ', service).strip()

    # 전체 리전 키워드 감지 → auto
    auto_keywords = ['전체 리전', '전체리전', '모든 리전', '모든리전', 'all region', 'all-region', 'auto']
    lower = text.lower()
    if any(kw in lower for kw in auto_keywords) or not region:
        detected_region = "auto"
    else:
        detected_region = region.group(1)

    return {
        "service_name": service[:50] if service else "unknown",
        "account_id": account.group(1) if account else "unknown",
        "region": detected_region,
    }


# ── arb-orchestrator 점검 (백그라운드) ──────────────────────────────────────
def run_inspection(question: str, say_fn):
    """별도 스레드에서 kiro-cli 실행 (tmpfile 방식 — 파이프 버퍼 포화 방지)"""
    import tempfile, time as _time
    params = parse_inspection_params(question)
    job_id = str(uuid.uuid4())
    if params['region'] == 'auto':
        prompt = f"{params['service_name']} 환경 ({params['account_id']}) ap-northeast-2 리전 ARB 점검"
    else:
        prompt = f"{params['service_name']} 환경 ({params['account_id']}) {params['region']} 리전 ARB 점검"

    try:
        db_create_job(job_id, params['service_name'], params['account_id'], params['region'], prompt)
    except Exception:
        pass

    say_fn(f"🔄 *ARB 점검 시작*\n• 서비스: {params['service_name']}\n• 계정: {params['account_id']}\n• 리전: {params['region']}\n\n완료까지 30~60분 소요됩니다.")

    tmp = tempfile.NamedTemporaryFile(mode='wb', suffix='.log', delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        proc_start = _time.time()
        with open(tmp_path, 'wb') as out_f:
            proc = subprocess.Popen(
                ["kiro-cli", "chat", "--agent", "arb-orchestrator"],
                stdin=subprocess.PIPE, stdout=out_f, stderr=out_f,
                cwd=str(REPO_DIR)
            )
            proc.stdin.write((prompt + "\n").encode())
            proc.stdin.close()

            # improvement-plan.md 생성 후 5분 타이머 (diagram/improvement 완성 보장)
            trigger_time = None
            while True:
                _time.sleep(2)
                if proc.poll() is not None:
                    break
                if trigger_time is None:
                    for md in Path(REPO_DIR / "arb-reports").rglob("improvement-plan.md"):
                        if md.stat().st_mtime >= proc_start:
                            trigger_time = _time.time()
                            break
                if trigger_time and (_time.time() - trigger_time) > 300:
                    proc.kill()
                    break
                if _time.time() - proc_start > 5400:  # 최대 90분
                    proc.kill()
                    break

        output = open(tmp_path, errors='replace').read()
        output = re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", output)
        summary = output[-2000:] if len(output) > 2000 else output
        db_finish_job(job_id, "done", output)
        say_fn(f"✅ *ARB 점검 완료*\n\n{md_to_slack(summary[-1500:])}\n\n📄 상세 리포트: <https://arb.cloud-aiops.com|Web UI 리포트 탭>")
    except Exception as e:
        db_finish_job(job_id, "error", str(e))
        say_fn(f"❌ 점검 중 오류: {e}")
    finally:
        import os
        try: os.unlink(tmp_path)
        except Exception: pass


# ── 메시지 처리 ─────────────────────────────────────────────────────────────
def handle_message(text: str, say):
    text = text.strip()
    if not text:
        say("안녕하세요! ARB 운영 가이드에 대해 질문하거나 점검을 요청하세요.\n\n💡 예시:\n• `ARB가 뭐야?`\n• `Multi-AZ 구성 방법 알려줘`\n• `spay.global.dev 764668829134 ap-northeast-2 점검해줘`")
        return

    if is_inspection_request(text):
        # 백그라운드 스레드에서 점검 실행
        t = threading.Thread(target=run_inspection, args=(text, say), daemon=True)
        t.start()
    else:
        answer = rag_answer(text)
        say(f"📖 *답변*\n\n{md_to_slack(answer)}")


@app.event("app_mention")
def handle_mention(event, say):
    question = re.sub(r"<@[^>]+>", "", event["text"]).strip()
    handle_message(question, say)


@app.event("message")
def handle_dm(message, say):
    if message.get("channel_type") != "im":
        return
    if message.get("bot_id") or message.get("subtype"):
        return
    handle_message(message.get("text", ""), say)


if __name__ == "__main__":
    print("ARB Slack Bot 시작 (Socket Mode)...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
