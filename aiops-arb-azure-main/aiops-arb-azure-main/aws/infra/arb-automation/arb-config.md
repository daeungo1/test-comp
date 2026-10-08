# ARB Review Configuration

## Target Regions
- ap-northeast-2

## Scope
검증 대상 카테고리. 비어있으면 전체 수행.
- architecture
- system-stability
- operation
- devops
- service-stability

## Input Sources
인프라 정보를 수집할 소스를 지정합니다.

### AWS Account
- profile: default
- regions: ap-northeast-2

### IaC Repository
- path: 
- type: terraform

### CI/CD 도구 선언
자동 탐지가 불가능한 외부 CI/CD 도구를 여기에 선언합니다.

- build_tool: none
- build_url: 
- deploy_tool: none
- deploy_url: 
- image_registry: none
- rollback_supported: false

### Monitoring
- tool: none
- endpoint: 

### 서비스 안정성 선언
자동 탐지가 불가능한 프로세스/문서 항목을 여기에 선언합니다.

- deploy_strategy: none
- deploy_monitoring: false
- change_sharing_process: false
- release_manager_assigned: false
- dependency_analysis_doc: false
- failure_scenario_doc: false
- aging_test_done: false

## Options
- fail_on_severity: critical
- output_format: markdown
- generate_diagram: true
- generate_improvement_plan: true

## 아키텍처 선언
자동 탐지가 불가능한 설계/문서 항목을 여기에 선언합니다.

- multi_region_required: false
- multi_region_user_scale: 
- multi_region_designed: false
- instance_type_rationale: false
- storage_type_rationale: false
- performance_tested: false
- capacity_plan: false
- lifecycle_capacity_plan: false
- msa_required: false

## 시스템 안정성 선언

- api_functional_test_done: false
- performance_test_done: false
- rto_rpo_defined: false
- rto_value: 
- rpo_value: 
- disaster_drill_planned: false

## 운영 적합성 선언

- incident_grade_defined: false
- escalation_list_defined: false
- cs_process_ready: false
- change_process_established: false
- data_extraction_process: false
- ops_tool: none
- realtime_comm_channel: false
- ops_documents_ready: false
- admin_implemented: false
