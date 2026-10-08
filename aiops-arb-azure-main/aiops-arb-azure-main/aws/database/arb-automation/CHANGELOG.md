# Change History

| 날짜 | 작성자 | 변경 내용 |
|------|--------|----------|
| 2026-07-30 | Ray Jung | feat: DB summary 파일명을 database-summary.md로 변경 — 오케스트레이터 summary.md와 충돌 및 중복 집계 방지, arb-database agent·steering·README·웹 백엔드·프론트엔드 전체 반영 |
| 2026-07-29 | Ray Jung | chore: .kiro/settings/cli.json에 chat.autoApprove 설정 추가 (tool 호출 자동 승인) |
| 2026-07-29 | Ray Jung | feat: 엔진별 subagent JSON 설정 추가 (.kiro/agents/database-*-reviewer.json), arb-config.md에서 dynamodb 기본 제외, README 멀티 리전 점검 안내 추가 |
| 2026-07-29 | Ray Jung | feat: arb-database agent 추가 — database 단독 실행 시 tool 자동 승인 지원 (.kiro/agents/arb-database.json) |
| 2026-07-29 | Ray Jung | 엔진별 리포트 중복 저장 문제 수정 — database steering subagent 전달 항목에 service_name 추가, 각 에이전트 출력 경로를 arb-reports/{service_name}/{region}/{date}/ 로 통일, elasticache 0단계(리소스 존재 여부 선검증) 추가, arb-config.md에 Service Name 항목 추가(DB 단독 실행 지원) |
| 2026-07-13 | JeongHun Kim | fix(dynamodb): 체크리스트 판정 로직 정비 및 오탐 항목 개선 |
| 2026-07-09 | Ray Jung | fix: ElastiCache discovery 및 로깅 개선 |
| 2026-07-02 | SeungHwan Lee | feat: 점검별 고유 리포트 경로 적용 (account_id/region/date/job_id), 리포트 경로를 service_name → account_id로 변경 |
| 2026-06-11 | SongHee Choi | ElastiCache pre-survey 추가 |
| 2026-06-11 | Yeonho Shin | fix: aurora-mysql pre-survey ACC-001/003 개선 |
| 2026-06-09 | YoungJu Kim | feat: Aurora PostgreSQL pre-survey 가이드 추가, mock 리포맷, 스크립트 service-guide로 이동 |
| 2026-06-09 | YoungJu Kim | feat: Aurora PostgreSQL pre-survey 스크립트 추가 (POSIX sh 호환) |
| 2026-06-05 | YoungJu Kim | feat: Aurora PostgreSQL pre-survey mock 및 체크리스트 Account/Schema 항목 추가 |
| 2026-06-02 | Ray Jung | fix: RDS MySQL/Aurora MySQL 체크리스트 severity 및 파라미터 기준값 업데이트 |
| 2026-06-01 | moonkag.ji | feat: 단일/멀티 리전 ARB 리뷰 시 summary.md 파일 저장 강제화 |
| 2026-05-28 | YoungJu Kim | feat: PostgreSQL parameter group 체크리스트 항목 추가, pg_tle passcheck hook 사용 금지 항목 추가 (AUR-SPL-003, RDSPG-SPL-003) |
| 2026-05-11 | Ray Jung | fix: 체크리스트 severity 레벨 rename (high→major, medium→minor) |
| 2026-05-07 | Yeonho Shin | Aurora MySQL 체크리스트 확장 (10→43항목) 및 reviewer 업데이트 |
| 2026-05-07 | YoungJu Kim | PostgreSQL ARB 체크리스트 추가 |
| 2026-05-07 | JeongHun Kim | DynamoDB 체크리스트 자동화 항목 확대 및 compliance 필드 적용 |
| 2026-05-07 | Ray Jung | 필터 비어있는 엔진 디스커버리 스킵 규칙 추가, arb-reports 쓰기 허용 규칙 추가, verify-reviewer 로그 기반 검증으로 변경 |
| 2026-05-07 | Ray Jung | steering 일반 규칙 추가 (md 파일 읽기 허용, subagent 자율 실행, AWS CLI 읽기 전용 제한) |
| 2026-05-07 | SongHee Choi | Elasticache ARB 체크리스트 항목 업데이트 |
| 2026-05-06 | JeongHun Kim | DynamoDB ARB 체크리스트 항목 업데이트 (#4) |
| 2026-05-06 | Ray Jung | 레거시 파일 삭제 (aurora-reviewer, rds-reviewer, rds.md, aurora.md) |
| 2026-05-06 | ray-jung | 공통 에이전트 규칙 분리 (`common-agent-rules.md`), AWS CLI 벌크 조회 전략 적용, 동일 API 중복 호출 금지 규칙 추가, 커맨드 로깅 추가, Verify Agent 추가, 단일 리전 구조로 단순화, 체크리스트 `auto` 플래그 통일 |
| 2026-04-29 | Ray Jung | 초기 버전 — 오케스트레이터, 엔진별 체크리스트 및 에이전트 프롬프트 구성 |
