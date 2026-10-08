# DynamoDB ARB Reviewer Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
AWS DynamoDB 테이블의 ARB 검증을 수행합니다.

## 입력
- region
- 대상 DynamoDB 테이블 목록
- `arb-checklist/common.md` 내용
- `arb-checklist/dynamodb.md` 내용
- 사전 조사 파일 (아래 순서로 결정):
  1. `arb-config.md`의 `Pre-Survey > DynamoDB > file` 값이 있으면 해당 파일 사용
  2. 없으면 `pre-survey/dynamodb*.md` 패턴으로 탐색
     - 1개: 자동 선택
     - 2개 이상: 사용자에게 선택 요청
     - 0개: 사전 조사 없이 진행 (`auto: false` 항목은 판정 불가로 N/A 처리)

## 체크리스트 우선순위
동일 주제에 대해 common.md와 dynamodb.md가 상충하는 경우, **dynamodb.md의 기준을 우선 적용**하고 common.md 해당 항목은 N/A 처리합니다.

- COM-BR-001 (자동 백업): DDB-BR-001(PITR)로 대체 → N/A
- COM-BR-002 (삭제 방지): DDB-INF-001로 대체 → N/A
- COM-SEC-001 (암호화): DDB-INF-005로 대체 → N/A

## 수행 절차

### 1단계: 벌크 조회 (리전당 1회)

아래 명령어를 리전당 한 번씩 호출하여 결과를 저장합니다. 이후 단계에서 재사용합니다.
리소스 존재 여부 확인은 공통 규칙(`arb-agents/common-agent-rules.md`) 0단계를 따릅니다.

| 명령어 | 저장 변수 | 사용 항목 |
|--------|----------|----------|
| `aws dynamodb list-tables --region {region}` | `TABLE_LIST` | 전체 테이블 목록 |
| `aws application-autoscaling describe-scalable-targets --service-namespace dynamodb --region {region}` | `AUTOSCALING` | (참고용) |
| `aws service-quotas get-service-quota --service-code dynamodb --quota-code L-CF0CBE56 --region {region}` | `QUOTA_TABLE_READ` | DDB-CAP-002 |
| `aws service-quotas get-service-quota --service-code dynamodb --quota-code L-AB614373 --region {region}` | `QUOTA_TABLE_WRITE` | DDB-CAP-002 |
| `aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.{region}.dynamodb --region {region}` | `VPC_ENDPOINTS` | DDB-SEC-004 |
| `aws dax describe-clusters --region {region}` | `DAX_CLUSTERS` | DDB-INF-004 |
| `aws iam list-policies --scope Local --no-paginate` | `IAM_POLICIES` | DDB-SEC-001, DDB-SEC-002 |

IAM 정책 문서 조회: `IAM_POLICIES`에서 `dynamodb:` 액션이 포함된 정책만 필터링하여 각 정책의 현재 버전 문서를 조회합니다.
```
aws iam get-policy-version --policy-arn {arn} --version-id {version}
```
→ 결과를 `IAM_POLICY_DOCS`로 저장. DDB-SEC-001, DDB-SEC-002에서 재사용.

### 2단계: 테이블별 추가 조회

`TABLE_LIST`의 각 테이블에 대해 아래 명령어를 호출합니다.

- `aws dynamodb describe-table --table-name {name} --region {region}`
- `aws dynamodb describe-continuous-backups --table-name {name} --region {region}`
- `aws dynamodb get-resource-policy --resource-arn {arn} --region {region}`
- `aws dynamodb list-tags-of-resource --resource-arn {arn} --region {region}`
- `aws cloudwatch describe-alarms --alarm-name-prefix {name} --region {region}`

> DynamoDB는 서브넷/Security Group에 배치되지 않으므로 COM-AC-001, COM-AC-002, COM-NI-001은 N/A 처리합니다.

### 3단계: 체크리스트 검증

수집된 데이터를 기반으로 common.md + dynamodb.md의 모든 항목을 검증합니다.

#### 설계 항목의 판정 방식 (스키마 모델링 & 액세스 패턴 참고 분석)

설계 관련 `auto: false` 항목(DDB-TD-001~004, DDB-IDX-006, DDB-IDX-010 등)은 **개발팀이 pre-survey에 표기한 O/X 응답을 기본 판정으로 삼습니다.** 어트리뷰트명·설명만으로는 개발팀의 설계 의도를 정확히 파악하기 어렵기 때문입니다.

에이전트는 사전 조사 파일에 첨부된 **스키마 모델링 문서**와 **액세스 패턴 정리 문서**를 함께 읽고, 설계상 우려되는 지점을 찾아 **상세란에 기재하여 개발팀이 인지할 수 있도록** 합니다. 이때 판정은 다음 원칙을 따릅니다.

- **기본 판정은 개발자 응답을 존중**합니다. 개발팀이 `O`로 표기했으면 원칙적으로 ✅ PASS, `X`면 ❌ FAIL.
- **FAIL로 뒤집는 것은 문서상 명백한 결함이 확인될 때만** 합니다. 다음과 같이 반박의 여지가 거의 없는 경우에 한합니다.
  - 액세스 패턴이 참조하는 키/인덱스가 스키마에 **아예 정의되어 있지 않음** (패턴 미커버)
  - 파티션 키를 특정하지 못해 **Scan이 불가피한** 액세스 패턴이 존재
  - 그 외 문서만으로 명백히 기준 위반이 드러나는 경우
- **애매하거나 의도 확인이 필요한 사항**(예: 어트리뷰트명 기반 카디널리티 추정, Projection 적정성, 설계 방식 근거의 충분성 등)은 **판정을 바꾸지 않고**, 상세란에 "⚠️ 우려 사항"으로 근거와 함께 기재하여 개발팀이 검토·해명할 수 있게 합니다.
- 사전 조사 파일에 스키마 모델링/액세스 패턴 문서가 첨부되지 않은 경우, 해당 설계 항목은 O/X 응답만으로 판정하고, 문서가 없어 추가 분석이 불가함을 상세란에 명시합니다.

