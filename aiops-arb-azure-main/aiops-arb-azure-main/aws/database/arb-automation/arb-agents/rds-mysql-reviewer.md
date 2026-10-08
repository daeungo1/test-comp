# RDS MySQL ARB Reviewer Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
AWS RDS MySQL 인스턴스의 ARB 검증을 수행합니다.
Aurora 엔진 및 RDS PostgreSQL은 제외합니다.

## 입력
- region
- `arb-checklist/common.md` 내용
- `arb-checklist/rds-mysql.md` 내용
- 사전 조사 파일 (아래 순서로 결정):
  1. `arb-config.md`의 `Pre-Survey > RDS MySQL > file` 값이 있으면 해당 파일 사용
  2. 없으면 `pre-survey/rds-mysql*.md` 패턴으로 탐색
     - 1개: 자동 선택
     - 2개 이상: 사용자에게 선택 요청
     - 0개: 사전 조사 없이 진행 (`auto: false` 항목은 N/A 처리)

## 수행 절차

### 1단계: 벌크 조회 (리전당 1회)

아래 명령어를 리전당 한 번씩 호출하여 결과를 저장합니다. 이후 단계에서 재사용합니다.
리소스 존재 여부 확인은 공통 규칙(`arb-agents/common-agent-rules.md`) 0단계를 따릅니다.

| 명령어 | 저장 변수 | 사용 항목 |
|--------|----------|----------|
| `aws rds describe-db-instances --filters Name=engine,Values=mysql --region {region}` | `INSTANCES` | 전체 인스턴스 기본 정보 |
| `aws ec2 describe-vpcs --region {region}` | `VPCS` | COM-NI-001, COM-SEC-004 |

### 2단계: 인스턴스별 추가 조회

`INSTANCES`의 각 인스턴스에 대해 아래 명령어를 호출합니다.

| 명령어 | 사용 항목 |
|--------|----------|
| `aws rds describe-db-parameters --db-parameter-group-name {param-group-name} --region {region}` | RDSMY-SEC-003 (`validate_password.*`), RDSMY-SEC-005 (`default_authentication_plugin`), RDSMY-MY-010~027 (각종 파라미터) |
| `aws rds list-tags-for-resource --resource-name {instance-arn} --region {region}` | COM-TAG-001 |
| `aws cloudwatch describe-alarms --alarm-name-prefix {instance-id} --region {region}` | COM-MON-001, COM-MON-004 |
| `aws ec2 describe-security-groups --group-ids {sg-ids} --region {region}` | COM-AC-001, COM-AC-002 |
| `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values={subnet-id} --region {region}` | COM-NI-001 (IGW 경로 확인) |
| `aws ec2 describe-vpcs --vpc-ids {vpc-id} --region {region}` | COM-SEC-004 (default VPC 확인) |
| `aws rds describe-db-engine-versions --engine mysql --include-all --region {region}` | RDSMY-MY-002 (deprecated 판정) |

> 동일 Parameter Group을 공유하는 인스턴스가 여러 개여도 **1회만 조회**합니다.

### 3단계: 체크리스트 검증

수집된 데이터를 기반으로 common.md + rds-mysql.md의 모든 항목을 검증합니다.

### 4단계: 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | AWS CLI 응답에서 기준 충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준에 부합 |
| ❌ FAIL | AWS CLI 응답에서 기준 미충족이 확인됨, 또는 사전 조사 파일에서 해당 항목이 기준 미충족 |
| N/A | 해당 구성에 적용되지 않는 항목, 또는 사전 조사 파일이 없어 `auto: false` 항목을 판정할 수 없는 경우 (사유 명시) |

## 검증 로직

### 엔진 버전 EOL 검증 로직 (RDSMY-MY-002)
- `describe-db-instances` → `EngineVersion` 추출 (예: `8.0.40`)
- deprecated 판정: `aws rds describe-db-engine-versions --engine mysql --include-all --query "DBEngineVersions[?Status=='deprecated'].EngineVersion"` 에 포함되면 FAIL
- available 버전이면 PASS
- 참고: AWS RDS의 지원 종료일은 커뮤니티 EOL과 다를 수 있으므로 AWS API 결과를 기준으로 판정
- **지원 종료 정보 리포트 표기 규칙 (오해 방지)**:
  - EngineVersion을 메이저(`8.0`)와 마이너(`8.0.40`)로 분리한다.
  - **검증 대상보다 낮은 메이저 버전의 EOL 정보는 표기하지 않는다.** (예: 8.0.x 검증 시 5.7 EOL은 노이즈이므로 제외)
  - 검증 대상이 마이너 버전이면, 리포트에 다음 두 날짜를 **반드시 구분하여** 명시한다.
    1. 사용 중인 메이저 버전(MySQL 8.0)의 RDS 표준 지원 종료일
    2. 사용 중인 마이너 버전(8.0.40) 자체의 RDS 표준 지원 종료일
  - 마이너 버전 종료일이 메이저보다 빠를 수 있음을 코멘트로 강조한다.
    - 실제 예: 8.0.40의 RDS 표준 지원 종료는 2026-05-31, 메이저 8.0은 2026-07-31.
  - 날짜 조회:
    - 마이너 버전: `aws rds describe-db-engine-versions --engine mysql --engine-version {major.minor.patch} --include-all` (권한/필드 없으면 Release Calendar minor version 표 참조)
    - 메이저 버전: `aws rds describe-db-major-engine-versions --engine mysql` (또는 Release Calendar major version 표)
    - 참고 문서: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Concepts.VersionMgmt.html
  - 리포트 참고 정보 표 형식 (검증 대상 버전만 포함):

    | 구분 | 버전 | RDS 표준 지원 종료일 |
    |------|------|---------------------|
    | 사용 중인 마이너 버전 | 8.0.40 | 2026-05-31 |
    | 사용 중인 메이저 버전 | MySQL 8.0 | 2026-07-31 |

    ※ 마이너 버전(8.0.40)의 표준 지원 종료일은 메이저 버전(8.0)보다 빠를 수 있습니다. 메이저 EOL이 아닌 **마이너 버전 종료일 기준**으로 업그레이드 계획을 수립해야 합니다.

## 리소스 요약 정보 (상세 리포트 헤더)
```
Engine: mysql | Class: {DBInstanceClass} | Region: {region}
```

## 출력 파일명
`arb-reports/{service_name}/{region}/{YYYY-MM-DD}/rds-mysql.md`
