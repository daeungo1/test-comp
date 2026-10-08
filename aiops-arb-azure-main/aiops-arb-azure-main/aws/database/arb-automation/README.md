# ARB Database Review Automation

AWS Database의 설계 안전성과 고가용성을 자동 검증하는 Kiro Agent 기반 ARB(Architecture Review Board) 자동화 도구입니다.

## 요약

- **코드 없이 MD 파일만으로 동작** — 설정, 체크리스트, 에이전트 행동 규칙 모두 Markdown으로 관리
- **자연어로 실행** — "us-east-1 ARB 검증해줘" 한마디로 전체 프로세스 수행
- **엔진별 병렬 검증** — RDS MySQL/PostgreSQL, Aurora MySQL/PostgreSQL, DynamoDB, ElastiCache를 subagent가 동시에 검증
- **공통 + 고유 체크리스트** — 모든 엔진에 적용되는 공통 항목과 엔진별 고유 항목 분리
- **커맨드 로깅 & 검증** — 모든 AWS CLI 호출을 로그로 남기고, Verify Agent가 결과 정확성을 재확인

## 프로젝트 구조

```
arb-automation/
├── README.md
├── arb-config.md                      # 설정 파일 (리전, 엔진, 필터, 옵션)
├── .kiro/steering/
│   └── arb-review.md                  # 오케스트레이터 행동 규칙
├── arb-checklist/
│   ├── common.md                      # 공통 체크리스트
│   ├── rds-mysql.md                   # RDS MySQL 고유 체크리스트
│   ├── rds-postgres.md                # RDS PostgreSQL 고유 체크리스트
│   ├── aurora-mysql.md                # Aurora MySQL 고유 체크리스트
│   ├── aurora-postgres.md             # Aurora PostgreSQL 고유 체크리스트
│   ├── dynamodb.md                    # DynamoDB 고유 체크리스트
│   └── elasticache.md                 # ElastiCache 고유 체크리스트
└── arb-agents/
    ├── common-agent-rules.md          # 공통 에이전트 규칙 (호출 전략, 판단 기준, 출력 형식, 로깅)
    ├── rds-mysql-reviewer.md          # RDS MySQL 검증 subagent 프롬프트
    ├── rds-postgres-reviewer.md       # RDS PostgreSQL 검증 subagent 프롬프트
    ├── aurora-mysql-reviewer.md       # Aurora MySQL 검증 subagent 프롬프트
    ├── aurora-postgres-reviewer.md    # Aurora PostgreSQL 검증 subagent 프롬프트
    ├── dynamodb-reviewer.md           # DynamoDB 검증 subagent 프롬프트
    ├── elasticache-reviewer.md        # ElastiCache 검증 subagent 프롬프트
    └── verify-reviewer.md             # 검증 결과 재확인 에이전트 프롬프트
```

## 빠른 시작

### 1. 실행 환경

`aiops-arb-kiro/database/arb-automation/` 내에서 실행합니다.

```bash
cd aiops-arb-kiro/database/arb-automation
kiro-cli chat
```

### 1-1. Agent 및 Tool 자동 승인 설정

subagent까지 포함하여 tool 승인 프롬프트 없이 사용하려면 `--trust-tools` 옵션으로 시작합니다:

```bash
kiro-cli chat --agent arb-database --trust-tools=execute_bash,fs_read,fs_write,use_subagent
```

또는 실행 중 agent 전환:

```
/agent swap arb-database
```

> ⚠️ `/agent swap`만 사용하면 메인 agent의 tool은 자동 승인되지만, **subagent의 tool 호출은 승인이 필요**합니다.
> subagent(엔진별 병렬 검증)도 자동 승인하려면 반드시 `--trust-tools` 또는 `-a` 플래그로 시작해야 합니다.

설정 파일: `.kiro/agents/arb-database.json`

### 2. 설정

`arb-config.md`에서 서비스명, 대상 리전과 엔진을 설정합니다:

```markdown
## Service Name
- my-service

## Target Region
- us-east-1

## Target Engines
- rds mysql
- rds postgres
- aurora mysql
- aurora postgres
- elasticache
```

> 설정 파일 없이도 자연어로 대상 지정 가능합니다 (예: "scloud-stg rds elasticache eu-west-1 점검해줘")

### 3. 실행

```
# 설정 파일 기준 전체 검증
ARB 검증해줘

# 특정 엔진만
RDS MySQL만 ARB 검증해줘

# 특정 인스턴스만
prod-mysql 인스턴스 ARB 검증해줘

# 특정 계정/리전 + 엔진 조합
scloud-stg rds elasticache eu-west-1과 ap-northeast-2 점검해줘
```

### 4. 결과

```
## 전체 요약
- 리전: us-east-1 | 일시: 2026-04-25
- RDS MySQL 2대, ElastiCache 1클러스터
- ✅ PASS: 28 | ❌ FAIL: 5 | ⚠️ MANUAL: 3
- 🚨 Critical FAIL: 2

## 🚨 Critical FAIL (즉시 조치 필요)
| 리소스 | Check ID | 항목 | 상세 |
|--------|----------|------|------|
| prod-mysql | COM-SEC-001 | 암호화 | StorageEncrypted: false |
| staging-db | COM-SEC-003 | 퍼블릭 접근 | PubliclyAccessible: true |
```

