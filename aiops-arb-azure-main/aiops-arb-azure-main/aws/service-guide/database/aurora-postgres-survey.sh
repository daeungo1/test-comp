#!/bin/bash
# =============================================================================
# Aurora PostgreSQL ARB Pre-Survey Script
# ARB 담당자가 개발팀에 전달하는 사전 조사 스크립트입니다.
#
# [개발팀 실행 방법]
#   chmod +x aurora-postgres-survey.sh
#   ./aurora-postgres-survey.sh
#
# [실행 결과]
#   aurora-postgres-survey-<CLUSTER_ID>-<DATE>.md 파일이 생성됩니다.
#   흰색(일반 텍스트) 부분만 작성 후 ARB 담당자에게 전달해주세요.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# [TEST] 테스트용 변수 직접 선언 - 배포 시 이 블록 삭제
# -----------------------------------------------------------------------------
# CLUSTER_ID="my-cluster"
# DB_HOST="my-cluster.cluster-xxxx.ap-northeast-2.rds.amazonaws.com"
# DB_PORT="5432"
# DB_USER="arb_readonly"
# DB_PASS='your_password'
# DB_NAME="your_database"
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 접속 정보 입력 - 위 [TEST] 블록 사용 시 아래 read 블록 주석 처리
# -----------------------------------------------------------------------------
CLUSTER_ID="${CLUSTER_ID:-}"
DB_HOST="${DB_HOST:-}"
DB_PORT="${DB_PORT:-}"
DB_USER="${DB_USER:-}"
DB_PASS="${DB_PASS:-}"
DB_NAME="${DB_NAME:-}"

echo "======================================================"
echo " Aurora PostgreSQL ARB Pre-Survey"
echo "======================================================"
echo ""

[ -z "$CLUSTER_ID" ] && read -rp "클러스터 식별자 (예: my-service-aurora-pg-cluster): " CLUSTER_ID
[ -z "$DB_HOST"    ] && read -rp "호스트 (Reader endpoint):                           " DB_HOST
[ -z "$DB_PORT"    ] && read -rp "포트 (기본 5432):                                   " DB_PORT
DB_PORT=${DB_PORT:-5432}
[ -z "$DB_USER"    ] && read -rp "읽기 전용 계정 (예: arb_readonly):                  " DB_USER
[ -z "$DB_PASS"    ] && { read -rsp "비밀번호:                                           " DB_PASS; echo ""; }
[ -z "$DB_NAME"    ] && read -rp "대상 데이터베이스 이름:                             " DB_NAME
# -----------------------------------------------------------------------------

# 필수값 검증
for var in CLUSTER_ID DB_HOST DB_PORT DB_USER DB_PASS DB_NAME; do
    eval val=\$$var
    if [ -z "$val" ]; then
        echo "[ERROR] 필수 값이 없습니다: $var"
        exit 1
    fi
done

GENERATED=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date '+%Y%m%d')
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${SCRIPT_DIR}/aurora-postgres-survey-${CLUSTER_ID}-${DATE}.md"
TMPFILE="/tmp/arb-survey-$$.tsv"
SQLFILE="/tmp/arb-survey-$$.sql"
trap 'rm -f "$TMPFILE" "$SQLFILE"' EXIT

export PGPASSWORD="$DB_PASS"

# -----------------------------------------------------------------------------
# 접속 확인
# -----------------------------------------------------------------------------
echo ""
echo "DB 접속 확인 중..."
CONN_ERR=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
           -tAc "SELECT 1" 2>&1 >/dev/null || true)
if [ -n "$CONN_ERR" ]; then
    echo "[ERROR] DB 접속에 실패했습니다."
    echo "        원인: $CONN_ERR"
    echo "        확인: 호스트(${DB_HOST}:${DB_PORT}), 계정(${DB_USER}), DB(${DB_NAME}), 네트워크/보안그룹"
    exit 1
fi
echo "접속 성공. 데이터 수집 중..."

# -----------------------------------------------------------------------------
# 단일 세션으로 모든 데이터 수집
# 섹션 구분자: --SECTION--
# -----------------------------------------------------------------------------
cat > "$SQLFILE" << 'ENDSQL'
-- [1] postgres 마스터 계정 존재 여부
SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres' AND rolcanlogin) THEN 'EXISTS' ELSE 'NOT_EXISTS' END;
SELECT '--SECTION--';

-- [2] 전체 계정 목록 (rolname / rolcanlogin / rolsuper / member_of)
SELECT r.rolname,
       r.rolcanlogin::text,
       r.rolsuper::text,
       COALESCE(string_agg(g.rolname, ',' ORDER BY g.rolname), '-')
