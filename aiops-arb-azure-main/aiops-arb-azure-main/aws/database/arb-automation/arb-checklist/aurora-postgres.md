# Aurora PostgreSQL ARB Checklist

Aurora PostgreSQL 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

## High Availability

- [AURPG-HA-001] 클러스터 인스턴스 수 | severity: critical | auto: true
  - 검증: 클러스터 내 인스턴스가 2개 이상인지 확인
  - 기준: Writer + 최소 1개 Reader 구성 필수

- [AURPG-HA-002] Multi-AZ 분산 | severity: critical | auto: true
  - 검증: 클러스터 인스턴스가 2개 이상의 AZ에 분산되어 있는지 확인
  - 기준: 단일 AZ 장애 대비

- [AURPG-HA-003] Global Database 구성 | severity: minor | auto: true
  - 검증: Global Database에 포함되어 있는지 확인
  - 기준: DR 요구사항이 있는 경우 Global Database 권장

- [AURPG-HA-004] Writer/Reader 인스턴스 클래스 동일성 | severity: major | auto: true
  - 검증: 클러스터 내 모든 인스턴스의 DBInstanceClass가 동일한지 확인
  - 기준: Failover 시 성능 저하 방지를 위해 Writer와 Reader는 동일 인스턴스 클래스 사용 권장

- [AURPG-HA-005] 클러스터 엔진 버전 LTS 사용 | severity: critical | auto: true
  - 검증: describe-db-clusters → EngineVersion이 Aurora PostgreSQL LTS 버전인지 확인
  - 기준: 안정성을 위해 LTS 버전 사용 권장
  - LTS 버전 확인 방법: AWS 공식 문서(https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Updates.LTS.html) 참조
  - deprecated 판정: `aws rds describe-db-engine-versions --engine aurora-postgresql --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
  - 참고: LTS 버전이 아닌 경우 WARNING, deprecated 버전인 경우 FAIL
  - 리포트 표기 원칙 (중요):
    - **검증 대상 버전(메이저/마이너)을 기준으로만** 지원 종료 정보를 제공한다. 검증 대상보다 낮은 메이저 버전의 EOL 정보는 오해를 유발하므로 표기하지 않는다.
    - 검증 대상이 **마이너 버전**(예: 17.9)인 경우, 다음을 **명확히 구분하여** 표기한다.
      - 현재 사용 중인 **메이저 버전 라인**(예: PostgreSQL 17)의 Aurora 표준 지원 종료일
      - 현재 사용 중인 **마이너 버전**(예: 17.9) 자체의 Aurora 표준 지원 종료일
      - 해당 마이너가 **LTS인지 여부**, 그리고 같은 메이저 라인의 LTS 버전(예: 17.7 LTS) 종료일과의 차이
    - Aurora는 같은 메이저 라인 안에서도 마이너 버전(특히 non-LTS)의 표준 지원 종료일이 LTS/메이저보다 크게 빠를 수 있으므로(예: 17.9 → 2027-09, 17.7 LTS → 2030-02, 메이저 17 → 2030-02), 마이너 버전 종료일을 반드시 별도로 명시하여 "메이저/LTS EOL까지 여유가 있다"는 오해를 방지한다.
    - non-LTS 마이너 버전을 사용 중이면, LTS 버전으로 전환 시 동일 메이저 라인에서 지원 기간을 크게 늘릴 수 있음을 함께 안내한다.
  - 조회 방법:
    - 마이너 버전 종료일: AWS Aurora PostgreSQL Release Calendar의 minor version 표 참조 (또는 `aws rds describe-db-engine-versions --engine aurora-postgresql --engine-version {major.minor} --include-all` 의 lifecycle 정보)
    - 메이저 버전 종료일: `aws rds describe-db-major-engine-versions --engine aurora-postgresql` (또는 Release Calendar major version 표) 참조
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/aurorapostgresql-release-calendar.html

## Backup & Recovery

- [AURPG-BR-001] 백업 보존 기간 | severity: critical | auto: true
  - 검증: `BackupRetentionPeriod` >= 7
  - 기준: 최소 7일 이상

## Security

- [AURPG-SEC-001] Default Port 사용 금지 | severity: critical | auto: true
  - 검증: 클러스터의 `Port` != 5432
  - 기준: PostgreSQL 기본 포트(5432) 사용을 지양하고, 비표준 포트를 사용하여 port scanning 공격 표면을 축소해야 합니다.
  - 권장조치: `aws rds modify-db-cluster --db-cluster-identifier {id} --port {new-port}`로 변경. 유효 범위 1150~65535. 포트 변경 시 클러스터 내 전체 인스턴스(Writer + Reader)가 영향을 받으므로 서비스 점검 시간에 수행 필요. 변경 후 Security Group 인바운드 규칙, 애플리케이션 connection string, Reader Endpoint 참조도 함께 업데이트해야 합니다.

- [AURPG-SEC-002] password_encryption scram-sha-256 사용 | severity: major | auto: true
  - 검증: DB Parameter Group에서 `password_encryption` 값이 `scram-sha-256`인지 확인
  - 기준: MD5는 취약한 해시 알고리즘으로, 계정 패스워드 저장 방식은 반드시 scram-sha-256을 사용해야 합니다. PostgreSQL 14 이상 기본값이지만 구버전 업그레이드 시 md5로 남아있을 수 있음.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='password_encryption'].ParameterValue"` 결과가 `scram-sha-256`이면 PASS
    - DB 내부: `SHOW password_encryption;` 결과가 `scram-sha-256`이면 PASS
  - 권장조치: `password_encryption = scram-sha-256`으로 설정. 변경 후 기존 MD5 비밀번호를 가진 계정은 비밀번호 재설정 필요.

