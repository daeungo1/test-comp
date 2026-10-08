# Subagent 출력 규칙

## 핵심 원칙
- 상세 결과는 **파일로 저장**
- 메인 에이전트에게는 **최대 20줄 이내 요약만 반환**
- PASS 항목은 파일에만 기록, 반환하지 않음

## 1) 상세 결과 파일 저장 경로
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{category}.md
```

## 2) 메인 에이전트 반환 형식 (최대 20줄)
```
## {category} 검증 요약
- 체크항목: N개
- ✅ PASS: X | ❌ FAIL: Y | ⚠️ N/A: Z
- 🚨 Critical FAIL: N건
- 상세 리포트: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{category}.md

### Critical/Major FAIL 목록
| No | 항목 | Severity | 상세 |
|----|------|----------|------|
```

## 3) 금지사항
- PASS 항목 나열 금지
- 상세 설명을 반환에 포함 금지 (파일에만 기록)
- 20줄 초과 금지
