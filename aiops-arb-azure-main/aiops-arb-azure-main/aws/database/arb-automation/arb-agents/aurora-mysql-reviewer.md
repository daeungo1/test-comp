# Aurora MySQL ARB Reviewer Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
AWS Aurora MySQL 클러스터의 ARB 검증을 수행합니다.
Aurora PostgreSQL은 제외합니다.

## 입력
- region
- 대상 Aurora MySQL 클러스터 목록 (JSON — `describe-db-clusters` 응답)
- `arb-checklist/common.md` 내용
- `arb-checklist/aurora-mysql.md` 내용
- 사전 조사 파일 (아래 순서로 결정):
  1. `arb-config.md`의 `Pre-Survey > Aurora MySQL > file` 값이 있으면 해당 파일 사용
  2. 없으면 `pre-survey/aurora-mysql*.md` 패턴으로 탐색
     - 1개: 자동 선택
     - 2개 이상: 사용자에게 선택 요청
     - 0개: 사전 조사 없이 진행 (`auto: false` 항목은 N/A 처리)

## 수행 절차

### 1단계: 벌크 조회 (리전당 1회)

아래 명령어를 리전당 한 번씩 호출하여 결과를 저장합니다. 이후 단계에서 재사용합니다.
리소스 존재 여부 확인은 공통 규칙(`arb-agents/common-agent-rules.md`) 0단계를 따릅니다.

| 명령어 | 저장 변수 | 사용 항목 |
|--------|----------|----------|
| `aws rds describe-db-clusters --filters Name=engine,Values=aurora-mysql --region {region}` | `CLUSTERS` | 전체 클러스터 기본 정보 |
| `aws rds describe-global-clusters --region {region}` | `GLOBAL_CLUSTERS` | AURMY-HA-003 |
| `aws ec2 describe-vpcs --region {region}` | `VPCS` | AURMY-NET-001 |

### 2단계: 클러스터별 추가 조회

`CLUSTERS`의 각 클러스터에 대해 아래 명령어를 호출합니다.

- `aws rds describe-db-instances --filters Name=db-cluster-id,Values={cluster-id} --region {region}`
- `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {param-group-name} --region {region}`
- `aws rds describe-db-cluster-snapshots --db-cluster-identifier {cluster-id} --region {region}`
- `aws rds describe-pending-maintenance-actions --resource-identifier {cluster-arn} --region {region}`

> 동일 Cluster Parameter Group을 공유하는 클러스터가 여러 개여도 **1회만 조회**합니다.

### 3단계: 체크리스트 검증

수집된 데이터를 기반으로 common.md + aurora-mysql.md의 모든 항목을 검증합니다.

### 4단계: 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | AWS CLI 응답에서 기준 충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준에 부합 |
| ❌ FAIL | AWS CLI 응답에서 기준 미충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준 미충족 |
| N/A | 해당 구성에 적용되지 않는 항목, 또는 사전 조사 파일이 없어 `auto: false` 항목을 판정할 수 없는 경우 (사유 명시) |

#### `auto: false` 항목 판정 방법

사전 조사 파일의 각 섹션은 아래 구조로 되어 있습니다:

```
# [AURMY-ACC-001 + AURMY-ACC-004] ...   ← Check ID가 포함된 섹션 헤더 (주석)
# ...                                ← 자동 조회 결과 (주석, 읽기 전용)
#
# -- 입력 ---
# ...

    항목명 : O          ← 흰색 줄, 개발팀이 작성한 O/X 값
    비고   : ...        ← 흰색 줄, 추가 설명
```

**파싱 규칙:**
1. `# [AURMY-XXX-NNN]` 패턴으로 섹션을 찾아 해당 Check ID 특정
2. 해당 섹션의 흰색 줄(주석이 아닌 줄)에서 `: O` 또는 `: X` 값 추출
3. `비고 :` 줄이 있으면 `#` 앞까지의 값을 추출하여 상세 컬럼에 포함
4. 판정:
   - 모든 입력값이 `O` → PASS
   - 하나라도 `X` → FAIL (비고가 있으면 상세 컬럼에 표시)
   - 입력값이 비어있거나 `<<FILL>>` 그대로 → N/A (미작성)

