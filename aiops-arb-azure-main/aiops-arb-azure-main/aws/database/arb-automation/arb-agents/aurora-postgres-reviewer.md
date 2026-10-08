# Aurora PostgreSQL ARB Reviewer Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
AWS Aurora PostgreSQL 클러스터의 ARB 검증을 수행합니다.
Aurora MySQL은 제외합니다.

## 입력
- region
- `arb-checklist/common.md` 내용
- `arb-checklist/aurora-postgres.md` 내용
- 사전 조사 파일 (아래 순서로 결정):
  1. `arb-config.md`의 `Pre-Survey > Aurora PostgreSQL > file` 값이 있으면 해당 파일 사용
  2. 없으면 `pre-survey/aurora-postgres*.md` 패턴으로 탐색
     - 1개: 자동 선택
     - 2개 이상: 사용자에게 선택 요청
     - 0개: 사전 조사 없이 진행 (`auto: false` 항목은 N/A 처리)

## 수행 절차

### 1단계: 벌크 조회 (리전당 1회)

아래 명령어를 리전당 한 번씩 호출하여 결과를 저장합니다. 이후 단계에서 재사용합니다.
리소스 존재 여부 확인은 공통 규칙(`arb-agents/common-agent-rules.md`) 0단계를 따릅니다.

| 명령어 | 저장 변수 | 사용 항목 |
|--------|----------|----------|
| `aws rds describe-db-clusters --filters Name=engine,Values=aurora-postgresql --region {region}` | `CLUSTERS` | 전체 클러스터 기본 정보 |
| `aws rds describe-global-clusters --region {region}` | `GLOBAL_CLUSTERS` | AURPG-HA-003 |
| `aws ec2 describe-vpcs --region {region}` | `VPCS` | COM-NI-001, COM-SEC-004 |

### 2단계: 클러스터별 추가 조회

`CLUSTERS`의 각 클러스터에 대해 아래 명령어를 호출합니다.

| 명령어 | 사용 항목 |
|--------|----------|
| `aws rds describe-db-instances --filters Name=db-cluster-id,Values={cluster-id} --region {region}` | AURPG-HA-001~004 (인스턴스 수/AZ/클래스), AURPG-PERF-002 (`AutoMinorVersionUpgrade`), AURPG-MON-001~003 (PI 설정), AURPG-MON-002 (`MonitoringInterval`) |
| `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {cluster-pg-name} --region {region}` | AURPG-SPL-001~002 (`shared_preload_libraries`), AURPG-PG-004 (`rds.logical_replication`), AURPG-PERF-003 (`log_executor_stats`, `log_statement_stats`), AURPG-PERF-004 (`synchronous_commit`), AURPG-AV-001~003 (`autovacuum`, `track_activity_query_size`, `autovacuum_max_workers`) |
| `aws rds describe-db-parameters --db-parameter-group-name {instance-pg-name} --region {region}` | AURPG-SPL-003 (`pgtle.enable_password_check`), AURPG-SEC-002 (`password_encryption`), AURPG-MEM-001 (`work_mem`, `max_connections`), AURPG-IP-001~008 (각종 파라미터), AURPG-PG-001~002 (커스텀 PG 확인) |
| `aws rds list-tags-for-resource --resource-name {cluster-arn} --region {region}` | COM-TAG-001 |
| `aws cloudwatch describe-alarms --alarm-name-prefix {cluster-id} --region {region}` | COM-MON-001, COM-MON-004 |
| `aws ec2 describe-security-groups --group-ids {sg-ids} --region {region}` | COM-AC-001, COM-AC-002 |
| `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values={subnet-id} --region {region}` | COM-NI-001 (IGW 경로 확인) |
| `aws ec2 describe-vpcs --vpc-ids {vpc-id} --region {region}` | AURPG-NET-001 (default VPC 확인) |
| `aws ec2 describe-instance-types --instance-types {instance-type} --region {region}` | AURPG-PERF-001 (인스턴스 클래스), AURPG-MEM-001 (총 메모리), AURPG-AV-003 (autovacuum_max_workers 계산), AURPG-IP-007 (max_parallel_workers 계산) |
| `aws rds describe-db-engine-versions --engine aurora-postgresql --include-all --region {region}` | AURPG-HA-005 (deprecated 판정) |

> 동일 Cluster Parameter Group 또는 Instance Parameter Group을 공유하는 클러스터가 여러 개여도 **1회만 조회**합니다.

### 3단계: 체크리스트 검증

수집된 데이터를 기반으로 common.md + aurora-postgres.md의 모든 항목을 검증합니다.

### 4단계: 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | AWS CLI 응답에서 기준 충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준에 부합 |
| ❌ FAIL | AWS CLI 응답에서 기준 미충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준 미충족 |
| N/A | 해당 구성에 적용되지 않는 항목, 또는 사전 조사 파일이 없어 `auto: false` 항목을 판정할 수 없는 경우 (사유 명시) |

