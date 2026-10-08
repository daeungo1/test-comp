# 공통 에이전트 규칙

모든 ARB Reviewer Agent가 따르는 공통 규칙입니다.
각 엔진별 에이전트 프롬프트에서 이 파일을 참조합니다.

## 입력값 우선순위

오케스트레이터(arb-database)로부터 전달받은 프롬프트 내 값을 **항상 최우선**으로 사용합니다.
`arb-config.md`는 프롬프트에 값이 없는 경우에만 fallback으로 참조합니다.

| 항목 | 우선순위 |
|------|---------|
| service_name | 1) 프롬프트 명시값 → 2) arb-config.md |
| region | 1) 프롬프트 명시값 → 2) arb-config.md |
| account_id | 1) 프롬프트 명시값 → 2) aws sts get-caller-identity |
| AWS 프로파일 | 1) 프롬프트 명시값 → 2) arb-target 기본값 |

> **주의**: 프롬프트에 service_name, region 등이 명시되어 있을 때 절대 사용자에게 재확인하거나 입력을 요청하지 마세요.

## AWS CLI 커맨드 로깅

**AWS CLI를 포함한 모든 행동(파일 읽기, 파일 저장, AWS CLI 호출 등)은 즉시 로그 파일에 기록합니다.**

### 로그 파일 경로
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/logs/{engine-slug}-commands.log
```

### 로그 형식
각 행동마다 다음을 기록:
```
[{timestamp}] ACTION: {수행한 행동 (예: AWS CLI 호출, 파일 읽기, 파일 저장 등)}
[{timestamp}] PURPOSE: {어떤 체크 항목을 위한 행동인지}
[{timestamp}] RESPONSE_SUMMARY: {응답 요약 — 리소스 수 또는 핵심 값}
---
```

### 규칙
- 검증 시작 시 로그 파일 생성
- AWS CLI 호출, 파일 읽기, 파일 저장 등 모든 행동을 빠짐없이 기록
- **각 행동 직후 즉시 로그 파일에 append하세요. 완료 후 일괄 저장하지 마세요.**
- 오케스트레이터로부터 전달받은 데이터를 사용한 경우에도 "DATA_FROM_ORCHESTRATOR" 로 기록

---

## 0단계: 리소스 존재 여부 선검증 (공통)

모든 엔진 reviewer는 본격적인 점검 전 **1단계 벌크 조회 결과를 먼저 확인**합니다.

| 조건 | 동작 |
|------|------|
| 리소스 0개 (빈 배열) | 점검 미수행. 리포트 파일에 "대상 리전에 {엔진명} 리소스가 존재하지 않아 점검 대상 없음 (점검 미수행)"을 기록하고 **리포트 파일은 정상 생성** |
| 리소스 1개 이상 | 결과를 저장 변수에 유지하고 2단계로 진행 |

> 각 엔진 reviewer의 1단계 벌크 조회 결과에서 빈 배열 여부를 확인합니다. 별도의 추가 API 호출은 불필요합니다.

---

## AWS CLI 호출 전략

**원칙: 벌크 조회 우선, 추가 호출 최소화**

1. **1차 벌크 조회** — 리소스 목록 API를 필터와 함께 한 번 호출하여 전체 상세 정보를 가져옴
   - 개별 리소스별로 describe를 반복 호출하지 않음
   - 오케스트레이터가 전달한 리소스 목록 JSON에 이미 상세 정보가 포함된 경우, 추가 describe 호출 불필요

2. **1차 응답으로 판정 가능한 항목 먼저 처리** — describe 응답만으로 확인 가능한 체크리스트 항목을 모두 판정

3. **추가 조회는 필요한 항목만** — 1차 응답으로 확인 불가한 항목에 한해 추가 API 호출:
   - Parameter Group 상세: `describe-db-parameters`
   - 태그: `list-tags-for-resource`
   - CloudWatch 알람: `describe-alarms`
   - Security Group: `describe-security-groups`
   - 서브넷 라우트 테이블: `describe-route-tables`

4. **동일 API 중복 호출 금지** — 같은 파라미터 그룹을 여러 인스턴스가 공유하면 한 번만 조회

5. **Pagination 처리** — AWS CLI 응답이 `NextToken`/`Marker`를 포함하면 모든 페이지를 조회하여 전체 결과를 확보. `--no-paginate` 옵션 사용 권장

6. **에러 핸들링**
   - API 호출 실패 시 로그에 에러 내용 기록
   - 권한 부족(`AccessDenied`): 해당 체크 항목을 `⚠️ MANUAL (권한 부족)` 으로 판정
   - 리소스 미존재(`NotFound`): 해당 리소스 건너뜀
   - 기타 에러: 3회 재시도 후 실패 시 `⚠️ MANUAL (API 에러)` 로 판정

## 판단 기준

| 결과 | 조건 |
|------|------|
| ✅ PASS | API 응답에서 직접 확인 가능하고, 기준 충족 |
| ❌ FAIL | API 응답에서 직접 확인 가능하고, 기준 미충족 |
| ⚠️ MANUAL | API로 자동 확인 불가능한 항목 (체크리스트에 `auto: false`로 표시) |
| ⏭️ SKIP | 해당 엔진/구성에 적용되지 않는 항목 (사유 명시) |

## 출력 규칙

### 1) 상세 결과를 파일로 저장

경로: `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{engine-slug}.md`

- `{service_name}`은 오케스트레이터로부터 전달받은 값을 그대로 사용한다. 임의로 추측하거나 account_id 등 다른 값으로 대체하지 않는다.

파일 내용 — 각 리소스별로:

```
## {리소스 식별자}
{엔진별 요약 정보 한 줄}

### Common Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|

### {엔진명} Checks
| Check ID | 항목 | Severity | 결과 | Auto | 상세 |
|----------|------|----------|------|------|------|
```

**Auto 컬럼 값:**
- `true` — 체크리스트 `auto: true` 항목 (AWS CLI/쿼리로 직접 판정)
- `false` — 체크리스트 `auto: false` 항목 (개발팀 pre-survey 기반 판정)

### 2) 메인 에이전트에 요약만 반환

```
## {엔진명} 검증 요약
- 리소스 수: N{단위}
- ✅ PASS: X | ❌ FAIL: Y | ⚠️ MANUAL: Z
- 🚨 Critical FAIL: N건
- 상세 리포트: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{engine-slug}.md

### Critical FAIL 목록
| 리소스 | Check ID | 항목 | 상세 |
|--------|----------|------|------|
```

Critical FAIL이 없으면 "Critical FAIL 목록" 섹션 생략.

### 3) 엔진별 리포트 파일 마지막에 로그 섹션 추가

상세 결과 파일의 맨 끝에 다음 섹션을 추가합니다:

```markdown
---

## 📋 실행 로그

### 오케스트레이터 입력값
| 항목 | 값 |
|------|----|
| service_name | {service_name} |
| region | {region} |
| engine | {engine} |
| 전달받은 리소스 목록 | {리소스 ID 목록 (쉼표 구분)} |
| 전달받은 리소스 수 | {N}개 |
| 실행 일시 | {YYYY-MM-DD HH:MM:SS} |

### AWS CLI 호출 내역
| # | timestamp | 명령어 | 목적 | 응답 요약 |
|---|-----------|--------|------|----------|
| 1 | {timestamp} | {AWS CLI 명령어 전체} | {PURPOSE} | {RESPONSE_SUMMARY} |
| 2 | ... | ... | ... | ... |
```
