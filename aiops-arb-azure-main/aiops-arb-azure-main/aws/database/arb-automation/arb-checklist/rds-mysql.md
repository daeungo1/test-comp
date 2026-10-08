# RDS MySQL ARB Checklist

RDS MySQL 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

## High Availability

- [RDSMY-HA-001] Multi-AZ 배포 | severity: critical | auto: true
  - 검증: `MultiAZ` == true
  - 기준: 프로덕션 DB는 반드시 Multi-AZ로 배포

- [RDSMY-HA-002] Read Replica 구성 | severity: major | auto: true
  - 검증: `ReadReplicaDBInstanceIdentifiers` 배열이 비어있지 않은지 확인
  - 기준: 최소 1개 Read Replica 권장

## Backup & Recovery

- [RDSMY-BR-001] PITR (Automatic Backup) 보존 기간 | severity: critical | auto: true
  - 검증: `BackupRetentionPeriod` >= 7
  - 기준: 최소 7일 이상

## Security

- [RDSMY-SEC-001] IAM 인증 비활성화 | severity: critical | auto: true
  - 검증: `IAMDatabaseAuthenticationEnabled` == false
  - 기준: IAM 인증은 사용하지 않아야 함

- [RDSMY-SEC-002] DB 포트 변경 | severity: critical | auto: true
  - 검증: `Endpoint.Port`가 3306(기본 포트)이 아닌지 확인
  - 기준: 기본 포트가 아닌 다른 포트로 변경하여 사용

- [RDSMY-SEC-003] Validate Password 플러그인 활성화 | severity: major | auto: true
  - 검증: Parameter Group에서 아래 파라미터 확인
    - `validate_password.length` >= 8
    - `validate_password.policy` = MEDIUM 이상
  - 기준: validate_password 플러그인을 활성화하고, 비밀번호 최소 길이 8자 이상, 정책 MEDIUM 이상 설정 필수

- [RDSMY-SEC-004] 계정 비밀번호 복잡도 | severity: critical | auto: false
  - 검증: 계정 비밀번호가 영문 대문자/소문자/숫자/특수문자 포함 최소 12자리 이상인지 확인
  - 기준: 비밀번호는 영문 대문자/소문자/숫자/특수문자를 모두 포함하여 최소 12자리 이상

- [RDSMY-SEC-005] 비밀번호 SHA256 알고리즘 적용 | severity: major | auto: true
  - 검증: Parameter Group에서 `default_authentication_plugin`이 `caching_sha2_password`인지 확인
  - 기준: 비밀번호는 SHA256 알고리즘(caching_sha2_password) 적용

- [RDSMY-SEC-006] 개인 사용자 비밀번호 정책 적용 | severity: major | auto: false
  - 검증: 개인 사용자 계정에 비밀번호 정책이 모두 적용되어 있는지 확인
  - 기준: 개인 사용자는 비밀번호 정책을 모두 적용하여 생성

## Performance

- [RDSMY-PERF-001] 인스턴스 클래스 적정성 | severity: minor | auto: true
  - 검증: `DBInstanceClass`가 최신 세대 인스턴스인지 확인. Graviton 기반(db.m7g, db.r7g, db.m6g, db.r6g 등 `g` 접미사) 사용 여부 확인
  - 기준: 최신 세대 인스턴스를 사용하고, 가능하면 Graviton 기반 인스턴스 사용 권장. 구세대(db.m5, db.r5, db.t2, db.t3 등) 및 burstable 소형 인스턴스 지양

## Monitoring

- [RDSMY-MON-002] CloudWatch Database Insights (DBI) 보존 기간 | severity: minor | auto: true
  - 검증: describe-db-instances → PerformanceInsightsRetentionPeriod >= 7
  - 기준: 최소 7일 이상 보존 필수 (Performance Insights는 2026-06-30 EOL, DBI로 전환 필요)

## MySQL Engine Version

