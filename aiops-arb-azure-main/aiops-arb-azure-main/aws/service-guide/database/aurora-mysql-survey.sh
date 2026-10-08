#!/bin/bash
# =============================================================================
# Aurora MySQL ARB Pre-Survey Script
# ARB 담당자가 개발팀에 전달하는 사전 조사 스크립트입니다.
#
# [개발팀 실행 방법]
#   chmod +x aurora-mysql-survey.sh
#   ./aurora-mysql-survey.sh
#
# [실행 결과]
#   aurora-mysql-survey-<CLUSTER_ID>-<DATE>.md 파일이 생성됩니다.
#   흰색(일반 텍스트) 부분만 작성 후 ARB 담당자에게 전달해주세요.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# [TEST] 테스트용 변수 직접 선언 - 배포 시 이 블록 삭제
# -----------------------------------------------------------------------------
# CLUSTER_ID="my-cluster"
# DB_HOST="my-cluster.xxxx.ap-northeast-2.rds.amazonaws.com"
# DB_PORT="3306"
# DB_USER="admin"
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
echo " Aurora MySQL ARB Pre-Survey"
echo "======================================================"
echo ""

[ -z "$CLUSTER_ID" ] && read -rp "클러스터 식별자 (예: my-service-aurora-cluster): " CLUSTER_ID
[ -z "$DB_HOST"    ] && read -rp "호스트 (Writer endpoint):                        " DB_HOST
[ -z "$DB_PORT"    ] && read -rp "포트 (기본 3306):                                " DB_PORT
DB_PORT=${DB_PORT:-3306}
[ -z "$DB_USER"    ] && read -rp "읽기 전용 계정 (예: arb_readonly):               " DB_USER
[ -z "$DB_PASS"    ] && { read -rsp "비밀번호:                                        " DB_PASS; echo ""; }
[ -z "$DB_NAME"    ] && read -rp "대상 데이터베이스(스키마) 이름:                  " DB_NAME
# -----------------------------------------------------------------------------

# 필수값 검증
for var in CLUSTER_ID DB_HOST DB_PORT DB_USER DB_PASS DB_NAME; do
    if [ -z "${!var}" ]; then
        echo "[ERROR] 필수 값이 없습니다: $var"
        exit 1
    fi
done

GENERATED=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date '+%Y%m%d')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${SCRIPT_DIR}/aurora-mysql-survey-${CLUSTER_ID}-${DATE}.md"
TMPFILE=$(mktemp /tmp/arb-survey-XXXXXX.tsv)
SQLFILE=$(mktemp /tmp/arb-survey-XXXXXX.sql)
trap 'rm -f "$TMPFILE" "$SQLFILE"' EXIT

export MYSQL_PWD="$DB_PASS"

# -----------------------------------------------------------------------------
# 접속 확인
# -----------------------------------------------------------------------------
echo ""
echo "DB 접속 확인 중..."
CONN_ERR=$(mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
           --batch --skip-column-names -e "SELECT 1" "$DB_NAME" 2>&1 >/dev/null || true)
if [ -n "$CONN_ERR" ]; then
    echo "[ERROR] DB 접속에 실패했습니다."
    echo "        원인: $CONN_ERR"
    echo "        확인: 호스트(${DB_HOST}:${DB_PORT}), 계정(${DB_USER}), DB(${DB_NAME}), 네트워크/보안그룹"
    exit 1
fi
echo "접속 성공. 데이터 수집 중..."

# -----------------------------------------------------------------------------
# 단일 세션, --batch로 모든 데이터 수집
# 섹션 구분자: --SECTION--
# -----------------------------------------------------------------------------
SQLFILE=$(mktemp /tmp/arb-survey-XXXXXX.sql)
trap 'rm -f "$TMPFILE" "$SQLFILE"' EXIT

cat > "$SQLFILE" << ENDSQL
-- [1] admin(기본 마스터) 계정 존재 여부
SELECT COUNT(*) FROM mysql.user WHERE user = 'admin';
SELECT '--SECTION--';