FROM pg_roles r
LEFT JOIN pg_auth_members m ON r.oid = m.member
LEFT JOIN pg_roles g ON m.roleid = g.oid
WHERE r.rolname NOT LIKE 'pg_%'
  AND r.rolname NOT IN ('rdsadmin','rds_superuser','rds_replication','rds_password','rdsrepladmin')
GROUP BY r.rolname, r.rolcanlogin, r.rolsuper
ORDER BY r.rolname;
SELECT '--SECTION--';

-- [3] 계정별 스키마 권한
SELECT grantee, table_schema, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema NOT IN ('pg_catalog','information_schema')
  AND grantee NOT LIKE 'pg_%'
  AND grantee NOT IN ('rdsadmin','rds_superuser','rds_replication','rds_password','rdsrepladmin')
ORDER BY grantee, table_schema, privilege_type;
SELECT '--SECTION--';

-- [4] FK 목록
SELECT tc.table_name, tc.constraint_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_catalog = ccu.constraint_catalog
 AND tc.constraint_schema = ccu.constraint_schema
 AND tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;
SELECT '--SECTION--';

-- [5] Function/Procedure 목록
SELECT p.proname,
       CASE p.prokind WHEN 'f' THEN 'FUNCTION' WHEN 'p' THEN 'PROCEDURE' ELSE 'OTHER' END
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
ORDER BY 2, 1;
SELECT '--SECTION--';

-- [6] PK 컬럼 현황
SELECT c.table_name, kcu.column_name, col.data_type,
       CASE WHEN col.column_default LIKE 'nextval%' OR col.is_identity = 'YES' THEN 'YES' ELSE 'NO' END AS auto_inc,
       CASE WHEN (col.data_type IN ('integer','bigint') OR col.data_type = 'uuid')
                 AND (col.column_default LIKE 'nextval%' OR col.is_identity = 'YES' OR col.data_type = 'uuid')
            THEN 'OK' ELSE 'WARN' END AS status
FROM information_schema.table_constraints c
JOIN information_schema.key_column_usage kcu
  ON c.constraint_name = kcu.constraint_name AND c.table_schema = kcu.table_schema
JOIN information_schema.columns col
  ON kcu.table_name = col.table_name AND kcu.column_name = col.column_name AND kcu.table_schema = col.table_schema
WHERE c.constraint_type = 'PRIMARY KEY'
  AND c.table_schema = 'public'
ORDER BY c.table_name;
SELECT '--SECTION--';

-- [7] UK 목록
SELECT tc.table_name, tc.constraint_name,
       string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position)
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema = 'public'
GROUP BY tc.table_name, tc.constraint_name
ORDER BY tc.table_name;
SELECT '--SECTION--';

-- [8] 인덱스 목록 (PK 제외)
SELECT tablename, indexname,
       pg_get_indexdef(i.indexrelid, 0, false),
       CASE WHEN indisunique THEN 'UNIQUE' ELSE 'INDEX' END
FROM pg_indexes pi
JOIN pg_index i ON i.indexrelid = (pi.schemaname || '.' || pi.indexname)::regclass
WHERE pi.schemaname = 'public'
  AND indexname NOT LIKE '%_pkey'
ORDER BY tablename, indexname;
ENDSQL

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
     -tA -F "	" -f "$SQLFILE" > "$TMPFILE" 2>&1 || { echo "[ERROR] 데이터 수집 중 오류:"; cat "$TMPFILE"; exit 1; }

echo "수집 완료. 파일 생성 중: $OUTPUT"

# -----------------------------------------------------------------------------
# 섹션별 파싱 (--SECTION-- 구분)
# -----------------------------------------------------------------------------
parse_section() {
    local n=$1
    awk -v n="$n" 'BEGIN{sec=0} /^--SECTION--/{sec++; next} sec==n-1{print}' "$TMPFILE"
}

SEC_MASTER=$(parse_section 1)
SEC_ACCOUNTS=$(parse_section 2)
SEC_GRANTS=$(parse_section 3)
SEC_FK=$(parse_section 4)
SEC_ROUTINES=$(parse_section 5)
SEC_PK=$(parse_section 6)
SEC_UK=$(parse_section 7)
SEC_INDEX=$(parse_section 8)

MASTER_STATUS=$(echo "$SEC_MASTER" | tr -d '[:space:]')
FK_COUNT=$(echo "$SEC_FK" | grep -c '.' || true)
ROUTINE_COUNT=$(echo "$SEC_ROUTINES" | grep -c '.' || true)
UK_COUNT=$(echo "$SEC_UK" | grep -c '.' || true)
PK_WARN=$(echo "$SEC_PK" | awk -F'\t' '$5=="WARN"' || true)