## Performance

- [AURPG-PERF-001] 인스턴스 클래스 적정성 | severity: minor | auto: true
  - 검증: `DBInstanceClass`가 메모리 최적화 타입(db.r6g, db.r7g 등)이고 현행 세대인지 확인
  - 기준: 프로덕션에서 구세대(db.r6g 미만) 및 large 미만 인스턴스 지양. 메모리 최적화(r 계열) large 이상 사용 권장.

- [AURPG-PERF-002] 자동 마이너 버전 업데이트 비활성화 | severity: minor | auto: true
  - 검증: describe-db-instances → AutoMinorVersionUpgrade == false
  - 기준: 프로덕션 안정성을 위해 자동 마이너 버전 업데이트 비활성화

- [AURPG-PERF-003] 통계 로그 비활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `log_executor_stats`와 `log_statement_stats`가 모두 `0`(off)인지 확인
  - 기준: 통계 로그 활성화 시 모든 쿼리 실행마다 추가 오버헤드가 발생하여 성능 저하 유발
  - 검증방법:
    - AWS CLI: `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {group-name} --query "Parameters[?ParameterName=='log_executor_stats' || ParameterName=='log_statement_stats'].[ParameterName,ParameterValue]"`에서 모두 `0`이면 PASS
    - DB 내부: `SHOW log_executor_stats; SHOW log_statement_stats;` 모두 `off`이면 PASS
  - 권장조치: 두 파라미터를 `0`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-PERF-004] synchronous_commit 비활성화 권고 | severity: minor | auto: true
  - 검증: Cluster Parameter Group에서 `synchronous_commit` 값이 `off`인지 확인
  - 기준: 복제 동기화로 인한 부하를 줄일 수 있으므로 `off` 설정 권고. PASS/FAIL이 아닌 권고 사항으로 리뷰 코멘트에 남김.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {group-name} --query "Parameters[?ParameterName=='synchronous_commit'].ParameterValue"`
    - DB 내부: `SHOW synchronous_commit;`
  - 리뷰 코멘트: `off`가 아닌 경우 "synchronous_commit = off 설정 시 복제 동기화로 인한 부하를 줄일 수 있습니다. 서비스 특성에 따라 검토를 권고합니다."

## Monitoring

- [AURPG-MON-001] Performance Insights | severity: minor | auto: true
  - 검증: `PerformanceInsightsEnabled` == true
  - 기준: Performance Insights 활성화 권장

- [AURPG-MON-002] Enhanced Monitoring | severity: minor | auto: true
  - 검증: `MonitoringInterval` > 0
  - 기준: Enhanced Monitoring 활성화 권장

- [AURPG-MON-003] Performance Insights 보존 기간 | severity: minor | auto: true
  - 검증: describe-db-instances → PerformanceInsightsRetentionPeriod >= 7
  - 기준: 최소 7일 이상 보존 권장

## Network & Connectivity

- [AURPG-NET-001] default VPC 사용 금지 | severity: critical | auto: true
  - 검증: describe-db-clusters → DBSubnetGroup → VpcId 확인 → ec2 describe-vpcs → IsDefault == false
  - 기준: default VPC 사용 금지, 별도 생성한 VPC에 배치 필수

## Maintenance

- [AURPG-MNT-001] Maintenance Window 명시적 설정 | severity: minor | auto: true
  - 검증: describe-db-clusters → PreferredMaintenanceWindow 값이 해당 리전의 default 랜덤 할당 블록 내에 있는지 확인
  - 기준: default 블록 밖이면 PASS (명시적 설정으로 판단). default 블록 내이면 WARNING.
  - 리전별 default 블록: ap-northeast-2(서울) = UTC 13:00~21:00, ap-northeast-1(도쿄) = UTC 13:00~21:00 등
  - WARNING 시 리뷰 코멘트: "사용자가 의도적으로 설정한 시간대인지 확인 필요"

- [AURPG-MNT-002] Backup Window 명시적 설정 | severity: minor | auto: true
  - 검증: describe-db-clusters → PreferredBackupWindow 값이 해당 리전의 default 랜덤 할당 블록 내에 있는지 확인
  - 기준: default 블록 밖이면 PASS (명시적 설정으로 판단). default 블록 내이면 WARNING.
  - WARNING 시 리뷰 코멘트: "사용자가 의도적으로 설정한 시간대인지 확인 필요"

## Instance Parameters

- [AURPG-IP-001] log_lock_waits 활성화 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `log_lock_waits` 값이 `1`(on)인지 확인
  - 기준: 잠금 대기 시간이 deadlock_timeout을 초과할 경우 로그에 기록하여 잠금 문제 진단에 활용
  - 권장조치: `log_lock_waits = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-IP-002] log_min_duration_statement 설정 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `log_min_duration_statement` 값이 -1이 아닌 양수로 설정되어 있는지 확인
  - 기준: 슬로우 쿼리 식별을 위해 임계값 설정 필수. 5000ms(5초) 이하 권장.
  - 권장조치: `log_min_duration_statement = 5000`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-IP-003] log_filename 분 단위 미포함 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `log_filename` 값에 `%M`(분)이 포함되어 있지 않은지 확인
  - 기준: 분 단위 로그 파일 생성 시 파일 수가 과도하게 많아져 관리 부담 증가. 시간 단위(`%Y-%m-%d-%H`) 권장.
  - 리뷰 코멘트: `%M` 포함 시 "로그 파일이 분 단위로 생성됩니다. 시간 단위(postgresql.log.%Y-%m-%d-%H) 사용을 권고합니다."

