# RDS PostgreSQL ARB Checklist

RDS PostgreSQL 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

## High Availability

- [RDSPG-HA-001] Multi-AZ 배포 | severity: critical | auto: true
  - 검증: `MultiAZ` == true
  - 기준: 프로덕션 DB는 반드시 Multi-AZ로 배포

- [RDSPG-HA-002] Read Replica 구성 | severity: major | auto: true
  - 검증: `ReadReplicaDBInstanceIdentifiers` 배열이 비어있지 않은지 확인
  - 기준: 최소 1개 Read Replica 권장

- [RDSPG-HA-003] 엔진 버전 EOL 확인 | severity: critical | auto: true
  - 검증: describe-db-instances → EngineVersion이 deprecated 상태가 아닌지 확인
  - 기준: deprecated 버전 사용 시 FAIL, available 버전 사용 시 PASS
  - deprecated 판정: `aws rds describe-db-engine-versions --engine postgres --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
  - 리포트 표기 원칙 (중요):
    - **검증 대상 버전(메이저/마이너)을 기준으로만** 지원 종료 정보를 제공한다. 검증 대상보다 낮은 메이저 버전의 EOL 정보는 오해를 유발하므로 표기하지 않는다.
    - 검증 대상이 **마이너 버전**(예: 17.9)인 경우, 다음 두 가지를 **명확히 구분하여** 표기한다.
      - 현재 사용 중인 **메이저 버전 라인**(예: PostgreSQL 17)의 RDS 표준 지원 종료일
      - 현재 사용 중인 **마이너 버전**(예: 17.9) 자체의 RDS 표준 지원 종료일
    - 마이너 버전의 표준 지원 종료일은 메이저 버전보다 빠를 수 있으므로(예: 17.9 → 2027-03, 메이저 17 → 2030-02), 마이너 버전 종료일을 반드시 별도로 명시하여 "메이저 EOL까지 여유가 있다"는 오해를 방지한다.
  - 조회 방법:
    - 마이너 버전 종료일: `aws rds describe-db-engine-versions --engine postgres --engine-version {major.minor} --include-all` 응답에서 lifecycle/지원 종료 정보 확인. (API 권한이 없거나 필드가 없으면 AWS RDS for PostgreSQL Release Calendar의 minor version 표 참조)
    - 메이저 버전 종료일: `aws rds describe-db-major-engine-versions --engine postgres` 의 SupportedEngineLifecycles(또는 Release Calendar major version 표) 참조
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-release-calendar.html

## Backup & Recovery

- [RDSPG-BR-001] 백업 보존 기간 | severity: critical | auto: true
  - 검증: `BackupRetentionPeriod` >= 7
  - 기준: 최소 7일 이상

## Security

- [RDSPG-SEC-001] IAM 인증 비활성화 | severity: critical | auto: true
  - 검증: `IAMDatabaseAuthenticationEnabled` == false
  - 기준: IAM 인증은 사용하지 않아야 함

- [RDSPG-SEC-002] Default Port 사용 금지 | severity: critical | auto: true
  - 검증: `Endpoint.Port` != 5432
  - 기준: PostgreSQL 기본 포트(5432) 사용을 지양하고, 비표준 포트를 사용하여 port scanning 공격 표면을 축소해야 합니다.
  - 권장조치: `aws rds modify-db-instance --db-instance-identifier {id} --db-port-number {new-port}`로 변경. 유효 범위 1150~65535. 포트 변경 시 ApplyImmediately 값과 무관하게 즉시 DB가 재시작되므로 서비스 점검 시간에 수행 필요. 변경 후 Security Group 인바운드 규칙과 애플리케이션 connection string도 함께 업데이트해야 합니다.

- [RDSPG-SEC-003] password_encryption scram-sha-256 사용 | severity: major | auto: true
  - 검증: Parameter Group에서 `password_encryption` 값이 `scram-sha-256`인지 확인
  - 기준: MD5는 취약한 해시 알고리즘으로, 계정 패스워드 저장 방식은 반드시 scram-sha-256을 사용해야 합니다. PostgreSQL 14 이상 기본값이지만 구버전 업그레이드 시 md5로 남아있을 수 있음.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='password_encryption'].ParameterValue"` 결과가 `scram-sha-256`이면 PASS
    - DB 내부: `SHOW password_encryption;` 결과가 `scram-sha-256`이면 PASS
  - 권장조치: `password_encryption = scram-sha-256`으로 설정. 변경 후 기존 MD5 비밀번호를 가진 계정은 비밀번호 재설정 필요.

