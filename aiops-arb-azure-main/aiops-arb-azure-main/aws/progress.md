# ARB 자동화 시스템 진행 현황

- **프로젝트**: aiops-arb-kiro
- **최종 업데이트**: 2026-08-05

---

## 완료 항목

### Phase 1 — KIRO CLI 기반 ARB 자동화 ✅

| 항목 | 내용 |
|------|------|
| ARB Agent 구현 | 14개 Agent (.kiro/agents/) |
| 인프라 체크리스트 | 75항목 (아키텍처/DevOps/운영/서비스안정성/시스템안정성) |
| DB 체크리스트 | 214항목 (공통18 + Aurora MySQL41 + Aurora PG36 + RDS MySQL27 + RDS PG36 + DynamoDB36 + ElastiCache20) |
| arb-orchestrator | infra/database 도메인 병렬 호출 + summary.md 자동 생성 |
| allowedTools | fs_write/execute_bash 추가 → y/n 입력 불필요 |
| 자동 종료 | improvement-plan.md 생성 후 5분 타이머 |

### Phase 2 — Web UI 구현 ✅

#### 기술 스택
| 레이어 | 기술 | 버전 |
|--------|------|------|
| Web Server | nginx | 1.28.2 |
| Backend | FastAPI + uvicorn | 0.128 / 0.39 |
| Frontend | React + Vite | 18 / 4.5 |
| Chart | recharts | 2 |
| Markdown | react-markdown + remark-gfm + rehype-raw | 8 / 3 / 6 |
| Diagram | mermaid.js | 10 |
| DB | SQLite3 | Python 표준 |
| 번역 | Amazon Translate | - |
| AI 채팅 | Amazon Bedrock Nova Lite | us-east-1 |

#### 구현된 탭 기능

| 탭 | 주요 기능 |
|----|-----------|
| 📊 ARB 대시보드 | 월별/연도별 비용+점검현황 차트, 프로젝트별 FAIL 추이 |
| 🔍 ARB 점검 | 서비스/계정/리전 입력, SSE 실시간 로그, 전체 리전 자동 탐지 |
| 📋 히스토리 | 점검 이력, PASS/FAIL/Critical 결과 요약, 로그 조회 |
| 📄 리포트 | 프로젝트>날짜>Summary/Infra/DB 트리, 마크다운+Mermaid 렌더링, 다운로드 |
| 📖 운영 가이드 | 645개 내부 Knowledge 문서, ARB 카테고리 트리, 키워드 AND 검색 |
| 💰 비용 | 연간 AWS 비용 차트, 과제별 점검 횟수 |

#### 리포트 탭 상세 기능
- summary.md 진입 시 **카테고리별 운영 가이드** 버튼 자동 표시
- ❌ FAIL 행 클릭 → 운영 가이드 탭으로 이동
- 리포트 내 가이드 패널 (Check ID별 관련 문서)

#### 운영 가이드 탭
- ARB 8개 카테고리 트리 (인프라/AutoScaling/모니터링/백업/DevOps/DB공통/Aurora/RDS)
- 각 Check ID별 관련 문서 수 배지 표시
- 키워드 AND 조합 검색 (공백 구분)
- 우측 채팅창에서 가이드 내용 질의 가능

### Phase 3 — RAG 기반 채팅 ✅

| 항목 | 내용 |
|------|------|
| 모델 | Amazon Nova Lite (us-east-1) |
| 컨텍스트 | Knowledge 인덱스 top-3 문서 + 현재 리포트 발췌 |
| 제약 | 내부 문서 외 답변 금지 (시스템 프롬프트 강제) |
| 위치 | 리포트 탭 + 운영 가이드 탭 우측 패널 |
| 다국어 | 한/영 답변 언어 자동 전환 |
| 스트리밍 | SSE 기반 타이핑 효과 |

### Phase 4 — 한/영 다국어 ✅

- 사이드바 언어 토글 (한국어/English)
- UI 전체 레이블 번역 (i18n)
- 리포트 내용 Amazon Translate 번역
- 운영 가이드 문서 Amazon Translate 번역
- 채팅 초기 메시지 + 답변 언어 자동 전환

### Phase 5 — 비용/대시보드 ✅

- AWS Cost Explorer 연간(1~12월) 비용 조회
- 일별 점검 현황 + 비용 복합 차트
- 계정 ID 기준 중복 프로젝트 통합
- 과제별 점검 횟수 + 최근 점검일 테이블

### Phase 6 — Slack Bot 연동 ✅ (2026-06-10)

