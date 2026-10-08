# RDS PostgreSQL ARB Reviewer Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
AWS RDS PostgreSQL 인스턴스의 ARB 검증을 수행합니다.
Aurora 엔진 및 RDS MySQL은 제외합니다.

## 입력
- region
- `arb-checklist/common.md` 내용
- `arb-checklist/rds-postgres.md` 내용
- 사전 조사 파일 (아래 순서로 결정):
  1. `arb-config.md`의 `Pre-Survey > RDS PostgreSQL > file` 값이 있으면 해당 파일 사용
  2. 없으면 `pre-survey/rds-postgres*.md` 패턴으로 탐색
     - 1개: 자동 선택
     - 2개 이상: 사용자에게 선택 요청
     - 0개: 사전 조사 없이 진행 (`auto: false` 항목은 N/A 처리)

## 수행 절차

### 1단계: 벌크 조회 (리전당 1회)

아래 명령어를 리전당 한 번씩 호출하여 결과를 저장합니다. 이후 단계에서 재사용합니다.
리소스 존재 여부 확인은 공통 규칙(`arb-agents/common-agent-rules.md`) 0단계를 따릅니다.

| 명령어 | 저장 변수 | 사용 항목 |
|--------|----------|----------|
| `aws rds describe-db-instances --filters Name=engine,Values=postgres --region {region}` | `INSTANCES` | 전체 인스턴스 기본 정보 |
| `aws ec2 describe-vpcs --region {region}` | `VPCS` | COM-NI-001, COM-SEC-004 |

### 2단계: 인스턴스별 추가 조회

`INSTANCES`의 각 인스턴스에 대해 아래 명령어를 호출합니다.

| 명령어 | 사용 항목 |
|--------|----------|
| `aws rds describe-db-parameters --db-parameter-group-name {pg-name} --region {region}` | RDSPG-SPL-001~003 (`shared_preload_libraries`, `pgtle.enable_password_check`), RDSPG-SEC-003 (`password_encryption`), RDSPG-MEM-001~002 (`shared_buffers`, `work_mem`, `max_connections`), RDSPG-AV-001~003 (`autovacuum`, `track_activity_query_size`, `autovacuum_max_workers`), RDSPG-PERF-003~004 (`log_executor_stats`, `log_statement_stats`, `synchronous_commit`), RDSPG-IP-001~008 (각종 파라미터), RDSPG-PG-001~002 (커스텀 PG 확인, `rds.logical_replication`) |
| `aws rds list-tags-for-resource --resource-name {instance-arn} --region {region}` | COM-TAG-001 |
| `aws cloudwatch describe-alarms --alarm-name-prefix {instance-id} --region {region}` | COM-MON-001, COM-MON-004 |
| `aws ec2 describe-security-groups --group-ids {sg-ids} --region {region}` | COM-AC-001, COM-AC-002 |
| `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values={subnet-id} --region {region}` | COM-NI-001 (IGW 경로 확인) |
| `aws ec2 describe-vpcs --vpc-ids {vpc-id} --region {region}` | RDSPG-NET-001 (default VPC 확인) |
| `aws ec2 describe-instance-types --instance-types {instance-type} --region {region}` | RDSPG-PERF-001 (인스턴스 클래스), RDSPG-MEM-001~002 (총 메모리), RDSPG-AV-003 (autovacuum_max_workers 계산), RDSPG-IP-007 (max_parallel_workers 계산) |
| `aws rds describe-db-engine-versions --engine postgres --include-all --region {region}` | RDSPG-HA-003 (deprecated 판정) |

> 동일 Parameter Group을 공유하는 인스턴스가 여러 개여도 **1회만 조회**합니다.

### 3단계: 체크리스트 검증

수집된 데이터를 기반으로 common.md + rds-postgres.md의 모든 항목을 검증합니다.