### 5. 멀티 리전 점검

복수 리전을 한 번에 점검하면 리전별로 리포트가 생성됩니다:

```
arb-reports/scloud-stg/
├── eu-west-1/2026-07-29/
│   ├── elasticache.md
│   └── rds-mysql.md
└── ap-northeast-2/2026-07-29/
    ├── elasticache.md
    ├── rds-mysql.md
    ├── rds-postgres.md
    └── aurora-mysql.md
```

### 5. 검증 (선택)

```
검증해줘
```

Verify Agent가 커맨드 로그를 기반으로 판정 결과를 재실행·재확인합니다.

---

## 동작 원리

```
사용자: "ARB 검증해줘"
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  메인 에이전트 (오케스트레이터)                             │
│                                                          │
│  1. arb-config.md 읽기 → 설정 로드                        │
│  2. AWS CLI 벌크 조회로 리소스 디스커버리 (API 1회씩만)      │
│  3. 플랜 수립 → 사용자 확인                                │
│  4. 발견된 엔진별로 subagent 병렬 호출                      │
│  5. 결과 취합 → 종합 리포트 출력 및 파일 저장               │
│  6. (선택) Verify Agent로 결과 재확인                      │
└──┬──────────┬──────────┬──────────┬──────────────────────┘
   │          │          │          │     병렬 실행 (최대 4개)
   ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│  RDS   │ │ Aurora │ │ Aurora │ │ DynamoDB │  ...
│ MySQL  │ │ MySQL  │ │  PG    │ │ subagent │
│subagent│ │subagent│ │subagent│ │          │
└────────┘ └────────┘ └────────┘ └──────────┘
```

## 핵심 설계 원칙

### AWS CLI 호출 최소화
- 오케스트레이터가 `describe-db-instances`, `describe-db-clusters` 등을 **1회 벌크 조회**
- 전체 JSON 응답을 subagent에 전달 → subagent는 추가 describe 불필요
- 추가 호출은 파라미터 그룹, 태그, 알람 등 1차 응답에 없는 항목만

### 공통 규칙 중앙 관리
- `arb-agents/common-agent-rules.md`에서 호출 전략, 판단 기준, 출력 형식, 로깅 규칙을 한 곳에서 관리
- 각 엔진 에이전트는 고유 정보(역할, CLI 명령어, 파일명)만 정의

### 커맨드 로깅 & Verify
- 모든 AWS CLI 호출을 `logs/{engine}-commands.log`에 기록
- Verify Agent가 로그 기반으로 Critical FAIL 항목을 재실행하여 정확성 확인

## 출력 디렉토리 구조

```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/
├── database-summary.md           # 종합 리포트
├── verify-result.md              # 검증 결과 (선택)
├── rds-mysql.md                  # RDS MySQL 상세
├── rds-postgres.md               # RDS PostgreSQL 상세
├── aurora-mysql.md               # Aurora MySQL 상세
├── aurora-postgres.md            # Aurora PostgreSQL 상세
├── dynamodb.md                   # DynamoDB 상세
├── elasticache.md                # ElastiCache 상세
└── logs/
    ├── discovery.log             # 디스커버리 로그
    ├── rds-mysql-commands.log    # RDS MySQL 커맨드 로그
    └── elasticache-commands.log  # ElastiCache 커맨드 로그
```

> **날짜 기준**: 리포트 파일 경로의 날짜는 한국 시간(KST, UTC+9) 기준 YYYY-MM-DD를 사용합니다.

## 판정 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | API 응답에서 확인, 기준 충족 |
| ❌ FAIL | API 응답에서 확인, 기준 미충족 |
| ⚠️ MANUAL | API로 자동 확인 불가 (체크리스트에 `auto: false`) |
| ⏭️ SKIP | 해당 엔진/구성에 적용되지 않는 항목 |

## 체크리스트 커스터마이징

- 공통 항목 추가/수정 → `arb-checklist/common.md`
- 엔진별 항목 추가/수정 → `arb-checklist/{engine}.md`
- 새 엔진 추가 → 체크리스트 + 에이전트 프롬프트 생성, `arb-config.md`에 엔진 추가

## 필요 권한

- `rds:DescribeDBInstances`, `rds:DescribeDBClusters`, `rds:DescribeDBParameters`, `rds:DescribeGlobalClusters`, `rds:ListTagsForResource`
- `dynamodb:ListTables`, `dynamodb:DescribeTable`, `dynamodb:DescribeContinuousBackups`, `dynamodb:DescribeContributorInsights`, `dynamodb:ListTagsOfResource`
- `elasticache:DescribeCacheClusters`, `elasticache:DescribeReplicationGroups`, `elasticache:ListTagsForResource`
- `ec2:DescribeSecurityGroups`, `ec2:DescribeRouteTables`
- `application-autoscaling:DescribeScalableTargets`
- `cloudwatch:DescribeAlarms`

## Options

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| skip_non_production | false | non-production 리소스 건너뛰기 |
| fail_on_severity | critical | 이 severity 이상 FAIL 시 하이라이트 |
| output_format | markdown | 출력 형식 |
| auto_verify | false | 검증 완료 후 자동으로 Verify Agent 실행 |
