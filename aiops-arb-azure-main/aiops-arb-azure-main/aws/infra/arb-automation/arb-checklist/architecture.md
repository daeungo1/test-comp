# Architecture ARB Checklist

## 1.1 Multi Region 아키텍쳐 구성

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-001 | Multi Region 아키텍쳐가 필요한 서비스인가? | major |
| ARCH-002 | Multi Region 아키텍쳐가 필요한 수준의 사용자가 예상되는 서비스인가? | major |
| ARCH-003 | Multi Region 아키텍쳐 설계(구현)를 어떻게 할 것인가? | major |
| ARCH-004 | 고성능 Routing 기능을 사용 하였는가? | major |
| ARCH-005 | Multi Region 데이터 동기화를 고려 하였는가? | critical |
| ARCH-006 | IaC로 설계하여 최소 시간에 생성(복구)할 수 있는가? | major |

## 1.2 인스턴스 Type

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-007 | 서비스 성격에 적합한 인스턴스 Type을 선택 하였는가? | major |
| ARCH-008 | 서비스 성격에 적합한 스토리지 Type을 선택 하였는가? | major |
| ARCH-009 | 인스턴스/스토리지 성능 측정(평가)을 진행 하였는가? | minor |
| ARCH-010 | 인스턴스/스토리지 모니터링을 구축 하였는가? | major |

## 1.3 Multi AZ 인스턴스 구성

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-011 | Multi AZ 기반으로 HA 구성이 되어 있는가? | critical |

## 1.4 VPC

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-012 | Public Cloud 환경에서 VPC를 구성하였는가? | critical |
| ARCH-013 | VPC에서 Public/Private Subnet을 기능별로 분리하여 네트워크를 구성하였는가? | critical |

## 1.5 Auto Scaling 구성

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-014 | 서비스 배포를 Auto Scaling 기반으로 구성하였는가? | critical |
| ARCH-015 | 적절한 Auto Scaling Policy가 적용 되었는가? | major |

## 1.6 Capacity Plan

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-016 | 서비스 사용자수에 맞추어 Architecture가 설계되어 있는가? | major |
| ARCH-017 | 서비스 생애주기/중요이벤트에 맞추어 서버 Capacity Plan이 산정되어 있는가? | major |

## 1.7 Immutable Infrastructure

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-018 | 서버관리자가 운영중인 서버에 접근할 필요가 없도록 구성하였는가? | major |
| ARCH-019 | Machine Image / container image를 이용하여 배포를 수행하는가? | major |
| ARCH-020 | 중앙 집중된 Logging, Monitoring 시스템을 활용하는가? | major |

## 1.8 Micro Service Architecture

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-021 | MSA 적용이 필요/적합한 서비스인가? | minor |
| ARCH-022 | 각 마이크로 서비스의 통신 내역을 추적하는 방법 또는 도구가 존재하는가? | major |
| ARCH-023 | 일부 마이크로 서비스의 장애에도 전체 서비스는 유지할 수 있도록 설계가 되어 있는가? | critical |
| ARCH-024 | 서비스 디스커버리가 적용되어 있는가? | major |
| ARCH-025 | 각 api로 routing할 수 있는 적절한 component를 구성하였는가? | major |
| ARCH-026 | 적절한 오케스트레이션 툴이 적용되었는가? | major |

## 1.9 HA아키텍쳐

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-027 | HA 구성 시 Multi AZ가 고려되었는가? | critical |
| ARCH-028 | SPOF(Single Point of Failure)가 없는가? | critical |
| ARCH-029 | 트래픽 급증에 대비한 인프라가 설정되어 있는가? | critical |

**ARCH-029 판정 기준:**
- ASG가 존재하고 AWS Scaling Policy(Target Tracking / Step Scaling 등)가 설정된 경우 → ✅ PASS
- EKS 노드그룹 ASG에 `k8s.io/cluster-autoscaler/enabled=true` 태그가 있고 **EKS addon에 karpenter 또는 cluster-autoscaler가 실제 등록**된 경우 → ✅ PASS
- EKS 노드그룹 ASG에 CA 태그(`k8s.io/cluster-autoscaler/enabled=true`)만 존재하고 **EKS addon에 autoscaler가 미등록**된 경우 → ❌ FAIL (태그만으로는 실제 동작 보장 불가)
- ASG 자체가 존재하지 않으면 → ⚠️ N/A

## 1.10 DR아키텍쳐

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-030 | RTO / RPO가 적절히 수립되었는가? | critical |
| ARCH-031 | DR 전략 수립이 되었는가? | critical |

## 1.11 Kubernetes

| Check ID | 항목 | Severity |
|----------|------|----------|
| ARCH-032 | Kubernetes cluster를 서비스 VPC 내 Multi-cluster 형태로 구성하였는가? | major |
| ARCH-033 | EKS cluster의 scaling policy는 Karpenter를 활용하여 구축하였는가? | major |
| ARCH-034 | 특정한 패턴을 갖는 Spike traffic은 KEDA Scaler를 활용하여 구축하였는가? | minor |