## Storage

- [RDSPG-STG-001] Storage Type 적정성 | severity: major | auto: true
  - 검증: describe-db-instances → StorageType 값 확인
  - 기준: gp3 권장. io1/io2도 허용. gp2/magnetic이면 FAIL.
  - 참고:
    - gp3: 최대 64,000 IOPS / 4,000 MiB/s
    - io1: 최대 256,000 IOPS / 4,000 MiB/s
    - io2: 최대 256,000 IOPS / 16,000 MiB/s (sub-ms 레이턴시)
  - 권장조치: 일반 워크로드는 gp3, I/O 집약적 OLTP는 io2 사용

## Performance

- [RDSPG-PERF-001] 인스턴스 클래스 적정성 | severity: minor | auto: true
  - 검증: `DBInstanceClass`가 메모리 최적화(db.r6g, db.r7g 등) 또는 범용(db.m6g, db.m7g 등) 타입이고 large 이상인지 확인
  - 기준: 프로덕션에서 구세대(db.r6g/db.m6g 미만) 및 large 미만 인스턴스 지양. 메모리 최적화(r 계열) 또는 범용(m 계열) large 이상 사용 권장.

- [RDSPG-PERF-002] 자동 마이너 버전 업데이트 비활성화 | severity: minor | auto: true
  - 검증: describe-db-instances → AutoMinorVersionUpgrade == false
  - 기준: 프로덕션 안정성을 위해 자동 마이너 버전 업데이트 비활성화

- [RDSPG-PERF-003] 통계 로그 비활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `log_executor_stats`와 `log_statement_stats`가 모두 `0`(off)인지 확인
  - 기준: 통계 로그 활성화 시 모든 쿼리 실행마다 추가 오버헤드가 발생하여 성능 저하 유발
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='log_executor_stats' || ParameterName=='log_statement_stats'].[ParameterName,ParameterValue]"`에서 모두 `0`이면 PASS
    - DB 내부: `SHOW log_executor_stats; SHOW log_statement_stats;` 모두 `off`이면 PASS
  - 권장조치: 두 파라미터를 `0`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-PERF-004] synchronous_commit 비활성화 권고 | severity: minor | auto: true
  - 검증: Parameter Group에서 `synchronous_commit` 값이 `off`인지 확인
  - 기준: 복제 동기화로 인한 부하를 줄일 수 있으므로 `off` 설정 권고. PASS/FAIL이 아닌 권고 사항으로 리뷰 코멘트에 남김.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='synchronous_commit'].ParameterValue"`
    - DB 내부: `SHOW synchronous_commit;`
  - 리뷰 코멘트: `off`가 아닌 경우 "synchronous_commit = off 설정 시 복제 동기화로 인한 부하를 줄일 수 있습니다. 서비스 특성에 따라 검토를 권고합니다."

## Monitoring

- [RDSPG-MON-001] Enhanced Monitoring | severity: minor | auto: true
  - 검증: `MonitoringInterval` > 0
  - 기준: Enhanced Monitoring 활성화 권장

- [RDSPG-MON-002] Performance Insights | severity: minor | auto: true
  - 검증: `PerformanceInsightsEnabled` == true
  - 기준: Performance Insights 활성화 권장

- [RDSPG-MON-003] Performance Insights 보존 기간 | severity: minor | auto: true
  - 검증: describe-db-instances → PerformanceInsightsRetentionPeriod >= 7
  - 기준: 최소 7일 이상 보존 권장

## Network & Connectivity

- [RDSPG-NET-001] default VPC 사용 금지 | severity: critical | auto: true
  - 검증: describe-db-instances → DBSubnetGroup → VpcId 확인 → ec2 describe-vpcs → IsDefault == false
  - 기준: default VPC 사용 금지, 별도 생성한 VPC에 배치 필수

