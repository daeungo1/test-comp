# Architecture ARB Review Report

- **Service**: aiops
- **Region**: ap-northeast-2
- **Date**: 2026-05-06
- **Environment**: dev

---

## 검증 결과 요약

| 구분 | 수량 |
|------|------|
| 총 체크항목 | 34 |
| ✅ PASS | 7 |
| ❌ FAIL | 18 |
| ⚠️ N/A | 9 |

### Critical FAIL: 8건

---

## 1.1 Multi Region 아키텍쳐 구성

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-001 | Multi Region 아키텍쳐가 필요한 서비스인가? | major | ⚠️ N/A | config 미선언, 사용자 확인 필요 |
| ARCH-002 | Multi Region 아키텍쳐가 필요한 수준의 사용자가 예상되는 서비스인가? | major | ⚠️ N/A | config 미선언, 사용자 확인 필요 |
| ARCH-003 | Multi Region 아키텍쳐 설계(구현)를 어떻게 할 것인가? | major | ⚠️ N/A | config 미선언, 사용자 확인 필요 |
| ARCH-004 | 고성능 Routing 기능을 사용 하였는가? | major | ❌ FAIL | Route53 Hosted Zone 없음, Global Accelerator 없음 |
| ARCH-005 | Multi Region 데이터 동기화를 고려 하였는가? | critical | ⚠️ N/A | 단일 리전 운영 중, Multi Region 필요성 미확인 상태 |
| ARCH-006 | IaC로 설계하여 최소 시간에 생성(복구)할 수 있는가? | major | ✅ PASS | Terraform 사용 확인 (terraform-state S3 버킷 존재, 리소스 태그 Terraform=true) |

## 1.2 인스턴스 Type

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-007 | 서비스 성격에 적합한 인스턴스 Type을 선택 하였는가? | major | ⚠️ N/A | config 미선언 (bastion: t3.micro, kiro: m8g.xlarge 확인됨) |
| ARCH-008 | 서비스 성격에 적합한 스토리지 Type을 선택 하였는가? | major | ⚠️ N/A | config 미선언, 스토리지 선정 근거 미확인 |
| ARCH-009 | 인스턴스/스토리지 성능 측정(평가)을 진행 하였는가? | minor | ⚠️ N/A | config 미선언, 성능 테스트 여부 미확인 |
| ARCH-010 | 인스턴스/스토리지 모니터링을 구축 하였는가? | major | ❌ FAIL | CloudWatch Alarms 0건, 인스턴스 모니터링 미구축 |

## 1.3 Multi AZ 인스턴스 구성

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-011 | Multi AZ 기반으로 HA 구성이 되어 있는가? | critical | ❌ FAIL | Subnet은 3 AZ에 분포하나, EC2 인스턴스 2대 모두 ap-northeast-2a에만 위치. ASG/EKS 없어 HA 미구성 |

## 1.4 VPC

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-012 | Public Cloud 환경에서 VPC를 구성하였는가? | critical | ✅ PASS | VPC 존재 (vpc-0eeeef2e55b43928f, CIDR: 10.10.0.0/16) |
| ARCH-013 | VPC에서 Public/Private Subnet을 기능별로 분리하여 네트워크를 구성하였는가? | critical | ✅ PASS | Public(3)/Private(3)/DB(3) 서브넷 분리 완료. Public에 IGW, Private에 NAT, DB는 isolated |

## 1.5 Auto Scaling 구성

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-014 | 서비스 배포를 Auto Scaling 기반으로 구성하였는가? | critical | ❌ FAIL | Auto Scaling Group 0개. EC2 인스턴스 수동 관리 |
| ARCH-015 | 적절한 Auto Scaling Policy가 적용 되었는가? | major | ❌ FAIL | ASG 미존재로 Scaling Policy 없음 |

## 1.6 Capacity Plan

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-016 | 서비스 사용자수에 맞추어 Architecture가 설계되어 있는가? | major | ⚠️ N/A | config 미선언, Capacity Plan 미확인 |
| ARCH-017 | 서비스 생애주기/중요이벤트에 맞추어 서버 Capacity Plan이 산정되어 있는가? | major | ⚠️ N/A | config 미선언 |

## 1.7 Immutable Infrastructure

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-018 | 서버관리자가 운영중인 서버에 접근할 필요가 없도록 구성하였는가? | major | ❌ FAIL | SSM Session Manager 미등록 (managed instances 0건), EC2 key pair(ec2-key) 사용 중, bastion 서버 존재 → SSH 접근 의존 구조 |
| ARCH-019 | Machine Image / container image를 이용하여 배포를 수행하는가? | major | ❌ FAIL | ECR 리포지토리 0개, EKS/ECS 미사용, 컨테이너 기반 배포 미확인 |
| ARCH-020 | 중앙 집중된 Logging, Monitoring 시스템을 활용하는가? | major | ❌ FAIL | CloudWatch Log Group은 Control Tower 기본 설정만 존재. 서비스 전용 로그 그룹 없음. CloudWatch Alarms 0건 |

