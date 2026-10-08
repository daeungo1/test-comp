"""
ARB Knowledge Index Builder
645개 md 파일에서 키워드 인덱스 생성
"""
import json, re
from pathlib import Path

DOCS_DIR = Path("/home/noboru78.lee/repo/aiops-arb-guide/OPSPROCESS_MD/docs")
OUT_FILE = Path("/home/noboru78.lee/repo/aiops-arb-kiro/web/backend/knowledge_index.json")

def extract_meta(text: str, filename: str) -> dict:
    # breadcrumb 추출
    breadcrumb = []
    m = re.search(r'breadcrumb:\s*\n((?:\s*-.*\n)+)', text[:600])
    if m:
        breadcrumb = [x.strip().strip("'\"") for x in re.findall(r'-\s*(.+)', m.group(1))]

    # 제목 추출 (frontmatter title 또는 첫 H1)
    title_m = re.search(r"title:\s*['\"]?(.+?)['\"]?\s*\n", text[:300])
    if not title_m:
        title_m = re.search(r'^#\s+(.+)', text, re.MULTILINE)
    title = title_m.group(1).strip(" '\"") if title_m else filename

    # 본문 텍스트 (frontmatter 제거, 첫 1500자)
    body = re.sub(r'^---[\s\S]+?---\n', '', text, count=1).strip()
    # 헤더들만 추출 (키워드 풍부)
    headers = re.findall(r'^#+\s+(.+)', body, re.MULTILINE)
    body_preview = body[:1500]

    # 핵심 키워드 (파일명 + 제목 + 헤더에서 추출)
    raw = f"{filename} {title} {' '.join(headers[:10])}"
    raw_lower = raw.lower()

    return {
        "file": filename,
        "title": title,
        "breadcrumb": breadcrumb,
        "headers": headers[:15],
        "body_preview": body_preview,
        "keywords_raw": raw_lower,
    }

# ARB Check ID → 검색 키워드 매핑
CHECK_KEYWORDS = {
    # Architecture
    "ARCH-005": ["multi region", "글로벌", "global table", "cross region"],
    "ARCH-010": ["모니터링", "monitoring", "cloudwatch", "alarm"],
    "ARCH-011": ["multi-az", "multi az", "고가용성", "ha", "단일 az"],
    "ARCH-012": ["vpc", "네트워크"],
    "ARCH-013": ["subnet", "public", "private", "서브넷"],
    "ARCH-014": ["auto scaling", "asg", "autoscaling"],
    "ARCH-015": ["scaling policy", "스케일링"],
    "ARCH-019": ["컨테이너", "docker", "ecr", "image"],
    "ARCH-022": ["x-ray", "추적", "tracing", "jaeger"],
    "ARCH-023": ["circuit breaker", "마이크로서비스", "장애 격리"],
    "ARCH-026": ["eks", "ecs", "kubernetes", "오케스트레이션"],
    "ARCH-027": ["ha", "고가용성", "multi-az"],
    "ARCH-028": ["spof", "단일장애점", "이중화"],
    "ARCH-029": ["auto scaling", "트래픽", "급증"],
    "ARCH-031": ["dr", "disaster recovery", "복구"],
    # Operation
    "OPS-002": ["sns", "알림", "에스컬레이션", "notification"],
    "OPS-006": ["dashboard", "대시보드", "모니터링"],
    "OPS-007": ["alarm", "알람", "임계값", "threshold"],
    "OPS-011": ["backup", "백업", "보관"],
    "OPS-012": ["backup", "백업", "retention"],
    "OPS-013": ["backup", "백업", "스냅샷"],
    # System Stability
    "SYS-001": ["성능 테스트", "performance test", "부하 테스트"],
    "SYS-002": ["aging", "에이징", "성능"],
    "SYS-003": ["ha test", "failover", "ha 테스트"],
    "SYS-004": ["dr", "disaster recovery", "복구 테스트"],
    # DevOps
    "DEV-001": ["terraform", "iac", "infrastructure as code"],
    "DEV-005": ["ci", "빌드", "build", "codebuild"],
    "DEV-011": ["pipeline", "cd", "배포", "deploy"],
    "DEV-012": ["rollback", "롤백"],
    # DB Common
    "COM-BR-001": ["backup", "백업", "retention"],
    "COM-BR-002": ["deletion protection", "삭제 방지"],
    "COM-NI-001": ["망분리", "subnet", "네트워크"],
    "COM-AC-001": ["sbc", "접근", "access control"],
    "COM-MON-001": ["cloudwatch", "모니터링", "alarm"],
    # Aurora MySQL
    "AUR-MY-003": ["parameter", "파라미터", "mysql"],
    "AUR-MY-006": ["password", "비밀번호", "validate_password"],
    "AUR-MON-003": ["log", "로그", "export", "cloudwatch"],
    # RDS
    "RDS-HA-001": ["multi-az", "rds", "failover"],
    "RDS-SEC-002": ["port", "포트"],
    # DynamoDB
    "DDB-SEC-002": ["iam", "policy", "resource", "와일드카드"],
    "DDB-SEC-004": ["vpc endpoint", "dynamodb endpoint"],
}

def build_index():
    index = []
    for f in sorted(DOCS_DIR.glob("*.md")):
        text = f.read_text(errors="replace")
        meta = extract_meta(text, f.name)
        index.append(meta)
    print(f"인덱스 생성: {len(index)}개 문서")

    # Check ID별 관련 문서 사전 계산
    check_map = {}
    for check_id, keywords in CHECK_KEYWORDS.items():
        matches = []
        for doc in index:
            score = 0
            kw_raw = doc["keywords_raw"]
            body = doc["body_preview"].lower()
            search_text = kw_raw + " " + body
            for kw in keywords:
                if kw.lower() in search_text:
                    score += 1
            if score > 0:
                matches.append({
                    "file": doc["file"],
                    "title": doc["title"],
                    "score": score,
                    "breadcrumb": doc["breadcrumb"],
                    "body_preview": doc["body_preview"][:800],
                })
        # 상위 5개만
        matches.sort(key=lambda x: -x["score"])
        check_map[check_id] = matches[:5]

    result = {"docs": index, "check_map": check_map}
    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"저장: {OUT_FILE}")

    # 샘플 확인
    for cid in ["ARCH-011", "OPS-011", "COM-BR-001"]:
        hits = check_map.get(cid, [])
        print(f"\n{cid}: {len(hits)}개 매칭")
        for h in hits[:2]:
            print(f"  [{h['score']}] {h['title']}")

if __name__ == "__main__":
    build_index()
