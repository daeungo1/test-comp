# ElastiCache ARB Checklist

ElastiCache(Redis, Valkey, Memcached) 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

> **우선순위**: 동일 주제에 대해 common.md와 본 체크리스트에 더 구체적인 항목이 있는 경우, EC-XXX 항목의 판정 결과를 COM-XXX에도 동일하게 적용(결과 매핑)합니다. COM-XXX는 SKIP하지 않고 PASS/FAIL로 표시하며, 상세 컬럼에 참조 항목을 명시합니다. 단, 기능 자체가 미지원인 항목은 N/A로 처리합니다.

## Engine Version

- [EC-ENG-001] Valkey 엔진 버전 사용 | severity: critical | auto: true
  - 검증: `Engine`이 `valkey`이고 `EngineVersion`이 7.2 이상인지 확인
  - 기준: 엔진은 Valkey를 사용해야 하며, 버전은 7.2 이상이어야 함. Redis 엔진 사용 시 또는 Valkey 7.2 미만이면 FAIL

## Parameter Group

- [EC-PG-001] 커스텀 파라미터 그룹 사용 | severity: major | auto: true
  - 검증: `CacheParameterGroupName`이 `default`로 시작하지 않는지 확인
  - 기준: Default 파라미터 그룹이 아닌 신규 생성한 파라미터 그룹을 사용해야 함

- [EC-PG-002] maxmemory-policy 적정 설정 | severity: major | auto: true
  - 검증: 각 Replication Group의 `CacheParameterGroupName`을 확인한 뒤, `aws elasticache describe-cache-parameters --cache-parameter-group-name {name}` 으로 `maxmemory-policy` 값을 조회한다. Replication Group마다 파라미터 그룹이 다를 수 있으므로 **고유한 파라미터 그룹 각각에 대해 반드시 조회**해야 한다.
  - 기준:
    - `noeviction` → ❌ FAIL (메모리 초과 시 쓰기 오류 발생, 캐시 용도에 부적합)
    - `volatile-lru`, `volatile-lfu`, `volatile-ttl`, `volatile-random`, `allkeys-lru`, `allkeys-lfu`, `allkeys-random` → ✅ PASS
    - 값이 비어있거나 조회 불가 → ⚠️ MANUAL

## Cluster Mode

- [EC-HA-001] Cluster Mode 검토 | severity: critical | auto: true
  - 검증: `ClusterEnabled` == true
  - 기준: 프로덕션 환경에서는 Cluster Mode 사용 권장

## Infrastructure

- [EC-INFRA-001] 인스턴스 네이밍 규칙 준수 | severity: minor | auto: true
  - 검증: `describe-replication-groups` / `describe-cache-clusters`로 조회한 `ReplicationGroupId` / `CacheClusterId`가 아래 조건을 모두 충족하는지 확인
    1. ARB 리뷰 시작 시 입력받은 서비스명(service_name)을 prefix로 포함
    2. `dev`, `stg`, `prod` 중 하나를 포함
  - 기준:
    - 두 조건 모두 충족 → ✅ PASS
    - 하나라도 미충족 → ❌ FAIL (미충족 조건 명시)

- [EC-INFRA-002] Network 설정 (VPC/서브넷) | severity: critical | auto: true
  - 검증: VPC 내 배치 여부, 서브넷 그룹 설정 확인
    1. `CacheSubnetGroupName` 존재 여부 확인
    2. `aws elasticache describe-cache-subnet-groups`로 서브넷 그룹의 `VpcId` 조회
    3. `aws ec2 describe-vpcs --vpc-ids {VpcId}`로 `IsDefault` 확인
  - 기준: 반드시 VPC 내 프라이빗 서브넷에 배치되어야 함
    - `CacheSubnetGroupName` 없음 → ❌ FAIL
    - `IsDefault == true` → ❌ FAIL (Default VPC 사용 금지)
    - `IsDefault == false` → ✅ PASS
  - 참고: Private Subnet 여부(IGW 경로 차단)는 COM-NI-001에서 별도 검증

- [EC-INFRA-003] Storage Encryption (At Rest) | severity: critical | auto: true
  - 검증: `AtRestEncryptionEnabled` == true
  - 기준: 저장 데이터 암호화 필수

- [EC-INFRA-004] 권장 인스턴스 타입 사용 | severity: minor | auto: true
  - 검증: `CacheNodeType` 확인
  - 기준: 프로덕션에서 cache.t2.micro, cache.t2.small, cache.t3.micro 지양

