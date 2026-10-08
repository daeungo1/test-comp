#!/usr/bin/env bash
#
# Synchronize embedded YAML blocks in service-guide.html with the authoritative
# YAML files under cloudformation/.
#
# Usage:
#   ./scripts/sync-templates.sh          # Apply changes
#   ./scripts/sync-templates.sh --check  # Dry-run; delegate to check-templates.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

if [[ "${1:-}" == "--check" ]]; then
  exec "$(dirname "${BASH_SOURCE[0]}")/check-templates.sh"
fi

# Replace the block between <script ... id="ID"> and </script> with file contents.
# Uses a Python one-liner for safe multiline replace (pure bash/sed struggles here).
replace_block() {
  local id="$1"
  local yaml_path="$2"

  python3 - "$HTML_FILE" "$id" "$yaml_path" <<'PY'
import re, sys, io

html_path, block_id, yaml_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(yaml_path, 'r', encoding='utf-8') as f:
    yaml_content = f.read()

# Ensure exactly one trailing newline for the embedded block body.
yaml_body = yaml_content.rstrip('\n') + '\n'

pattern = re.compile(
    r'(<script[^>]*id="' + re.escape(block_id) + r'"[^>]*>)\n.*?\n(</script>)',
    re.DOTALL,
)

new_block = r'\1' + '\n' + yaml_body + r'\2'
new_html, count = pattern.subn(new_block, html, count=1)

if count == 0:
    sys.stderr.write(f'ERROR: script block with id="{block_id}" not found in {html_path}\n')
    sys.exit(2)

if new_html == html:
    print(f'  (unchanged) {block_id}')
    sys.exit(0)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f'  updated     {block_id} <- {yaml_path}')
PY
}

echo "${C_CYAN}Syncing embedded templates in service-guide.html ...${C_RESET}"
for id in "${!TEMPLATE_MAP[@]}"; do
  yaml_path="${TEMPLATE_MAP[$id]}"
  if [[ ! -f "$yaml_path" ]]; then
    echo "${C_RED}✗ Missing source file: $yaml_path${C_RESET}" >&2
    exit 1
  fi
  replace_block "$id" "$yaml_path"
done

echo
echo "${C_GREEN}Done.${C_RESET}"
echo "Review the change:  ${C_CYAN}git diff -- service-guide/service-guide.html${C_RESET}"
