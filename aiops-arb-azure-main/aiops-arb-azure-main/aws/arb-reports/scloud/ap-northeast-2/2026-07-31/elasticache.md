# ElastiCache ARB 검증 리포트

- **서비스명**: scloud
- **계정 ID**: 325339151285
- **리전**: ap-northeast-2
- **검증 일시**: 2026-07-30 17:39 KST
- **사전 조사 파일**: pre-survey/elasticache_sample.md

---

## s2an2commonvalkey
Engine: valkey 7.2.6 | NodeType: cache.m6g.large | Nodes: 6 (3 shards × 2) | Region: ap-northeast-2

### Common Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| COM-SEC-001 | 저장 데이터 암호화 | critical | ✅ PASS | true | AtRestEncryptionEnabled: true (EC-INFRA-003 참조) |
| COM-SEC-002 | 전송 중 암호화 | critical | ✅ PASS | true | TransitEncryptionEnabled: true (EC-SEC-002 참조) |
| COM-SEC-003 | 퍼블릭 접근 차단 | critical | ✅ PASS | true | VPC 내 프라이빗 서브넷 배치 확인 (EC-INFRA-002 참조) |
| COM-SEC-004 | VPC 내 배치 | critical | ✅ PASS | true | CacheSubnetGroupName: stg-com-valkey-sg, non-default VPC (EC-INFRA-002 참조) |
| COM-BR-001 | 자동 백업 활성화 | critical | ✅ PASS | true | 캐시 용도 — 백업 비활성화 정책 적용 (EC-BR-001 참조) |
| COM-BR-002 | 삭제 방지 | major | N/A | true | ElastiCache는 삭제 방지 기능 미지원 |
| COM-MON-001 | CloudWatch 알람 설정 | major | ❌ FAIL | true | ElastiCache 관련 CloudWatch 알람 0건 |
| COM-MON-002 | 로깅 활성화 | minor | ✅ PASS | true | slowlog-log-slower-than=10000 (EC-MON-001 참조) |
| COM-MON-003 | 상시 모니터링 솔루션 적용 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |
| COM-MON-004 | 알람 수신 항목 설정 | major | ❌ FAIL | true | ElastiCache 관련 CloudWatch 알람 0건 — 알람 수신 항목 미설정 |
| COM-TAG-001 | 필수 태그 존재 | major | ❌ FAIL | true | Environment, Owner, Team 태그 모두 없음 |
| COM-AC-001 | SBC 경유 DB 접근 제한 | critical | ❌ FAIL | true | SG(sg-0e1fcec3c86854c77) 인바운드에 SBC NAT IP(211.189.57.60/32) 미허용 |
| COM-AC-002 | 허가된 IP/SG 기반 접속 제한 | critical | ✅ PASS | true | 0.0.0.0/0 없음. SG 소스 기반 접근만 허용 |
| COM-AC-003 | Bastion 서버 분리 | major | ⚠️ MANUAL | true | arb-config.md에 Bastion 정보 미설정 |
| COM-AC-004 | DB 계정 비밀번호 암호화 | critical | ✅ PASS | false | AUTH 토큰/RBAC 인증 적용 (EC-SEC-001 참조) |
| COM-AA-001 | DB 접속 기록 정기 점검 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |
| COM-NI-001 | DB 서브넷 망분리 | critical | ✅ PASS | true | 3개 서브넷 모두 라우트 테이블에 IGW 경로 없음 (프라이빗 서브넷) |
| COM-DR-001 | DR 구축 검토 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |

