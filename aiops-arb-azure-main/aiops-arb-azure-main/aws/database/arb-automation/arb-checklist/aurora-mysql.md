# Aurora MySQL ARB Checklist

Aurora MySQL 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

## High Availability

- [AURMY-HA-001] 클러스터 인스턴스 수 | severity: critical | auto: true
  - 검증: 클러스터 내 인스턴스가 2개 이상인지 확인
  - 기준: Writer + 최소 1개 Reader 구성 필수

- [AURMY-HA-002] Multi-AZ 분산 | severity: critical | auto: true
  - 검증: 클러스터 인스턴스가 2개 이상의 AZ에 분산되어 있는지 확인
  - 기준: 단일 AZ 장애 대비

- [AURMY-HA-003] Global Database 구성 | severity: minor | auto: true
  - 검증: Global Database에 포함되어 있는지 확인
  - 기준: DR 요구사항이 있는 경우 Global Database 권장

- [AURMY-HA-004] Reader Failover Priority 분산 | severity: minor | auto: true
  - 검증: describe-db-instances → PromotionTier 값이 적절히 분산되어 있는지 확인
  - 기준: Failover 시 승격 우선순위가 명확하게 설정되어야 함

- [AURMY-HA-005] 클러스터 엔진 버전 LTS 사용 | severity: critical | auto: true
  - 검증: describe-db-clusters → EngineVersion이 Aurora MySQL LTS 버전인지 확인
  - 기준: 안정성을 위해 LTS 버전 사용 필수
  - 참고: EOL 정보는 검증 대상 버전 기준으로만 표기하며, 마이너 버전의 표준 지원 종료일을 메이저 라인/LTS 종료일과 구분하여 명시 (리포트 표기 규칙은 reviewer 출력 규칙 참조)

- [AURMY-HA-006] Writer/Reader 인스턴스 클래스 동일성 | severity: major | auto: true
  - 검증: 클러스터 내 모든 인스턴스의 DBInstanceClass가 동일한지 확인
  - 기준: Failover 시 성능 저하 방지를 위해 동일 클래스 권장

## Backup & Recovery

- [AURMY-BR-001] PITR (Automatic Backup) 보존 기간 | severity: critical | auto: true
  - 검증: `BackupRetentionPeriod` >= 7
  - 기준: 최소 7일 이상

- [AURMY-BR-002] Backtrack 활성화 | severity: minor | auto: true
  - 검증: `EarliestBacktrackTime`이 존재하는지 확인
  - 기준: 빠른 복구를 위해 Backtrack 권장 (Aurora MySQL 전용 기능)

- [AURMY-BR-003] Cross-Region 스냅샷 복사본 존재 | severity: minor | auto: true
  - 검증: describe-db-cluster-snapshots로 다른 리전 복사본 존재 여부 확인
  - 기준: DR 대비 Cross-Region 스냅샷 복사 권장

- [AURMY-BR-004] Point-in-Time Recovery 가능 상태 | severity: major | auto: true
  - 검증: describe-db-clusters → EarliestRestorableTime 존재 확인
  - 기준: PITR이 정상 동작 가능한 상태여야 함

## Security

- [AURMY-SEC-001] Default Port 변경 | severity: critical | auto: true
  - 검증: describe-db-clusters → Port != 3306
  - 기준: 보안을 위해 기본 포트(3306) 사용 지양

- [AURMY-SEC-002] 비밀번호 정책 설정 | severity: major | auto: true
  - 검증: describe-db-cluster-parameters로 아래 확인
    - validate_password 관련 파라미터 활성화 여부
    - validate_password_length >= 8
    - validate_password_policy = MEDIUM 이상
    - default_authentication_plugin = caching_sha2_password
  - 기준: 비밀번호 복잡도 정책 및 SHA256 인증 알고리즘 적용 필수

## Performance

- [AURMY-PERF-001] 권장 인스턴스 타입 사용 | severity: minor | auto: true
  - 검증: DBInstanceClass가 현행 세대(db.r5, db.r6g, db.r7g 등)인지 확인
  - 기준: 프로덕션에서 구세대(db.r4 이하) 및 소형(db.t3.small 이하) 인스턴스 지양

