# DynamoDB ARB Checklist

DynamoDB 고유 검증 항목입니다.
공통 항목은 `common.md`를 참조합니다.

## Table Design

- [DDB-TD-001] 파티션 키 카디널리티 | severity: critical | auto: false
  - 검증: 파티션 키(PK)가 높은 카디널리티를 가지는지 확인
  - 참고 정보: 계정 내 모든 DynamoDB 테이블을 조회한 뒤, 테이블별로 `aws dynamodb describe-table --table-name {name}`의 `KeySchema`에서 PK/SK 어트리뷰트명을 추출하여 아래 형식으로 상세에 기재
    ```
    테이블: {table-name}
      PK: {pk-attribute-name} → 판정: 높음/낮음/확인필요 (판단 근거)
      SK: {sk-attribute-name} (없으면 생략)
    ```
    판정 기준 (PK 어트리뷰트명 기반 대략적 판단, 참고용):
    - 높음: userId, orderId, deviceId, sessionId, requestId 등 고유 ID성 명칭
    - 낮음: status, type, category, flag, yn 등 열거형·상태값성 명칭
    - 확인필요: date, region, code 등 범위에 따라 카디널리티가 달라질 수 있는 명칭
  - 기준: 파티션 키는 데이터가 고르게 분산되도록 높은 카디널리티를 가져야 함

- [DDB-TD-002] 액세스 패턴 기반 키 설계 | severity: critical | auto: false
  - 검증: 모든 액세스 패턴이 정의되어 있고, PK/SK가 해당 패턴을 커버하도록 설계되었는지 확인
  - 기준: 액세스 패턴을 사전에 모두 정의하고, 이를 기반으로 PK/SK를 설계해야 함

- [DDB-TD-003] LSI/GSI 액세스 패턴 기반 설계 | severity: major | auto: false
  - 검증: LSI/GSI가 액세스 패턴에 기반하여 설계되었는지 확인
  - 기준: 인덱스는 실제 액세스 패턴을 기반으로 설계해야 함

- [DDB-TD-004] 테이블 설계 방식 선택 근거 | severity: major | auto: false
  - 검증: Single Table Design / Multi Table Design 선택 근거가 명확한지 확인
  - 기준: 설계 방식 선택 근거를 문서화해야 함

- [DDB-TD-005] 어트리뷰트 네이밍 컨벤션 | severity: minor | auto: false
  - 검증: 어트리뷰트 네이밍 컨벤션이 정의되어 있는지 확인
  - 기준: 일관된 네이밍 컨벤션을 정의하고 준수해야 함

- [DDB-TD-006] 어트리뷰트 네이밍 최소화 | severity: minor | auto: false
  - 검증: 어트리뷰트 이름이 불필요하게 길지 않은지 확인
  - 참고 정보: `aws dynamodb describe-table --table-name {name}`의 `TableSizeBytes`와 `ItemCount`로 평균 아이템 크기를 계산하여 아래 형식으로 상세에 기재
    ```
    테이블: {table-name}
      TableSizeBytes: {value} bytes
      ItemCount: {value}
      평균 아이템 크기: {TableSizeBytes / ItemCount} bytes → 판정: {판정}
    ```
    판정 기준 (평균 아이템 크기 기반, 참고용):
    - 여유 (~1KB 미만): 풀네임 어트리뷰트 사용해도 비용 영향 미미
    - 최소화 권고 (1KB 초과): 어트리뷰트명 축약으로 스토리지 비용 절감 효과 있음
  - 기준: 어트리뷰트 이름은 최소화하여 스토리지 비용 절감

## LSI/GSI Index Design

- [DDB-IDX-001] LSI 필요성 검토 | severity: major | auto: false
  - 검증: LSI가 반드시 필요한지, GSI로 대체 가능한지 검토 여부 확인
  - 기준: LSI는 생성 후 삭제 불가하므로 GSI 대체 가능 여부를 먼저 검토해야 함

