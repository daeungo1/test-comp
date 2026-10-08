# Operation ARB Checklist

## 3.1 장애프로세스

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-001 | 장애등급 정의서가 정의되었는가? | critical |
| OPS-002 | 장애 에스컬레이션, 전파 명단이 적절하게 정의되어 있는가? | critical |

## 3.2 CS 프로세스

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-003 | CS 프로세스에 맞춰 고객지원 채널 셋업 및 고객지원 준비가 되어 있는가? | major |

## 3.3 시스템 변경 프로세스

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-004 | 시스템 변경 프로세스를 수립하고 준수하고 있는가? | major |
| OPS-005 | 데이터 추출 관련 프로세스를 인지하고 준수하고 있는가? | major |

## 3.4 모니터링

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-006 | 신규로 구성된 시스템에 대한 모니터링 환경은 구성되어 있는가? | critical |
| OPS-007 | 주요 모니터링 항목이 정의되고 임계값 초과 시 감지되고 있는가? | critical |
| OPS-008 | APM 필요성을 검토하였는가? | minor |

## 3.5 운영관리 Tool

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-009 | JIRA 등 티켓 기반의 운영 관리 Tool을 준비하여 사용하고 있는가? | major |
| OPS-010 | 실시간 서버 운영을 위한 소통 채널이 구축되어 있는가? | major |

## 3.6 백업/보관 방식 및 기본 정책

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-011 | 백업(Backup)과 보관(Archiving)을 구분하여 정책 수립하였는가? | critical |

**OPS-011 판정 기준:**
- AWS Backup Plan이 존재하고 RDS/EFS 등 핵심 리소스가 포함된 경우 → ✅ PASS
- AWS Backup Plan 없고, RDS 자동 백업 / EBS 스냅샷 등 개별 백업만 존재하는 경우 → ❌ FAIL (통합 정책 미수립) **severity: critical**
- AWS Backup 완전 미구성이고 개별 백업도 없는 경우 → ❌ FAIL **severity: critical**
- 인프라(RDS/EFS 등 백업 대상) 자체가 없는 경우 → ⚠️ N/A
| OPS-012 | 데이터 분류에 따른 백업/보관 정책을 수립하였는가? | major |
| OPS-013 | 인프라에 따른 기본 백업 방식을 지정하였는가? | major |

## 3.7 운영 산출물

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-014 | 운영 업무에 필요한 서비스 소개 및 시스템 정보에 대한 산출물이 준비되어 있는가? | major |

## 3.8 운영 Admin 구현

| Check ID | 항목 | Severity |
|----------|------|----------|
| OPS-015 | 운영자를 위한 Admin 기능이 적절하게 구현되어 있는가? | major |
