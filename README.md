# test-comp: ARB 자동화 (AWS 버전)

AWS 환경을 대상으로 ARB(Architecture Review Board) 점검을 자동화하는 프로젝트입니다. Kiro CLI Agent가 Markdown 기반 체크리스트와 규칙에 따라 AWS 리소스를 점검하고 리포트를 생성합니다. Web UI와 Slack Bot으로 점검 실행, 이력 조회, 리포트 열람, RAG 채팅을 제공합니다.

## 폴더 구조

```text
aiops-arb-azure-main/aiops-arb-azure-main/aws/
├── infra/arb-automation/     # 인프라 ARB Agent (5개 카테고리, 75항목)
│   ├── .kiro/steering/       #   오케스트레이터 규칙
│   ├── arb-agents/           #   카테고리별 리뷰어 + 다이어그램/개선계획 Agent
│   ├── arb-checklist/        #   아키텍처/시스템안정성/운영/DevOps/서비스안정성
│   ├── arb-commands/         #   검증용 AWS CLI/kubectl 명령어
│   └── arb-reports/          #   점검 결과 샘플 (summary, improvement-plan 등)
├── database/arb-automation/  # DB ARB Agent (공통 + 엔진별, 214항목)
│   ├── .kiro/agents/         #   Kiro Agent 정의 (JSON)
│   ├── arb-agents/           #   RDS/Aurora MySQL·PG, DynamoDB, ElastiCache, Verify 리뷰어
│   ├── arb-checklist/        #   엔진별 체크리스트
│   └── pre-survey/           #   사전 설문 샘플
├── arb-templates/            # 리포트·subagent 출력 공통 템플릿
├── arb-reports/              # 프로젝트별 DB 점검 결과 + 명령 로그
├── service-guide/            # 서비스 팀 사전 준비 가이드 (CloudFormation, 설문 스크립트, HTML)
├── webfront/                 # Web UI 소스 (Git 관리용)
│   ├── backend/              #   FastAPI, Slack Bot, Knowledge 인덱스 빌더
│   ├── frontend/             #   React + Vite SPA
│   └── nginx.conf, *.service #   배포 설정 (nginx, systemd)
├── web/                      # Web UI 실행 환경 사본 (빌드 결과, SQLite arb.db)
├── docs/                     # 발표 자료, 매뉴얼, 서비스 가이드 HTML
└── progress.md               # 단계별 진행 현황
```

## 동작 흐름

1. 사용자가 Web UI 또는 Slack에서 서비스명, 계정 ID, 리전을 입력합니다.
2. FastAPI 백엔드가 `kiro-cli`로 `arb-orchestrator`를 실행합니다.
3. 오케스트레이터가 infra/database 도메인의 subagent를 병렬 호출합니다.
4. 각 subagent는 체크리스트 기준으로 AWS CLI를 실행하고 PASS/FAIL 리포트를 작성합니다.
5. `summary.md`, `improvement-plan.md`가 생성되고, 결과는 SSE 로그와 SQLite 이력으로 노출됩니다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Agent | Kiro CLI (Markdown 기반 steering, checklist, agent 규칙) |
| Backend | FastAPI, uvicorn, SQLite, Slack Bolt (Socket Mode) |
| Frontend | React 18, Vite, recharts, react-markdown, mermaid |
| AWS 서비스 | Bedrock Nova Lite (RAG 채팅), Translate (한/영), Cost Explorer |
| 배포 | EC2 + ALB + nginx + systemd |

## 판정 기준

* PASS: 모든 카테고리에서 Critical FAIL이 0건
* FAIL: Critical FAIL이 1건 이상

자세한 내용은 [progress.md](./aiops-arb-azure-main/aiops-arb-azure-main/aws/progress.md)와 각 하위 폴더의 README를 참고하세요.
