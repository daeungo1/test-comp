# Aurora MySQL ARB Review Report

- **Service**: scloud
- **Account**: 325339151285
- **Region**: ap-northeast-2
- **Date**: 2026-07-31
- **Engine**: aurora-mysql

---

## s2an2planauroramy01

Engine: aurora-mysql | Instances: 1 | Region: ap-northeast-2

### Common Checks

| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| COM-SEC-001 | 저장 데이터 암호화 | critical | ✅ PASS | true | StorageEncrypted=true, KMS Key: mrk-b648c3ad65354b979b4d2140f807b9e4 |
| COM-SEC-002 | 전송 중 암호화 | critical | ❌ FAIL | true | require_secure_transport 미설정 (engine-default=OFF) |
| COM-SEC-003 | 퍼블릭 접근 차단 | critical | ✅ PASS | true | PubliclyAccessible=false |
| COM-SEC-004 | VPC 내 배치 | critical | ✅ PASS | true | VpcId=vpc-1771b67e (SCloud 2.0 STG) |
| COM-BR-001 | 자동 백업 활성화 | critical | ✅ PASS | true | BackupRetentionPeriod=7 |
| COM-BR-002 | 삭제 방지 (Deletion Protection) | major | ✅ PASS | true | DeletionProtection=true (클러스터 레벨) |
| COM-MON-001 | CloudWatch 알람 설정 | major | ❌ FAIL | true | RDS 관련 CloudWatch 알람 0건 - CPU/메모리/디스크 알람 미설정 |
| COM-MON-002 | 로깅 활성화 | minor | ❌ FAIL | true | EnabledCloudwatchLogsExports=null - 로그 전송 미설정 |
| COM-MON-003 | 상시 모니터링 솔루션 적용 | major | N/A | false | 사전 조사 파일에 해당 항목 없음 |
| COM-MON-004 | 알람 수신 항목 설정 | major | ❌ FAIL | true | RDS 관련 CloudWatch 알람 0건 |
| COM-TAG-001 | 필수 태그 존재 | major | ❌ FAIL | true | Environment, Owner, Team 태그 미존재. 존재 태그: GBL_CLASS_0, SEC_ASSETS_PII, class2, GBL_CLASS_1, class1, GBL_CLASS_2, class0, developer, Name, jira |
| COM-AC-001 | 내부 접속 서비스(SBC) 경유 DB 접근 제한 | critical | ❌ FAIL | true | DB SG 및 Bastion SG 인바운드에 SBC NAT IP(211.189.57.60/32) 미등록 |
| COM-AC-002 | 허가된 IP/SG 기반 접속 제한 | critical | ✅ PASS | true | 모든 인바운드 규칙이 Security Group 기반, 0.0.0.0/0 없음 |
| COM-AC-003 | Bastion(Jumphost) 서버 분리 | major | ✅ PASS | true | Bastion(i-080fdcc132cb1d68b, s2an2bastion001_new) running, DB SG(sg-0992a77fc4dabe205)에서 db-jmp-SG(sg-0f09c0a34b3a70689) 허용 |
| COM-AC-004 | DB 계정 비밀번호 암호화 | critical | N/A | false | 사전 조사 파일에 해당 항목 없음 |
| COM-AA-001 | DB 접속 기록 정기 점검 | major | N/A | false | 사전 조사 파일에 해당 항목 없음 |
| COM-NI-001 | DB 서브넷 망분리 (인터넷 격리) | critical | ✅ PASS | true | 3개 서브넷 라우트 테이블에 IGW(0.0.0.0/0 → igw-*) 경로 없음 |
| COM-DR-001 | DR 구축 검토 | major | N/A | false | 사전 조사 파일에 해당 항목 없음 |

### Aurora MySQL Checks

| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| AURMY-HA-001 | 클러스터 인스턴스 수 | critical | ❌ FAIL | true | 인스턴스 1개 (Writer만 존재). Writer + 최소 1 Reader 필요 |
| AURMY-HA-002 | Multi-AZ 분산 | critical | ❌ FAIL | true | 단일 인스턴스(ap-northeast-2b)만 존재하여 Multi-AZ 분산 불가 |
| AURMY-HA-003 | Global Database 구성 | minor | N/A | true | Global Database 미구성. DR 요구사항 미확인 상태 |
| AURMY-HA-004 | Reader Failover Priority 분산 | minor | N/A | true | Reader 인스턴스 없음 (단일 Writer만 존재) |
| AURMY-HA-005 | 클러스터 엔진 버전 LTS 사용 | critical | ❌ FAIL | true | Aurora MySQL 3.10.0 (MySQL 8.0 호환) 사용 중 - non-LTS 버전. LTS 전환 권고 (아래 표 참조) |
| AURMY-HA-006 | Writer/Reader 인스턴스 클래스 동일성 | major | N/A | true | Reader 인스턴스 없음 (단일 Writer만 존재) |
| AURMY-BR-001 | PITR 보존 기간 | critical | ✅ PASS | true | BackupRetentionPeriod=7 (기준: ≥7) |
| AURMY-BR-002 | Backtrack 활성화 | minor | ❌ FAIL | true | EarliestBacktrackTime 미존재 - Backtrack 비활성화 |
| AURMY-BR-003 | Cross-Region 스냅샷 복사본 | minor | ❌ FAIL | true | Cross-Region 스냅샷 복사본 없음 (자동 스냅샷 7개만 존재) |
| AURMY-BR-004 | PITR 가능 상태 | major | ✅ PASS | true | EarliestRestorableTime=2026-07-22T20:11:13 존재 |
| AURMY-SEC-001 | Default Port 변경 | critical | ✅ PASS | true | Port=5306 (기본 3306이 아님) |
| AURMY-SEC-002 | 비밀번호 정책 설정 | major | ❌ FAIL | true | validate_password 관련 파라미터 미설정, default_authentication_plugin=mysql_native_password (caching_sha2_password 아님) |
| AURMY-PERF-001 | 권장 인스턴스 타입 사용 | minor | ✅ PASS | true | db.r6g.large - 현행 세대(Graviton2) |
| AURMY-PERF-002 | 자동 마이너 버전 업데이트 비활성화 | minor | ✅ PASS | true | AutoMinorVersionUpgrade=false |
| AURMY-MON-002 | Enhanced Monitoring 활성화 | minor | ✅ PASS | true | MonitoringInterval=60초 |
| AURMY-MON-003 | CloudWatch Logs Export 활성화 | major | ❌ FAIL | true | EnabledCloudwatchLogsExports=null - audit, error, slowquery 로그 미전송 |
| AURMY-MON-004 | CloudWatch Database Insights 보존 기간 | minor | ✅ PASS | true | PerformanceInsightsRetentionPeriod=7 (기준: ≥7) |
| AURMY-NET-001 | default VPC 사용 금지 | critical | ✅ PASS | true | VpcId=vpc-1771b67e, IsDefault=false (SCloud 2.0 STG) |
| AURMY-NET-002 | 클러스터 엔드포인트 활용 | minor | ✅ PASS | true | Endpoint 및 ReaderEndpoint 모두 존재 |
| AURMY-MY-001 | Cluster Parameter Group 커스텀 사용 | minor | ✅ PASS | true | aurora-large-31-aorc-cluster (default가 아닌 커스텀) |
| AURMY-MY-002 | DB Parameter Group 커스텀 사용 | minor | ✅ PASS | true | aurora-large-31-aorc (default가 아닌 커스텀) |
| AURMY-MY-003 | 서버 가이드 권장 파라미터 설정 | major | ❌ FAIL | true | 불일치 항목: binlog_format=OFF (기준: ROW), lower_case_table_names=미설정 (기준: 1), innodb_open_files=미설정 (기준: 65536), innodb_io_capacity=미설정 (기준: 2000), innodb_io_capacity_max=미설정 (기준: 4000), max_allowed_packet=미설정 (기준: 1073741824), innodb_parallel_read_threads=미설정 (기준: 2), join_buffer_size=미설정 (기준: 8388608), read_buffer_size=262144 (기준: 8388608), read_rnd_buffer_size=524288 (기준: 8388608), sort_buffer_size=미설정 (기준: 8388608), innodb_print_all_deadlocks=미설정 (기준: 1). 준수: log_bin_trust_function_creators=1(✅), log_output=FILE(✅), long_query_time=1(✅) |
| AURMY-MY-004 | 문자셋/Collation 설정 확인 | minor | ❌ FAIL | true | character_set_server=미설정(engine-default), collation_server=미설정(engine-default) - 명시적 설정 필요 |
| AURMY-MNT-001 | Maintenance Window 업무시간 외 설정 | minor | ❌ FAIL | true | PreferredMaintenanceWindow=thu:02:00-thu:02:30 (UTC) = KST 목요일 11:00-11:30 (업무시간 내) |
| AURMY-MNT-002 | Backup Window 업무시간 외 설정 | minor | ✅ PASS | true | PreferredBackupWindow=20:06-20:36 (UTC) = KST 05:06-05:36 (업무시간 외) |
| AURMY-MNT-003 | Pending Maintenance Action | major | ❌ FAIL | true | 미적용 유지보수 1건: os-upgrade (New Operating System patch is available) |
| AURMY-ACC-001 | DB 계정 서비스/관리자/개인 분류 | major | ✅ PASS | false | 사전 조사: 4개 계정 분류 완료 (SERVICE: svc_payment, DBA: dba_admin, PERSONAL: dev_john, dev_jane) |
| AURMY-ACC-002 | 개인 사용자 계정 1인 1계정 원칙 | major | ✅ PASS | false | 사전 조사: 개인 계정 공용 사용 없음 = O |
| AURMY-ACC-003 | 기본 마스터(admin) 계정 미사용 | critical | ✅ PASS | false | 사전 조사: root 계정 없음 (자동 조회 결과로 판정) |
| AURMY-ACC-004 | 개인 사용자 계정 조회 권한만 부여 | major | ❌ FAIL | false | 사전 조사: dev_jane 계정에 INSERT 권한 존재 (X) - 조치 필요 |
| AURMY-ACC-005 | DB 계정 관리 DBA 담당 | minor | ✅ PASS | false | 사전 조사: DBA가 계정 관리 담당 = O (김철수 / DB운영팀) |
| AURMY-ACC-006 | DB 계정 신규/변경/삭제 프로세스 | minor | ✅ PASS | false | 사전 조사: 계정 관리 프로세스 문서 존재 = O |
| AURMY-ACC-007 | DB 계정 권한 리스트 문서 관리 | minor | ✅ PASS | false | 사전 조사: 권한 현황 문서 최신 유지 = O (최종 갱신: 2026-05-20) |
| AURMY-ACC-008 | DB 계정 내역 5년 보관 | minor | ❌ FAIL | false | 사전 조사: 계정 내역 5년 보관 중 = X (현재 1년치만 보관, 개선 예정) |
| AURMY-ACC-009 | Instance Name Rule 준수 | minor | ✅ PASS | false | 사전 조사: 네이밍 규칙 준수 = O |
| AURMY-SCH-001 | FK 미사용 설계 | major | ❌ FAIL | false | 사전 조사: FK 사용이 의도된 설계 = X (order_detail 테이블, 2026-06-30 제거 예정) |
| AURMY-SCH-002 | Procedure 제약사항 확인 | minor | ✅ PASS | false | 사전 조사: 등록된 Routine 없음 (자동 조회 결과로 판정) |
| AURMY-SCH-003 | 테이블 PK Autoincrement int/bigint 사용 | major | ❌ FAIL | false | 사전 조사: WARN 항목 존재 (order_detail.detail_id=varchar, AUTO_INC=NO). 개선 예정 = O이나 현재 미충족 |
| AURMY-SCH-004 | 중복 체크 UK 또는 로직단 처리 | minor | ✅ PASS | false | 사전 조사: UK 없는 테이블의 중복 방지를 로직단에서 처리 = O |
| AURMY-SCH-005 | 인덱스 네이밍룰 준수 | minor | ❌ FAIL | false | 사전 조사: 네이밍룰 미준수 항목 있음 = X (orders.myindex1 → idx_created_at 변경 예정) |

