# Architecture 검증 명령어

## 1단계: AWS 계정 내 리소스 확인
```bash
# Multi-AZ 확인
aws ec2 describe-subnets --filters Name=vpc-id,Values={vpc_id} --region {region}

# Auto Scaling 확인
aws autoscaling describe-auto-scaling-groups --region {region}
aws autoscaling describe-policies --auto-scaling-group-name {asg} --region {region}

# EKS 클러스터 상세
aws eks describe-cluster --name {cluster} --region {region}
aws eks list-nodegroups --cluster-name {cluster} --region {region}

# VPC 구성
aws ec2 describe-vpcs --region {region}
aws ec2 describe-route-tables --filters Name=vpc-id,Values={vpc_id} --region {region}

# Global Accelerator / Route53 (Multi Region)
aws globalaccelerator list-accelerators --region us-west-2
aws route53 list-hosted-zones

# EC2 인스턴스 타입
aws ec2 describe-instances --region {region}
```

## 2단계: EKS 클러스터 내 확인
```bash
kubectl get provisioners -A 2>/dev/null || kubectl get nodepools -A 2>/dev/null
kubectl get scaledobjects -A 2>/dev/null
kubectl get virtualservices -A 2>/dev/null
kubectl get services -A
kubectl get ingress -A
```
