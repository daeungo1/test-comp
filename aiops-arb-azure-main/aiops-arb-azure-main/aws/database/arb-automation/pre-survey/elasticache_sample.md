# ElastiCache 캐시 설계 사전 조사

ARB 리뷰 전 개발팀에서 작성하여 제출하는 문서입니다.
각 항목을 확인하고 완료 여부와 비고를 기재해 주세요.

- **서비스명**: order-cache-service
- **작성자**: 홍길동
- **작성일**: 2026-05-22

---

## 1. 클러스터 목록

사용 중인 ElastiCache 클러스터를 모두 기재해 주세요.

| 클러스터명(ReplicationGroupId) | 엔진 | 용도 | Cluster Mode | 노드 타입 |
|-------------------------------|------|------|-------------|----------|
| order-svc-prod-session | Redis 7.1 | 세션 저장 | Enabled | cache.r7g.large |
| order-svc-prod-cache | Valkey 7.2 | 상품/재고 캐시 | Enabled | cache.r7g.xlarge |

---

## 2. 설계 검토 항목

> **완료 여부 표기 기준**
> - **O**: 완료, 검토 완료, 인지 완료, 반영 완료 등 해당 항목을 충족한 경우
> - **X**: 미완료, 미검토, 미흡, 미사용, 해당 없음 등 충족하지 못하거나 해당하지 않는 경우
>   - X 표기 시 비고란에 사유 또는 추가 설명을 작성해 주세요.

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| EC-DATA-001 | 사용 중인 Redis Data Type(String, Hash, List, Set, Sorted Set 등)이 용도에 적합한지 검토하였나요? | O | 하단 Data Type 상세 참고 |
| EC-DATA-002 | Cache Design Pattern(Cache-Aside, Write-Through, Write-Behind 등)을 선택하고 근거를 정리하였나요? | O | 하단 Cache Design Pattern 상세 참고 |
| EC-CLI-001 | 공식 권장 Redis Client를 사용하고 있나요? | O | 하단 Client 정보 참고 |

---

## 3. Data Type 상세 (EC-DATA-001)

각 클러스터에서 사용하는 주요 Key 패턴과 Data Type을 기재해 주세요.

### order-svc-prod-session

| Key 패턴 | Data Type | 용도 | TTL |
|----------|-----------|------|-----|
| `sess:{session_id}` | Hash | 사용자 세션 정보 (uid, role, login_at 등) | 30분 |
| `sess:{session_id}:cart` | List | 장바구니 아이템 목록 | 30분 |

### order-svc-prod-cache

| Key 패턴 | Data Type | 용도 | TTL |
|----------|-----------|------|-----|
| `product:{product_id}` | Hash | 상품 상세 정보 캐시 | 5분 |
| `stock:{product_id}` | String | 재고 수량 (INCR/DECR 연산) | 10초 |
| `ranking:daily` | Sorted Set | 일별 상품 판매 랭킹 | 1시간 |
| `user:{user_id}:recent` | List | 최근 본 상품 목록 (LPUSH + LTRIM) | 24시간 |

---

## 4. Cache Design Pattern 상세 (EC-DATA-002)

각 데이터별 적용한 캐시 디자인 패턴과 선택 이유를 기재해 주세요.

| 대상 데이터 | 패턴 | 선택 이유 |
|------------|------|----------|
| 상품 정보 | Cache-Aside (Lazy Loading) | 읽기 빈도 높고 변경 빈도 낮음. Cache Miss 시에만 DB 조회 후 캐시 적재 |
| 재고 수량 | Write-Through | 주문/결제 시 즉시 반영 필요. 쓰기 시 캐시와 DB 동시 업데이트 |
| 세션 데이터 | Write-Through | 로그인/권한 변경 즉시 반영 필요. 일관성 보장 우선 |
| 판매 랭킹 | Cache-Aside + TTL | 실시간성 불필요. 1시간 주기로 갱신하여 DB 부하 최소화 |

---

## 5. Client 정보 (EC-CLI-001)

애플리케이션에서 사용하는 Redis Client 라이브러리를 기재해 주세요.

| 언어 | Client 라이브러리 | 버전 | Cluster Mode 지원 | 비고 |
|------|-----------------|------|-----------------|------|
| Java | Lettuce | 6.3.x | O | Spring Data Redis 기본 클라이언트, 비동기/리액티브 지원 |
| Python | redis-py | 5.0.x | O | 배치 스크립트용 |
