# DynamoDB 스키마 설계 사전 조사

ARB 리뷰 전 개발팀에서 작성하여 제출하는 문서입니다.
각 항목을 확인하고 완료 여부와 비고를 기재해 주세요.

- **서비스명**: order-service
- **작성자**: 홍길동
- **작성일**: 2026-05-22

---

## 1. 테이블 목록

사용 중인 DynamoDB 테이블을 모두 기재해 주세요.

| 테이블명 | 설명 | 설계 방식 (Single/Multi Table) | 선택 이유 |
|---------|------|-------------------------------|----------|
| order-service-prod | 주문/상품/배송 통합 테이블 | Single Table | 주문-상품-배송 간 관계 조회 및 트랜잭션 처리가 빈번하여 Single Table 선택 |

---

## 2. 스키마 모델링 문서 및 액세스 패턴 문서 제출

| 항목 | 제출여부(O/X) | 비고 |
|------|-------------|------|
| 스키마 모델링 문서 | O | 하단 샘플 참고 |
| 액세스 패턴 정리 문서 | O | 하단 샘플 참고 |

---

## 3. 설계 검토 항목

> **완료 여부 표기 기준**
> - **O**: 완료, 검토 완료, 인지 완료, 반영 완료 등 해당 항목을 충족한 경우
> - **X**: 미완료, 미검토, 미흡, 미사용, 해당 없음 등 충족하지 못하거나 해당하지 않는 경우
>   - X 표기 시 비고란에 사유 또는 추가 설명을 작성해 주세요.

### 3.1 테이블 설계

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| DDB-TD-001 | 파티션 키(PK)의 카디널리티가 높은지 검토하였나요? (카디널리티: 해당 키가 가질 수 있는 고유값의 수. userId, orderId처럼 고유값이 많을수록 높음) | O | PK=orderId (주문 수만큼 고유값 생성, 카디널리티 높음) |
| DDB-TD-002 | 서비스의 모든 Read/Write 액세스 패턴을 사전에 정의하고, PK/SK가 해당 패턴을 커버하도록 설계하였나요? | O | 하단 액세스 패턴 문서 참고 (AP-01~AP-09) |
| DDB-TD-003 | LSI/GSI가 실제 액세스 패턴에 기반하여 설계되었나요? | O | gsi_user_orders: uid(PK), cat(SK) — AP-04, AP-05 대응 |
| DDB-TD-004 | Single Table / Multi Table 설계 방식 선택 근거가 명확한가요? | O | 1번 테이블 목록 참고 |
| DDB-TD-005 | 어트리뷰트 네이밍 컨벤션이 정의되어 있고 일관되게 적용되었나요? | O | 3자리 이내 축약 소문자 snake_case 적용 (pk, sk, oid, uid 등) |
| DDB-TD-006 | 어트리뷰트 이름이 불필요하게 길지 않게 설계되었나요? | O | 전체 어트리뷰트명 3자리 이내 축약 적용 |

### 3.2 인덱스 설계

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| DDB-IDX-001 | LSI 사용 전 GSI로 대체 가능한지 검토하였나요? | O | LSI 미사용, GSI만 사용 |
| DDB-IDX-002 | LSI가 있는 테이블에서 아이템 크기가 기본 테이블 + 모든 LSI 합산 400KB를 초과하지 않도록 설계하였나요? | X | LSI 미사용 |
| DDB-IDX-003 | LSI 사용 시 동일 파티션 키 값의 아이템 컬렉션(기본 테이블 + 모든 LSI 합산)이 10GB로 제한됨을 인지하고 있나요? | X | LSI 미사용 |
| DDB-IDX-006 | GSI의 파티션 키 카디널리티를 검토하였나요? | O | gsi_user_orders PK=uid (사용자 수만큼 고유값, 카디널리티 높음) |
| DDB-IDX-009 | Sparse Index 패턴 적용을 검토하였나요? | X | 현재 액세스 패턴상 Sparse Index 적용 대상 없음 |
| DDB-IDX-010 | GSI 파티션 키 값 변경 시 동작 방식을 인지하고 애플리케이션 로직에 반영하였나요? | O | uid 변경 시 기존 항목 삭제 후 재삽입 동작 인지, 애플리케이션에서 uid 변경 불가 처리 |

### 3.3 용량 및 비용

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| DDB-CAP-005 | 파티션당 처리량 한도(3,000 RCU / 1,000 WCU)를 인지하고 있나요? | O | orderId를 PK로 사용하여 트래픽 분산, 핫 파티션 위험 낮음 |
| DDB-CAP-006 | On-Demand 모드 사용 시 Reserved Capacity 구매가 불가함을 인지하고 있나요? (구매 시 당사-AWS 간 PPA 파기됨) | O | On-Demand 모드 사용 예정, PPA 파기 위험 인지 완료 |

