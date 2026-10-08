# Common ARB Checklist

모든 DB 엔진에 공통으로 적용되는 검증 항목입니다.

## Security

- [COM-SEC-001] 저장 데이터 암호화 (Encryption at Rest) | severity: critical | auto: true
  - 기준: 모든 DB는 저장 시 암호화가 활성화되어야 합니다.

- [COM-SEC-002] 전송 중 암호화 (Encryption in Transit) | severity: critical | auto: true
  - 기준: SSL/TLS를 통한 전송 암호화가 강제되어야 합니다.

- [COM-SEC-003] 퍼블릭 접근 차단 | severity: critical | auto: true
  - 기준: DB는 퍼블릭 인터넷에서 직접 접근이 불가해야 합니다.

- [COM-SEC-004] VPC 내 배치 | severity: critical | auto: true
  - 기준: DB는 반드시 VPC 내에 배치되어야 합니다.

## Backup & Recovery

- [COM-BR-001] 자동 백업 활성화 | severity: critical | auto: true
  - 기준: 자동 백업이 활성화되어 있어야 합니다.

- [COM-BR-002] 삭제 방지 (Deletion Protection) | severity: major | auto: true
  - 기준: 프로덕션 DB는 삭제 방지가 활성화되어야 합니다.

## Monitoring

- [COM-MON-001] CloudWatch 알람 설정 | severity: major | auto: true
  - 기준: CPU, 메모리, 디스크 등 주요 메트릭에 대한 알람이 설정되어야 합니다.

- [COM-MON-002] 로깅 활성화 | severity: minor | auto: true
  - 기준: 감사/쿼리 로그가 CloudWatch Logs로 전송되어야 합니다.

- [COM-MON-003] 상시 모니터링 솔루션 적용 | severity: major | auto: false
  - 검증: 상시 모니터링이 가능한 모니터링 솔루션 사용 여부 확인
  - 기준: DB에 대한 상시 모니터링 솔루션이 적용되어야 합니다.

- [COM-MON-004] 알람 수신 항목 설정 | severity: major | auto: true
  - 검증: 필요 알람 수신 항목이 설정되어 있는지 확인
  - 기준: 주요 메트릭에 대한 알람 수신 항목이 설정되어야 합니다.

## Tagging

- [COM-TAG-001] 필수 태그 존재 | severity: major | auto: true
  - 기준: Environment, Owner, Team 태그가 반드시 존재해야 합니다.

## Access Control

- [COM-AC-001] 내부 접속 서비스(SBC) 경유 DB 접근 제한 | severity: critical | auto: true
  - 검증: DB의 Security Group 인바운드 규칙에 SBC NAT IP(211.189.57.60/32)가 허용되어 있는지 확인
  - 기준: 개인정보 취급 대상자는 반드시 SBC(NAT IP: 211.189.57.60/32)를 경유하여 DB에 접근해야 합니다.

- [COM-AC-002] 허가된 IP/SG 기반 접속 제한 | severity: critical | auto: true
  - 검증: DB의 Security Group 인바운드 규칙에 허가되지 않은 IP 대역이나 0.0.0.0/0이 포함되어 있지 않은지 확인
  - 기준: 허가된 IP(예: SBC NAT IP 211.189.57.60/32) 또는 허가된 Security Group에서만 접속이 허용되어야 합니다.

- [COM-AC-003] Bastion(Jumphost) 서버 분리 | severity: major | auto: true
  - 검증: arb-config.md의 DB Bastion 설정(instance-id 또는 tag)으로 EC2 인스턴스를 조회하여 존재 여부, 별도 SG 사용, DB SG와의 연결 관계를 확인
  - 기준: DB 접속 전용 Bastion 서버가 존재하고, DB의 Security Group이 Bastion의 SG 또는 IP로부터의 접근을 허용해야 합니다.

- [COM-AC-004] DB 계정 비밀번호 암호화 | severity: critical | auto: false
  - 검증: WAS/Application에서 사용하는 DB 계정 비밀번호가 암호화되어 있는지 확인
  - 기준: WAS config 내 DB 비밀번호는 반드시 암호화되어 사용해야 합니다.

## Access Audit

- [COM-AA-001] DB 접속 기록 정기 점검 | severity: major | auto: false
  - 검증: DB 접속 기록에 대한 월 1회 정기 점검 실시 여부 확인 (STI 자동점검)
  - 기준: DB 접속 기록을 월 1회 이상 정기 점검해야 합니다.

## Network Isolation

- [COM-NI-001] DB 서브넷 망분리 (인터넷 격리) | severity: critical | auto: true
  - 검증: DB가 배치된 서브넷의 라우트 테이블을 조회하여 Internet Gateway(0.0.0.0/0 → igw-*) 경로가 없는지 확인
  - 기준: DB 서브넷은 별도의 프라이빗 서브넷이어야 하며, 라우트 테이블에 Internet Gateway 경로가 존재하지 않아야 합니다.

## Disaster Recovery

- [COM-DR-001] DR 구축 검토 | severity: major | auto: false
  - 검증: DR 구축 필요성 검토 여부 확인
  - 기준: DR 구축 필요 여부를 검토하고 결과를 문서화해야 합니다.
