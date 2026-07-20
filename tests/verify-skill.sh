#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill="$root/SKILL.md"
template="$root/assets/report-template.html"
publishing="$root/references/publishing.md"

require() {
  file=$1
  pattern=$2
  label=$3
  if ! grep -Fq -- "$pattern" "$file"; then
    printf 'FAIL: %s\n' "$label" >&2
    exit 1
  fi
}

require "$template" '--paper: #f7f7f5' 'article paper token'
require "$template" 'class="doc"' 'article document shell'
require "$template" 'class="doc-header"' 'article header'
require "$template" 'class="tldr"' 'TLDR block'
require "$template" '<span class="num">01</span>' 'numbered section'
require "$template" '作者与公开联系路径' 'Chinese author section'
require "$template" '{{AUTHOR_ROWS}}' 'author rows token'
require "$skill" 'references/publishing.md' 'publishing instructions'
require "$skill" 'gh-pages' 'dedicated Pages branch'
require "$publishing" '<arxiv-id>/index.html' 'stable report path'

if grep -Eqi '<script|<link[^>]+stylesheet|url\([[:space:]]*["'"'"']?https?://' "$template"; then
  printf 'FAIL: template contains an external runtime or asset\n' >&2
  exit 1
fi

printf 'PASS: standalone Skill contract verified\n'