### ElastiCache Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| EC-ENG-001 | Valkey 엔진 버전 사용 | critical | ✅ PASS | true | Engine: valkey, EngineVersion: 7.2.6 (≥ 7.2) |
| EC-PG-001 | 커스텀 파라미터 그룹 사용 | major | ✅ PASS | true | CacheParameterGroupName: stg-common-valkey7-cluster-allkey (default가 아님) |
| EC-PG-002 | maxmemory-policy 적정 설정 | major | ✅ PASS | true | maxmemory-policy: allkeys-lru |
| EC-HA-001 | Cluster Mode 검토 | critical | ✅ PASS | true | ClusterEnabled: true |
| EC-HA-002 | Automatic Failover | critical | ✅ PASS | true | AutomaticFailover: enabled |
| EC-HA-003 | Multi-AZ 활성화 | critical | ✅ PASS | true | MultiAZ: enabled |
| EC-HA-004 | Replica 수 | major | ✅ PASS | true | 각 NodeGroup당 2개 멤버 (Primary 1 + Replica 1) |
| EC-INFRA-001 | 인스턴스 네이밍 규칙 준수 | minor | ❌ FAIL | true | 서비스명 'scloud' prefix 미포함, dev/stg/prod 환경 구분자 미포함 |
| EC-INFRA-002 | Network 설정 (VPC/서브넷) | critical | ✅ PASS | true | CacheSubnetGroupName: stg-com-valkey-sg, VpcId: vpc-1771b67e, IsDefault: false |
| EC-INFRA-003 | Storage Encryption (At Rest) | critical | ✅ PASS | true | AtRestEncryptionEnabled: true |
| EC-INFRA-004 | 권장 인스턴스 타입 사용 | minor | ✅ PASS | true | cache.m6g.large (권장 수준 충족) |
| EC-INFRA-005 | Default Port 변경 | critical | ✅ PASS | true | Port: 13211 (기본값 6379 아님) |
| EC-INFRA-006 | 자동 마이너 버전 업데이트 비활성화 | major | ❌ FAIL | true | AutoMinorVersionUpgrade: true (비활성화 필요) |
| EC-BR-001 | Backup/데이터 영속성 비활성화 권장 | minor | ✅ PASS | true | SnapshotRetentionLimit: 0, appendonly: no |
| EC-SEC-001 | AUTH 인증 설정 | major | ✅ PASS | true | UserGroupIds: [commonvalkey] (RBAC 적용) |
| EC-SEC-002 | 전송 중 암호화 (In-Transit) | critical | ✅ PASS | true | TransitEncryptionEnabled: true, TransitEncryptionMode: required |
| EC-DATA-001 | Data Type 이해 및 적정 사용 | minor | ✅ PASS | false | 사전 조사: O — Data Type 상세 검토 완료 |
| EC-DATA-002 | Cache Design Pattern 적용 | minor | ✅ PASS | false | 사전 조사: O — Cache-Aside, Write-Through 패턴 적용 |
| EC-CLI-001 | 권장 Redis Client 사용 | minor | ✅ PASS | false | 사전 조사: O — Lettuce 6.3.x (Java), redis-py 5.0.x (Python) |
| EC-MON-001 | 슬로우 로그 활성화 | minor | ✅ PASS | true | slowlog-log-slower-than: 10000 (≥ 0, 활성화) |

---

## s2an2publicvalkey
Engine: valkey 7.2.6 | NodeType: cache.m6g.large | Nodes: 6 (3 shards × 2) | Region: ap-northeast-2

