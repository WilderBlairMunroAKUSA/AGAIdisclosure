#!/usr/bin/env bash
# tree_to_readme.sh
# Runs `tree -L 3 --charset=C` and writes output to README.md,
# replacing each entry (file or directory) with an HTML anchor link,
# wrapped in <pre> so tree structure is preserved and links are clickable.

set -euo pipefail

OUTPUT="README.md"

if ! command -v tree &>/dev/null; then
  echo "Error: 'tree' is not installed." >&2
  exit 1
fi

IFS=$'\n' read -r -d '' -a LINES <<< "$(tree -L 3 -F --charset=C --noreport)"$'\0' || true

DIR_STACK[0]="."   # root

{
  echo "<pre>"

  # First line is always the root dir — emit as-is
  echo "${LINES[0]}"

  for (( i=1; i<${#LINES[@]}; i++ )); do
    line="${LINES[$i]}"

    # Skip any entry marked as private
    [[ "$line" == *🔒* ]] && continue

    # Isolate the prefix: everything before the first name character.
    prefix="${line%%[^|\ \`\-]*}"
    depth=$(( ${#prefix} / 4 ))

    # The raw entry is everything after the prefix (e.g. "file.txt" or "dir/")
    raw="${line#"$prefix"}"

    # Strip any trailing tree -F classifier (/ * @ = | >)
    name="${raw%%[/\*@=>|]}"

    # Rebuild the relative path from the directory stack
    rel_path="."
    for (( d=1; d<depth; d++ )); do
      rel_path="$rel_path/${DIR_STACK[$d]}"
    done
    rel_path="$rel_path/$name"

    if [[ "$raw" == */ ]]; then
      # Directory — emit as an HTML anchor, then record in stack for children
      html_link="<a href=\"$rel_path\">$name</a>"
      echo "${prefix}${html_link}/"
      DIR_STACK[$depth]="$name"
      for (( d=depth+1; d<${#DIR_STACK[@]}; d++ )); do
        unset "DIR_STACK[$d]"
      done
    else
      # File — emit as an HTML anchor
      html_link="<a href=\"$rel_path\">$name</a>"
      echo "${prefix}${html_link}"
    fi
  done

  echo "</pre>"
} > "$OUTPUT"

echo "✓ Written to $OUTPUT"