- [DDB-IDX-002] LSI 아이템 크기 제한 인지 | severity: major | auto: false
  - 검증: LSI가 있는 테이블에서 아이템당 400KB 제한이 기본 테이블 + 모든 LSI 인덱스 엔트리 합산임을 인지하고 있는지 확인
  - 기준: LSI 사용 시 아이템 크기 제한 특성을 이해하고 설계에 반영해야 함

- [DDB-IDX-003] LSI 아이템 컬렉션 10GB 제한 인지 | severity: major | auto: false
  - 검증: LSI가 있는 테이블에서 동일 파티션 키 값의 아이템 컬렉션(기본 테이블 + 모든 LSI 항목 합산) 크기가 10GB로 제한됨을 인지하고 있는지 확인
  - 기준: LSI 사용 시 아이템 컬렉션 10GB 제한 특성을 이해하고, 초과 위험이 있는 파티션 키 설계를 지양해야 함

- [DDB-IDX-004] LSI 수 적정성 | severity: major | auto: true
  - 검증: `LocalSecondaryIndexes` 배열 길이가 5 이하인지 확인
  - 기준: LSI는 테이블당 최대 5개로 제한되며, 불필요한 LSI는 생성하지 않아야 함
  - 판정:
    - `LocalSecondaryIndexes` 없음 → N/A
    - 배열 길이 ≤ 5 → ✅ PASS
    - 배열 길이 > 5 → ❌ FAIL

- [DDB-IDX-005] LSI 프로젝션 타입 적정성 | severity: minor | auto: true
  - 검증: `LocalSecondaryIndexes[].Projection.ProjectionType` 확인 (참고용)
  - 기준: 프로젝션 타입은 액세스 패턴에 따라 선택하는 설계 결정이므로 타입 자체로 결함을 판정하지 않음
  - 판정:
    - LSI 없음 → N/A
    - ProjectionType과 무관하게 → ✅ PASS
    - 단, `ALL` ProjectionType인 LSI가 있는 경우 상세에 해당 인덱스명을 명시하고 "ALL 프로젝션은 쓰기 비용·스토리지 증가를 유발하므로 반드시 필요한 설정인지 재검토 권고" 기재

- [DDB-IDX-006] GSI 파티션 키 카디널리티 | severity: critical | auto: false
  - 검증: GSI의 파티션 키가 높은 카디널리티를 가지는지 확인
  - 참고 정보: `aws dynamodb describe-table --table-name {name}`의 `GlobalSecondaryIndexes[].KeySchema`에서 각 GSI별 `KeyType == HASH`인 어트리뷰트명(PK)과 `KeyType == RANGE`인 어트리뷰트명(SK)을 조회하여 상세에 기재 (예: GSI1-PK=status, GSI1-SK=createdAt / GSI2-PK=category, GSI2-SK=없음)
  - 기준: GSI 파티션 키도 데이터가 고르게 분산되도록 높은 카디널리티를 가져야 함

- [DDB-IDX-007] GSI 수 적정성 | severity: major | auto: true
  - 검증: `GlobalSecondaryIndexes` 배열 길이가 20 이하인지 확인
  - 기준: GSI는 테이블당 최대 20개로 제한되며, 과도한 GSI는 쓰기 비용 증가를 유발함
  - 판정:
    - `GlobalSecondaryIndexes` 없음 → N/A
    - 배열 길이 ≤ 20 → ✅ PASS
    - 배열 길이 > 20 → ❌ FAIL

- [DDB-IDX-008] GSI 프로젝션 타입 적정성 | severity: minor | auto: true
  - 검증: `GlobalSecondaryIndexes[].Projection.ProjectionType` 확인 (참고용)
  - 기준: 프로젝션 타입은 액세스 패턴에 따라 선택하는 설계 결정이므로 타입 자체로 결함을 판정하지 않음
  - 판정:
    - GSI 없음 → N/A
    - ProjectionType과 무관하게 → ✅ PASS
    - 단, `ALL` ProjectionType인 GSI가 있는 경우 상세에 해당 인덱스명을 명시하고 "ALL 프로젝션은 쓰기 비용·스토리지 증가를 유발하므로 반드시 필요한 설정인지 재검토 권고" 기재