## Maintenance

- [RDSPG-MNT-001] Maintenance Window 명시적 설정 | severity: minor | auto: true
  - 검증: describe-db-instances → PreferredMaintenanceWindow 값이 해당 리전의 default 랜덤 할당 블록 내에 있는지 확인
  - 기준: default 블록 밖이면 PASS (명시적 설정으로 판단). default 블록 내이면 WARNING.
  - 리전별 default 블록: ap-northeast-2(서울) = UTC 13:00~21:00, ap-northeast-1(도쿄) = UTC 13:00~21:00 등
  - WARNING 시 리뷰 코멘트: "사용자가 의도적으로 설정한 시간대인지 확인 필요"

- [RDSPG-MNT-002] Backup Window 명시적 설정 | severity: minor | auto: true
  - 검증: describe-db-instances → PreferredBackupWindow 값이 해당 리전의 default 랜덤 할당 블록 내에 있는지 확인
  - 기준: default 블록 밖이면 PASS (명시적 설정으로 판단). default 블록 내이면 WARNING.
  - WARNING 시 리뷰 코멘트: "사용자가 의도적으로 설정한 시간대인지 확인 필요"

## Instance Parameters

- [RDSPG-IP-001] log_lock_waits 활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `log_lock_waits` 값이 `1`(on)인지 확인
  - 기준: 잠금 대기 시간이 deadlock_timeout을 초과할 경우 로그에 기록하여 잠금 문제 진단에 활용
  - 권장조치: `log_lock_waits = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-IP-002] log_min_duration_statement 설정 | severity: minor | auto: true
  - 검증: Parameter Group에서 `log_min_duration_statement` 값이 -1이 아닌 양수로 설정되어 있는지 확인
  - 기준: 슬로우 쿼리 식별을 위해 임계값 설정 필수. 5000ms(5초) 이하 권장.
  - 권장조치: `log_min_duration_statement = 5000`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-IP-003] log_filename 분 단위 미포함 | severity: minor | auto: true
  - 검증: Parameter Group에서 `log_filename` 값에 `%M`(분)이 포함되어 있지 않은지 확인
  - 기준: 분 단위 로그 파일 생성 시 파일 수가 과도하게 많아져 관리 부담 증가. 시간 단위(`%Y-%m-%d-%H`) 권장.
  - 리뷰 코멘트: `%M` 포함 시 "로그 파일이 분 단위로 생성됩니다. 시간 단위(postgresql.log.%Y-%m-%d-%H) 사용을 권고합니다."

- [RDSPG-IP-004] auto_explain.log_analyze 비활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `auto_explain.log_analyze` 값이 `0`(off)인지 확인
  - 기준: 활성화 시 EXPLAIN ANALYZE가 기본 적용되어 실제 쿼리가 수행되므로 성능 저하 유발
  - 권장조치: `auto_explain.log_analyze = 0`으로 설정.

- [RDSPG-IP-005] enable_seqscan 기본값 유지 | severity: minor | auto: true
  - 검증: Parameter Group에서 `enable_seqscan` 값이 `1`(on, 기본값)인지 확인
  - 기준: 비활성화 시 옵티마이저가 sequential scan이 최적인 경우에도 사용하지 못해 오히려 성능 저하 발생 가능
  - 권장조치: `enable_seqscan = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-IP-006] force_parallel_mode 비활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `force_parallel_mode` 값이 `0`(off)인지 확인
  - 기준: 활성화 시 병렬 처리가 비효율적인 쿼리에도 강제 적용되어 성능 저하 유발
  - 권장조치: `force_parallel_mode = 0`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-IP-007] max_parallel_workers 적정성 | severity: minor | auto: true
  - 검증: Parameter Group에서 `max_parallel_workers` 값이 기본 수식 `GREATEST({DBInstanceVCPU/2},8)` 결과 이상인지 확인
  - 기준: 기본 수식보다 작게 설정된 경우 병렬 쿼리 실행이 제한되어 성능 저하 가능
  - 검증방법:
    - 파라미터 값이 수식 형태(`GREATEST({DBInstanceVCPU/2},8)`)이면 즉시 PASS (기본값 사용)
    - 고정 숫자값인 경우: 인스턴스 vCPU 수 / 2와 8 중 큰 값이 기본값. 실제 설정값 ≥ 기본값이면 PASS, 미만이면 WARNING
  - 권장조치: 기본 수식 사용을 권장. static 파라미터이므로 변경 후 인스턴스 재시작 필요.

