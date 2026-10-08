# Aurora PostgreSQL 사전 조사

ARB 리뷰 전 개발팀에서 작성하여 제출하는 문서입니다.
각 항목을 확인하고 완료 여부와 비고를 기재해 주세요.

- **서비스명**: payment-service
- **작성자**: 홍길동
- **작성일**: 2026-06-05
- **클러스터**: payment-aurora-pg-cluster
- **호스트**: payment-aurora-pg-cluster.cluster-cjw3rjxuxcfa.ap-northeast-2.rds.amazonaws.com
- **데이터베이스**: paymentdb

---

## 1. 계정 목록

> **완료 여부 표기 기준**
> - **O**: 완료, 검토 완료, 인지 완료, 반영 완료 등 해당 항목을 충족한 경우
> - **X**: 미완료, 미검토, 미흡, 미사용, 해당 없음 등 충족하지 못하거나 해당하지 않는 경우
>   - X 표기 시 비고란에 사유 또는 추가 설명을 작성해 주세요.

### 자동 조회 결과

| rolname | rolcanlogin | rolsuper | member_of |
|---------|-------------|----------|-----------|
| svc_payment | true | false | svc_payment_role |
| dba_admin | true | false | rds_superuser |
| dev_park | true | false | readonly_role |
| dev_lee | true | false | readonly_role |

### 계정별 권한

| 계정 | 권한 |
|------|------|
| svc_payment_role | GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public |
| dba_admin | GRANT rds_superuser |
| readonly_role | GRANT SELECT ON ALL TABLES IN SCHEMA public |

---

## 2. Account Management

### 2.1 계정 분류 및 권한 확인

| Check ID | 항목 | ACCOUNT | 용도 | 권한적절(O/X) | 비고 |
|----------|------|---------|------|--------------|------|
| AURPG-ACC-001 + AURPG-ACC-004 | DB 계정 분류 및 권한 확인 | svc_payment | SERVICE | O | WAS 서비스 계정, DML만 허용 |
| | | dba_admin | DBA | O | 관리자 계정 |
| | | dev_park | PERSONAL | O | 개발자 개인 계정, SELECT만 허용 |
| | | dev_lee | PERSONAL | X | 개발자 개인 계정이나 INSERT 권한 존재 -- 조치 필요 |

### 2.2 기타 계정 관리

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| AURPG-ACC-002 | 개인 사용자 계정 1인 1계정 원칙 (공용 계정 사용 금지) | O | |
| AURPG-ACC-003 | postgres 기본 마스터 유저명 서비스 미사용 (마스터 계정은 관리 목적으로만 사용) | O | svc_payment 별도 계정 사용 |
| AURPG-ACC-005 | DB 계정 관리 DBA 담당 | O | 김철수 / DB운영팀 |
| AURPG-ACC-006 | DB 계정 신규/변경/삭제 프로세스 문서 존재 | O | https://confluence.example.com/db-account-process |
| AURPG-ACC-007 | DB 계정 권한 리스트 문서 최신 유지 | O | 최종 갱신일: 2026-05-20 |
| AURPG-ACC-008 | DB 계정 내역 5년 보관 | X | 현재 1년치만 보관 중, 개선 예정 |
| AURPG-ACC-009 | Instance Name Rule 준수 (클러스터: payment-aurora-pg-cluster) | O | |

---

## 3. Schema Design

### 3.1 FK 사용 의도 확인

#### 자동 조회 결과

| TABLE | CONSTRAINT | REF TABLE |
|-------|-----------|-----------|
| order_items | fk_order_id | orders |

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| AURPG-SCH-001 | FK 사용이 의도된 설계인가 | O | |
| | 성능 영향 검토 완료 | O | |

### 3.2 Function/Procedure 제약사항 확인

#### 자동 조회 결과

등록된 Function/Procedure : 없음

### 3.3 테이블 PK 타입 확인

#### 자동 조회 결과

| TABLE | COLUMN | DATA_TYPE | AUTO/IDENTITY | STATUS |
|-------|--------|-----------|---------------|--------|
| orders | id | bigint | IDENTITY | OK |
| order_items | item_id | varchar | - | WARN |
| payments | payment_id | bigint | IDENTITY | OK |

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| AURPG-SCH-003 | WARN 항목 개선 예정 | O | |

### 3.4 중복 체크 UK 또는 로직단 처리

#### 자동 조회 결과

| TABLE | CONSTRAINT | COLUMNS |
|-------|-----------|---------|
| orders | uk_order_no | order_no |
| payments | uk_tx_id | transaction_id |

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| AURPG-SCH-004 | UK 없는 테이블의 중복 방지를 로직단에서 처리 | O | order_items는 order_id+seq 복합키로 중복 방지 |

### 3.5 인덱스 네이밍룰 준수

#### 자동 조회 결과

| TABLE | INDEX | COLUMNS | TYPE |
|-------|-------|---------|------|
| orders | idx_user_id | user_id | btree |
| orders | myindex1 | created_at | btree |
| order_items | idx_order_id | order_id | btree |
| payments | idx_user_amt | user_id, amount | btree |

| Check ID | 항목 | 완료 여부(O/X) | 비고 |
|----------|------|--------------|------|
| AURPG-SCH-005 | 네이밍룰 미준수 항목 없음 또는 개선 예정 | X | orders.myindex1 → idx_created_at 으로 변경 예정 (2026-07-30) |