-- [2] 전체 계정 목록
SELECT user, host, plugin FROM mysql.user
WHERE user NOT IN ('mysql.sys','mysql.session','mysql.infoschema')
ORDER BY user;
SELECT '--SECTION--';

-- [3] 계정별 권한
SELECT CONCAT(
    'GRANT ',
    GROUP_CONCAT(PRIVILEGE_TYPE ORDER BY PRIVILEGE_TYPE SEPARATOR ', '),
    ' ON \`', TABLE_SCHEMA, '\`.* TO ', GRANTEE,
    IF(MAX(IS_GRANTABLE)='YES', ' WITH GRANT OPTION', ''))
FROM information_schema.SCHEMA_PRIVILEGES
WHERE GRANTEE NOT LIKE "'mysql.%'@'%'"
GROUP BY GRANTEE, TABLE_SCHEMA
UNION ALL
SELECT CONCAT(
    'GRANT ',
    GROUP_CONCAT(PRIVILEGE_TYPE ORDER BY PRIVILEGE_TYPE SEPARATOR ', '),
    ' ON *.* TO ', GRANTEE,
    IF(MAX(IS_GRANTABLE)='YES', ' WITH GRANT OPTION', ''))
FROM information_schema.USER_PRIVILEGES
WHERE GRANTEE NOT LIKE "'mysql.%'@'%'"
  AND PRIVILEGE_TYPE != 'USAGE'
GROUP BY GRANTEE
ORDER BY 1;
SELECT '--SECTION--';

-- [4] FK 목록
SELECT kcu.TABLE_NAME, rc.CONSTRAINT_NAME, rc.REFERENCED_TABLE_NAME
FROM information_schema.REFERENTIAL_CONSTRAINTS rc
JOIN information_schema.KEY_COLUMN_USAGE kcu
  ON rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
 AND rc.CONSTRAINT_NAME   = kcu.CONSTRAINT_NAME
WHERE rc.CONSTRAINT_SCHEMA = '${DB_NAME}'
GROUP BY kcu.TABLE_NAME, rc.CONSTRAINT_NAME, rc.REFERENCED_TABLE_NAME
ORDER BY kcu.TABLE_NAME;
SELECT '--SECTION--';

-- [5] Routine 목록
SELECT ROUTINE_NAME, ROUTINE_TYPE, DATE_FORMAT(CREATED,'%Y-%m-%d')
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = '${DB_NAME}'
ORDER BY ROUTINE_TYPE, ROUTINE_NAME;
SELECT '--SECTION--';

-- [6] PK 컬럼 현황
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE,
       IF(EXTRA LIKE '%auto_increment%', 'YES', 'NO'),
       IF(DATA_TYPE IN ('int','bigint') AND EXTRA LIKE '%auto_increment%', 'OK', 'WARN')
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = '${DB_NAME}'
  AND COLUMN_KEY = 'PRI'
ORDER BY TABLE_NAME;
SELECT '--SECTION--';

-- [7] UK 목록
SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME,
       GROUP_CONCAT(kcu.COLUMN_NAME ORDER BY kcu.ORDINAL_POSITION)
FROM information_schema.TABLE_CONSTRAINTS tc
JOIN information_schema.KEY_COLUMN_USAGE kcu
  ON tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
 AND tc.TABLE_NAME   = kcu.TABLE_NAME
 AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_TYPE = 'UNIQUE'
  AND tc.TABLE_SCHEMA = '${DB_NAME}'
GROUP BY tc.TABLE_NAME, tc.CONSTRAINT_NAME
ORDER BY tc.TABLE_NAME;
SELECT '--SECTION--';

-- [8] 인덱스 목록 (PK 제외)
SELECT TABLE_NAME, INDEX_NAME,
       GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX),
       IF(NON_UNIQUE = 0, 'UNIQUE', 'INDEX')
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = '${DB_NAME}'
  AND INDEX_NAME != 'PRIMARY'
GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE
ORDER BY TABLE_NAME, INDEX_NAME;
ENDSQL

mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
      --batch --skip-column-names "$DB_NAME" \
      < "$SQLFILE" > "$TMPFILE" 2>&1 || { echo "[ERROR] 데이터 수집 중 오류:"; cat "$TMPFILE"; exit 1; }

echo "수집 완료. 파일 생성 중: $OUTPUT"

# -----------------------------------------------------------------------------
# 섹션별 파싱 (--SECTION-- 탭 구분 텍스트 기준)
# -----------------------------------------------------------------------------
parse_section() {
    local n=$1
    awk -v n="$n" 'BEGIN{sec=0} /^--SECTION--/{sec++; next} sec==n-1{print}' "$TMPFILE"
}

SEC_ROOT=$(parse_section 1)
SEC_ACCOUNTS=$(parse_section 2)
SEC_GRANTS=$(parse_section 3)
SEC_FK=$(parse_section 4)
SEC_ROUTINES=$(parse_section 5)
SEC_PK=$(parse_section 6)
SEC_UK=$(parse_section 7)
SEC_INDEX=$(parse_section 8)

ADMIN_COUNT=$(echo "$SEC_ROOT" | tr -d '[:space:]')
FK_COUNT=$(echo "$SEC_FK" | grep -c '.' || true)
ROUTINE_COUNT=$(echo "$SEC_ROUTINES" | grep -c '.' || true)
UK_COUNT=$(echo "$SEC_UK" | grep -c '.' || true)
PK_WARN=$(echo "$SEC_PK" | awk -F'\t' '$5=="WARN"' || true)

if [ "${ADMIN_COUNT:-0}" -eq 0 ] 2>/dev/null; then
    ACC003_RESULT="PASS"
    ACC003_MSG="admin 계정 없음"
else
    ACC003_RESULT="FAIL"
    ACC003_MSG="admin 계정이 존재합니다 -- 기본 마스터 계정 미사용 조치 필요"
fi

# -----------------------------------------------------------------------------
# 계정 목록 추출 (입력란 생성용)
# -----------------------------------------------------------------------------
ACCOUNT_LINES=$(echo "$SEC_ACCOUNTS" | awk -F'\t' '{print $1}' | grep -v '^$' || true)

# =============================================================================
# MD 파일 생성
# =============================================================================
{

cat << HEADER
# Aurora MySQL ARB Pre-Survey
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

echo "# -- 계정 목록 (user / host / plugin) --"
echo "$SEC_ACCOUNTS" | awk -F'\t' '{printf "#   %-30s %-15s %s\n", $1, $2, $3}' 
echo "#"
echo "# -- 계정별 권한 --"
while IFS= read -r line; do
    [ -z "$line" ] && continue
    echo "# $line"
done <<< "$SEC_GRANTS"
echo "#"
echo "# -- 입력 ---------------------------------------------------------------"
echo "# 형식: ACCOUNT | SERVICE/DBA/PERSONAL/SYSTEM | 권한적절 O/X | 비고"
echo ""

# AWS RDS 내부 시스템 계정 목록
SYSTEM_ACCOUNTS="rdsadmin rdsrepladmin rdsproxy rds_superuser_role"

while IFS= read -r user; do
    [ -z "$user" ] && continue
    if echo "$SYSTEM_ACCOUNTS" | grep -qw "$user"; then
        printf "ACCOUNT : %-20s | SYSTEM               | O            | AWS RDS 내부 시스템 계정\n" "$user"
    else
        printf "ACCOUNT : %-20s | <<FILL: SERVICE/DBA/PERSONAL>> | <<FILL: O/X>> | <<FILL: 비고>>\n" "$user"
    fi
done <<< "$ACCOUNT_LINES"

printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-002] 개인 사용자 계정 1인 1계정 원칙  [severity: high]\n'
printf '#\n'
printf '# 개인 사용자 계정이 1인 1계정으로 발급되었는지 확인해주세요. (공용 계정 사용 금지)\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    개인 계정 공용 사용 없음 : <<FILL: O/X>\n'
printf '    비고                     : <<FILL>>  # 공용 계정이 있는 경우 해당 계정명 및 사유\n'
printf '\n\n'

