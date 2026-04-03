#!/usr/bin/env bash
# tree_to_readme.sh
# Runs `tree -L 3 --charset=C` and writes output to README.md,
# replacing each entry (file or directory) with a relative markdown link,
# using the tree structure itself to reconstruct accurate relative paths.

set -euo pipefail

OUTPUT="README.md"

if ! command -v tree &>/dev/null; then
  echo "Error: 'tree' is not installed." >&2
  exit 1
fi

# --charset=C gives us clean ASCII box-drawing: |, `-- , |--
# -F appends '/' to directories so we can distinguish them from files.
# --noreport suppresses the "N directories, M files" summary line.
#
# We read into an array without mapfile (bash 3 compatible).
IFS=$'\n' read -r -d '' -a LINES <<< "$(tree -L 3 -F --charset=C --noreport)"$'\0' || true

# With --charset=C, each depth level adds exactly 4 characters of prefix:
#   "|   "  — vertical continuation
#   "|-- "  — branch
#   "`-- "  — last branch
#   "    "  — blank continuation
#
# Depth = (length of prefix before the entry name) / 4

DIR_STACK[0]="."   # root

{
  # First line is always the root dir — emit as-is (it's the working dir itself)
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
      # Directory — emit as a markdown link, then record in stack for children
      md_link="[$name]($rel_path)"
      echo "${line/"$raw"/$md_link/}"
      DIR_STACK[$depth]="$name"
      for (( d=depth+1; d<${#DIR_STACK[@]}; d++ )); do
        unset "DIR_STACK[$d]"
      done
    else
      # File — emit as a markdown link
      md_link="[$name]($rel_path)"
      echo "${line/"$raw"/$md_link}"
    fi
  done
} > "$OUTPUT"

echo "✓ Written to $OUTPUT"
