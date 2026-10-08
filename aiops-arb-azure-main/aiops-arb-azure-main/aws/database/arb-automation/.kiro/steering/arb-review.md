# ARB Database Review Agent

## 일반 규칙
- 이 프로젝트 내 `.md` 파일은 별도 권한 확인 없이 바로 읽는다.
- subagent는 별도 사용자 확인 없이 파일 읽기/쓰기 및 AWS CLI 호출을 수행한다.
- `arb-reports/` 디렉토리에 리포트 파일을 생성·덮어쓸 때는 사용자 확인 없이 바로 수행한다.
- AWS CLI는 읽기 전용(describe, list, get)만 허용한다. 변경(create, update, modify, delete, put, remove 등)은 절대 실행하지 않는다.

## 트리거
사용자가 DB ARB 검증/리뷰를 요청하면 이 프로세스를 따릅니다.

## 입력 파싱
1. `arb-config.md` 파일을 읽어 기본 설정(service_name, region, engine, filters, options)을 로드합니다.
2. 사용자 요청에 명시된 값이 있으면 설정 파일보다 우선 적용합니다:
   - **service_name**: 명시되면 해당 값, 없으면 설정 파일의 Service Name 사용. 둘 다 없으면 사용자에게 입력 요청
   - **region**: 명시되면 해당 리전, 없으면 설정 파일의 Target Regions 사용
   - **engine**: 명시되면 해당 엔진만, 없으면 설정 파일의 Target Engines 사용
   - **scope**: 특정 인스턴스명이 있으면 해당 건만, 없으면 설정 파일의 Filters 참조

## 엔진 매핑

Target Engines의 값과 AWS 리소스 매핑:

| 설정값 | AWS 엔진 필터 | 디스커버리 명령어 |
|--------|--------------|-----------------|
| rds mysql | Engine: mysql, mariadb | `aws rds describe-db-instances` (aurora 제외) |
| rds postgres | Engine: postgres | `aws rds describe-db-instances` (aurora 제외) |
| aurora mysql | Engine: aurora-mysql | `aws rds describe-db-clusters` |
| aurora postgres | Engine: aurora-postgresql | `aws rds describe-db-clusters` |
| dynamodb | - | `aws dynamodb list-tables` |
| elasticache | - | `aws elasticache describe-replication-groups` |

## 1단계: 리소스 디스커버리

대상 region에서 AWS CLI로 존재하는 DB 리소스를 조회합니다.

### 디스커버리 호출 규칙
- **Filters 섹션이 비어있는 엔진은 디스커버리 및 검증을 스킵**한다 (API 호출하지 않음)
- RDS와 Aurora가 모두 대상이어도 `describe-db-instances`와 `describe-db-clusters`는 각각 **1회만** 호출
- 응답을 엔진별로 필터링하여 분배

### RDS (rds mysql / rds postgres)
```
aws rds describe-db-instances --region {region} --no-paginate
```
- **한 번만 호출**하여 전체 인스턴스를 가져온 뒤 엔진별로 필터링
- Aurora 엔진(`aurora`, `aurora-mysql`, `aurora-postgresql`)은 제외
- **rds mysql**: `Engine`이 `mysql` 또는 `mariadb`인 인스턴스만 필터
- **rds postgres**: `Engine`이 `postgres`인 인스턴스만 필터

### Aurora (aurora mysql / aurora postgres)
```
aws rds describe-db-clusters --region {region} --no-paginate
```
- **한 번만 호출**하여 전체 클러스터를 가져온 뒤 엔진별로 필터링
- **aurora mysql**: `Engine`이 `aurora-mysql`인 클러스터만 필터
- **aurora postgres**: `Engine`이 `aurora-postgresql`인 클러스터만 필터

### DynamoDB
```
aws dynamodb list-tables --region {region}
```

### ElastiCache
```
aws elasticache describe-replication-groups --region {region}
```

- 엔진이 명시된 경우 해당 엔진만 조회
- 결과가 없는 엔진은 건너뜀
- 발견된 리소스 요약을 사용자에게 보여주고 진행 여부 확인