- [RDSPG-IP-008] pg_stat_statements.max 적정성 | severity: minor | auto: true
  - 검증: Parameter Group에서 `pg_stat_statements.max` 값이 5000 이상인지 확인
  - 기준: 기본값(5000) 미만으로 설정 시 쿼리 통계가 조기 eviction되어 성능 분석 누락 발생 가능
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='pg_stat_statements.max'].ParameterValue"` 결과가 5000 이상이면 PASS
    - DB 내부: `SHOW pg_stat_statements.max;` 결과가 5000 이상이면 PASS
  - 권장조치: 기본값(5000) 이상 유지. 쿼리 종류가 많은 환경에서는 10000 이상 권장. static 파라미터이므로 변경 후 인스턴스 재시작 필요.

## Autovacuum

- [RDSPG-AV-001] autovacuum 활성화 여부 | severity: critical | auto: true
  - 검증: Parameter Group에서 `autovacuum` 값이 `1`(on)인지 확인
  - 기준: 비활성화 시 dead tuple 누적으로 bloat 증가 및 성능 저하, 최악의 경우 Transaction ID Wraparound로 DB 강제 정지 발생
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='autovacuum'].ParameterValue"` 결과가 `1`이면 PASS
    - DB 내부: `SHOW autovacuum;` 결과가 `on`이면 PASS
  - 권장조치: Parameter Group에서 `autovacuum = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [RDSPG-AV-002] track_activity_query_size 적정성 | severity: minor | auto: true
  - 검증: Parameter Group에서 `track_activity_query_size` 값이 8192 이상인지 확인
  - 기준: 기본값(4096)에서는 긴 쿼리가 잘려서 pg_stat_activity, pg_stat_statements에서 문제 쿼리 식별이 어려움. 프로덕션에서는 8192 이상 권장.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='track_activity_query_size'].ParameterValue"` 결과가 8192 이상이면 PASS
    - DB 내부: `SHOW track_activity_query_size;` 결과가 8192 이상이면 PASS
  - 권장조치: Parameter Group에서 `track_activity_query_size`를 8192 이상으로 설정. static 파라미터이므로 변경 후 DB 인스턴스 재시작 필요.

- [RDSPG-AV-003] autovacuum_max_workers 적정성 | severity: minor | auto: true
  - 검증: Parameter Group에서 `autovacuum_max_workers` 값이 기본 수식 `GREATEST({DBInstanceClassMemory/64371566592},3)` 결과 이상인지 확인
  - 기준: 기본 수식보다 작게 설정된 경우 vacuum 병렬 처리 능력이 저하되어 dead tuple 정리 지연 발생 가능
  - 검증방법:
    - 파라미터 값이 수식 형태(`GREATEST({DBInstanceClassMemory/...},3)`)이면 즉시 PASS (기본값 사용)
    - 고정 숫자값인 경우: 인스턴스 메모리(Bytes) / 64371566592 계산 후 3과 비교하여 큰 값이 기본값. 실제 설정값 ≥ 기본값이면 PASS, 미만이면 WARNING
  - 권장조치: 기본 수식 사용을 권장. 커스텀 값 설정 시 기본 수식 결과 이상으로 설정. static 파라미터이므로 변경 후 DB 인스턴스 재시작 필요.

## Memory Parameters