### Common Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| COM-SEC-001 | 저장 데이터 암호화 | critical | ✅ PASS | true | AtRestEncryptionEnabled: true (EC-INFRA-003 참조) |
| COM-SEC-002 | 전송 중 암호화 | critical | ❌ FAIL | true | TransitEncryptionEnabled: false (EC-SEC-002 참조) |
| COM-SEC-003 | 퍼블릭 접근 차단 | critical | ✅ PASS | true | VPC 내 프라이빗 서브넷 배치 확인 (EC-INFRA-002 참조) |
| COM-SEC-004 | VPC 내 배치 | critical | ✅ PASS | true | CacheSubnetGroupName: stg-com-valkey-sg, non-default VPC (EC-INFRA-002 참조) |
| COM-BR-001 | 자동 백업 활성화 | critical | ✅ PASS | true | 캐시 용도 — 백업 비활성화 정책 적용 (EC-BR-001 참조) |
| COM-BR-002 | 삭제 방지 | major | N/A | true | ElastiCache는 삭제 방지 기능 미지원 |
| COM-MON-001 | CloudWatch 알람 설정 | major | ❌ FAIL | true | ElastiCache 관련 CloudWatch 알람 0건 |
| COM-MON-002 | 로깅 활성화 | minor | ✅ PASS | true | slowlog-log-slower-than=10000 (EC-MON-001 참조) |
| COM-MON-003 | 상시 모니터링 솔루션 적용 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |
| COM-MON-004 | 알람 수신 항목 설정 | major | ❌ FAIL | true | ElastiCache 관련 CloudWatch 알람 0건 — 알람 수신 항목 미설정 |
| COM-TAG-001 | 필수 태그 존재 | major | ❌ FAIL | true | Environment, Owner, Team 태그 모두 없음 |
| COM-AC-001 | SBC 경유 DB 접근 제한 | critical | ❌ FAIL | true | SG(sg-009003c8f534f792c) 인바운드에 SBC NAT IP(211.189.57.60/32) 미허용 |
| COM-AC-002 | 허가된 IP/SG 기반 접속 제한 | critical | ✅ PASS | true | 0.0.0.0/0 없음. SG 소스 기반 접근만 허용 |
| COM-AC-003 | Bastion 서버 분리 | major | ⚠️ MANUAL | true | arb-config.md에 Bastion 정보 미설정 |
| COM-AC-004 | DB 계정 비밀번호 암호화 | critical | ❌ FAIL | false | AUTH 토큰 미설정, RBAC(UserGroup) 미적용 (EC-SEC-001 참조) |
| COM-AA-001 | DB 접속 기록 정기 점검 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |
| COM-NI-001 | DB 서브넷 망분리 | critical | ✅ PASS | true | 3개 서브넷 모두 라우트 테이블에 IGW 경로 없음 (프라이빗 서브넷) |
| COM-DR-001 | DR 구축 검토 | major | ⚠️ MANUAL | false | 사전 조사 파일에 해당 항목 없음 |

### ElastiCache Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
| EC-ENG-001 | Valkey 엔진 버전 사용 | critical | ✅ PASS | true | Engine: valkey, EngineVersion: 7.2.6 (≥ 7.2) |
| EC-PG-001 | 커스텀 파라미터 그룹 사용 | major | ✅ PASS | true | CacheParameterGroupName: stg-public-valkey7-cluster-allkey (default가 아님) |
| EC-PG-002 | maxmemory-policy 적정 설정 | major | ✅ PASS | true | maxmemory-policy: allkeys-lru |
| EC-HA-001 | Cluster Mode 검토 | critical | ✅ PASS | true | ClusterEnabled: true |
| EC-HA-002 | Automatic Failover | critical | ✅ PASS | true | AutomaticFailover: enabled |
| EC-HA-003 | Multi-AZ 활성화 | critical | ✅ PASS | true | MultiAZ: enabled |
| EC-HA-004 | Replica 수 | major | ✅ PASS | true | 각 NodeGroup당 2개 멤버 (Primary 1 + Replica 1) |
| EC-INFRA-001 | 인스턴스 네이밍 규칙 준수 | minor | ❌ FAIL | true | 서비스명 'scloud' prefix 미포함, dev/stg/prod 환경 구분자 미포함 |
| EC-INFRA-002 | Network 설정 (VPC/서브넷) | critical | ✅ PASS | true | CacheSubnetGroupName: stg-com-valkey-sg, VpcId: vpc-1771b67e, IsDefault: false |
| EC-INFRA-003 | Storage Encryption (At Rest) | critical | ✅ PASS | true | AtRestEncryptionEnabled: true |
| EC-INFRA-004 | 권장 인스턴스 타입 사용 | minor | ✅ PASS | true | cache.m6g.large (권장 수준 충족) |
| EC-INFRA-005 | Default Port 변경 | critical | ✅ PASS | true | Port: 13211 (기본값 6379 아님) |
| EC-INFRA-006 | 자동 마이너 버전 업데이트 비활성화 | major | ❌ FAIL | true | AutoMinorVersionUpgrade: true (비활성화 필요) |
| EC-BR-001 | Backup/데이터 영속성 비활성화 권장 | minor | ✅ PASS | true | SnapshotRetentionLimit: 0, appendonly: no |
| EC-SEC-001 | AUTH 인증 설정 | major | ❌ FAIL | true | AuthTokenEnabled: false, UserGroupIds 미설정 — 인증 방식 미적용 |
| EC-SEC-002 | 전송 중 암호화 (In-Transit) | critical | ❌ FAIL | true | TransitEncryptionEnabled: false |
| EC-DATA-001 | Data Type 이해 및 적정 사용 | minor | ✅ PASS | false | 사전 조사: O — Data Type 상세 검토 완료 |
| EC-DATA-002 | Cache Design Pattern 적용 | minor | ✅ PASS | false | 사전 조사: O — Cache-Aside, Write-Through 패턴 적용 |
| EC-CLI-001 | 권장 Redis Client 사용 | minor | ✅ PASS | false | 사전 조사: O — Lettuce 6.3.x (Java), redis-py 5.0.x (Python) |
| EC-MON-001 | 슬로우 로그 활성화 | minor | ✅ PASS | true | slowlog-log-slower-than: 10000 (≥ 0, 활성화) |