# ACC-003 (자동 판별)
if [ "${ROOT_COUNT:-0}" -eq 0 ] && [ "${ADMIN_COUNT:-0}" -eq 0 ] 2>/dev/null; then
cat << ACC003
#
#
# ==============================================================================
# [AUR-ACC-003] 기본 마스터(admin) 계정 미사용  [severity: critical]
#
# Aurora MySQL 생성 시 기본 마스터 계정(admin)은 서비스/운영에 직접 사용하지 않아야 합니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   admin 계정 존재 여부 : ${ACC003_MSG}
#

    admin 계정 미사용 : O

ACC003
else
cat << ACC003
#
#
# ==============================================================================
# [AUR-ACC-003] 기본 마스터(admin) 계정 미사용  [severity: critical]
#
# Aurora MySQL 생성 시 기본 마스터 계정(admin)은 서비스/운영에 직접 사용하지 않아야 합니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   admin 계정 존재 여부 : ${ACC003_MSG}
#

    admin 계정 미사용 : X
    비고              : <<FILL>>  # admin 계정 교체 예정일 및 조치 계획

ACC003
fi

printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-005] DB 계정 관리 DBA 담당  [severity: medium]\n'
printf '#\n'
printf '# DB 계정 생성/변경/삭제 업무를 DBA가 담당하고 있는지 확인해주세요.\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    DBA가 계정 관리 담당 : <<FILL: O/X>\n'
printf '    비고                 : <<FILL>>  # DBA가 아닌 경우 실제 담당자/팀 명시\n'
printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-006] DB 계정 신규/변경/삭제 프로세스  [severity: medium]\n'
printf '#\n'
printf '# DB 계정 관리 프로세스(문서)가 존재하는지 확인해주세요.\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    계정 관리 프로세스 문서 존재 : <<FILL: O/X>\n'
printf '    비고                         : <<FILL>>  # 문서 위치/링크, 없는 경우 작성 예정일\n'
printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-007] DB 계정 권한 리스트 문서 관리  [severity: medium]\n'
printf '#\n'
printf '# 계정 권한 현황 문서가 최신 상태로 유지되고 있는지 확인해주세요.\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    권한 현황 문서 최신 유지 : <<FILL: O/X>\n'
printf '    비고                     : <<FILL>>  # 최종 갱신일, 미유지 시 갱신 예정일\n'
printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-008] DB 계정 내역 5년 보관  [severity: medium]\n'
printf '#\n'
printf '# 계정 신규/변경/삭제 내역(결재 문서)을 5년간 보관하고 있는지 확인해주세요.\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    계정 내역 5년 보관 중 : <<FILL: O/X>\n'
printf '    비고                  : <<FILL>>  # 보관 위치/방식, 미보관 시 조치 예정일\n'
printf '\n\n'

printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-ACC-009] Instance Name Rule 준수  [severity: medium]\n'
printf '#\n'
printf '# -- 자동 조회 결과 -----------------------------------------------------------\n'
printf '#   클러스터 식별자 : %s\n' "${CLUSTER_ID}"
printf '#\n'
printf '# 위 식별자가 조직 네이밍 규칙을 준수하는지 확인해주세요.\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    네이밍 규칙 준수 : <<FILL: O/X>\n'
printf '    비고             : <<FILL>>  # 미준수 시 사유 및 개선 예정일\n'
printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# SECTION 2. Schema Design\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '\n'

# SCH-001
if [ "${FK_COUNT:-0}" -eq 0 ]; then
cat << 'SCH001_PASS'
#
#
# ==============================================================================
# [AUR-SCH-001] FK 미사용 설계  [severity: high]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   FK 사용 테이블 : 없음
#

    FK 미사용 : O

SCH001_PASS
else
cat << 'SCH001_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-001] FK 미사용 설계  [severity: high]
#
# FK가 존재합니다. 의도된 설계인지 확인해주세요.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH001_HEAD
echo "$SEC_FK" | awk -F'\t' '{printf "#   TABLE: %-30s CONSTRAINT: %-30s REF: %s\n", $1, $2, $3}'
printf '#\n# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    FK 사용이 의도된 설계인가 : <<FILL: O/X>\n'
printf '    비고                      : <<FILL>>  # 의도된 경우 설계 사유, 미의도 시 제거 예정일\n'
printf '\n\n'
fi