if [ "$MASTER_STATUS" = "EXISTS" ]; then
    ACC003_DETAIL="postgres 마스터 계정 존재 (기본값 사용)"
else
    ACC003_DETAIL="postgres 계정 없음 (마스터 유저명 변경됨)"
fi

# -----------------------------------------------------------------------------
# 계정 목록 추출 (입력란 생성용)
# -----------------------------------------------------------------------------
ACCOUNT_LINES=$(echo "$SEC_ACCOUNTS" | awk -F'\t' '$2=="true"{print $1}' | grep -v '^$' || true)

# =============================================================================
# MD 파일 생성
# =============================================================================
{

cat << HEADER
# Aurora PostgreSQL ARB Pre-Survey
#
# [작성 안내]
#   - 보라색(#) 줄 : 설명 및 자동 조회 결과 -- 읽기만 하세요
#   - 흰색 줄      : 직접 입력이 필요한 부분 -- <<FILL>> 을 채워주세요
#   - 작성 완료 후 ARB 담당자에게 이 파일을 전달해주세요
#
# CLUSTER   : ${CLUSTER_ID}
# HOST      : ${DB_HOST}
# DATABASE  : ${DB_NAME}
# GENERATED : ${GENERATED}

AUTHOR : <<FILL: 작성자 이름>>


#
#
# ==============================================================================
# SECTION 1. Account Management
#
#
# ==============================================================================


#
#
# ==============================================================================
# [AUR-ACC-001 + AUR-ACC-004] DB 계정 분류 및 권한 확인  [severity: high]
#
# 아래 계정 목록과 권한을 참고하여 입력란을 작성해주세요.
# 용도 기준: SERVICE(WAS 서비스 계정) / DBA(관리자) / PERSONAL(개발자 개인) / SYSTEM(AWS 내부 시스템 계정)
# 권한 적절 기준:
#   SERVICE  -> DML(SELECT/INSERT/UPDATE/DELETE) 만 허용
#   DBA      -> 관리 권한 허용
#   PERSONAL -> SELECT 만 허용
#   SYSTEM   -> AWS/RDS 내부 관리용 계정 (rdsadmin 등), 검토 제외
#
HEADER

echo "# -- 계정 목록 (rolname / rolcanlogin / rolsuper / member_of) --"
echo "$SEC_ACCOUNTS" | awk -F'\t' '{printf "#   %-30s %-8s %-8s %s\n", $1, $2, $3, $4}'
echo "#"
echo "# -- 계정별 스키마 권한 --"
echo "$SEC_GRANTS" | awk -F'\t' '{printf "# %s : %s.%s\n", $1, $2, $3}' | sort -u
echo "#"
echo "# -- 입력 ---------------------------------------------------------------"
echo "# 형식: ACCOUNT | SERVICE/DBA/PERSONAL/SYSTEM | 권한적절 O/X | 비고"
echo ""

# AWS RDS 내부 시스템 계정 목록
SYSTEM_ACCOUNTS="rdsadmin rds_superuser rdsrepladmin rds_replication rds_password rdswriteforwarduser"

echo "$ACCOUNT_LINES" | while IFS= read -r user; do
    [ -z "$user" ] && continue
    if echo "$SYSTEM_ACCOUNTS" | grep -qw "$user"; then
        printf "ACCOUNT : %-20s | SYSTEM               | O            | AWS RDS 내부 시스템 계정\n" "$user"
    else
        printf "ACCOUNT : %-20s | <<FILL: SERVICE/DBA/PERSONAL>> | <<FILL: O/X>> | <<FILL: 비고>>\n" "$user"
    fi
done

cat << 'ACC_RESULT'



#
#
# ==============================================================================
# [AUR-ACC-002] 개인 사용자 계정 1인 1계정 원칙  [severity: high]
#
# 개인 사용자 계정이 1인 1계정으로 발급되었는지 확인해주세요. (공용 계정 사용 금지)
#
# -- 입력 ---------------------------------------------------------------------

    개인 계정 공용 사용 없음 : <<FILL: O/X>>
    비고                     : <<FILL>>  # 공용 계정이 있는 경우 해당 계정명 및 사유


ACC_RESULT

# ACC-003 (자동 판별)
if [ "$MASTER_STATUS" = "NOT_EXISTS" ]; then
cat << ACC003
#
#
# ==============================================================================
# [AUR-ACC-003] postgres 기본 마스터 유저명 미사용  [severity: critical]
#
# Aurora PostgreSQL에서 postgres는 기본 마스터 유저입니다.
# 서비스(애플리케이션)에서 postgres 계정을 직접 사용하지 않는지 확인해주세요.
# 마스터 계정은 관리 목적으로만 사용해야 합니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   마스터 유저 상태 : ${ACC003_DETAIL}
#

    postgres 계정 서비스 미사용 : O

ACC003
else
cat << ACC003
#
#
# ==============================================================================
# [AUR-ACC-003] postgres 기본 마스터 유저명 미사용  [severity: critical]
#
# Aurora PostgreSQL에서 postgres는 기본 마스터 유저입니다.
# 서비스(애플리케이션)에서 postgres 계정을 직접 사용하지 않는지 확인해주세요.
# 마스터 계정은 관리 목적으로만 사용해야 합니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   마스터 유저 상태 : ${ACC003_DETAIL}
#

    postgres 계정 서비스 미사용 : <<FILL: O/X>>
    비고                       : <<FILL>>  # 서비스에서 사용 중인 경우 교체 계획

ACC003
fi

cat << 'ACC_REST'
#
#
# ==============================================================================
# [AUR-ACC-005] DB 계정 관리 DBA 담당  [severity: medium]
#
# DB 계정 생성/변경/삭제 업무를 DBA가 담당하고 있는지 확인해주세요.
#
# -- 입력 ---------------------------------------------------------------------

    DBA가 계정 관리 담당 : <<FILL: O/X>>
    비고                 : <<FILL>>  # DBA가 아닌 경우 실제 담당자/팀 명시



#
#
# ==============================================================================
# [AUR-ACC-006] DB 계정 신규/변경/삭제 프로세스  [severity: medium]
#
# DB 계정 관리 프로세스(문서)가 존재하는지 확인해주세요.
#
# -- 입력 ---------------------------------------------------------------------

    계정 관리 프로세스 문서 존재 : <<FILL: O/X>>
    비고                         : <<FILL>>  # 문서 위치/링크, 없는 경우 작성 예정일



#
#
# ==============================================================================
# [AUR-ACC-007] DB 계정 권한 리스트 문서 관리  [severity: medium]
#
# 계정 권한 현황 문서가 최신 상태로 유지되고 있는지 확인해주세요.
#
# -- 입력 ---------------------------------------------------------------------

    권한 현황 문서 최신 유지 : <<FILL: O/X>>
    비고                     : <<FILL>>  # 최종 갱신일, 미유지 시 갱신 예정일



#
#
# ==============================================================================
# [AUR-ACC-008] DB 계정 내역 5년 보관  [severity: medium]
#
# 계정 신규/변경/삭제 내역(결재 문서)을 5년간 보관하고 있는지 확인해주세요.
#
# -- 입력 ---------------------------------------------------------------------

    계정 내역 5년 보관 중 : <<FILL: O/X>>
    비고                  : <<FILL>>  # 보관 위치/방식, 미보관 시 조치 예정일


ACC_REST

cat << ACC009
#
#
# ==============================================================================
# [AUR-ACC-009] Instance Name Rule 준수  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   클러스터 식별자 : ${CLUSTER_ID}
#
# 위 식별자가 조직 네이밍 규칙을 준수하는지 확인해주세요.
#
# -- 입력 ---------------------------------------------------------------------

    네이밍 규칙 준수 : <<FILL: O/X>>
    비고             : <<FILL>>  # 미준수 시 사유 및 개선 예정일



#
#
# ==============================================================================
# SECTION 2. Schema Design
#
#
# ==============================================================================

ACC009

# SCH-001
if [ "${FK_COUNT:-0}" -eq 0 ]; then
cat << 'SCH001_PASS'
#
#
# ==============================================================================
# [AUR-SCH-001] FK 사용 의도 확인  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   FK 사용 테이블 : 없음
#

SCH001_PASS
else
cat << 'SCH001_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-001] FK 사용 의도 확인  [severity: medium]
#
# FK가 존재합니다. 의도된 설계인지 확인해주세요.
# PostgreSQL에서는 FK 사용이 허용되나, 대규모 트래픽 환경에서는
# 잠금 경합 및 성능 영향을 검토해야 합니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH001_HEAD
echo "$SEC_FK" | awk -F'\t' '{printf "#   TABLE: %-30s CONSTRAINT: %-30s REF: %s\n", $1, $2, $3}'
cat << 'SCH001_FILL'
#
# -- 입력 ---------------------------------------------------------------------

    FK 사용이 의도된 설계인가 : <<FILL: O/X>>
    성능 영향 검토 완료       : <<FILL: O/X>>
    비고                      : <<FILL>>  # 의도된 경우 설계 사유, 미의도 시 제거 예정일


SCH001_FILL
fi

# SCH-002
if [ "${ROUTINE_COUNT:-0}" -eq 0 ]; then
cat << 'SCH002_PASS'
#
#
# ==============================================================================
# [AUR-SCH-002] Function/Procedure 제약사항 확인  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   등록된 Function/Procedure : 없음
#

SCH002_PASS
else
cat << 'SCH002_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-002] Function/Procedure 제약사항 확인  [severity: medium]
#
# Function/Procedure가 존재합니다. 아래 제약사항을 검토하였는지 확인해주세요.
#   - Function 내 COMMIT/ROLLBACK 불가 (Procedure에서만 가능, PG 11+)
#   - 실행 계획 확인이 어려움 (auto_explain으로도 내부 쿼리 추적 제한적)
#   - 파라미터 변경 시 DROP 후 재생성 필요
#   - SECURITY DEFINER 사용 시 권한 상승 위험
#   - pg_stat_statements에서 내부 개별 쿼리 추적 제한적
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH002_HEAD
echo "$SEC_ROUTINES" | awk -F'\t' '{printf "#   %-40s %s\n", $1, $2}'
cat << 'SCH002_FILL'
#
# -- 입력 ---------------------------------------------------------------------

    제약사항 검토 완료 : <<FILL: O/X>>
    비고               : <<FILL>>  # 미검토 시 예정일, 검토 결과 이슈 사항


SCH002_FILL
fi

# SCH-003
cat << 'SCH003_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-003] 테이블 PK 타입 확인  [severity: medium]
#
# PK가 정수형 자동 증가(SERIAL/BIGSERIAL/IDENTITY) 또는 UUID인지 확인합니다.
# STATUS=WARN 항목은 위 조건을 충족하지 않습니다.
# 의도된 설계인지 검토해주세요.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH003_HEAD
echo "$SEC_PK" | awk -F'\t' '{printf "#   %-30s %-20s %-10s AUTO/ID=%-5s %s\n", $1, $2, $3, $4, $5}'

if [ -z "$PK_WARN" ]; then
cat << 'SCH003_PASS'
#

SCH003_PASS
else
cat << 'SCH003_FILL'
#
# -- 입력 ---------------------------------------------------------------------

    WARN 항목 개선 예정                 : <<FILL: O/X>>
    비고                                : <<FILL>>  # 의도된 설계인 경우 예외 사유, 개선 예정일


SCH003_FILL
fi

# SCH-004
if [ "${UK_COUNT:-0}" -eq 0 ]; then
cat << 'SCH004_NOUK'
#
#
# ==============================================================================
# [AUR-SCH-004] 중복 체크 UK 또는 로직단 처리  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   UNIQUE 제약조건 없음
#
# -- 입력 ---------------------------------------------------------------------

    UK 없는 테이블의 중복 방지를 로직단에서 처리 : <<FILL: O/X>>
    비고                                         : <<FILL>>  # 처리 방식 설명, X인 경우 개선 계획


SCH004_NOUK
else
cat << 'SCH004_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-004] 중복 체크 UK 또는 로직단 처리  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH004_HEAD
echo "$SEC_UK" | awk -F'\t' '{printf "#   %-30s %-30s %s\n", $1, $2, $3}'
cat << 'SCH004_FILL'
#
# -- 입력 ---------------------------------------------------------------------

    UK 없는 테이블의 중복 방지를 로직단에서 처리 : <<FILL: O/X>>
    비고                                         : <<FILL>>  # 처리 방식 설명, X인 경우 개선 계획


SCH004_FILL
fi

# SCH-005
cat << 'SCH005_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-005] 인덱스 네이밍룰 준수  [severity: medium]
#
# 조직 네이밍 규칙에 맞지 않는 항목을 확인해주세요.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH005_HEAD
echo "$SEC_INDEX" | awk -F'\t' '{printf "#   %-30s %-30s %-40s %s\n", $1, $2, $3, $4}'
cat << 'SCH005_FILL'
#
# -- 입력 ---------------------------------------------------------------------

    네이밍룰 미준수 항목 없음 또는 개선 예정 : <<FILL: O/X>>
    비고                                    : <<FILL>>  # 미준수 항목명 및 예외 사유, 개선 예정일



#
#
# ==============================================================================
# END OF SURVEY
#
#
# ==============================================================================
SCH005_FILL

} > "$OUTPUT"

echo ""
echo "======================================================"
echo " 완료: $OUTPUT"
echo "======================================================"
echo ""
echo " 흰색(일반 텍스트) <<FILL>> 부분을 작성 후 ARB 담당자에게 전달해주세요."
echo ""