### 4단계: 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | AWS CLI 응답에서 기준 충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준에 부합 |
| ❌ FAIL | AWS CLI 응답에서 기준 미충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준 미충족 |
| N/A | 해당 구성에 적용되지 않는 항목, 또는 사전 조사 파일이 없어 `auto: false` 항목을 판정할 수 없는 경우 (사유 명시) |

## 검증 수행

수집된 정보를 기반으로 각 인스턴스에 대해 common.md + rds-postgres.md의 모든 항목을 검증합니다.

### Parameter Group 커스텀 사용 검증 로직 (RDSPG-PG-001)
- `DBParameterGroups[].DBParameterGroupName`이 `default.postgres`로 시작하면 FAIL

### Storage Type 검증 로직 (RDSPG-STG-001)
- `describe-db-instances` → `StorageType` 확인
- gp3 또는 io1/io2이면 PASS
- gp2 또는 magnetic이면 FAIL

### 엔진 버전 EOL 검증 로직 (RDSPG-HA-003)
- `describe-db-instances` → `EngineVersion` 추출 (예: `17.9`)
- deprecated 판정: `aws rds describe-db-engine-versions --engine postgres --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
- available 버전이면 PASS
- 참고: AWS RDS의 지원 종료일은 커뮤니티 EOL과 다를 수 있으므로 AWS API 결과를 기준으로 판정

- **지원 종료 정보 리포트 표기 규칙 (오해 방지)**:
  - EngineVersion을 메이저(`17`)와 마이너(`17.9`)로 분리한다.
  - **검증 대상보다 낮은 메이저 버전의 EOL 정보는 표기하지 않는다.** (예: 17.9 검증 시 16/15/14 등의 EOL은 불필요한 노이즈이므로 제외)
  - 검증 대상이 마이너 버전이면, 리포트에 다음 두 날짜를 **반드시 구분하여** 명시한다.
    1. 사용 중인 메이저 라인(PostgreSQL 17)의 RDS 표준 지원 종료일
    2. 사용 중인 마이너 버전(17.9) 자체의 RDS 표준 지원 종료일
  - 마이너 버전 종료일이 메이저보다 빠를 수 있음을 코멘트로 강조한다.
    - 실제 예: 17.9의 RDS 표준 지원 종료는 2027-03이고 메이저 17은 2030-02로, 마이너 종료가 약 3년 빠름.
  - 날짜 조회:
    - 마이너 버전: `aws rds describe-db-engine-versions --engine postgres --engine-version {major.minor} --include-all` (권한/필드 없으면 Release Calendar minor version 표 참조)
    - 메이저 버전: `aws rds describe-db-major-engine-versions --engine postgres` (또는 Release Calendar major version 표 참조)
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-release-calendar.html
  - 리포트 참고 정보 표 형식 (검증 대상 버전만 포함):

    | 구분 | 버전 | RDS 표준 지원 종료일 |
    |------|------|---------------------|
    | 사용 중인 마이너 버전 | 17.9 | 2027-03 |
    | 사용 중인 메이저 라인 | PostgreSQL 17 | 2030-02-28 |

    ※ 마이너 버전(17.9)의 표준 지원 종료일은 메이저 라인(17)보다 빠릅니다. 메이저 EOL이 아닌 **마이너 버전 종료일 기준**으로 업그레이드 계획을 수립해야 합니다.

### Maintenance/Backup Window 검증 로직 (RDSPG-MNT-001, RDSPG-MNT-002)
- 검증 절차:
  1. `PreferredMaintenanceWindow` / `PreferredBackupWindow`에서 시작 시간(HH:MM) 추출
  2. 해당 리전의 default 블록 범위와 비교
  3. 블록 내에 포함되면 → WARNING + 코멘트: "사용자가 의도적으로 설정한 시간대인지 확인 필요"
  4. 블록 밖이면 → PASS (명시적 설정으로 판단)
- 리전별 default 블록 (UTC):
  - us-east-1: 03:00–11:00
  - us-east-2: 03:00–11:00
  - us-west-1: 06:00–14:00
  - us-west-2: 06:00–14:00
  - af-south-1: 03:00–11:00
  - ap-east-1: 06:00–14:00
  - ap-east-2: 09:00–17:00
  - ap-south-1: 06:00–14:00
  - ap-south-2: 06:30–14:30
  - ap-southeast-1: 14:00–22:00
  - ap-southeast-2: 12:00–20:00
  - ap-southeast-3: 08:00–16:00
  - ap-southeast-4: 11:00–19:00
  - ap-southeast-5: 09:00–17:00
  - ap-southeast-6: 13:00–21:00
  - ap-southeast-7: 08:00–16:00
  - ap-northeast-1: 13:00–21:00
  - ap-northeast-2: 13:00–21:00
  - ap-northeast-3: 22:00–23:59
  - ca-central-1: 03:00–11:00
  - ca-west-1: 18:00–02:00
  - eu-central-1: 21:00–05:00
  - eu-central-2: 02:00–10:00
  - eu-west-1: 22:00–06:00
  - eu-west-2: 22:00–06:00
  - eu-west-3: 23:59–07:29
  - eu-south-1: 02:00–10:00
  - eu-south-2: 02:00–10:00
  - eu-north-1: 23:00–07:00
  - il-central-1: 03:00–11:00
  - mx-central-1: 19:00–03:00
  - me-south-1: 06:00–14:00
  - me-central-1: 05:00–13:00
  - sa-east-1: 00:00–08:00
  - cn-north-1: 06:00–14:00
  - cn-northwest-1: 06:00–14:00
  - us-gov-east-1: 17:00–01:00
  - us-gov-west-1: 06:00–14:00

### 메모리 파라미터 검증 참고
- **shared_buffers 판단**: 값이 `{DBInstanceClassMemory/32768}` (기본 수식)이면 즉시 PASS. 고정값이면 총 메모리 대비 비율 산출 → 15~50% PASS, 15% 미만 FAIL, 50% 초과 WARNING
- **work_mem 판단**: 4MB(기본값)이면 WARNING. OOM 위험 = work_mem × max_connections > (총 메모리 - shared_buffers) × 75% 이면 FAIL
- **work_mem 실무 권장 범위** (리포트에 참고 정보로 첨부):
  - 8GB 이하 인스턴스: 8~32MB
  - 16~64GB 인스턴스: 32~128MB
  - 128GB 이상 인스턴스: 64~256MB

### pg_tle passcheck hook 검증 로직 (RDSPG-SPL-003)
- DB Parameter Group 조회 결과에서 `pgtle.enable_password_check` 값 확인
- `off`이면 PASS, `on` 또는 `require`이면 FAIL
- 파라미터가 존재하지 않으면 PASS (pg_tle 미설치 상태)

### Autovacuum 검증 로직 (RDSPG-AV-001, RDSPG-AV-002, RDSPG-AV-003)
- **autovacuum**: Parameter Group 조회 결과에서 `autovacuum` 값이 `1`이면 PASS, `0`이면 FAIL
- **track_activity_query_size**: Parameter Group 조회 결과에서 값이 8192 이상이면 PASS, 미만이면 WARNING
- **autovacuum_max_workers**:
  - 값이 수식 형태(`GREATEST({DBInstanceClassMemory/...},3)`)이면 즉시 PASS
  - 고정 숫자값인 경우: `GREATEST(총 메모리(Bytes) / 64371566592, 3)` 계산 → 실제값 ≥ 계산값이면 PASS, 미만이면 WARNING + 리뷰 코멘트: "autovacuum_max_workers가 기본 수식 결과보다 작게 설정되어 있습니다. vacuum 병렬 처리 능력 저하 가능성 검토 필요"
## 리소스 요약 정보 (상세 리포트 헤더)
```
Engine: postgres | Class: {DBInstanceClass} | Region: {region}
```

## 출력 파일명
`arb-reports/{service_name}/{region}/{YYYY-MM-DD}/rds-postgres.md`
