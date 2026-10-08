#!/usr/bin/env bash
# Common helpers for service-guide sync/check scripts.
# Not intended to be executed directly.

set -euo pipefail

# Resolve service-guide directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_GUIDE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HTML_FILE="$SERVICE_GUIDE_DIR/service-guide.html"
YAML_GLOBAL="$SERVICE_GUIDE_DIR/cloudformation/01-global.yaml"
YAML_REGIONAL="$SERVICE_GUIDE_DIR/cloudformation/02-regional.yaml"

# Map: html-id -> yaml-file
declare -A TEMPLATE_MAP=(
  [tpl-global]="$YAML_GLOBAL"
  [tpl-regional]="$YAML_REGIONAL"
)

# Extract the embedded YAML block matching the given id from service-guide.html.
# Outputs the content (without the leading newline) to stdout.
extract_embedded() {
  local id="$1"
  # Pattern: <script type="text/yaml" id="ID">...</script>
  # Print lines strictly between the opening tag and </script>.
  awk -v id="$id" '
    BEGIN { in_block = 0 }
    {
      if (!in_block) {
        # Match opening tag with the target id
        if ($0 ~ "<script[^>]*id=\"" id "\"[^>]*>") {
          in_block = 1
          next
        }
      } else {
        if ($0 ~ "</script>") {
          in_block = 0
          exit
        }
        print
      }
    }
  ' "$HTML_FILE"
}

# Pretty colors (fallback to empty if not a TTY).
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_CYAN=$'\033[36m'
  C_RESET=$'\033[0m'
else
  C_RED=""; C_GREEN=""; C_YELLOW=""; C_CYAN=""; C_RESET=""
fi