- [AURMY-PERF-002] 자동 마이너 버전 업데이트 비활성화 | severity: minor | auto: true
  - 검증: describe-db-instances → AutoMinorVersionUpgrade == false
  - 기준: 프로덕션 안정성을 위해 자동 마이너 업데이트 비활성화

## Monitoring

- [AURMY-MON-002] Enhanced Monitoring 활성화 | severity: minor | auto: true
  - 검증: `MonitoringInterval` > 0
  - 기준: Enhanced Monitoring 활성화 권장

- [AURMY-MON-003] CloudWatch Logs Export 활성화 | severity: major | auto: true
  - 검증: describe-db-clusters → EnabledCloudwatchLogsExports에 audit, error, slowquery 포함 여부
  - 기준: 감사/에러/슬로우쿼리 로그가 CloudWatch로 전송되어야 함

- [AURMY-MON-004] CloudWatch Database Insights (DBI) 보존 기간 | severity: minor | auto: true
  - 검증: describe-db-instances → PerformanceInsightsRetentionPeriod >= 7
  - 기준: 최소 7일 이상 보존 필수

## Network & Connectivity

- [AURMY-NET-001] default VPC 사용 금지 | severity: critical | auto: true
  - 검증: describe-db-clusters → DBSubnetGroup → VpcId 확인 → ec2 describe-vpcs → IsDefault == false
  - 기준: default VPC 사용 금지, 별도 생성한 VPC에 배치 필수

- [AURMY-NET-002] 클러스터 엔드포인트 활용 | severity: minor | auto: true
  - 검증: describe-db-clusters → Endpoint, ReaderEndpoint 모두 존재 확인
  - 기준: Writer/Reader 엔드포인트를 분리하여 활용 권장

## MySQL Specific

- [AURMY-MY-001] Cluster Parameter Group 커스텀 사용 | severity: minor | auto: true
  - 검증: describe-db-clusters → DBClusterParameterGroup이 default.aurora-mysql*이 아닌지 확인
  - 기준: Default 파라미터 그룹 사용 금지, 커스텀 생성 필수

- [AURMY-MY-002] DB Parameter Group 커스텀 사용 | severity: minor | auto: true
  - 검증: describe-db-instances → DBParameterGroups[].DBParameterGroupName이 default.*이 아닌지 확인
  - 기준: Default 파라미터 그룹 사용 금지, 커스텀 생성 필수

- [AURMY-MY-003] 서버 가이드 권장 파라미터 설정 | severity: major | auto: true
  - 검증: describe-db-cluster-parameters로 아래 파라미터가 기준값과 일치하는지 확인
    - binlog_format = ROW
    - log_bin_trust_function_creator = ON
    - lower_case_table_names = 1
    - log_output = FILE
    - innodb_open_files = 65536
    - innodb_io_capacity = 2000
    - innodb_io_capacity_max = 4000
    - max_allowed_packet = 1073741824
    - innodb_parallel_read_threads = 2
    - join_buffer_size = 8388608
    - read_buffer_size = 8388608
    - read_rnd_buffer_size = 8388608
    - sort_buffer_size = 8388608
    - long_query_time <= 1
    - innodb_print_all_deadlocks = 1
  - 기준: 하나라도 불일치하면 FAIL, 상세에 불일치 파라미터 목록 표시

- [AURMY-MY-004] 문자셋/Collation 설정 확인 | severity: minor | auto: true
  - 검증: describe-db-cluster-parameters → character_set_server, collation_server 값이 default가 아닌 목적에 맞게 설정되어 있는지 확인
  - 기준: 서비스 목적에 맞는 문자셋/Collation이 명시적으로 설정되어 있어야 함

## Maintenance

- [AURMY-MNT-001] Maintenance Window 업무시간 외 설정 | severity: minor | auto: true
  - 검증: describe-db-clusters → PreferredMaintenanceWindow이 업무시간(KST 09-18) 외인지 확인
  - 기준: 유지보수 작업은 업무시간 외에 수행되어야 함

- [AURMY-MNT-002] Backup Window 업무시간 외 설정 | severity: minor | auto: true
  - 검증: describe-db-clusters → PreferredBackupWindow이 업무시간 외인지 확인
  - 기준: 백업은 업무시간 외에 수행되어야 함

