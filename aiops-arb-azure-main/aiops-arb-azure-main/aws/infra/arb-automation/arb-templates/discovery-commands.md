# 리소스 디스커버리 명령어

## VPC/네트워크
```bash
aws ec2 describe-vpcs --region {region}
aws ec2 describe-subnets --region {region}
```

## 컴퓨팅
```bash
aws ec2 describe-instances --region {region}
aws autoscaling describe-auto-scaling-groups --region {region}
```

## EKS
```bash
aws eks list-clusters --region {region}
aws eks describe-cluster --name {cluster} --region {region}
```

## 로드밸런서
```bash
aws elbv2 describe-load-balancers --region {region}
```

## 모니터링
```bash
aws cloudwatch describe-alarms --region {region}
```

## IaC 상태
```bash
terraform state list
```
