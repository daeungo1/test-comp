# DB ARB 종합 리포트

## 전체 요약
- **서비스**: scloud
- **리전**: ap-northeast-2
- **계정**: 325339151285
- **검증일**: 2026-07-31
- **점검 엔진**: Aurora MySQL, ElastiCache
- **최종 판정**: ❌ FAIL

## 엔진별 결과 요약

| No | 엔진 | PASS | FAIL | N/A | Critical FAIL | 판정 |
|----|------|------|------|-----|---------------|------|
| 1  | Aurora MySQL | 29 | 22 | 7 | 5 | ❌ |
| 2  | ElastiCache | 50 | 16 | 2 | 5 | ❌ |
| **합계** | | **79** | **38** | **9** | **10** | |

> ⚠️ **주의**: setup-arb-profile.sh 없음, arb-target 프로파일 미설정 상태로 점검이 수행되었습니다.  
> ElastiCache: auto:true 항목 8개 MANUAL 처리됨. 환경 설정 후 재점검을 권장합니다.

## Critical FAIL 목록

| 엔진 | 리소스 | Check ID | 항목 | 상세 |
|------|--------|----------|------|------|
| Aurora MySQL | s2an2planauroramy01 | COM-SEC-002 | 전송 중 암호화 | require_secure_transport 미설정 |
| Aurora MySQL | s2an2planauroramy01 | COM-AC-001 | SBC 경유 DB 접근 제한 | SBC NAT IP(211.189.57.60/32) 미등록 |
| Aurora MySQL | s2an2planauroramy01 | AURMY-HA-001 | 클러스터 인스턴스 수 | Writer만 1개, Reader 없음 |
| Aurora MySQL | s2an2planauroramy01 | AURMY-HA-002 | Multi-AZ 분산 | 단일 AZ(ap-northeast-2b)에만 배치 |
| Aurora MySQL | s2an2planauroramy01 | AURMY-HA-005 | 엔진 버전 LTS 사용 | 3.10.0 (non-LTS) 사용 중, LTS 전환 권고 |
| ElastiCache | s2an2commonvalkey | COM-AC-001 | SBC 경유 DB 접근 제한 | SG(sg-0e1fcec3c86854c77) 인바운드에 SBC NAT IP(211.189.57.60/32) 미허용 |
| ElastiCache | s2an2publicvalkey | COM-SEC-002 | 전송 중 암호화 | TransitEncryptionEnabled: false |
| ElastiCache | s2an2publicvalkey | COM-AC-001 | SBC 경유 DB 접근 제한 | SG(sg-009003c8f534f792c) 인바운드에 SBC NAT IP(211.189.57.60/32) 미허용 |
| ElastiCache | s2an2publicvalkey | COM-AC-004 | DB 계정 비밀번호 암호화 | AuthTokenEnabled: false, UserGroupIds 미설정 — 인증 방식 미적용 |
| ElastiCache | s2an2publicvalkey | EC-SEC-002 | 전송 중 암호화 (In-Transit) | TransitEncryptionEnabled: false |

## 상세 리포트 경로
- Aurora MySQL: `/scloud/aiops-arb-kiro/arb-reports/scloud/ap-northeast-2/2026-07-31/aurora-mysql.md`
- ElastiCache: `/scloud/aiops-arb-kiro/arb-reports/scloud/ap-northeast-2/2026-07-31/elasticache.md`