### AURMY-HA-005 엔진 버전 EOL 참고

사용 중인 버전: Aurora MySQL 3.10.0 (MySQL 8.0 호환)

| 구분 | 버전 | LTS 여부 | 표준 지원 종료일 |
|------|------|---------|-----------------|
| 사용 중인 마이너 버전 | Aurora MySQL 3.10.* (MySQL 8.0) | non-LTS | 2026-10-31 (예상) |
| 같은 메이저 라인 LTS | Aurora MySQL 3.04.* | LTS | 2028-02-28 |
| 사용 중인 메이저 라인 | Aurora MySQL v3 (MySQL 8.0) | - | 2030-10-31 |

> ⚠️ non-LTS 마이너(3.10.x)는 LTS/메이저보다 표준 지원 종료일이 빠릅니다. 안정성 확보를 위해 LTS 버전(3.04.x) 또는 차기 LTS로 전환을 권고합니다.

---

## 검증 요약

| 구분 | 건수 |
|------|------|
| ✅ PASS | 29 |
| ❌ FAIL | 22 |
| N/A | 7 |
| **합계** | **58** |

### 🚨 Critical FAIL 목록

| 리소스 | Check ID | 항목 | 상세 |
|--------|----------|------|------|
| s2an2planauroramy01 | COM-SEC-002 | 전송 중 암호화 | require_secure_transport 미설정 |
| s2an2planauroramy01 | COM-AC-001 | SBC 경유 DB 접근 제한 | SBC NAT IP(211.189.57.60/32) 미등록 |
| s2an2planauroramy01 | AURMY-HA-001 | 클러스터 인스턴스 수 | Writer만 1개, Reader 없음 |
| s2an2planauroramy01 | AURMY-HA-002 | Multi-AZ 분산 | 단일 AZ(ap-northeast-2b)에만 배치 |
| s2an2planauroramy01 | AURMY-HA-005 | 엔진 버전 LTS 사용 | 3.10.0 (non-LTS) 사용 중 |

