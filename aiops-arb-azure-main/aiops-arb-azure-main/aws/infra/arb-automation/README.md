# Infrastructure ARB Automation

인프라 ARB(Architecture Review Board) 리뷰를 자동화하는 Kiro Agent 시스템입니다.

## 구조

```
arb-automation/
├── .kiro/steering/
│   └── arb-review.md              # 오케스트레이션 에이전트 (핵심 흐름만)
├── arb-config.md                  # 설정 파일
├── arb-checklist/                 # 카테고리별 체크리스트
│   ├── architecture.md            # 1. 아키텍처 (34항목)
│   ├── system-stability.md        # 2. 시스템 안정성 (6항목)
│   ├── operation.md               # 3. 운영 적합성 (15항목)
│   ├── devops.md                  # 4. DevOps 자동화 (13항목)
│   └── service-stability.md       # 5. 서비스 안정성 (7항목)
├── arb-agents/                    # 카테고리별 리뷰어 에이전트 (행동 규칙만)
│   ├── architecture-reviewer.md
│   ├── system-stability-reviewer.md
│   ├── operation-reviewer.md
│   ├── devops-reviewer.md
│   ├── service-stability-reviewer.md
│   ├── diagram-generator.md
│   └── improvement-planner.md
├── arb-commands/                  # 검증용 AWS CLI/kubectl 명령어 (필요 시 참조)
│   ├── architecture-commands.md
│   ├── system-stability-commands.md
│   ├── operation-commands.md
│   ├── service-stability-commands.md
│   └── devops-commands.md
├── ../../arb-templates/                 # 출력 형식/템플릿 (필요 시 참조)
│   ├── discovery-commands.md
│   ├── plan-template.md
│   ├── report-template.md
│   └── subagent-output-format.md
└── arb-reports/                   # 결과 리포트 (자동 생성)
    └── {region}/{YYYY-MM-DD}/
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

## Context 효율화 설계

| 원칙 | 적용 |
|------|------|
| Steering 최소화 | 핵심 흐름만 기술, 템플릿/명령어는 외부 참조 |
| 경로 기반 위임 | subagent에 파일 내용 대신 경로만 전달 |
| Lazy Loading | 명령어/템플릿은 해당 단계에서만 읽기 |
| 출력 제한 | subagent → orchestrator 반환은 20줄 이내 |
| 파일 기반 공유 | discovery.json으로 인프라 정보 공유 (context 복사 방지) |

## 사용법

```
# 전체 ARB 리뷰 실행
"인프라 ARB 리뷰 진행해줘. 리전은 ap-northeast-2"

# 특정 카테고리만
"아키텍처 카테고리만 ARB 검증해줘"

# 특정 서비스
"payment 서비스 인프라 ARB 리뷰 진행해줘"
```

## 판정 기준

- **PASS**: 모든 카테고리에서 Critical FAIL이 0건
- **FAIL**: Critical FAIL이 1건이라도 존재