#### 인스턴스 메모리 조회 (1회)
- Writer 인스턴스의 `DBInstanceClass`에서 db. prefix 제거: 예) db.r6g.xlarge → r6g.xlarge
- `aws ec2 describe-instance-types --instance-types {instance-type} --query "InstanceTypes[0].MemoryInfo.SizeInMiB" --output text --region {region}`
- 결과를 `총 메모리(MiB)`로 저장하여 이후 메모리 관련 항목에서 재사용

#### Cluster Parameter Group 파라미터 조회 (1회, 클러스터 레벨)
- `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {Cluster PG명} --region {region} --no-paginate --query "Parameters[?ParameterName=='shared_preload_libraries' || ParameterName=='rds.logical_replication' || ParameterName=='autovacuum' || ParameterName=='track_activity_query_size' || ParameterName=='autovacuum_max_workers' || ParameterName=='log_executor_stats' || ParameterName=='log_statement_stats' || ParameterName=='synchronous_commit'].[ParameterName,ParameterValue]" --output table`
- 결과를 저장하여 AURPG-SPL-*, AURPG-PG-*, AURPG-AV-*, AURPG-PERF-003/004 항목에서 재사용

#### DB Parameter Group 파라미터 조회 (1회, 인스턴스 레벨)
- `aws rds describe-db-parameters --db-parameter-group-name {인스턴스 PG명} --region {region} --no-paginate --query "Parameters[?ParameterName=='work_mem' || ParameterName=='max_connections' || ParameterName=='shared_buffers' || ParameterName=='pgtle.enable_password_check' || ParameterName=='log_lock_waits' || ParameterName=='log_min_duration_statement' || ParameterName=='log_filename' || ParameterName=='auto_explain.log_analyze' || ParameterName=='enable_seqscan' || ParameterName=='force_parallel_mode' || ParameterName=='max_parallel_workers' || ParameterName=='pg_stat_statements.max' || ParameterName=='password_encryption'].[ParameterName,ParameterValue]" --output table`
- 결과를 저장하여 AURPG-MEM-*, AURPG-SPL-003, AURPG-SEC-002, AURPG-IP-* 항목에서 재사용

## 검증 수행

수집된 정보를 기반으로 각 클러스터에 대해 common.md + aurora-postgres.md의 모든 항목을 검증합니다.

### Parameter Group 커스텀 사용 검증 로직 (AURPG-PG-001, AURPG-PG-002)
- Cluster 레벨: `DBClusterParameterGroup`이 `default.aurora-postgresql`로 시작하면 FAIL
- Instance 레벨: `DBParameterGroups[].DBParameterGroupName`이 `default.`로 시작하면 FAIL

### 인스턴스 네이밍 역할명 검증 로직 (AURPG-PG-003)
- 클러스터 내 각 인스턴스의 `DBInstanceIdentifier`를 소문자로 변환
- 다음 키워드 포함 여부 확인: writer, reader, master, replica, primary, secondary, slave, wo, ro
- 하나라도 포함되면 FAIL + 코멘트: "Failover 시 역할 변경으로 인스턴스명과 실제 역할이 불일치할 수 있음"

### 인스턴스 클래스 적정성 검증 로직 (AURPG-PERF-001)
- `DBInstanceClass`에서 인스턴스 패밀리 추출 (예: db.r6g.xlarge → r6g)
- 메모리 최적화 타입(r 계열): r6g, r6i, r7g, r7i, r8g 이상 → PASS
- 구세대(r6g 미만: r5, r4 등): FAIL
- large 미만 사이즈: FAIL
- 범용 타입(m 계열) 또는 burstable(t 계열): FAIL

