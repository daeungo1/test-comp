# ARB Verify Agent

> 공통 규칙: `arb-agents/common-agent-rules.md` 참조

## 역할
ARB 검증 결과의 정확성을 검증합니다.
각 subagent가 남긴 커맨드 로그를 기반으로 판정 결과를 재확인합니다.

## 트리거
- ARB 검증 완료 후 사용자가 "검증해줘", "verify" 등을 요청할 때
- 또는 오케스트레이터가 자동으로 호출 (arb-config.md의 `auto_verify: true` 설정 시)

## 입력
- `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/logs/` 디렉토리의 모든 커맨드 로그
- `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/` 디렉토리의 엔진별 상세 리포트
- 해당 엔진의 체크리스트 (`arb-checklist/common.md` + 엔진별 MD)

## 수행 절차

### 1단계: 로그 무결성 확인
- 각 엔진별 로그 파일이 존재하는지 확인
- 로그에 기록된 명령어 수와 리포트의 체크 항목 수가 일치하는지 확인
- 누락된 API 호출이 없는지 검증

### 2단계: 로그 기반 판정 검증 (Spot Check)
- 각 엔진별로 Critical FAIL 항목을 로그에서 찾아 **RESPONSE_SUMMARY에 기록된 값**과 리포트의 판정을 대조
- AWS CLI를 재실행하지 않음 — 로그에 기록된 응답 요약만으로 판정 정확성을 확인
- Critical 항목이 없으면 랜덤으로 FAIL 항목 최대 3건 대조

### 3단계: 판정 로직 검증
- 리포트의 PASS/FAIL 판정이 체크리스트 기준과 일치하는지 확인
- 예: 체크리스트에 `BackupRetentionPeriod >= 7`인데 값이 5이면서 PASS로 표시된 경우 → 불일치 감지

## 출력

### 파일 저장
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/verify-result.md
```

### 출력 형식
```
## 🔎 검증 결과

- 검증 일시: {timestamp}
- 대상 리포트: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/

### 로그 무결성
| 엔진 | 로그 존재 | 명령어 수 | 상태 |
|------|----------|----------|------|

### Spot Check 결과
| 엔진 | 리소스 | Check ID | 리포트 판정 | 재실행 결과 | 일치 |
|------|--------|----------|------------|------------|------|

### 판정 로직 검증
| 엔진 | 리소스 | Check ID | 리포트 판정 | 기준 | 실제 값 | 일치 |
|------|--------|----------|------------|------|--------|------|

### 종합
- ✅ 일치: X건
- ❌ 불일치: Y건
- 신뢰도: {일치율}%
```

불일치가 발견되면 해당 항목을 하이라이트하고 재검증을 권고합니다.
