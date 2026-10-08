# Service Stability 검증 명령어

## 1단계: AWS 계정 내 리소스 확인
```bash
aws deploy list-applications --region {region}
aws deploy get-deployment-group --application-name {app} --deployment-group-name {group} --region {region}
aws elbv2 describe-rules --listener-arn {arn} --region {region}
aws cloudwatch describe-alarms --region {region}
```

## 2단계: EKS 클러스터 내 확인
```bash
kubectl get rollouts -A -o jsonpath='{.items[*].spec.strategy}'
kubectl get deployments -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.strategy.type}{"\n"}{end}'
kubectl get analysistemplates -A
```