- [DDB-IDX-009] Sparse Index 패턴 활용 | severity: minor | auto: false
  - 검증: 일부 아이템에만 존재하는 어트리뷰트를 GSI 키로 활용하는 Sparse Index 패턴을 검토하였는지 확인
  - 기준: 조건부 쿼리가 필요한 경우 Sparse Index 패턴 활용을 권장

- [DDB-IDX-010] GSI 파티션 키 값 변경 동작 인지 | severity: major | auto: false
  - 검증: GSI 파티션 키 값 변경 시 기존 항목 삭제 후 새 항목 추가로 동작함을 인지하고 있는지 확인
  - 기준: GSI 키 값 변경의 동작 방식을 이해하고 애플리케이션 로직에 반영해야 함

## Capacity Mode

- [DDB-CAP-001] On-Demand 모드 사용 | severity: critical | auto: true
  - 검증: `BillingModeSummary.BillingMode` == PAY_PER_REQUEST 인지 확인
  - 기준: 예측 불가한 트래픽 패턴의 경우 On-Demand 모드 사용 권장
  - 판정:
    - `BillingModeSummary.BillingMode` == `PAY_PER_REQUEST` → ✅ PASS
    - `BillingModeSummary.BillingMode` == `PROVISIONED` → ❌ FAIL

- [DDB-CAP-002] 테이블 레벨 처리량 한도 증설 여부 | severity: major | auto: true
  - 검증: `aws service-quotas get-service-quota --service-code dynamodb --quota-code L-CF0CBE56 --region {region}` (Table-level read throughput limit) 및 `--quota-code L-AB614373` (Table-level write throughput limit)로 현재 할당된 한도 확인
  - 기준: 테이블 레벨 처리량 한도(기본값: 테이블/GSI당 40,000 RCU / 40,000 WCU)가 서비스 트래픽 대비 충분하도록 증설 신청이 되어 있어야 함. 이 한도는 On-Demand·Provisioned 모드 모두에 적용됨 (계정 레벨 처리량 한도는 Provisioned 모드에만 적용되며 On-Demand에는 적용되지 않으므로, 모드와 무관하게 유효한 테이블 레벨 한도를 점검함)
  - 판정:
    - Read, Write `Value`가 모두 > 40000 → ✅ PASS (한도 증설 완료)
    - Read 또는 Write 중 하나라도 `Value` == 40000 (기본값) → ❌ FAIL (기본값 유지 중 — 트래픽 규모에 맞는 한도 증설 신청 필요, 상세에 기본값인 항목 명시)
    - API 호출 실패 (AccessDenied 등) → N/A

- [DDB-CAP-003] On-Demand 최대 처리량 상한 미설정 | severity: major | auto: true
  - 검증: `OnDemandThroughput.MaxReadRequestUnits`, `OnDemandThroughput.MaxWriteRequestUnits`가 설정되어 있지 않은지 확인
  - 기준: On-Demand 테이블에 불필요한 처리량 상한을 설정하지 않아야 함 (필요 시에만 설정)
  - 판정:
    - On-Demand 모드가 아님 → N/A
    - `OnDemandThroughput` 필드 없음 또는 MaxReadRequestUnits/MaxWriteRequestUnits 미설정 → ✅ PASS
    - MaxReadRequestUnits 또는 MaxWriteRequestUnits가 설정되어 있음 → ❌ FAIL (상세에 설정값 명시)

- [DDB-CAP-004] Warm Throughput 설정 | severity: major | auto: true
  - 검증: `WarmThroughput` 필드가 존재하고 `ReadUnitsPerSecond`, `WriteUnitsPerSecond`가 설정되어 있는지 확인
  - 기준: 콜드 스타트로 인한 처리량 제한을 방지하기 위해 Warm Throughput 설정 권장
  - 판정:
    - `WarmThroughput.ReadUnitsPerSecond` 및 `WriteUnitsPerSecond`가 모두 존재 → ✅ PASS
    - `WarmThroughput` 필드 없음 또는 값 미설정 → ❌ FAIL