---

## 📋 실행 로그

### 오케스트레이터 입력값
| 항목 | 값 |
|------|----|
| service_name | scloud |
| region | ap-northeast-2 |
| engine | elasticache (valkey) |
| 전달받은 리소스 목록 | s2an2commonvalkey, s2an2publicvalkey |
| 전달받은 리소스 수 | 2개 |
| 실행 일시 | 2026-07-30 17:39:10 |

### AWS CLI 호출 내역
| # | timestamp | 명령어 | 목적 | 응답 요약 |
|---|-----------|--------|------|----------|
| 1 | 17:39:10 | `aws elasticache describe-replication-groups --region ap-northeast-2 --no-paginate` | Step 0 선검증 + RG 상세 수집 | 2개 RG (s2an2commonvalkey, s2an2publicvalkey) |
| 2 | 17:39:15 | `aws elasticache describe-cache-clusters --show-cache-node-info --region ap-northeast-2 --no-paginate` | Port, PG, SG, EngineVersion 수집 | 12개 노드, Port=13211, PG 2종 |
| 3 | 17:39:18 | `aws elasticache describe-cache-parameters --cache-parameter-group-name stg-common-valkey7-cluster-allkey` | maxmemory-policy, slowlog, appendonly | allkeys-lru, 10000, no |
| 4 | 17:39:20 | `aws elasticache describe-cache-parameters --cache-parameter-group-name stg-public-valkey7-cluster-allkey` | maxmemory-policy, slowlog, appendonly | allkeys-lru, 10000, no |
| 5 | 17:39:22 | `aws elasticache list-tags-for-resource (s2an2commonvalkey)` | COM-TAG-001 태그 확인 | 10개 태그, 필수 태그 없음 |
| 6 | 17:39:24 | `aws elasticache list-tags-for-resource (s2an2publicvalkey)` | COM-TAG-001 태그 확인 | 10개 태그, 필수 태그 없음 |
| 7 | 17:39:26 | `aws elasticache describe-cache-subnet-groups --cache-subnet-group-name stg-com-valkey-sg` | VpcId, 서브넷 조회 | vpc-1771b67e, 3개 서브넷 |
| 8 | 17:39:28 | `aws ec2 describe-vpcs --vpc-ids vpc-1771b67e` | IsDefault 확인 | false |
| 9 | 17:39:30 | `aws ec2 describe-security-groups --group-ids sg-0e1fcec3c86854c77 sg-009003c8f534f792c` | SBC NAT IP, 0.0.0.0/0 확인 | SG 소스만 허용, CIDR 없음 |
| 10 | 17:39:32 | `aws ec2 describe-route-tables (3개 서브넷)` | IGW 경로 확인 | IGW 없음 (프라이빗) |
| 11 | 17:39:34 | `aws cloudwatch describe-alarms (AWS/ElastiCache)` | 알람 설정 확인 | 0건 |