- [EC-INFRA-005] Default Port 변경 | severity: critical | auto: true
  - 검증: `aws elasticache describe-cache-clusters --show-cache-node-info` 결과에서 `CacheNodes[].Endpoint.Port` 확인. Cluster Mode 클러스터는 개별 노드 Port로 확인한다.
  - 기준: Port가 6379(Redis/Valkey 기본값)이면 ❌ FAIL, 다른 포트이면 ✅ PASS

- [EC-INFRA-006] 자동 마이너 버전 업데이트 비활성화 | severity: major | auto: true
  - 검증: `AutoMinorVersionUpgrade` == false
  - 기준: 예기치 않은 버전 변경 방지를 위해 자동 마이너 버전 업데이트 비활성화 필수

## High Availability

- [EC-HA-002] Automatic Failover | severity: critical | auto: true
  - 검증: `AutomaticFailover` == enabled
  - 기준: 자동 장애 조치 필수

- [EC-HA-003] Multi-AZ 활성화 | severity: critical | auto: true
  - 검증: Replica가 2개 이상의 AZ에 분산되어 있는지 확인. `MultiAZ` == enabled
  - 기준: 단일 AZ 장애 대비. `MultiAZ: disabled`이면 ❌ FAIL

- [EC-HA-004] Replica 수 | severity: major | auto: true
  - 검증: Replica 노드가 1개 이상 존재하는지 확인. 각 NodeGroup의 `NodeGroupMembers` 수가 2개 이상(Primary 1 + Replica 1 이상)인지 확인
  - 기준: 최소 1개 Replica 필수. NodeGroupMembers 수가 1이면 ❌ FAIL

## Backup & Recovery

- [EC-BR-001] Backup/데이터 영속성(AOF/RDB) 비활성화 권장 | severity: minor | auto: true
  - 검증:
    1. RDB(스냅샷): `SnapshotRetentionLimit` == 0 인지 확인
    2. AOF: 파라미터 그룹의 `appendonly` 값이 `no` 인지 확인
       (`aws elasticache describe-cache-parameters --cache-parameter-group-name {name}`)
  - 기준: 캐시 용도에 맞게 백업/영속성을 비활성화해야 함
    - `SnapshotRetentionLimit == 0` 그리고 `appendonly == no` → ✅ PASS
    - `SnapshotRetentionLimit > 0` 또는 `appendonly == yes` → ❌ FAIL (활성화된 항목 명시)
    - 파라미터 조회 불가 → ⚠️ MANUAL

## Security

- [EC-SEC-001] AUTH 인증 설정 | severity: major | auto: true
  - 검증: `AuthTokenEnabled` == true 또는 `UserGroupIds`가 설정되어 있는지 확인
  - 기준: AUTH 토큰 또는 RBAC(User Group) 중 하나 이상의 인증 방식 적용 필수

- [EC-SEC-002] 전송 중 암호화 (In-Transit) | severity: critical | auto: true
  - 검증: `TransitEncryptionEnabled` == true
  - 기준: TLS를 통한 전송 암호화 필수

## Data Usage

- [EC-DATA-001] Data Type 이해 및 적정 사용 | severity: minor | auto: false
  - 검증: 사용 중인 Redis Data Type(String, Hash, List, Set, Sorted Set 등)이 용도에 적합한지 확인
  - 기준: 데이터 특성에 맞는 적절한 Data Type 사용 필요 (수동 확인)

- [EC-DATA-002] Cache Design Pattern 적용 | severity: minor | auto: false
  - 검증: Cache-Aside, Write-Through, Write-Behind 등 적절한 캐시 디자인 패턴 적용 여부 확인
  - 기준: 서비스 특성에 맞는 캐시 디자인 패턴 적용 필요 (수동 확인)

## Client

- [EC-CLI-001] 권장 Redis Client 사용 | severity: minor | auto: false
  - 검증: 애플리케이션에서 사용하는 Redis Client가 권장 클라이언트인지 확인
  - 기준: 공식 권장 클라이언트 사용 필요 (수동 확인)

## Monitoring

- [EC-MON-001] 슬로우 로그 활성화 | severity: minor | auto: true
  - 검증: 아래 두 가지를 순서대로 확인한다.
    1. `LogDeliveryConfigurations`에 `LogType: slow-log` 항목이 있고 `Status: active`이면 ✅ PASS
    2. 없으면 파라미터 그룹에서 `slowlog-log-slower-than` 값을 조회한다.
       - 값이 `-1` 이면 ❌ FAIL (슬로우 로그 비활성화)
       - 값이 `0` 이상이면 ✅ PASS (슬로우 로그 활성화, 값이 클수록 임계값이 높음)
       - 값이 없거나 조회 불가이면 ⚠️ MANUAL