### 디스커버리 로그 저장

모든 디스커버리 API 호출 결과를 요약하여 파일로 저장합니다.

#### 저장 경로
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/logs/discovery.log
```

#### 로그 형식
각 엔진 디스커버리마다 다음을 기록:
```
[{timestamp}] ENGINE: {engine}
[{timestamp}] COMMAND: {실행한 AWS CLI 명령어 전체}
[{timestamp}] RESPONSE_SUMMARY: {응답 요약 — 발견된 리소스 수 및 리소스 ID 목록}
[{timestamp}] FILTERED: {엔진별 필터링 후 최종 대상 리소스 ID 목록}
---
```

#### 규칙
- 디스커버리 시작 시 로그 파일 생성
- 스킵된 엔진도 사유와 함께 기록: `[{timestamp}] ENGINE: {engine} | SKIPPED: {사유}`
- 리소스가 0건인 엔진도 빈 응답 JSON 그대로 기록
- subagent 호출 전에 반드시 저장 완료

## 2단계: 플랜 수립 및 사용자 확인

디스커버리 결과를 바탕으로 실행 플랜을 수립하고, **subagent 호출 전에 사용자에게 플랜을 보여주고 확인을 받습니다.**

### 플랜 출력 형식

```
## 🔍 ARB 검증 플랜

- 리전: {region}
- 일시: {YYYY-MM-DD}

### 검증 대상 리소스

| 엔진 | 리소스 수 | 리소스 목록 |
|------|----------|------------|
| RDS MySQL | 2대 | prod-mysql-01, prod-mysql-02 |
| Aurora PostgreSQL | 1클러스터 | prod-aurora-pg |
| DynamoDB | 3테이블 | user-session, order-history, ... |

### 적용 체크리스트
- 공통: common.md (18항목)
- RDS MySQL: rds-mysql.md (25항목)
- Aurora PostgreSQL: aurora-postgres.md (10항목)
- DynamoDB: dynamodb.md (8항목)

진행할까요? (y/n)
```

- 사용자가 **y** → 3단계(subagent 위임)로 진행
- 사용자가 **n** 또는 수정 요청 → 요청에 맞게 플랜 조정 후 재확인

## 3단계: subagent 위임

사용자 확인 후, 발견된 엔진별로 subagent를 병렬 생성합니다. 각 subagent에게 전달할 내용:

1. **공통 에이전트 규칙**: `arb-agents/common-agent-rules.md` 파일 내용
2. **에이전트 프롬프트**: `arb-agents/{engine}-reviewer.md` 의 행동 규칙
3. **공통 체크리스트**: `arb-checklist/common.md` 파일 내용
4. **엔진별 체크리스트**: `arb-checklist/{engine}.md` 파일 내용
5. **대상 리소스**: 1단계에서 조회한 리소스 상세 정보 (JSON 전체 응답)
6. **region**: 대상 리전
7. **service_name**: 오케스트레이터로부터 전달받은 서비스명 (리포트 저장 경로 `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/` 에 반드시 사용, 임의로 추측하거나 변경하지 말 것)

> **중요**: 1단계 디스커버리에서 이미 `describe-db-instances`, `describe-db-clusters`, `describe-replication-groups`, `list-tables` 등의 전체 응답을 받았으므로, 해당 JSON을 그대로 subagent에 전달합니다. subagent는 이 데이터로 대부분의 항목을 판정하고, 추가 API 호출은 최소화합니다.

### 엔진별 파일 매핑

| 엔진 | 체크리스트 | 에이전트 프롬프트 |
|------|-----------|-----------------|
| rds mysql | `arb-checklist/rds-mysql.md` | `arb-agents/rds-mysql-reviewer.md` |
| rds postgres | `arb-checklist/rds-postgres.md` | `arb-agents/rds-postgres-reviewer.md` |
| aurora mysql | `arb-checklist/aurora-mysql.md` | `arb-agents/aurora-mysql-reviewer.md` |
| aurora postgres | `arb-checklist/aurora-postgres.md` | `arb-agents/aurora-postgres-reviewer.md` |
| dynamodb | `arb-checklist/dynamodb.md` | `arb-agents/dynamodb-reviewer.md` |
| elasticache | `arb-checklist/elasticache.md` | `arb-agents/elasticache-reviewer.md` |

### subagent 출력 규칙

각 subagent는 **상세 결과를 파일로 저장**하고, 메인 에이전트에게는 **요약만 반환**합니다.

#### 1) 상세 결과 파일 저장

subagent가 직접 파일을 생성합니다:

```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{engine}.md
```

예시: `arb-reports/us-east-1/2026-04-27/rds-mysql.md`

파일 내용은 리소스별 전체 체크 결과 테이블:

```
## {리소스 이름/ID}