- [RDSMY-MY-001] MySQL Major 버전 | severity: critical | auto: true
  - 검증: `EngineVersion`의 Major 버전이 8.4인지 확인
  - 기준: Major 버전은 8.4 사용 (8.0은 EOL 예정)

- [RDSMY-MY-002] 엔진 버전 EOL 확인 | severity: critical | auto: true
  - 검증: describe-db-instances → EngineVersion이 deprecated 상태가 아닌지 확인
  - 기준: deprecated 버전 사용 시 FAIL, available 버전 사용 시 PASS
  - deprecated 판정: `aws rds describe-db-engine-versions --engine mysql --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
  - 리포트 표기 원칙 (중요):
    - **검증 대상 버전(메이저/마이너)을 기준으로만** 지원 종료 정보를 제공한다. 검증 대상보다 낮은 메이저 버전(예: 5.7)의 EOL 정보는 오해를 유발하므로 표기하지 않는다.
    - 검증 대상이 **마이너 버전**(예: 8.0.40)인 경우, 다음을 **명확히 구분하여** 표기한다.
      - 현재 사용 중인 **메이저 버전**(예: MySQL 8.0)의 RDS 표준 지원 종료일
      - 현재 사용 중인 **마이너 버전**(예: 8.0.40) 자체의 RDS 표준 지원 종료일
    - 마이너 버전의 표준 지원 종료일은 메이저 버전보다 빠를 수 있으므로(예: 8.0.40 → 2026-05-31, 메이저 8.0 → 2026-07-31), 마이너 버전 종료일을 반드시 별도로 명시하여 "메이저 EOL까지 여유가 있다"는 오해를 방지한다.
  - 조회 방법:
    - 마이너 버전 종료일: `aws rds describe-db-engine-versions --engine mysql --engine-version {major.minor.patch} --include-all` 응답에서 lifecycle/지원 종료 정보 확인. (API 권한이 없거나 필드가 없으면 AWS RDS for MySQL Release Calendar의 minor version 표 참조)
    - 메이저 버전 종료일: `aws rds describe-db-major-engine-versions --engine mysql` (또는 Release Calendar major version 표) 참조
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Concepts.VersionMgmt.html

- [RDSMY-MY-003] 자동 마이너 버전 업데이트 비활성화 | severity: minor | auto: true
  - 검증: `AutoMinorVersionUpgrade` == false
  - 기준: 의도하지 않은 버전 변경 방지를 위해 자동 마이너 버전 업데이트 비활성화

## MySQL Parameter Group

- [RDSMY-MY-010] 커스텀 Parameter Group 사용 | severity: major | auto: true
  - 검증: `DBParameterGroups[].DBParameterGroupName`이 `default.mysql*`이 아닌지 확인
  - 기준: 기본 Parameter Group을 사용하지 않고 신규 생성하여 사용

- [RDSMY-MY-011] binlog_format 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 `binlog_format` == ROW
  - 기준: Replication 안정성을 위해 binlog_format은 ROW 권장

- [RDSMY-MY-012] Collation 설정 확인 | severity: minor | auto: true
  - 검증: Parameter Group에서 `collation_server` 값 확인
  - 기준: 서비스에서 의도한 Collation이 설정되어 있어야 함

- [RDSMY-MY-013] Character Set 설정 확인 | severity: minor | auto: true
  - 검증: Parameter Group에서 `character_set_server`, `character_set_database` 값 확인
  - 기준: 서비스에서 의도한 Character Set이 설정되어 있어야 함

- [RDSMY-MY-014] 테이블 이름 대소문자 구분 비활성화 | severity: minor | auto: true
  - 검증: Parameter Group에서 `lower_case_table_names` == 1
  - 기준: 테이블 이름을 대소문자 구분하지 않도록 설정

- [RDSMY-MY-015] 로그 파일 산출물 설정 | severity: minor | auto: true
  - 검증: `EnabledCloudwatchLogsExports`에 general, audit, error, slowquery 로그가 포함되어 있는지 확인
  - 기준: 필요한 로그 파일이 CloudWatch Logs로 내보내기 설정되어 있어야 함

- [RDSMY-MY-016] InnoDB Buffer Pool 설정 | severity: minor | auto: true
  - 검증: Parameter Group에서 `innodb_buffer_pool_size` 값이 인스턴스 메모리의 적정 비율(일반적으로 75~80%)로 설정되어 있는지 확인
  - 기준: 인스턴스 사양을 고려하여 적절하게 설정

- [RDSMY-MY-017] max_allowed_packet 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 `max_allowed_packet` == 1073741824 (1GB)
  - 기준: max_allowed_packet은 1073741824 (1GB)로 설정

- [RDSMY-MY-018] log_bin_trust_function_creator 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 `log_bin_trust_function_creator` == ON
  - 기준: Stored Function/Trigger 사용 시 Replication 안정성을 위해 ON 설정 필수

- [RDSMY-MY-019] Buffer Size 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 아래 파라미터 값 확인
    - `sort_buffer_size` = 8388608 (8MB)
    - `join_buffer_size` = 8388608 (8MB)
    - `read_buffer_size` = 8388608 (8MB)
    - `read_rnd_buffer_size` = 8388608 (8MB)
  - 기준: 하나라도 불일치하면 FAIL

- [RDSMY-MY-022] log_output 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 `log_output` == FILE
  - 기준: 로그 출력을 FILE로 설정하여 CloudWatch Logs 연동

- [RDSMY-MY-023] InnoDB Open Files 설정 | severity: minor | auto: true
  - 검증: Parameter Group에서 `innodb_open_files` == 65536
  - 기준: 대량 테이블 환경 대비 innodb_open_files를 65536으로 설정

- [RDSMY-MY-024] InnoDB IO Capacity 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 아래 파라미터 값 확인
    - `innodb_io_capacity` = 2000
    - `innodb_io_capacity_max` = 4000
  - 기준: gp3 스토리지 성능에 맞게 IO Capacity 설정

- [RDSMY-MY-025] long_query_time 설정 | severity: major | auto: true
  - 검증: Parameter Group에서 `long_query_time` <= 1
  - 기준: 슬로우 쿼리 감지 임계값을 1초 이하로 설정

- [RDSMY-MY-026] InnoDB Deadlock 로깅 | severity: minor | auto: true
  - 검증: Parameter Group에서 `innodb_print_all_deadlocks` == 1
  - 기준: Deadlock 발생 시 에러 로그에 기록되도록 활성화

- [RDSMY-MY-027] InnoDB Parallel Read Threads 설정 | severity: minor | auto: true
  - 검증: Parameter Group에서 `innodb_parallel_read_threads` == 2
  - 기준: 병렬 읽기 스레드 수를 2로 설정

## MySQL Schema Design

- [RDSMY-MY-020] FK 미사용 설계 | severity: major | auto: false
  - 검증: FK(Foreign Key)를 사용하지 않도록 설계되어 있는지 확인
  - 기준: FK 사용 금지

- [RDSMY-MY-021] Procedure 제약사항 확인 | severity: minor | auto: false
  - 검증: Stored Procedure 사용 시 제약사항 검토 여부 확인
  - 기준: Procedure 제약사항을 확인하고 준수

## DB Server Infrastructure

- [RDSMY-MY-030] Instance Name Rule 준수 | severity: minor | auto: true
  - 검증: `DBInstanceIdentifier`가 네이밍 규칙을 준수하는지 확인
  - 기준: 정해진 Instance Name Rule을 준수하여 생성

- [RDSMY-MY-031] Storage Type gp3 사용 | severity: major | auto: true
  - 검증: `StorageType` == gp3
  - 기준: Storage Type은 gp3만 사용


