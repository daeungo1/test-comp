# DevOps 검증 명령어

## 1단계: AWS 계정 내 리소스 확인
```bash
aws codepipeline list-pipelines --region {region}
aws codebuild list-projects --region {region}
aws deploy list-applications --region {region}
aws ecr describe-repositories --region {region}
aws ecr get-lifecycle-policy --repository-name {repo} --region {region}
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --region {region}
aws s3 ls s3://{bucket}/terraform/
```

## 2단계: 소스코드/IaC 레포 기반 탐지
```bash
find {repo_path} -name "*.tf" -type f | head -5
find {repo_path} -name "backend.tf" -type f
ls {repo_path}/.git
find {repo_path} -path "*/.github/workflows/*.yml" -type f
find {repo_path} -name "Jenkinsfile" -type f
find {repo_path} -name "Dockerfile" -type f
find {repo_path} -name "Chart.yaml" -type f
find {repo_path} -name "kustomization.yaml" -type f
```

## 3단계: EKS 클러스터 내 확인
```bash
kubectl get ns argocd 2>/dev/null && kubectl get applications.argoproj.io -A
kubectl get ns flux-system 2>/dev/null && kubectl get gitrepositories -A
kubectl get rollouts -A 2>/dev/null
```
