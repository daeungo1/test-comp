#!/usr/bin/env bash
#
# Verify that embedded YAML blocks in service-guide.html match the authoritative
# YAML files under cloudformation/. Exits non-zero on any mismatch.
#
# Usage:
#   ./scripts/check-templates.sh
#
# Intended for local pre-commit checks.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

fail_count=0

for id in "${!TEMPLATE_MAP[@]}"; do
  yaml_path="${TEMPLATE_MAP[$id]}"
  yaml_name="$(basename "$yaml_path")"

  if [[ ! -f "$yaml_path" ]]; then
    echo "${C_RED}✗ Missing file: $yaml_path${C_RESET}" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  embedded="$(extract_embedded "$id")"
  source_content="$(cat "$yaml_path")"

  if [[ "$embedded" == "$source_content" ]]; then
    echo "${C_GREEN}✓${C_RESET} $yaml_name (id=$id) is in sync"
  else
    echo "${C_RED}✗${C_RESET} $yaml_name (id=$id) is OUT OF SYNC with service-guide.html"
    fail_count=$((fail_count + 1))
  fi
done

echo

if (( fail_count > 0 )); then
  cat >&2 <<EOF
${C_RED}Template sync check failed.${C_RESET}
${C_YELLOW}Run ${C_CYAN}./service-guide/scripts/sync-templates.sh${C_YELLOW} to update service-guide.html, then re-commit.${C_RESET}
EOF
  exit 1
fi

echo "${C_GREEN}All embedded templates are in sync.${C_RESET}"
