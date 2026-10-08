# Service Stability ARB Checklist

## 5.1 개발자 커뮤니케이션

| Check ID | 항목 | Severity |
|----------|------|----------|
| SVC-001 | 단말, 서버 개발팀 간 정기적 서비스 변경에 대한 계획 및 결과 공유를 진행하는가? | major |
| SVC-002 | RM 담당자 지정 및 R&R 정의하고 배포 전 Deploy Review를 진행 하는가? | major |
| SVC-003 | 타 서비스와 연동, 영향도 분석을 정의하였는가? | major |
| SVC-004 | 예상되는 장애 시나리오 및 장애 처리 방안을 정의 하였는가? | critical |

## 5.2 검증

| Check ID | 항목 | Severity |
|----------|------|----------|
| SVC-005 | 앱 에이징 테스트를 수행 하였는가? | major |

## 5.3 배포

| Check ID | 항목 | Severity |
|----------|------|----------|
| SVC-006 | 변경 시 위험 분산을 위한 배포 프로세스를 적용 하였는가? (Blue/Green, Canary 등) | critical |
| SVC-007 | 점진 배포 적용 시 변경분 모니터링 방안이 확보되었는가? | major |
