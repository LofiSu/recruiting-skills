#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

cd "$repo_root"
bash tests/verify-skill.sh
python3 -m unittest tests.test_build_pages_index -v
python3 /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .

cd "$repo_root/research-talent-scout"
python3 -m unittest discover -s tests -v
python3 /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .

echo "PASS: both collaborating Skills verified"