### 3.4 인프라

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| DDB-INF-002 | IaC에서 테이블 삭제 방지 설정이 되어 있나요? | O | Terraform prevent_destroy = true 설정 완료 |
| DDB-INF-003 | Global Tables 사용 시 그 특성(멀티리전 복제)과 주의사항(쓰기 충돌 해결, 복제 지연, 추가 비용, 제약사항)을 충분히 검토·인지하였나요? (미사용 시 X, 사유: 미사용) | X | Global Tables 미사용 (단일 리전 운영) |

---

## 스키마 모델링 문서

### 테이블명: order-service-prod

#### 엔티티 목록

- 주문 (Order)
- 주문 상품 (Order Item)
- 배송 (Delivery)

#### 엔티티별 어트리뷰트

**주문 (Order)**

| 어트리뷰트 (축약) | 어트리뷰트 (풀네임) | 타입 | 예시 값 | 설명 |
|----------------|------------------|------|--------|------|
| pk | PartitionKey | S | `ORDER#o-5678` | 주문 ID |
| sk | SortKey | S | `ORDER#o-5678` | 주문 ID (동일값, 단일 아이템 조회용) |
| oid | orderId | S | `o-5678` | 주문 번호 |
| uid | userId | S | `u-1234` | 사용자 ID (GSI PK로 활용) |
| st | status | S | `PAID` | 주문 상태 (PENDING/PAID/SHIPPED/DELIVERED/CANCELLED) |
| amt | totalAmount | N | `35000` | 총 결제 금액 |
| cat | createdAt | S | `2026-05-22T10:00:00Z` | 주문 생성 시각 (ISO 8601) |

**주문 상품 (Order Item)**

| 어트리뷰트 (축약) | 어트리뷰트 (풀네임) | 타입 | 예시 값 | 설명 |
|----------------|------------------|------|--------|------|
| pk | PartitionKey | S | `ORDER#o-5678` | 주문 ID |
| sk | SortKey | S | `ITEM#i-001` | 상품 순번 |
| pid | productId | S | `p-9999` | 상품 ID |
| pnm | productName | S | `무선 마우스` | 상품명 |
| qty | quantity | N | `2` | 수량 |
| prc | price | N | `15000` | 단가 |

**배송 (Delivery)**

| 어트리뷰트 (축약) | 어트리뷰트 (풀네임) | 타입 | 예시 값 | 설명 |
|----------------|------------------|------|--------|------|
| pk | PartitionKey | S | `ORDER#o-5678` | 주문 ID |
| sk | SortKey | S | `DELIVERY#d-001` | 배송 ID |
| car | carrier | S | `CJ대한통운` | 택배사 |
| trk | trackingNumber | S | `1234567890` | 운송장 번호 |
| dat | deliveredAt | S | `2026-05-24T14:30:00Z` | 배송 완료 시각 |

#### GSI

| 인덱스명 | Partition Key | Sort Key | Projection 타입 | 카디널리티 설명 | 대응 액세스 패턴 |
|---------|--------------|----------|----------------|--------------|---------------|
| gsi_user_orders | `uid` (S) | `cat` (S) | INCLUDE (oid, st, amt) | userId 수만큼 고유값 생성 — 카디널리티 높음 | AP-04, AP-05 |

---

## 액세스 패턴 정리 문서

| # | 유형 | 패턴 설명 | Key Condition | Filter Expression | 사용 키/인덱스 |
|---|------|----------|--------------|------------------|--------------|
| AP-01 | Read | 특정 주문 상세 조회 | pk = `ORDER#{orderId}`, sk = `ORDER#{orderId}` | - | 기본 테이블 |
| AP-02 | Read | 특정 주문의 상품 목록 조회 | pk = `ORDER#{orderId}`, sk begins_with `ITEM#` | - | 기본 테이블 |
| AP-03 | Read | 특정 주문의 배송 정보 조회 | pk = `ORDER#{orderId}`, sk begins_with `DELIVERY#` | - | 기본 테이블 |
| AP-04 | Read | 특정 사용자의 주문 목록 조회 (최신순) | uid = `{userId}` | - | gsi_user_orders |
| AP-05 | Read | 특정 사용자의 특정 기간 주문 조회 | uid = `{userId}`, cat between `2026-05-01T00:00:00Z` and `2026-05-31T23:59:59Z` | amt > `10000` | gsi_user_orders |
| AP-06 | Write | 신규 주문 생성 | pk = `ORDER#{orderId}`, sk = `ORDER#{orderId}` PutItem | - | 기본 테이블 |
| AP-07 | Write | 주문에 상품 추가 | pk = `ORDER#{orderId}`, sk = `ITEM#{itemId}` PutItem | - | 기본 테이블 |
| AP-08 | Write | 주문 상태 업데이트 | pk = `ORDER#{orderId}`, sk = `ORDER#{orderId}` UpdateItem (st) | - | 기본 테이블 |
| AP-09 | Write | 배송 정보 등록 | pk = `ORDER#{orderId}`, sk = `DELIVERY#{deliveryId}` PutItem | - | 기본 테이블 |