- [RDSPG-MEM-001] shared_buffers 적정성 | severity: major | auto: true
  - 검증: Parameter Group에서 `shared_buffers` 값을 조회하고, 인스턴스 클래스(`DBInstanceClass`)의 총 메모리 대비 비율을 확인
  - 기준:
    - 기본 수식 `{DBInstanceClassMemory/32768}` (약 25%) 사용 중이면 PASS
    - 고정값인 경우 총 메모리의 15~50% 범위이면 PASS
    - 총 메모리의 15% 미만이면 FAIL (캐시 부족으로 디스크 I/O 증가)
    - 총 메모리의 50% 초과이면 WARNING (OS 파일 캐시 부족, checkpoint 부하 증가 가능)
  - 권장조치: AWS 기본값 `{DBInstanceClassMemory/32768}` (25%) 사용을 권장. 커스텀 파라미터 그룹에서 고정값으로 설정한 경우, 인스턴스 스케일업/다운 시 반드시 재검토 필요. 변경 후 DB 인스턴스 재시작 필요.

- [RDSPG-MEM-002] work_mem 적정성 | severity: minor | auto: true
  - 검증: Parameter Group에서 `work_mem`, `max_connections`, `shared_buffers` 값을 조회하여 OOM 위험 여부를 판단
  - 기준:
    - `work_mem` = 4MB (기본값 그대로)이면 WARNING — 프로덕션에서 기본값 사용은 검토 필요
    - `work_mem × max_connections` > (총 메모리 - shared_buffers)의 75%이면 FAIL — OOM 위험
    - 4MB < `work_mem`이고 OOM 위험 없으면 PASS
  - 권장조치: `log_temp_files = 0` 설정으로 임시 파일 사용을 모니터링하고, 임시 파일이 빈번하면 work_mem 증가를 검토. dynamic 파라미터이므로 재시작 없이 변경 가능.

## Shared Preload Libraries

- [RDSPG-SPL-001] pg_stat_statements 로드 여부 | severity: critical | auto: true
  - 검증: Parameter Group에서 `shared_preload_libraries` 값에 `pg_stat_statements`가 포함되어 있는지 확인
  - 기준: 쿼리 성능 분석의 기본이며 Performance Insights의 기반. AWS 기본값에 포함되어 있으나, 커스텀 파라미터 그룹에서 다른 라이브러리 추가 시 누락될 수 있으므로 반드시 확인 필요.
  - 권장조치: Parameter Group에서 `shared_preload_libraries`에 `pg_stat_statements`를 추가. 변경 후 DB 인스턴스 재시작 필요.

- [RDSPG-SPL-002] pgaudit 로드 여부 | severity: minor | auto: true
  - 검증: Parameter Group에서 `shared_preload_libraries` 값에 `pgaudit`가 포함되어 있는지 확인
  - 기준: SQL 감사 로깅(DDL/DML/ROLE)을 위해 권장. 컴플라이언스 및 보안 감사 대응에 활용됩니다.
  - 권장조치: Parameter Group에서 `shared_preload_libraries`에 `pgaudit`를 추가하고, `pgaudit.log` 파라미터로 감사 대상을 설정. 변경 후 DB 인스턴스 재시작 필요.

- [RDSPG-SPL-003] pg_tle passcheck hook 사용 금지 | severity: critical | auto: true
  - 검증: DB Parameter Group에서 `pgtle.enable_password_check` 값이 `off`인지 확인
  - 기준: 해당 TLE의 경우 모든 계정을 포함해서 적용되는 기능이다 보니 서비스 계정이 잠기는 상황이 발생할 경우 서비스 장애 발생함
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='pgtle.enable_password_check'].ParameterValue"` 결과가 `off`이면 PASS, `on` 또는 `require`이면 FAIL
    - DB 내부: `SHOW pgtle.enable_password_check;` 결과가 `off`이면 PASS
  - 권장조치: `aws rds modify-db-parameter-group --db-parameter-group-name {group-name} --parameters "ParameterName=pgtle.enable_password_check,ParameterValue=off,ApplyMethod=immediate"`로 비활성화

## PostgreSQL Specific

- [RDSPG-PG-001] 커스텀 Parameter Group 사용 | severity: minor | auto: true
  - 검증: DBParameterGroups[].DBParameterGroupName이 default.postgres*이 아닌지 확인
  - 기준: Default 파라미터 그룹 사용 금지, 커스텀 생성 필수

- [RDSPG-PG-002] 논리적 복제 설정 | severity: minor | auto: true
  - 검증: Parameter Group에서 `rds.logical_replication`이 1인지 확인
  - 기준: 논리적 복제가 필요한 경우 활성화 권장