---

## 📋 실행 로그

### 오케스트레이터 입력값

| 항목 | 값 |
|------|----|
| service_name | scloud |
| region | ap-northeast-2 |
| engine | aurora-mysql |
| 전달받은 리소스 목록 | s2an2planauroramy01 |
| 전달받은 리소스 수 | 1개 |
| 실행 일시 | 2026-07-30 17:39:04 |

### AWS CLI 호출 내역

| # | timestamp | 명령어 | 목적 | 응답 요약 |
|---|-----------|--------|------|----------|
| 1 | 17:39:10 | `aws rds describe-db-clusters --filters Name=engine,Values=aurora-mysql --region ap-northeast-2` | 전체 클러스터 목록 조회 | 1개 클러스터 |
| 2 | 17:39:12 | `aws rds describe-global-clusters --region ap-northeast-2` | Global Cluster 확인 | 0건 |
| 3 | 17:39:12 | `aws ec2 describe-vpcs --region ap-northeast-2` | VPC 정보 확인 | 2개 VPC, IsDefault=false |
| 4 | 17:39:14 | `aws rds describe-db-instances --filters Name=db-cluster-id,Values=s2an2planauroramy01` | 인스턴스 상세 | 1개 인스턴스 (db.r6g.large) |
| 5 | 17:39:14 | `aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name aurora-large-31-aorc-cluster` | 클러스터 파라미터 조회 | 424개 파라미터 |
| 6 | 17:39:16 | `aws rds describe-pending-maintenance-actions --resource-identifier {cluster-arn}` | Pending Maintenance 확인 | 1건 (os-upgrade) |
| 7 | 17:39:16 | `aws rds describe-db-cluster-snapshots --db-cluster-identifier s2an2planauroramy01` | 스냅샷 확인 | 7개 자동, Cross-Region 0건 |
| 8 | 17:39:18 | `aws ec2 describe-security-groups --group-ids sg-0992a77fc4dabe205 sg-031cd4fcd419f15f1` | DB SG 인바운드 확인 | SG 기반 접근만 허용 |
| 9 | 17:39:19 | `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values={3 subnets}` | DB 서브넷 라우트 테이블 | IGW 경로 없음 |
| 10 | 17:39:20 | `aws cloudwatch describe-alarms (AWS/RDS namespace)` | CloudWatch 알람 확인 | 0건 |
| 11 | 17:39:21 | `aws ec2 describe-instances --filters Name=instance.group-id,Values=sg-0f09c0a34b3a70689` | Bastion 존재 확인 | 1대 running |
| 12 | 17:39:22 | `aws ec2 describe-security-groups --group-ids sg-455df82c` | Bastion SG(jmp-SG) 확인 | SBC NAT IP 미발견 |
| 13 | 17:39:23 | `aws rds list-tags-for-resource --resource-name {cluster-arn}` | 필수 태그 확인 | Environment/Owner/Team 없음 |
| 14 | 17:39:24 | `aws rds describe-db-engine-versions --engine aurora-mysql` | 엔진 버전 EOL 조회 | 3.10.0 available (non-LTS) |
| 15 | 17:39:25 | `aws rds describe-db-parameters --db-parameter-group-name aurora-large-31-aorc` | DB 인스턴스 파라미터 조회 | user-modified 7개 |
