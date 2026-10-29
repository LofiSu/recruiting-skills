#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill="$root/SKILL.md"
template="$root/assets/report-template.html"
publishing="$root/references/publishing.md"
search="$root/references/search.md"
verify_all="$root/tests/verify-all.sh"

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
require "$template" '{{OVERVIEW_BODY}}' 'detailed overview token'
require "$template" '作者与公开联系路径' 'Chinese author section'
require "$template" '{{AUTHOR_ROWS}}' 'author rows token'
require "$search" 'Restricted-platform search' 'restricted platform search guidance'
require "$skill" 'references/publishing.md' 'publishing instructions'
require "$skill" 'gh-pages' 'dedicated Pages branch'
require "$publishing" '<arxiv-id>/index.html' 'stable report path'
require "$publishing" 'scripts/build_pages_index.py' 'Pages homepage generator'
require "$publishing" 'git add .nojekyll index.html "<arxiv-id>/index.html"' 'homepage staged with report'
require "$skill" 'collection homepage URL' 'homepage returned after publication'
require "$verify_all" 'python3 -m unittest tests.test_build_pages_index -v' 'homepage tests in full verification'
require "$root/README.md" 'https://github.com/LofiSu/recruiting-skills.git' 'current clone URL'
require "$root/README.md" 'cd recruiting-skills' 'clone directory name'
require "$root/LICENSE" 'MIT License' 'MIT license'
require "$root/.gitignore" 'outputs/' 'local report directory ignored'
require "$root/.github/workflows/ci.yml" 'bash tests/verify-all.sh' 'CI verification command'
require "$verify_all" 'scripts/validate_skill_frontmatter.py' 'portable frontmatter validator'

if grep -Fq 'https://github.com/LofiSu/researcher-recruiting-skill.git' "$root/README.md"; then
  printf 'FAIL: README still documents the pre-rename clone URL\n' >&2
  exit 1
fi

if grep -Fq '/Users/' "$verify_all"; then
  printf 'FAIL: verify-all.sh contains a machine-local path\n' >&2
  exit 1
fi

if grep -Eqi '<script|<link[^>]+stylesheet|url\([[:space:]]*["'"'"']?https?://' "$template"; then
  printf 'FAIL: template contains an external runtime or asset\n' >&2
  exit 1
fi

if grep -Eq 'SUMMARY_CARDS|class="cards"|class="card"|\\.cards|\\.card' "$template"; then
  printf 'FAIL: template contains removed summary-card UI\n' >&2
  exit 1
fi

printf 'PASS: standalone Skill contract verified\n'
