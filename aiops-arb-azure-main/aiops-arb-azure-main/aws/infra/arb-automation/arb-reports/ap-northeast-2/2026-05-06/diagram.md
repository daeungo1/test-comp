# 인프라 아키텍처 다이어그램

## 현재 아키텍처 다이어그램

```mermaid
graph TB
    subgraph Internet["🌐 Internet"]
        User["사용자"]
    end

    subgraph AWS["☁️ AWS ap-northeast-2 (Account: 260544022684)"]
        subgraph VPC["VPC: aiops-vpc-apne2-dev (10.10.0.0/16)"]
            IGW["Internet Gateway<br/>igw-03f062319b30b404c"]

            subgraph AZ_A["AZ: ap-northeast-2a"]
                subgraph PUB_A["Public Subnet (10.10.0.0/24)"]
                    BASTION["🖥️ Bastion<br/>t3.micro<br/>3.37.25.127"]
                    NAT_A["NAT Gateway<br/>nat-035494f9c75438bf9"]
                end
                subgraph PRI_A["Private Subnet (10.10.10.0/24)"]
                    KIRO["🖥️ aiops-kiro<br/>m8g.xlarge<br/>(단일 인스턴스 ⚠️)"]
                end
                subgraph DB_A["DB Subnet (10.10.20.0/24)"]
                    DB_A_EMPTY["(미사용)"]
                end
            end

            subgraph AZ_B["AZ: ap-northeast-2b"]
                subgraph PUB_B["Public Subnet (10.10.1.0/24)"]
                    NAT_B["NAT Gateway<br/>nat-057c3052f3f63bd9e"]
                end
                subgraph PRI_B["Private Subnet (10.10.11.0/24)"]
                    PRI_B_EMPTY["(미사용)"]
                end
                subgraph DB_B["DB Subnet (10.10.21.0/24)"]
                    DB_B_EMPTY["(미사용)"]
                end
            end

            subgraph AZ_C["AZ: ap-northeast-2c"]
                subgraph PUB_C["Public Subnet (10.10.2.0/24)"]
                    NAT_C["NAT Gateway<br/>nat-040ac43b0ef5e53a6"]
                end
                subgraph PRI_C["Private Subnet (10.10.12.0/24)"]
                    PRI_C_EMPTY["(미사용)"]
                end
                subgraph DB_C["DB Subnet (10.10.22.0/24)"]
                    DB_C_EMPTY["(미사용)"]
                end
            end
        end

        CT["CloudTrail<br/>(Multi-Region ✅)"]
    end

    User --> IGW
    IGW --> BASTION
    BASTION --> KIRO
    KIRO --> NAT_A
    NAT_A --> IGW
```

## 개선 후 아키텍처 다이어그램

```mermaid
graph TB
    subgraph Internet["🌐 Internet"]
        User["사용자"]
    end

    subgraph AWS["☁️ AWS ap-northeast-2"]
        subgraph VPC["VPC: aiops-vpc-apne2-dev (10.10.0.0/16)"]
            IGW["Internet Gateway"]
            ALB["Application Load Balancer<br/>(Multi-AZ)"]

            subgraph AZ_A["AZ: ap-northeast-2a"]
                subgraph PUB_A["Public Subnet (10.10.0.0/24)"]
                    BASTION_A["🖥️ Bastion"]
                    NAT_A["NAT Gateway"]
                end
                subgraph PRI_A["Private Subnet (10.10.10.0/24)"]
                    ASG_A["🖥️ App Instance<br/>(ASG Member)"]
                end
                subgraph DB_A["DB Subnet (10.10.20.0/24)"]
                    RDS_PRIMARY["🗄️ RDS Primary"]
                end
            end

            subgraph AZ_B["AZ: ap-northeast-2b"]
                subgraph PUB_B["Public Subnet (10.10.1.0/24)"]
                    NAT_B["NAT Gateway"]
                end
                subgraph PRI_B["Private Subnet (10.10.11.0/24)"]
                    ASG_B["🖥️ App Instance<br/>(ASG Member)"]
                end
                subgraph DB_B["DB Subnet (10.10.21.0/24)"]
                    RDS_STANDBY["🗄️ RDS Standby"]
                end
            end

            subgraph AZ_C["AZ: ap-northeast-2c"]
                subgraph PUB_C["Public Subnet (10.10.2.0/24)"]
                    NAT_C["NAT Gateway"]
                end
                subgraph PRI_C["Private Subnet (10.10.12.0/24)"]
                    ASG_C["🖥️ App Instance<br/>(ASG Member)"]
                end
                subgraph DB_C["DB Subnet (10.10.22.0/24)"]
                    DB_C_EMPTY["(DR 대기)"]
                end
            end
        end

        subgraph Monitoring["📊 모니터링/운영"]
            CW["CloudWatch<br/>Dashboard + Alarms"]
            SNS["SNS<br/>알림 채널"]
            BACKUP["AWS Backup<br/>자동 백업"]
        end

        subgraph CICD["🔄 CI/CD"]
            GHA["GitHub Actions<br/>(Build/Test)"]
            ARGOCD["ArgoCD / CodeDeploy<br/>(배포 + Rollback)"]
        end

        CT["CloudTrail<br/>(Multi-Region + Log Validation)"]

        subgraph DR["🔁 DR Region"]
            S3_DR["S3 Cross-Region<br/>Backup"]
        end
    end

    User --> IGW
    IGW --> ALB
    ALB --> ASG_A
    ALB --> ASG_B
    ALB --> ASG_C
    ASG_A --> NAT_A
    ASG_B --> NAT_B
    ASG_C --> NAT_C
    ASG_A --> RDS_PRIMARY
    ASG_B --> RDS_PRIMARY
    RDS_PRIMARY --> RDS_STANDBY
    CW --> SNS
    BACKUP --> S3_DR
    GHA --> ARGOCD
    ARGOCD --> ASG_A
    ARGOCD --> ASG_B
    ARGOCD --> ASG_C
```

## 주요 변경점

| 구분 | 현재 | 개선 후 | 관련 Check ID |
|------|------|---------|--------------|
| 고가용성 | 단일 AZ(2a) EC2 1대 | Multi-AZ ASG (최소 2대) | ARCH-011, ARCH-027, ARCH-028 |
| Auto Scaling | 없음 | ASG + Target Tracking Policy | ARCH-014, ARCH-029 |
| 로드밸런서 | 없음 | ALB (Multi-AZ) | ARCH-028 |
| 모니터링 | CloudWatch Alarm 0개 | Dashboard + CPU/Memory/Disk Alarm | OPS-006, OPS-007 |
| 알림 | SNS Topic 0개 | SNS + 에스컬레이션 정책 | OPS-002 |
| 백업 | Backup Plan 0개 | AWS Backup (일일 백업, 30일 보관) | OPS-011, ARCH-030 |
| DR | 없음 | Cross-Region S3 백업 + RTO/RPO 정의 | ARCH-031, SYS-004, SYS-005 |
| CI/CD | 없음 | GitHub Actions (CI) + ArgoCD/CodeDeploy (CD) | DEV-005, DEV-011, DEV-012 |
| 장애 격리 | 없음 | Circuit Breaker 패턴 적용 | ARCH-023 |
| DB | 없음 | RDS Multi-AZ (Primary + Standby) | ARCH-011 |
| CloudTrail | Log Validation 미적용 | Log File Validation 활성화 | - |