- [AURPG-IP-004] auto_explain.log_analyze 비활성화 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `auto_explain.log_analyze` 값이 `0`(off)인지 확인
  - 기준: 활성화 시 EXPLAIN ANALYZE가 기본 적용되어 실제 쿼리가 수행되므로 성능 저하 유발
  - 권장조치: `auto_explain.log_analyze = 0`으로 설정.

- [AURPG-IP-005] enable_seqscan 기본값 유지 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `enable_seqscan` 값이 `1`(on, 기본값)인지 확인
  - 기준: 비활성화 시 옵티마이저가 sequential scan이 최적인 경우에도 사용하지 못해 오히려 성능 저하 발생 가능
  - 권장조치: `enable_seqscan = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-IP-006] force_parallel_mode 비활성화 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `force_parallel_mode` 값이 `0`(off)인지 확인
  - 기준: 활성화 시 병렬 처리가 비효율적인 쿼리에도 강제 적용되어 성능 저하 유발
  - 권장조치: `force_parallel_mode = 0`으로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-IP-007] max_parallel_workers 적정성 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `max_parallel_workers` 값이 기본 수식 `GREATEST({DBInstanceVCPU/2},8)` 결과 이상인지 확인
  - 기준: 기본 수식보다 작게 설정된 경우 병렬 쿼리 실행이 제한되어 성능 저하 가능
  - 검증방법:
    - 파라미터 값이 수식 형태(`GREATEST({DBInstanceVCPU/2},8)`)이면 즉시 PASS (기본값 사용)
    - 고정 숫자값인 경우: 인스턴스 vCPU 수 / 2와 8 중 큰 값이 기본값. 실제 설정값 ≥ 기본값이면 PASS, 미만이면 WARNING
  - 권장조치: 기본 수식 사용을 권장. static 파라미터이므로 변경 후 인스턴스 재시작 필요.

- [AURPG-IP-008] pg_stat_statements.max 적정성 | severity: minor | auto: true
  - 검증: DB Parameter Group에서 `pg_stat_statements.max` 값이 5000 이상인지 확인
  - 기준: 기본값(5000) 미만으로 설정 시 쿼리 통계가 조기 eviction되어 성능 분석 누락 발생 가능
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='pg_stat_statements.max'].ParameterValue"` 결과가 5000 이상이면 PASS
    - DB 내부: `SHOW pg_stat_statements.max;` 결과가 5000 이상이면 PASS
  - 권장조치: 기본값(5000) 이상 유지. 쿼리 종류가 많은 환경에서는 10000 이상 권장. static 파라미터이므로 변경 후 인스턴스 재시작 필요.