아래 관점으로 각 설계 항목을 살펴보고, 결함이나 우려사항을 해당 항목의 **상세란에 기재**합니다. (별도 분석 파일이나 추가 점검 항목은 만들지 않습니다.)

> **판정 기조**: DynamoDB에서 통용되는 정상적인 설계 패턴(예: Query로 파티션 키를 지정해 특정 파티션만 읽은 뒤 Filter Expression으로 걸러내기)은 결함이 아닙니다. 확실한 결함만 FAIL로 판정하고, 나머지 우려는 상세란 기재로 갈음합니다.

| Check ID | 검토 관점 (문서 기반) | 판정 원칙 |
|----------|---------------------|----------|
| DDB-TD-001 | 기본 테이블 PK가 특정 소수 값에 데이터가 집중될 소지가 있는지 | 명백한 핫 파티션(예: PK가 Y/N 같은 이진값)만 FAIL 검토. 그 외는 개발자 응답 유지 + 우려 시 상세 기재 |
| DDB-TD-002 | 각 AP의 Key Condition이 참조하는 키/인덱스가 스키마에 정의되어 있는지 | 미정의(패턴 미커버) 또는 Scan 불가피 시 FAIL. 파티션 키 지정 후 Filter 사용은 정상(PASS) |
| DDB-TD-003 | 정의된 GSI/LSI가 실제 AP에 대응하는지 | AP가 요구하는 인덱스가 없으면 FAIL. 대응 없는 인덱스나 Projection 적정성은 상세란에 우려로 기재 |
| DDB-TD-004 | Single/Multi Table 선택 근거 기재 여부 | 개발자 응답 유지. 근거가 액세스 패턴과 명백히 배치되면 우려로 기재 |
| DDB-IDX-006 | 각 GSI PK가 특정 소수 값에 집중될 소지가 있는지 | 명백한 경우만 FAIL 검토. 그 외 개발자 응답 유지 + 우려 시 상세 기재 |
| DDB-IDX-010 | GSI PK/SK가 갱신 대상(mutable)일 가능성 | 개발자 응답 유지. mutable 소지가 보이면 상세란에 "키 변경 시 삭제-재삽입 동작 확인 필요"로 기재 |
| DDB-IDX-002 | LSI 존재 시 아이템 400KB 초과 소지 | LSI 미사용 시 N/A. 명백한 초과 우려만 상세란에 기재 |

추가로 위 항목 판정 과정에서 발견한 Projection 미스매치(대응 AP가 요구하는 어트리뷰트 누락으로 Fetch 발생, 또는 불필요한 `ALL`) 등 보완사항은 가장 관련 있는 항목(DDB-TD-003 또는 해당 IDX 항목)의 상세란에 함께 기재합니다.

### 4단계: 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | API 응답에서 확인 가능하고 기준 충족, 또는 사전 조사 파일에서 해당 Check ID의 완료 여부가 `O`이고 비고 내용이 기준에 부합 |
| ❌ FAIL | API 응답에서 확인 가능하고 기준 미충족, 또는 사전 조사 파일에서 해당 Check ID의 완료 여부가 `X` |
| N/A | 해당 엔진/구성에 적용되지 않는 항목, 다른 항목으로 대체된 항목, 또는 사전 조사 파일이 없어 `auto: false` 항목을 판정할 수 없는 경우 (사유 명시) |

> **`auto: false` 항목 판정 방법**
> - **설계 항목(DDB-TD-001~004, DDB-IDX-006, DDB-IDX-010, DDB-IDX-002 등)**: 사전 조사 파일의 해당 Check ID `완료 여부(O/X)`를 **기본 판정으로 삼습니다.** 에이전트는 3단계에서 스키마 모델링·액세스 패턴 문서를 참고 분석하되, **문서상 명백한 결함이 확인될 때만 FAIL로 뒤집고**, 그 외 우려사항은 판정을 바꾸지 않고 상세란에 "⚠️ 우려 사항"으로 기재하여 개발팀이 인지·검토하도록 합니다. 문서 미첨부 시 O/X만으로 판정하고 상세에 명시합니다.
> - **그 외 `auto: false` 항목(DDB-CAP-005, DDB-CAP-006, DDB-INF-002, DDB-INF-003, DDB-IDX-002, DDB-IDX-003 등 인지·설정 확인성 항목)**: 사전 조사 파일의 해당 Check ID `완료 여부(O/X)` 및 `비고` 내용을 읽어 판정합니다.
> - 사전 조사 파일이 없는 경우: N/A 처리하고 상세에 "사전 조사 파일 없음" 명시

## 출력 규칙

공통 규칙(`arb-agents/common-agent-rules.md`)을 따릅니다.
아래는 DynamoDB 특화 사항입니다.

### 리소스 단위
- 리소스 단위: 테이블(table)
- 리소스 식별자: `TableName`

### 섹션 구성
각 테이블별 출력은 Common Checks → DynamoDB Checks 순으로 작성합니다.

### N/A 처리 명시
N/A 항목은 결과 컬럼에 `N/A`로 표시하고 상세 컬럼에 사유를 명시합니다.
예: `COM-AC-001 | ... | N/A | DynamoDB는 Security Group 미적용`

## 리소스 요약 정보 (상세 리포트 헤더)
```
BillingMode: {mode} | ItemCount: {count} | Region: {region}
```

## 출력 파일명
`arb-reports/{service_name}/{region}/{YYYY-MM-DD}/dynamodb.md`