### 엔진 버전 LTS 검증 로직 (AURPG-HA-005)
- `describe-db-clusters` → `EngineVersion` 추출
- deprecated 판정: `aws rds describe-db-engine-versions --engine aurora-postgresql --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
- LTS 버전 확인: AWS 공식 문서(https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Updates.LTS.html) 를 웹 조회하여 최신 LTS 버전 목록을 확인
- LTS 버전이면 PASS, LTS가 아니고 deprecated도 아니면 WARNING, deprecated이면 FAIL

- **지원 종료 정보 리포트 표기 규칙 (오해 방지)**:
  - EngineVersion을 메이저(`17`)와 마이너(`17.9`)로 분리한다.
  - **검증 대상보다 낮은 메이저 버전의 EOL 정보는 표기하지 않는다.** (예: 17.9 검증 시 16/15/14 등의 EOL은 불필요한 노이즈이므로 제외)
  - 검증 대상이 마이너 버전이면, 리포트에 다음을 **반드시 구분하여** 명시한다.
    1. 사용 중인 메이저 라인(PostgreSQL 17)의 Aurora 표준 지원 종료일
    2. 사용 중인 마이너 버전(17.9) 자체의 Aurora 표준 지원 종료일
    3. 해당 마이너의 LTS 여부, 같은 메이저 라인 LTS 버전(예: 17.7 LTS)의 종료일
  - Aurora는 같은 메이저 라인 안에서도 non-LTS 마이너 버전 종료일이 LTS/메이저보다 크게 빠를 수 있음을 코멘트로 강조한다.
    - 실제 예: Aurora 17.9의 표준 지원 종료는 2027-09-30, 17.7(LTS)은 2030-02-28, 메이저 17은 2030-02-28로, non-LTS 마이너 종료가 약 2.5년 빠름.
  - non-LTS 마이너 버전 사용 시, LTS 전환으로 동일 메이저 라인에서 지원 기간을 크게 늘릴 수 있음을 안내한다.
  - 날짜 조회:
    - 마이너 버전: AWS Aurora PostgreSQL Release Calendar minor version 표 (또는 `aws rds describe-db-engine-versions --engine aurora-postgresql --engine-version {major.minor} --include-all`)
    - 메이저 버전: `aws rds describe-db-major-engine-versions --engine aurora-postgresql` (또는 Release Calendar major version 표)
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/aurorapostgresql-release-calendar.html
  - 리포트 참고 정보 표 형식 (검증 대상 버전만 포함):

    | 구분 | 버전 | LTS 여부 | Aurora 표준 지원 종료일 |
    |------|------|---------|------------------------|
    | 사용 중인 마이너 버전 | 17.9 | non-LTS | 2027-09-30 |
    | 같은 메이저 라인 LTS | 17.7 | LTS | 2030-02-28 |
    | 사용 중인 메이저 라인 | PostgreSQL 17 | - | 2030-02-28 |

    ※ 사용 중인 마이너 버전(17.9, non-LTS)의 표준 지원 종료일은 메이저 라인(17) 및 LTS 버전(17.7)보다 약 2.5년 빠릅니다. 메이저/LTS EOL이 아닌 **현재 마이너 버전 종료일 기준**으로 업그레이드 계획을 수립해야 합니다. 장기 운영이 필요하면 LTS 버전(17.7) 전환을 검토하세요.

### Maintenance/Backup Window 검증 로직 (AURPG-MNT-001, AURPG-MNT-002)
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
- **work_mem 판단**: 4MB(기본값)이면 WARNING. OOM 위험 = work_mem × max_connections > (총 메모리 - shared_buffers) × 75% 이면 FAIL
- **work_mem 실무 권장 범위** (리포트에 참고 정보로 첨부):
  - 8GB 이하 인스턴스: 8~32MB
  - 16~64GB 인스턴스: 32~128MB
  - 128GB 이상 인스턴스: 64~256MB

### pg_tle passcheck hook 검증 로직 (AURPG-SPL-003)
- DB Parameter Group(인스턴스 레벨) 조회 결과에서 `pgtle.enable_password_check` 값 확인
- `off`이면 PASS, `on` 또는 `require`이면 FAIL
- 파라미터가 존재하지 않으면 PASS (pg_tle 미설치 상태)

### Autovacuum 검증 로직 (AURPG-AV-001, AURPG-AV-002, AURPG-AV-003)
- **autovacuum**: Cluster Parameter Group 조회 결과에서 `autovacuum` 값이 `1`이면 PASS, `0`이면 FAIL
- **track_activity_query_size**: Cluster Parameter Group 조회 결과에서 값이 8192 이상이면 PASS, 미만이면 WARNING
- **autovacuum_max_workers**: 
  - 값이 수식 형태(`GREATEST({DBInstanceClassMemory/...},3)`)이면 즉시 PASS
  - 고정 숫자값인 경우: `GREATEST(총 메모리(Bytes) / 64371566592, 3)` 계산 → 실제값 ≥ 계산값이면 PASS, 미만이면 WARNING + 리뷰 코멘트: "autovacuum_max_workers가 기본 수식 결과보다 작게 설정되어 있습니다. vacuum 병렬 처리 능력 저하 가능성 검토 필요"


## 리소스 요약 정보 (상세 리포트 헤더)
```
Engine: aurora-postgresql | Instances: {count} | Region: {region}
```

## `auto: false` 항목 판정 방법

사전 조사 파일의 각 섹션은 아래 구조로 되어 있습니다:

```
# [AURPG-ACC-001 + AURPG-ACC-004] ...   ← Check ID가 포함된 섹션 헤더 (주석)
# ...                                ← 자동 조회 결과 (주석, 읽기 전용)
#
# -- 입력 ---
# ...

    항목명 : O          ← 흰색 줄, 개발팀이 작성한 O/X 값
    비고   : ...        ← 흰색 줄, 추가 설명
```

**파싱 규칙:**
1. `# [AURPG-XXX-NNN]` 패턴으로 섹션을 찾아 해당 Check ID 특정
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

## 출력 파일명
`arb-reports/{service_name}/{region}/{YYYY-MM-DD}/aurora-postgres.md`
