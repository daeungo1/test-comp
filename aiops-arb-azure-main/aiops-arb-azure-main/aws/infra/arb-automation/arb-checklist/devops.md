# DevOps ARB Checklist

## 4.1 Infrastructure as Code

| Check ID | 항목 | Severity |
|----------|------|----------|
| DEV-001 | Cloud Infra.를 코드로 관리하는가? (Terraform, CloudFormation 등) | critical |
| DEV-002 | Cloud Infra. 코드를 VCS 연동하는가? (GitHub) | critical |
| DEV-003 | Cloud Infra.의 실행 권한을 관리하는가? | major |
| DEV-004 | 생성한 Infra의 상태를 자동으로 관리하는가? (Terraform state file) | major |

## 4.2 CI/CD pipeline

| Check ID | 항목 | Severity |
|----------|------|----------|
| DEV-005 | 자동화된 빌드 시스템이 구축되어 있는가? | critical |
| DEV-006 | 자동화된 검증 절차가 있는가? (자주검증, 기능검증, 성능검증) | major |
| DEV-007 | 검증/배포 실패시 자동 알림이 지원되는가? | major |
| DEV-008 | 이미지 기반의 어플리케이션 배포 환경이 구축되었는가? | major |
| DEV-009 | 이미지 생성 과정이 자동화 되어 있는가? | major |
| DEV-010 | 이미지 보관 정책이 있는가? | minor |
| DEV-011 | 배포 파이프라인이 구축되었는가? (ArgoCD, Jenkins 등) | critical |
| DEV-012 | 빠른 복구 (Rollback)가 지원되는가? | critical |
| DEV-013 | 배포 후 어플리케이션 동작을 진단하는 방법이 있는가? | major |