- [DDB-CAP-005] 파티션당 처리량 한도 인지 | severity: major | auto: false
  - 검증: 파티션당 처리량 한도(3,000 RCU / 1,000 WCU)를 인지하고 설계에 반영하였는지 확인
  - 기준: 파티션당 처리량 한도를 초과하지 않도록 파티션 키 설계 및 트래픽 분산 전략을 수립해야 함

- [DDB-CAP-006] Reserved Capacity 구매 불가 인지 | severity: minor | auto: false
  - 검증: On-Demand 모드에서 Reserved Capacity 구매가 불가함을 인지하고 있는지 확인
  - 기준: On-Demand 모드 선택 시 Reserved Capacity를 통한 비용 절감이 불가함을 인지해야 함

## Backup & Recovery

- [DDB-BR-001] PITR(Point-in-Time Recovery) 활성화 | severity: major | auto: true
  - 검증: `aws dynamodb describe-continuous-backups --table-name {name}`의 `ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus` == `ENABLED`
  - 기준: 데이터 복구를 위해 PITR이 반드시 활성화되어야 함
  - 판정:
    - `PointInTimeRecoveryStatus` == `ENABLED` → ✅ PASS
    - `PointInTimeRecoveryStatus` == `DISABLED` → ❌ FAIL

## Infra

- [DDB-INF-001] Deletion Protection 활성화 | severity: critical | auto: true
  - 검증: `DeletionProtectionEnabled` == true
  - 기준: 프로덕션 테이블 삭제 방지 필수
  - 판정:
    - `DeletionProtectionEnabled` == true → ✅ PASS
    - `DeletionProtectionEnabled` == false 또는 필드 없음 → ❌ FAIL

- [DDB-INF-002] IaC 테이블 삭제 방지 설정 | severity: major | auto: false
  - 검증: IaC(CloudFormation/Terraform 등)에서 테이블 삭제 방지 설정이 되어 있는지 확인
  - 기준: IaC에서도 DeletionPolicy 또는 prevent_destroy 설정으로 테이블 삭제를 방지해야 함

- [DDB-INF-003] Global Tables 특성 및 주의사항 인지 | severity: major | auto: false
  - 검증: Global Tables 사용 시 그 특성(멀티리전 복제)과 주의사항(쓰기 충돌 해결 방식, 리전 간 복제 지연, 추가 비용, 제약사항 등)을 충분히 검토하고 인지하였는지 확인
  - 기준: Global Tables 사용 전 특성과 주의사항을 충분히 검토해야 함. Global Tables 미사용 시 해당 없음(X, 사유: 미사용)

- [DDB-INF-004] DAX 사용 필요성 검토 | severity: critical | auto: true
  - 검증: `aws dax describe-clusters --region {region}`으로 리전 내 DAX 클러스터 존재 여부 확인
  - 기준: DAX는 대부분의 경우 불필요하며, 사용 중인 경우 도입 근거와 대안(ElastiCache 등) 검토가 필요함
  - 판정:
    - `Clusters` 배열이 비어 있음 → ✅ PASS (DAX 미사용)
    - `Clusters` 배열에 1개 이상 존재 → ❌ FAIL (DAX 사용 중 — 도입 필요성 및 대안 검토 필요, 상세에 클러스터명 명시)
    - API 호출 실패 (AccessDenied 등) → N/A

