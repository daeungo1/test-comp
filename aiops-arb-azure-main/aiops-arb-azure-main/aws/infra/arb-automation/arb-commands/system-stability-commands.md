# System Stability 검증 명령어

## 1단계: AWS 계정 내 리소스 확인
```bash
aws cloudwatch describe-alarms --region {region}
aws route53 list-health-checks
aws backup list-backup-plans --region {region}
aws backup list-backup-selections --backup-plan-id {id} --region {region}
aws rds describe-db-clusters --region {region}
aws rds describe-db-instances --region {region}
aws rds describe-events --source-type db-instance --event-categories failover --region {region}
```

## 2단계: EKS 클러스터 내 확인
```bash
kubectl get pdb -A
kubectl get hpa -A
```