| 항목 | 내용 |
|------|------|
| 방식 | Socket Mode (포트 오픈 불필요, EC2 아웃바운드 WSS) |
| 이중 동작 | 일반 질의 → RAG 답변 / 점검 요청 → arb-orchestrator 실행 |
| 점검 판별 | 명시적 패턴 + 계정ID & 실행 키워드 조합 (조회성 질문 제외) |
| 리포트 컨텍스트 | 계정 ID 포함 시 최근 summary.md 자동 로드 |
| DB 연동 | Slack 점검도 SQLite에 기록 → 대시보드 집계 |
| 호칭 제거 | 이름/호칭 없이 바로 답변, 내부 문서 기반 응답 |
| mrkdwn 변환 | 마크다운 → Slack 포맷 자동 변환 |
| 서비스 | arb-slack-bot.service (systemd 자동 시작) |

### Phase 7 — 버그 수정 및 UX 개선 ✅ (2026-06-11~12)

| 항목 | 내용 |
|------|------|
| Slack 점검 오판 수정 | 조회성 질문(`결과`, `어디야` 등)은 점검 요청으로 분류 안 함 |
| Slack 시스템 프롬프트 완화 | 리포트 내용 기반 답변 허용, 가이드 없을 때 별도 언급 안 함 |
| 리포트 컨텍스트 자동 로드 | 계정 ID 포함 질문 시 최근 summary.md 자동 포함 |
| Mermaid 대형 다이어그램 | maxTextSize 확대, 파이프 안 한글 제거로 렌더링 수정 |
| 히스토리 레코드 정리 | 오입력 점검 레코드 SQLite 직접 삭제 기능 |

### Phase 8 — 대화 UX, 반응형 UI, 안정성 ✅ (2026-06-13~18)

| 항목 | 내용 |
|------|------|
| 일상 대화 처리 | 인사/기능소개/점검방법/ARB소개 템플릿 응답 추가 |
| 범위 밖 질문 필터 | AWS/인프라 무관 질문은 "ARB 점검 범위 밖" 안내 |
| 채팅 프롬프트 개선 | 내부문서 우선, 없으면 "일반적인 Best Practice는:" 으로 보완 |
| 다국어 자동 감지 | Slack도 영어 질문 시 영어 답변 자동 전환 |
| 반응형 레이아웃 | sidebar/chat panel 고정px → clamp() 비율 기반 |
| 채팅 패널 리사이저 | 드래그로 채팅 패널 너비 조절 (180~700px) |
| 이미지 반응형 | markdown-body img max-width:100% 적용 |
| 고정 비용 기준선 | 대시보드 비용 차트에 ReferenceLine 추가 |
| diagram/improvement 누락 수정 | arb-orchestrator 프롬프트에 필수 호출 지시 추가 |
| Slack run_inspection tmpfile | 파이프 버퍼 포화 방지, improvement-plan 타이머 적용 |
| Slack auto 리전 처리 | auto → ap-northeast-2 기본값 전달 |
| KST 시간대 적용 | 신규 job KST 저장, 기존 36건 DB 보정 |
| 히스토리→리포트 매핑 | 파일 mtime UTC→KST 변환으로 정확한 매핑 |
| 서비스명 파싱 개선 | 단어 경계 기반 노이즈 제거 (부분 매칭 방지) |

### Phase 9 — 리포트 경로 구조 개선 ✅ (2026-07-02~29)

