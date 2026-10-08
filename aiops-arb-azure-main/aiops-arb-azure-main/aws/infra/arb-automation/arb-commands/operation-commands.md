# Operation 검증 명령어

## 1단계: AWS 계정 내 리소스 확인
```bash
aws cloudwatch describe-alarms --region {region}
aws cloudwatch list-dashboards --region {region}
aws sns list-topics --region {region}
aws sns list-subscriptions --region {region}
aws backup list-backup-plans --region {region}
aws backup list-backup-vaults --region {region}
aws ssm describe-maintenance-windows --region {region}
aws cloudtrail describe-trails --region {region}
```

## 2단계: EKS 클러스터 내 확인
```bash
kubectl get ns monitoring 2>/dev/null
kubectl get pods -n monitoring 2>/dev/null
kubectl get alertmanagerconfigs -A 2>/dev/null
```