## 1.8 Micro Service Architecture

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-021 | MSA 적용이 필요/적합한 서비스인가? | minor | ⚠️ N/A | config 미선언, 서비스 규모/특성 미확인 |
| ARCH-022 | 각 마이크로 서비스의 통신 내역을 추적하는 방법 또는 도구가 존재하는가? | major | ❌ FAIL | X-Ray는 Default 규칙만 존재 (커스텀 설정 없음), 별도 tracing 도구 미확인 |
| ARCH-023 | 일부 마이크로 서비스의 장애에도 전체 서비스는 유지할 수 있도록 설계가 되어 있는가? | critical | ❌ FAIL | 단일 EC2 기반 구조, Circuit Breaker/서비스 격리 미확인, EKS/ECS 미사용 |
| ARCH-024 | 서비스 디스커버리가 적용되어 있는가? | major | ❌ FAIL | EKS/Cloud Map/Consul 미존재 |
| ARCH-025 | 각 api로 routing할 수 있는 적절한 component를 구성하였는가? | major | ❌ FAIL | ALB/NLB/API Gateway/Ingress Controller 없음 (Load Balancer 0개) |
| ARCH-026 | 적절한 오케스트레이션 툴이 적용되었는가? | major | ❌ FAIL | EKS/ECS 클러스터 없음 |

## 1.9 HA아키텍쳐

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-027 | HA 구성 시 Multi AZ가 고려되었는가? | critical | ❌ FAIL | EC2 인스턴스 모두 단일 AZ(ap-northeast-2a)에 위치. Multi-AZ HA 미구성 |
| ARCH-028 | SPOF(Single Point of Failure)가 없는가? | critical | ❌ FAIL | aiops-kiro-apne2-dev (m8g.xlarge) 단일 인스턴스가 SPOF. LB/ASG/복제 없음 |
| ARCH-029 | 트래픽 급증에 대비한 인프라가 설정되어 있는가? | critical | ❌ FAIL | ASG 없음, SQS/SNS 없음, Karpenter 없음. 트래픽 급증 대응 불가 |

## 1.10 DR아키텍쳐

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-030 | RTO / RPO가 적절히 수립되었는가? | critical | ❌ FAIL | Backup Plan 0건, RDS 없음, 별도 DR 인프라 미확인 |
| ARCH-031 | DR 전략 수립이 되었는가? | critical | ❌ FAIL | Multi-Region 미구성, Backup 미구성, DR 전략 부재 |

## 1.11 Kubernetes

| Check ID | 항목 | Severity | 결과 | 근거 |
|----------|------|----------|------|------|
| ARCH-032 | Kubernetes cluster를 서비스 VPC 내 Multi-cluster 형태로 구성하였는가? | major | ❌ FAIL | EKS 클러스터 0개 |
| ARCH-033 | EKS cluster의 scaling policy는 Karpenter를 활용하여 구축하였는가? | major | ❌ FAIL | EKS 미사용 |
| ARCH-034 | 특정한 패턴을 갖는 Spike traffic은 KEDA Scaler를 활용하여 구축하였는가? | minor | ❌ FAIL | EKS 미사용, KEDA 미적용 |

---

## 주요 발견사항

### Critical Issues (즉시 조치 필요)

1. **HA 미구성 (ARCH-011, 027, 028)**: 모든 EC2 인스턴스가 단일 AZ(ap-northeast-2a)에 위치하며, ASG/LB 없이 단일 인스턴스로 운영. SPOF 존재.
2. **Auto Scaling 부재 (ARCH-014, 029)**: ASG 미구성으로 트래픽 급증 시 대응 불가.
3. **장애 격리 불가 (ARCH-023)**: 단일 EC2 기반으로 서비스 격리/Circuit Breaker 미적용.
4. **DR 전략 부재 (ARCH-030, 031)**: Backup Plan, Multi-Region, DR 인프라 모두 미구성.

### Major Issues

1. 모니터링 미구축 (CloudWatch Alarms 0건)
2. SSH 기반 서버 접근 (Immutable Infrastructure 미달성)
3. 컨테이너/오케스트레이션 미사용
4. 로드밸런서/API Gateway 미구성
5. 중앙 로깅 시스템 미구축

### 긍정적 사항

1. VPC 네트워크 설계 우수 (Public/Private/DB 3-tier 분리, 3 AZ 서브넷)
2. Terraform 기반 IaC 관리
3. CloudTrail 활성화 (Multi-Region)

---

## 판정: ❌ FAIL

Critical FAIL 8건 존재로 Architecture ARB 기준 미달.