## Autovacuum

- [AURPG-AV-001] autovacuum 활성화 여부 | severity: critical | auto: true
  - 검증: Cluster Parameter Group에서 `autovacuum` 값이 `1`(on)인지 확인
  - 기준: 비활성화 시 dead tuple 누적으로 bloat 증가 및 성능 저하, 최악의 경우 Transaction ID Wraparound로 DB 강제 정지 발생
  - 검증방법:
    - AWS CLI: `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {group-name} --query "Parameters[?ParameterName=='autovacuum'].ParameterValue"` 결과가 `1`이면 PASS
    - DB 내부: `SHOW autovacuum;` 결과가 `on`이면 PASS
  - 권장조치: Cluster Parameter Group에서 `autovacuum = 1`로 설정. dynamic 파라미터이므로 재시작 없이 변경 가능.

- [AURPG-AV-002] track_activity_query_size 적정성 | severity: minor | auto: true
  - 검증: Cluster Parameter Group에서 `track_activity_query_size` 값이 8192 이상인지 확인
  - 기준: 기본값(4096)에서는 긴 쿼리가 잘려서 pg_stat_activity, pg_stat_statements에서 문제 쿼리 식별이 어려움. 프로덕션에서는 8192 이상 권장.
  - 검증방법:
    - AWS CLI: `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name {group-name} --query "Parameters[?ParameterName=='track_activity_query_size'].ParameterValue"` 결과가 8192 이상이면 PASS
    - DB 내부: `SHOW track_activity_query_size;` 결과가 8192 이상이면 PASS
  - 권장조치: Cluster Parameter Group에서 `track_activity_query_size`를 8192 이상으로 설정. static 파라미터이므로 변경 후 클러스터 내 전체 인스턴스 재시작 필요.

- [AURPG-AV-003] autovacuum_max_workers 적정성 | severity: minor | auto: true
  - 검증: Cluster Parameter Group에서 `autovacuum_max_workers` 값이 기본 수식 `GREATEST({DBInstanceClassMemory/64371566592},3)` 결과 이상인지 확인
  - 기준: 기본 수식보다 작게 설정된 경우 vacuum 병렬 처리 능력이 저하되어 dead tuple 정리 지연 발생 가능
  - 검증방법:
    - 파라미터 값이 수식 형태(`GREATEST({DBInstanceClassMemory/...},3)`)이면 즉시 PASS (기본값 사용)
    - 고정 숫자값인 경우: 인스턴스 메모리(Bytes) / 64371566592 계산 후 3과 비교하여 큰 값이 기본값. 실제 설정값 ≥ 기본값이면 PASS, 미만이면 WARNING
  - 권장조치: 기본 수식 사용을 권장. 커스텀 값 설정 시 기본 수식 결과 이상으로 설정. static 파라미터이므로 변경 후 클러스터 내 전체 인스턴스 재시작 필요.

## Memory Parameters