- [DDB-INF-005] 암호화 키 유형 확인 (CMK vs AWS Owned) | severity: major | auto: true
  - 검증: `SSEDescription.SSEType` 및 `SSEDescription.Status` 확인
  - 기준: 민감 데이터를 다루는 테이블은 AWS Owned Key, AWS Managed Key(aws:kms) 또는 Customer Managed Key(aws:kms:dsse)를 사용해야 함
  - 판정:
    - `SSEDescription` 없음 또는 `SSEType` == `AES256` → ✅ PASS (AWS Owned Key 사용 중)
    - `SSEType` == `KMS` 또는 `DSSE_KMS` → ✅ PASS

## Security

- [DDB-SEC-001] IAM 최소 권한 원칙 | severity: critical | auto: true
  - 검증:
    1. `aws iam list-policies --scope Local`로 계정 내 커스텀 정책 목록 조회
    2. 각 정책의 현재 버전 문서를 `aws iam get-policy-version --policy-arn {arn} --version-id {version}`으로 조회
    3. `Statement[].Action`에 `dynamodb:` 접두사가 포함된 정책을 필터링
    4. 해당 정책의 Action에 `dynamodb:*` 또는 `*` 포함 여부 확인
  - 기준: DynamoDB 액션이 포함된 IAM 정책에 `dynamodb:*` 또는 `*` 와일드카드 액션이 허용되어서는 안 됨
  - 판정:
    - DynamoDB 관련 커스텀 정책 없음 → N/A
    - 모든 DynamoDB 관련 정책에 와일드카드 액션 없음 → ✅ PASS
    - `dynamodb:*` 또는 `*` 액션이 포함된 정책 존재 → ❌ FAIL (상세에 위배 정책명 전체 목록 및 해당 Statement 명시, 예: PolicyName1, PolicyName2, ...)
    - API 호출 실패 (AccessDenied 등) → N/A

- [DDB-SEC-002] IAM 정책 Resource 와일드카드 미사용 | severity: critical | auto: true
  - 검증: DDB-SEC-001에서 조회한 DynamoDB 관련 커스텀 정책 문서의 `Statement[].Resource` 확인
  - 기준: DynamoDB 액션이 포함된 Statement의 Resource는 아래 형식 중 하나여야 함
    - 테이블 ARN: `arn:aws:dynamodb:{region}:{account}:table/{table-name}`
    - 인덱스 ARN: `arn:aws:dynamodb:{region}:{account}:table/{table-name}/index/{index-name}`
    - 인덱스 전체: `arn:aws:dynamodb:{region}:{account}:table/{table-name}/index/*`
  - 판정:
    - DynamoDB 관련 커스텀 정책 없음 → N/A
    - 모든 Statement의 Resource가 위 허용 형식에 해당 → ✅ PASS
    - `*` 또는 `arn:aws:dynamodb:*` 등 테이블명이 명시되지 않은 Resource 존재 → ❌ FAIL (상세에 위배 정책명 전체 목록 및 해당 Resource 값 명시, 예: PolicyName1, PolicyName2, ...)
    - API 호출 실패 (AccessDenied 등) → N/A

- [DDB-SEC-003] Resource-based Policy 설정 | severity: critical | auto: true
  - 검증: `aws dynamodb get-resource-policy --resource-arn {table-arn}`으로 정책 존재 여부 확인
  - 기준: 각 테이블별로 Resource-based Policy를 설정하여 접근 제어를 강화해야 함
  - 판정:
    - Policy 존재 → ✅ PASS
    - Policy 없음 (ResourceNotFoundException 또는 빈 응답) → ❌ FAIL (상세에 Resource-based Policy 미설정 테이블명 전체 목록 명시, 예: TableName1, TableName2, ...)

- [DDB-SEC-004] VPC Endpoint를 통한 접근 | severity: critical | auto: true
  - 검증: `aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.{region}.dynamodb`로 Gateway Endpoint 존재 여부 확인
  - 기준: 인터넷을 경유하지 않고 VPC Endpoint(Gateway)를 통해 DynamoDB에 접근해야 함
  - 판정:
    - `VpcEndpoints` 배열에 `State` == `available`인 Gateway Endpoint 존재 → ✅ PASS
    - Gateway Endpoint 없음 → ❌ FAIL
