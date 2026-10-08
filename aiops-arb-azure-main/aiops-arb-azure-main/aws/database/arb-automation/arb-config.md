# ARB Review Configuration

## Service Name
- 

## Target Region
- 

## Target Engines
 - rds mysql
 - rds postgres
 - aurora mysql
 - aurora postgres
 - dynamodb
 - elasticache

## Filters
특정 리소스만 검증하려면 아래에 이름을 나열합니다. 비어있으면 전체 스캔.

### RDS MySQL Instances
 - 

### RDS PostgreSQL Instances
 - 

### Aurora MySQL Clusters
 - 

### Aurora PostgreSQL Clusters
 - 

### DynamoDB Tables
 - 

### ElastiCache Clusters
 - 

## DB Bastion
DB 접속용 Bastion(Jumphost) 서버 정보. instance-id 또는 tag로 지정합니다.

### By Instance ID
- 

### By Tag
- Key: Name
- Value: 

## Pre-Survey
- path: database/arb-automation/pre-survey/
- 엔진별 사전 조사 파일을 아래에 명시합니다. 명시된 파일이 있으면 우선 사용하고, 없으면 `{path}/{engine}*.md` 패턴으로 자동 탐색합니다.
- 탐색 결과가 2개 이상이면 사용자에게 선택을 요청합니다.

### DynamoDB
- file:

### RDS MySQL
- file:

### RDS PostgreSQL
- file:

### Aurora MySQL
- file: aurora-mysql-survey-mock.md

### Aurora PostgreSQL
- file:

### ElastiCache
- file:


 - skip_non_production: false
 - fail_on_severity: critical
 - output_format: markdown
 - auto_verify: false