| Check ID | 항목 | Severity | 결과 | 상세 |
|----------|------|----------|------|------|
| HA-001 | Multi-AZ | critical | ✅ PASS | MultiAZ: true |
```

#### 2) 메인 에이전트에 요약만 반환

반환 형식:

```
## {engine} 검증 요약
- 리소스 수: N대
- ✅ PASS: X | ❌ FAIL: Y | ⚠️ MANUAL: Z
- 🚨 Critical FAIL: N건
- 상세 리포트: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{engine}.md

### Critical FAIL 목록
| 리소스 | Check ID | 항목 | 상세 |
|--------|----------|------|------|
```

Critical FAIL이 없으면 "Critical FAIL 목록" 섹션은 생략합니다.

## 4단계: 종합 리포트

subagent가 반환한 **요약**을 취합하여 다음을 출력합니다:

### 전체 요약
- 검증 리전, 일시
- 엔진별 리소스 수
- 전체 PASS / FAIL / MANUAL 카운트
- Critical FAIL 수

### 🚨 Critical FAIL 항목 (즉시 조치 필요)
Critical severity이면서 FAIL인 항목만 별도 하이라이트

### 엔진별 요약
각 subagent의 요약 결과 정리

### 상세 리포트 경로 안내
각 엔진별 상세 파일 경로를 안내

### 권고사항
FAIL 항목에 대한 조치 방법 안내

## 5단계: 종합 리포트 파일 저장

종합 리포트를 채팅에 출력한 후, 동일한 내용을 파일로 저장합니다.

### 저장 경로
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/database-summary.md
```

예시: `arb-reports/us-east-1/2026-04-27/database-summary.md`

### 최종 디렉토리 구조 예시
```
arb-reports/us-east-1/2026-04-27/
├── database-summary.md     # 메인 에이전트가 생성 (종합 리포트)
├── rds-mysql.md            # subagent가 생성 (상세)
├── aurora-postgres.md      # subagent가 생성 (상세)
├── dynamodb.md             # subagent가 생성 (상세)
└── elasticache.md          # subagent가 생성 (상세)
```

### 저장 규칙
- `arb-reports/` 디렉토리가 없으면 자동 생성
- 같은 리전 + 같은 날짜에 재실행하면 기존 파일을 덮어씀

## 6단계: 검증 (Verify)

종합 리포트 출력 후, 사용자가 "검증해줘" 또는 "verify"를 요청하면 verify agent를 호출합니다.
`arb-config.md`에 `auto_verify: true`가 설정된 경우 자동으로 호출합니다.

### verify agent에 전달할 내용
1. **에이전트 프롬프트**: `arb-agents/verify-reviewer.md`
2. **커맨드 로그**: `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/logs/` 전체
3. **상세 리포트**: `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/` 엔진별 MD 파일
4. **체크리스트**: `arb-checklist/common.md` + 해당 엔진별 MD
5. **region**: 대상 리전

### 최종 디렉토리 구조 (verify 포함)
```
arb-reports/us-east-1/2026-04-27/
├── database-summary.md
├── verify-result.md         # verify agent가 생성
├── rds-mysql.md
├── aurora-postgres.md
├── dynamodb.md
├── elasticache.md
└── logs/
    ├── discovery.log
    ├── rds-mysql-commands.log
    ├── aurora-postgres-commands.log
    ├── dynamodb-commands.log
    └── elasticache-commands.log
```
