#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
validator="$repo_root/scripts/validate_skill_frontmatter.py"

cd "$repo_root"
bash tests/verify-skill.sh
python3 -m unittest tests.test_build_pages_index -v
python3 -m unittest tests.test_demo_report -v
python3 -m unittest tests.test_validate_skill_frontmatter -v
python3 "$validator" "$repo_root"

cd "$repo_root/research-talent-scout"
python3 -m unittest discover -s tests -v
python3 "$validator" "$repo_root/research-talent-scout"

echo "PASS: both collaborating Skills verified"
