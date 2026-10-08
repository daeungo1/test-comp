# 종합 리포트 구조

```markdown
# 인프라 ARB 리뷰 리포트

## 전체 요약
- 서비스: {service_name}
- 리전: {region}
- 검증일: {YYYY-MM-DD}
- **최종 판정: ✅ PASS / ❌ FAIL**
- 총 체크항목: N개 (PASS: X | FAIL: Y | N/A: Z)
- Critical FAIL: N건

## 카테고리별 결과 요약

| No | 카테고리 | PASS | FAIL | N/A | Critical | 판정 |
|----|---------|------|------|-----|----------|------|

## FAIL/N/A 항목 상세

### 🚨 Critical FAIL (즉시 조치 필요)
| 카테고리 | 항목 | 현재 상태 | 권고사항 |
|---------|------|----------|---------|

### ⚠️ Major FAIL
| 카테고리 | 항목 | 현재 상태 | 권고사항 |
|---------|------|----------|---------|

### ℹ️ Minor FAIL / N/A
| 카테고리 | 항목 | 사유 |
|---------|------|------|

## 아키텍처 다이어그램
(diagram-generator agent 결과 삽입)

## 개선 계획
(improvement-planner agent 결과 삽입)
```

## 판정 기준
- **PASS**: 모든 카테고리에서 Critical FAIL이 0건
- **FAIL**: Critical FAIL이 1건이라도 존재