- [AURPG-MEM-001] work_mem 적정성 | severity: minor | auto: true
  - 검증: DB Parameter Group(인스턴스 레벨)에서 `work_mem`, `max_connections` 값을 조회하여 OOM 위험 여부를 판단
  - 기준:
    - `work_mem` = 4MB (기본값 그대로)이면 WARNING — 프로덕션에서 기본값 사용은 검토 필요
    - `work_mem × max_connections` > (총 메모리 - shared_buffers)의 75%이면 FAIL — OOM 위험
    - 4MB < `work_mem`이고 OOM 위험 없으면 PASS
  - 권장조치: `log_temp_files = 0` 설정으로 임시 파일 사용을 모니터링하고, 임시 파일이 빈번하면 work_mem 증가를 검토. dynamic 파라미터이므로 재시작 없이 변경 가능.

## Shared Preload Libraries

- [AURPG-SPL-001] pg_stat_statements 로드 여부 | severity: critical | auto: true
  - 검증: Cluster Parameter Group에서 `shared_preload_libraries` 값에 `pg_stat_statements`가 포함되어 있는지 확인
  - 기준: 쿼리 성능 분석의 기본이며 Performance Insights의 기반. AWS 기본값에 포함되어 있으나, 커스텀 파라미터 그룹에서 다른 라이브러리 추가 시 누락될 수 있으므로 반드시 확인 필요.
  - 권장조치: Cluster Parameter Group에서 `shared_preload_libraries`에 `pg_stat_statements`를 추가. 변경 후 클러스터 내 전체 인스턴스 재시작 필요.

- [AURPG-SPL-002] pgaudit 로드 여부 | severity: minor | auto: true
  - 검증: Cluster Parameter Group에서 `shared_preload_libraries` 값에 `pgaudit`가 포함되어 있는지 확인
  - 기준: SQL 감사 로깅(DDL/DML/ROLE)을 위해 권장. 컴플라이언스 및 보안 감사 대응에 활용됩니다.
  - 권장조치: Cluster Parameter Group에서 `shared_preload_libraries`에 `pgaudit`를 추가하고, `pgaudit.log` 파라미터로 감사 대상을 설정. 변경 후 클러스터 내 전체 인스턴스 재시작 필요.

- [AURPG-SPL-003] pg_tle passcheck hook 사용 금지 | severity: critical | auto: true
  - 검증: DB Parameter Group(인스턴스 레벨)에서 `pgtle.enable_password_check` 값이 `off`인지 확인
  - 기준: 해당 TLE의 경우 모든 계정을 포함해서 적용되는 기능이다 보니 서비스 계정이 잠기는 상황이 발생할 경우 서비스 장애 발생함
  - 검증방법:
    - AWS CLI: `aws rds describe-db-parameters --db-parameter-group-name {group-name} --query "Parameters[?ParameterName=='pgtle.enable_password_check'].ParameterValue"` 결과가 `off`이면 PASS, `on` 또는 `require`이면 FAIL
    - DB 내부: `SHOW pgtle.enable_password_check;` 결과가 `off`이면 PASS
  - 권장조치: `aws rds modify-db-parameter-group --db-parameter-group-name {group-name} --parameters "ParameterName=pgtle.enable_password_check,ParameterValue=off,ApplyMethod=immediate"`로 비활성화

## PostgreSQL Specific

- [AURPG-PG-001] Cluster Parameter Group 커스텀 사용 | severity: minor | auto: true
  - 검증: describe-db-clusters → DBClusterParameterGroup이 default.aurora-postgresql*이 아닌지 확인
  - 기준: Default 파라미터 그룹 사용 금지, 커스텀 생성 필수

- [AURPG-PG-002] DB Parameter Group 커스텀 사용 | severity: minor | auto: true
  - 검증: describe-db-instances → DBParameterGroups[].DBParameterGroupName이 default.*이 아닌지 확인
  - 기준: Default 파라미터 그룹 사용 금지, 커스텀 생성 필수

- [AURPG-PG-003] 인스턴스 네이밍 역할명 미포함 | severity: minor | auto: true
  - 검증: 클러스터 내 각 인스턴스의 `DBInstanceIdentifier`에 역할을 나타내는 단어가 포함되지 않았는지 확인
  - 차단 키워드: writer, reader, master, replica, primary, secondary, slave, wo, ro
  - 기준: Failover 시 역할이 변경되므로 인스턴스명에 역할명을 포함하면 안 됨

- [AURPG-PG-004] 논리적 복제 설정 | severity: minor | auto: true
  - 검증: Cluster Parameter Group에서 `rds.logical_replication`이 1인지 확인
  - 기준: 논리적 복제가 필요한 경우 활성화 권장

## Account Management (수동 확인)

