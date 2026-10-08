# service-guide

ARB 점검을 받을 서비스 팀이 수행해야하는 ARB 점검 사전 준비 가이드입니다.\
ARB 팀은 `service-guide.html` 을 서비스 팀에 전달합니다.

> 변경 이력은 [CHANGELOG.md](./CHANGELOG.md) 참조.

## 구성

```
service-guide/
├── cloudformation/
│   ├── 01-global.yaml        ← CloudFormation 글로벌 스택 템플릿 (계정 단위 리소스)
│   └── 02-regional.yaml      ← CloudFormation 리저널 스택 템플릿 (리전 단위 리소스)
├── scripts/
│   ├── check-templates.sh    ← YAML ⇔ HTML 내장본 동기화 상태 점검 스크립트
│   └── sync-templates.sh     ← YAML ⇒ HTML 내장본 동기화 스크립트
├── CHANGELOG.md
├── README.md
└── service-guide.html        ← 서비스 팀 전달용 단일 HTML 가이드 (YAML 내장)
```

## 대상 리소스 추가/수정 시

### 글로벌 스택 (계정 단위 리소스)

1. `cloudformation/01-global.yaml` 추가/수정
2. `service-guide.html` STEP 1 에 해당 리소스 관련 안내 추가/수정
3. [공통 마무리](#공통-마무리) 단계 수행

### 리저널 스택 (리전 단위 리소스)

1. `cloudformation/02-regional.yaml` 추가/수정
2. `service-guide.html` STEP 2 에 해당 리소스 관련 안내 추가/수정
3. [공통 마무리](#공통-마무리) 단계 수행

### 공통 마무리

1. `scripts/sync-templates.sh` 실행 (YAML ⇒ HTML 내장본 동기화)
2. `scripts/check-templates.sh` 실행 (동기화 상태 점검)
3. `CHANGELOG.md` 에 새 버전 엔트리 추가
4. `service-guide.html` 헤더의 버전/날짜 갱신