- [AURMY-MNT-003] Pending Maintenance Action 존재 여부 | severity: major | auto: true
  - 검증: describe-pending-maintenance-actions → 미적용 유지보수 작업이 있는지 확인
  - 기준: 미적용 유지보수 작업이 있으면 계획 수립 필요

## Account Management (수동 확인)

- [AURMY-ACC-001] DB 계정 서비스/관리자/개인 분류 | severity: major | auto: false
  - 검증: DB 계정이 서비스 계정(WAS), 관리자 계정(DBA), 개인 사용자 계정(개발자)으로 분류되어 있는지 확인
  - 기준: 계정 용도별 분류 필수

- [AURMY-ACC-002] 개인 사용자 계정 1인 1계정 원칙 | severity: major | auto: false
  - 검증: 개인 사용자 계정이 1인 1계정으로 발급되었는지 확인
  - 기준: 공용 계정 사용 금지

- [AURMY-ACC-003] 기본 마스터(admin) 계정 미사용 | severity: critical | auto: false
  - 검증: Aurora MySQL 생성 시 자동 생성되는 기본 마스터 계정(admin)을 서비스/운영에 직접 사용하지 않는지 확인
  - 기준: 기본 마스터 계정(admin) 직접 사용 금지, 전용 계정으로 교체 필수

- [AURMY-ACC-004] 개인 사용자 계정 조회 권한만 부여 | severity: major | auto: false
  - 검증: 개인 사용자 계정에 DML, DDL 권한이 부여되지 않았는지 확인
  - 기준: 개인 계정은 SELECT 권한만 부여

- [AURMY-ACC-005] DB 계정 관리 DBA 담당 | severity: minor | auto: false
  - 검증: DB 계정 관리 업무를 DBA가 담당하고 있는지 확인
  - 기준: 계정 관리 책임자 명확화

- [AURMY-ACC-006] DB 계정 신규/변경/삭제 프로세스 | severity: minor | auto: false
  - 검증: DB 계정 생성/변경/삭제에 대한 프로세스가 구성되어 있는지 확인
  - 기준: 계정 관리 프로세스 문서화 필수

- [AURMY-ACC-007] DB 계정 권한 리스트 문서 관리 | severity: minor | auto: false
  - 검증: 계정 발급 관리 문서가 갱신 및 보관되고 있는지 확인
  - 기준: 계정 권한 현황 문서 최신 유지

- [AURMY-ACC-008] DB 계정 내역 5년 보관 | severity: minor | auto: false
  - 검증: 계정 신규/변경/삭제 내역(결재 문서)을 5년간 보관하고 있는지 확인
  - 기준: 감사 대비 5년 보관 필수

- [AURMY-ACC-009] Instance Name Rule 준수 | severity: minor | auto: false
  - 검증: DBClusterIdentifier가 조직 네이밍 규칙을 준수하는지 확인
  - 기준: 서비스별 네이밍 규칙에 따라 생성해야 함

## Schema Design (수동 확인)

- [AURMY-SCH-001] FK 미사용 설계 | severity: major | auto: false
  - 검증: FK(Foreign Key)를 사용하지 않도록 설계되어 있는지 확인
  - 기준: FK 사용 금지

- [AURMY-SCH-002] Procedure 제약사항 확인 | severity: minor | auto: false
  - 검증: Procedure 사용 시 제약사항을 확인하였는지 확인
  - 기준: Procedure 제약사항 검토 필수

- [AURMY-SCH-003] 테이블 PK Autoincrement int/bigint 사용 | severity: major | auto: false
  - 검증: 테이블 PK가 Autoincrement 속성의 int 또는 bigint 컬럼으로 생성되었는지 확인
  - 기준: PK는 Autoincrement int/bigint 필수

- [AURMY-SCH-004] 중복 체크 UK 또는 로직단 처리 | severity: minor | auto: false
  - 검증: 중복 체크가 필요한 컬럼에 UK를 생성하거나 로직단에서 처리하는지 확인
  - 기준: 중복 방지 방안 적용 필수

- [AURMY-SCH-005] 인덱스 네이밍룰 준수 | severity: minor | auto: false
  - 검증: 테이블 인덱스 생성 시 네이밍룰을 준수하였는지 확인
  - 기준: 조직 인덱스 네이밍 규칙 준수
