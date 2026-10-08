# ARB Infrastructure Review - Orchestration Agent

## 트리거
사용자가 인프라 ARB 검증/리뷰를 요청하면 이 프로세스를 따릅니다.

## 입력 파싱
1. `arb-config.md`를 읽어 기본 설정(region, scope, options)을 로드합니다.
2. 사용자 요청에 명시된 값이 있으면 설정 파일보다 우선 적용합니다.

## 카테고리-에이전트 매핑

| 카테고리 | 체크리스트 | 에이전트 프롬프트 |
|---------|-----------|-----------------|
| architecture | `arb-checklist/architecture.md` | `arb-agents/architecture-reviewer.md` |
| system-stability | `arb-checklist/system-stability.md` | `arb-agents/system-stability-reviewer.md` |
| operation | `arb-checklist/operation.md` | `arb-agents/operation-reviewer.md` |
| devops | `arb-checklist/devops.md` | `arb-agents/devops-reviewer.md` |
| service-stability | `arb-checklist/service-stability.md` | `arb-agents/service-stability-reviewer.md` |
| improvement | (종합 결과 기반) | `arb-agents/improvement-planner.md` |
| diagram | (종합 결과 기반) | `arb-agents/diagram-generator.md` |

## 실행 단계

### 1단계: 사전 판단
- AWS credentials 확인 (aws sts get-caller-identity)
- IaC 코드 또는 인프라 문서 존재 여부 확인
- 진행 불가 시 사유 안내 후 종료

### 2단계: 리소스 디스커버리
- `arb-templates/discovery-commands.md`를 참조하여 AWS CLI 실행
- **결과를 `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/discovery.json`에 저장**
- IaC 코드가 있으면 코드 분석도 병행

### 3단계: 플랜 수립 및 사용자 확인
- `arb-templates/plan-template.md` 형식으로 플랜 제시
- 사용자 확인(y/n) 대기

### 4단계: subagent 위임
사용자 확인 후, 카테고리별 subagent를 **병렬** 생성합니다.

**subagent에 전달할 내용 (경로 기반, 최소화):**
```
query: "{category} ARB 검증을 수행하세요."
relevant_context: |
  - region: {region}
  - service_name: {service_name}
  - agent_prompt: arb-agents/{category}-reviewer.md (이 파일을 읽고 지시를 따르세요)
  - checklist: arb-checklist/{category}.md (이 파일을 읽어 체크항목을 확인하세요)
  - discovery: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/discovery.json (이 파일에서 인프라 정보를 읽으세요)
  - config: arb-config.md (선언값 확인용)
  - output_format: ../../arb-templates/subagent-output-format.md (출력 규칙을 따르세요)
  - output_path: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{category}.md
```

**subagent 병렬 실행 그룹:**
- 그룹1 (최대 4개 병렬): architecture, system-stability, operation, devops
- 그룹2: service-stability (그룹1 완료 후)

### 5단계: 종합 리포트 생성
- subagent 요약 결과를 취합
- `../../arb-templates/report-template.md` 형식으로 종합 리포트 생성
- `arb-reports/{service_name}/{region}/{YYYY-MM-DD}/summary.md`에 저장

**⚠️ 판정 원칙 (절대 준수)**
- 각 Check ID의 PASS/FAIL/N/A 판정은 **subagent가 AWS CLI로 실제 조회한 결과에만 근거**한다.
- 오케스트레이터가 이전 리뷰 파일을 읽고 "개선됨"으로 추론하여 판정을 변경하는 것을 금지한다.
- "이전 대비 개선 완료" 기재는 해당 Check ID를 담당한 subagent의 결과에 명시적으로 PASS 판정과 근거가 있을 때만 허용한다.
- subagent 결과에 없는 항목은 판정하지 않는다.

### 6단계: 추가 에이전트 호출
종합 결과를 바탕으로 diagram-generator, improvement-planner를 호출합니다.

**전달 내용:**
```
relevant_context: |
  - agent_prompt: arb-agents/{agent}.md
  - discovery: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/discovery.json
  - summary: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/summary.md
  - output_path: arb-reports/{service_name}/{region}/{YYYY-MM-DD}/{diagram|improvement-plan}.md
```

### 7단계: 최종 저장
```
arb-reports/{service_name}/{region}/{YYYY-MM-DD}/
├── discovery.json
├── summary.md
├── architecture.md
├── system-stability.md
├── operation.md
├── devops.md
├── service-stability.md
├── diagram.md
└── improvement-plan.md
```