# SCH-002
if [ "${ROUTINE_COUNT:-0}" -eq 0 ]; then
cat << 'SCH002_PASS'
#
#
# ==============================================================================
# [AUR-SCH-002] Procedure 제약사항 확인  [severity: medium]
#
# -- 자동 조회 결과 -----------------------------------------------------------
#   등록된 Routine : 없음
#

    Procedure 미사용 : O

SCH002_PASS
else
cat << 'SCH002_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-002] Procedure 제약사항 확인  [severity: medium]
#
# Routine이 존재합니다. 제약사항을 검토하였는지 확인해주세요.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH002_HEAD
echo "$SEC_ROUTINES" | awk -F'\t' '{printf "#   %-40s %-12s %s\n", $1, $2, $3}'
printf '#\n# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    제약사항 검토 완료 : <<FILL: O/X>\n'
printf '    비고               : <<FILL>>  # 미검토 시 예정일, 검토 결과 이슈 사항\n'
printf '\n\n'
fi

# SCH-003
cat << 'SCH003_HEAD'
#
#
# ==============================================================================
# [AUR-SCH-003] 테이블 PK Autoincrement int/bigint 사용  [severity: high]
#
# STATUS=WARN 항목은 int/bigint + AUTO_INCREMENT 조건 미충족입니다.
#
# -- 자동 조회 결과 -----------------------------------------------------------
SCH003_HEAD
echo "$SEC_PK" | awk -F'\t' '{printf "#   %-30s %-20s %-10s AUTO_INC=%-5s %s\n", $1, $2, $3, $4, $5}'

if [ -z "$PK_WARN" ]; then
cat << 'SCH003_PASS'
#

    PK 규칙 준수 : O

SCH003_PASS
else
printf '#\n# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    WARN 항목 개선 예정 : <<FILL: O/X>\n'
printf '    비고                : <<FILL>>  # 의도된 설계인 경우 예외 사유, 개선 예정일\n'
printf '\n\n'
fi

# SCH-004
if [ "${UK_COUNT:-0}" -eq 0 ]; then
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# [AUR-SCH-004] 중복 체크 UK 또는 로직단 처리  [severity: medium]\n'
printf '#\n'
printf '# -- 자동 조회 결과 -----------------------------------------------------------\n'
printf '#   UK 없음\n'
printf '#\n'
printf '# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    UK 없는 테이블의 중복 방지를 로직단에서 처리 : <<FILL: O/X>\n'
printf '    비고                                         : <<FILL>>  # 처리 방식 설명, X인 경우 개선 계획\n'
printf '\n\n'
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
printf '#\n# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    UK 없는 테이블의 중복 방지를 로직단에서 처리 : <<FILL: O/X>\n'
printf '    비고                                         : <<FILL>>  # 처리 방식 설명, X인 경우 개선 계획\n'
printf '\n\n'
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
echo "$SEC_INDEX" | awk -F'\t' '{printf "#   %-30s %-30s %-30s %s\n", $1, $2, $3, $4}'
printf '#\n# -- 입력 ---------------------------------------------------------------\n'
printf '\n'
printf '    네이밍룰 미준수 항목 없음 또는 개선 예정 : <<FILL: O/X>\n'
printf '    비고                                    : <<FILL>>  # 미준수 항목명 및 예외 사유, 개선 예정일\n'
printf '\n\n\n'
printf '#\n#\n'
printf '# ==============================================================================\n'
printf '# END OF SURVEY\n'
printf '#\n#\n'
printf '# ==============================================================================\n'

} > "$OUTPUT"

echo ""
echo "======================================================"
echo " 완료: $OUTPUT"
echo "======================================================"
echo ""
echo " 흰색(일반 텍스트) <<FILL>> 부분을 작성 후 ARB 담당자에게 전달해주세요."
echo ""