- [AURPG-ACC-001] DB 계정 서비스/관리자/개인 분류 | severity: major | auto: false
  - 검증: DB 계정이 서비스 계정(WAS), 관리자 계정(DBA), 개인 사용자 계정(개발자)으로 분류되어 있는지 확인
  - 기준: 계정 용도별 분류 필수

- [AURPG-ACC-002] 개인 사용자 계정 1인 1계정 원칙 | severity: major | auto: false
  - 검증: 개인 사용자 계정이 1인 1계정으로 발급되었는지 확인
  - 기준: 공용 계정 사용 금지

- [AURPG-ACC-003] postgres 기본 마스터 유저명 미사용 | severity: critical | auto: false
  - 검증: postgres 마스터 계정을 서비스(애플리케이션)에서 직접 사용하지 않는지 확인
  - 기준: 마스터 계정은 관리 목적으로만 사용, 서비스 계정은 별도 생성 필수

- [AURPG-ACC-004] 개인 사용자 계정 조회 권한만 부여 | severity: major | auto: false
  - 검증: 개인 사용자 계정에 DML, DDL 권한이 부여되지 않았는지 확인
  - 기준: 개인 계정은 SELECT 권한만 부여

- [AURPG-ACC-005] DB 계정 관리 DBA 담당 | severity: minor | auto: false
  - 검증: DB 계정 관리 업무를 DBA가 담당하고 있는지 확인
  - 기준: 계정 관리 책임자 명확화

- [AURPG-ACC-006] DB 계정 신규/변경/삭제 프로세스 | severity: minor | auto: false
  - 검증: DB 계정 생성/변경/삭제에 대한 프로세스가 구성되어 있는지 확인
  - 기준: 계정 관리 프로세스 문서화 필수

- [AURPG-ACC-007] DB 계정 권한 리스트 문서 관리 | severity: minor | auto: false
  - 검증: 계정 발급 관리 문서가 갱신 및 보관되고 있는지 확인
  - 기준: 계정 권한 현황 문서 최신 유지

- [AURPG-ACC-008] DB 계정 내역 5년 보관 | severity: minor | auto: false
  - 검증: 계정 신규/변경/삭제 내역(결재 문서)을 5년간 보관하고 있는지 확인
  - 기준: 감사 대비 5년 보관 필수

- [AURPG-ACC-009] Instance Name Rule 준수 | severity: minor | auto: false
  - 검증: DBClusterIdentifier가 조직 네이밍 규칙을 준수하는지 확인
  - 기준: 서비스별 네이밍 규칙에 따라 생성해야 함

## Schema Design (수동 확인)

- [AURPG-SCH-001] FK 미사용 설계 | severity: major | auto: false
  - 검증: FK(Foreign Key)를 사용하지 않도록 설계되어 있는지 확인
  - 기준: FK 사용 금지

- [AURPG-SCH-002] Function/Procedure 제약사항 확인 | severity: minor | auto: false
  - 검증: Function/Procedure 사용 시 제약사항을 확인하였는지 확인
  - 기준: Function 내 COMMIT/ROLLBACK 불가(Procedure에서만 가능), 실행 계획 추적 제한, SECURITY DEFINER 권한 상승 위험, pg_stat_statements 내부 쿼리 추적 제한 등 검토 필수

- [AURPG-SCH-003] 테이블 PK 타입 확인 | severity: minor | auto: false
  - 검증: 테이블 PK가 정수형 자동 증가(SERIAL/BIGSERIAL/IDENTITY) 또는 UUID로 생성되었는지 확인
  - 기준: 의도된 설계인지 검토. 정수형 자동 증가 또는 UUID 사용 권장

- [AURPG-SCH-004] 중복 체크 UK 또는 로직단 처리 | severity: minor | auto: false
  - 검증: 중복 체크가 필요한 컬럼에 UNIQUE 제약조건을 생성하거나 로직단에서 처리하는지 확인
  - 기준: DB 레벨 UNIQUE 제약 우선 사용 권장, 로직단만 의존 시 race condition 위험

- [AURPG-SCH-005] 인덱스 네이밍룰 준수 | severity: minor | auto: false
  - 검증: 테이블 인덱스 생성 시 네이밍룰을 준수하였는지 확인
  - 기준: 조직 인덱스 네이밍 규칙 준수