| 항목 | 내용 |
|------|------|
| 리포트 저장 경로 변경 | `{service_name}` → `{account_id}/{region}/{date}/{job_id}/` |
| 계정 기준 분리 | PRD/DEV 등 서로 다른 서비스가 같은 폴더에 섞이는 문제 해결 |
| 덮어쓰기 방지 | 같은 날 여러 번 점검 시 job_id로 구분하여 충돌 없음 |
| 동시 요청 충돌 방지 | UUID 기반 job_id로 race condition 원천 차단 |
| reports_tree API 개선 | 계정 ID 폴더를 서비스명으로 표시, 신/구 구조 모두 지원 |
| 중복 파일 자동 정리 | job_id 폴더 있는 날짜 폴더의 직접 하위 md 파일 스킵 |
| Slack 서비스명 파싱 재수정 | 한국어 조사/따옴표/불필요 단어 제거 로직 강화 |
| 아키텍처 다이어그램 PPTX | Agent/Resource 연관관계 도형 기반 문서 생성 |
| 멀티 리전 순차 점검 | regions 배열 기반 리전별 개별 job 순차 실행 |
| 서버 재시작 시 stale job 정리 | 24시간 초과 running 상태 job 자동 error 처리 |
| reports_tree 성능 개선 | job_dir 캐싱으로 7.7초 → 0.06초 (PR #69) |
| /opt/web 배포 환경 구축 | arb-web 그룹 권한, deploy.sh, 팀원 13명 배포 권한 부여 |
| DB 전용 점검 (PR #63) | 점검 범위 선택 (전체 / DB만) + 엔진 체크박스 선택 |
| arb-database agent (PR #65) | 인프라 sub-agent 호출 차단, DB 전용 프롬프트 분기 |
| database-summary.md (PR #67) | DB 전용 완료 트리거, PASS/FAIL 파싱 2순위, reports_tree 지원 |

### Phase 10 — 사전 서베이 기능 ✅ (2026-08-05)

| 항목 | 내용 |
|------|------|
| Infra 사전 서베이 웹폼 | ARB 점검 탭 내 7개 섹션 아코디언 폼 (인프라선정/계정/예산/시스템안정성/운영/서비스안정성/DevOps) |
| 서베이 저장/로드 | `web/surveys/{account_id}.json`, 계정 ID 입력 시 자동 로드, 한/영 레이블 지원 |
| DB 사전 서베이 — 스크립트 | Aurora MySQL/PostgreSQL 스크립트 다운로드 + 결과 md 업로드 |
| DB 사전 서베이 — 수동 설문 | 4개 엔진 × 총 49개 수동 입력 항목 (계정관리/스키마/인덱스/용량 등) |
| DB 수동 설문 UI 순서 | 수동 설문 폼 위쪽, 스크립트 안내 아래쪽으로 배치 |
| 사전 서베이 버튼 UX | Account ID 미입력 시 항상 표시하되 비활성화(회색), 안내 문구 표시 |
| summary.md 서베이 표시 | Infra 서베이 + DB 스크립트 결과 + DB 수동 설문 모두 접힌 상태로 상단 표시 |
| 한/영 지원 | 모든 서베이 레이블/안내문/버튼 한/영 전환 지원 |
| python-multipart 설치 | 파일 업로드 API 지원 패키지 /opt/web/venv에 설치 |

---

## Backlog

| 항목 | 설명 | 우선순위 |
|------|------|---------|
| 사용자 역할 기반 접근 제어 | 의뢰자/점검자 역할 분리, 프로젝트별 열람 제한 | Medium |
| 전체 리전 자동 탐지 점검 | EC2/RDS 존재 리전 자동 탐지 후 점검 (UI 옵션 구현, 오케스트레이터 미연동) | Medium |
| AgentCore 연동 | Bedrock AgentCore 기반 병렬 실행, 진행률 표시 (SCP 제약으로 보류) | Low |
| 점검 스케줄링 | 정기 자동 점검 + Slack 알림 | Low |

---

## 시스템 구성

```
Browser → ALB(80, 사내IP) → EC2:80 nginx
                                → uvicorn:8000 FastAPI  [/opt/web/aiops-arb-kiro/web/backend/main.py]
                                    ├── kiro-cli subprocess (arb-orchestrator / arb-database)
                                    ├── SQLite (web/arb.db)
                                    ├── arb-reports/{account_id}/{region}/{date}/{job_id}/
                                    ├── web/surveys/{account_id}.json          (Infra 사전 서베이)
                                    ├── web/db-presurveys/{account_id}/*.md    (DB 스크립트 결과)
                                    ├── web/db-manual-surveys/{account_id}/*.json  (DB 수동 설문)
                                    ├── Amazon Translate (번역)
                                    └── Bedrock Nova Lite (RAG 채팅)

Slack DM/@mention → slack_bot.py (Socket Mode)  [web/backend/slack_bot.py]
                        ├── 일반 질의 → Knowledge 인덱스 → Nova Lite → Slack 답변
                        └── 점검 요청 → kiro-cli → SQLite → Slack 결과 전송

배포:
  /opt/web/aiops-arb-kiro/  (실제 서비스 환경)
  /opt/web/venv/             (Python 가상환경)
  ./deploy.sh                (arb-web 그룹 멤버 배포 스크립트)

systemd 서비스:
  /etc/systemd/system/arb-backend.service    (FastAPI)
  /etc/systemd/system/arb-slack-bot.service  (Slack Bot)

Knowledge Base: ~/repo/aiops-arb-guide/OPSPROCESS_MD/docs/ (645개 md)
인덱스: web/backend/knowledge_index.json
```

## 접속 정보

- **Web URL**: https://arb.cloud-aiops.com
- **Slack**: DM 또는 채널에서 @ARB Assistant 멘션
- **계정**: 260544022684 (EC2RoleAmazonQ)
- **작업 브랜치**: feat/merge-ray-prs (→ main PR 생성 필요)