**ACC-001 + ACC-004 합산 섹션 처리:**
- `ACCOUNT :` 로 시작하는 줄에서 `| O |` 또는 `| X |` 추출
- 하나라도 `X` 이면 해당 Check ID FAIL

**자동 조회 결과가 포함된 항목 (ACC-003, SCH-001, SCH-002, SCH-003):**
- 조회 결과가 이미 판정 가능한 경우 (예: FK 없음 → SCH-001 PASS) 흰색 입력란 없이 자동 판정
- 조회 결과에 WARN이 있는 경우 흰색 입력란의 O/X로 최종 판정

## 출력 규칙

공통 규칙(`arb-agents/common-agent-rules.md`)을 따릅니다.
아래는 Aurora MySQL 특화 사항입니다.

### 리소스 단위
- 리소스 단위: 클러스터(cluster)
- 리소스 식별자: `DBClusterIdentifier`

### 섹션 구성
각 클러스터별 출력은 Common Checks → Aurora MySQL Checks 순으로 작성합니다.

### N/A 처리 명시
N/A 항목은 결과 컬럼에 `N/A`로 표시하고 상세 컬럼에 사유를 명시합니다.

### 엔진 버전 EOL 표기 규칙 (AURMY-HA-005)
- 지원 종료(EOL) 정보는 **검증 대상 버전 기준으로만** 표기합니다. 검증 대상보다 낮은 메이저 라인(예: v2 = MySQL 5.7 호환)의 EOL은 v3 사용 시 오해를 유발하므로 표기하지 않습니다.
- Aurora MySQL 버전(예: `3.08.0`)은 호환 community MySQL 버전(예: 8.0)을 함께 표기합니다. 예: `Aurora MySQL 3.08.0 (MySQL 8.0 호환)`
- 검증 대상 마이너 버전에 대해 다음을 구분하여 명시합니다.
  1. 사용 중인 메이저 라인(Aurora MySQL v3 / MySQL 8.0)의 표준 지원 종료일
  2. 사용 중인 마이너 버전(예: 3.08.*) 자체의 표준 지원 종료일
  3. 해당 마이너의 LTS 여부 및 같은 메이저 라인 LTS 버전의 종료일
- non-LTS 마이너 버전은 LTS/메이저보다 표준 지원 종료일이 빠를 수 있으므로, 마이너 종료일을 별도 명시하여 "메이저/LTS EOL까지 여유 있다"는 오해를 방지합니다. non-LTS 사용 시 LTS 전환 권고를 함께 안내합니다.
- 날짜 조회: AWS Aurora MySQL Release Calendar(https://docs.aws.amazon.com/AmazonRDS/latest/AuroraMySQLReleaseNotes/auroramysql-release-calendar.html) 또는 `aws rds describe-db-engine-versions --engine aurora-mysql --include-all`, 메이저는 `aws rds describe-db-major-engine-versions --engine aurora-mysql`
- 리포트 참고 표 예시 (검증 대상 버전만 포함):

  | 구분 | 버전 | LTS 여부 | 표준 지원 종료일 |
  |------|------|---------|-----------------|
  | 사용 중인 마이너 버전 | Aurora MySQL 3.08.* (MySQL 8.0) | non-LTS | {조회값} |
  | 같은 메이저 라인 LTS | Aurora MySQL {LTS버전} | LTS | {조회값} |
  | 사용 중인 메이저 라인 | Aurora MySQL v3 (MySQL 8.0) | - | {조회값} |

## 리소스 요약 정보 (상세 리포트 헤더)
```
Engine: aurora-mysql | Instances: {count} | Region: {region}
```

## 출력 파일명
`arb-reports/{service_name}/{region}/{YYYY-MM-DD}/aurora-mysql.md`
