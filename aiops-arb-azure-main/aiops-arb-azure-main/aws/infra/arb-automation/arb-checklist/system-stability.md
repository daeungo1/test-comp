# System Stability ARB Checklist

## 2.1 성능,안정성 테스트(Aging)

| Check ID | 항목 | Severity |
|----------|------|----------|
| SYS-001 | API 기능 검증 테스트에서 PASS 되었는가? | critical |
| SYS-002 | 성능검증 테스트에서 PASS 되었는가? | critical |

## 2.2 고가용성(HA) 테스트

| Check ID | 항목 | Severity |
|----------|------|----------|
| SYS-003 | HA 테스트를 수행하였는가? | critical |

## 2.3 장애복구(DR) 테스트

| Check ID | 항목 | Severity |
|----------|------|----------|
| SYS-004 | DR 시나리오에 따라 전환 테스트가 적절히 수행되었는가? | critical |
| SYS-005 | 테스트 시 RTO / RPO가 복구 목표 시간에 부합하는가? | critical |
| SYS-006 | 장애복구의 훈련을 위한 모의장애 훈련 계획이 수립되었는가? | major |
