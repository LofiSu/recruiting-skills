from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.validate_skill_frontmatter import main, validate_skill


ROOT = Path(__file__).resolve().parents[1]


def write_skill(directory: Path, frontmatter: str, body: str = "# Skill\n") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n{body}",
        encoding="utf-8",
    )


class ValidateSkillFrontmatterTests(unittest.TestCase):
    def test_repository_skills_are_valid(self):
        for skill_dir in (ROOT, ROOT / "research-talent-scout"):
            valid, message = validate_skill(skill_dir)
            self.assertTrue(valid, f"{skill_dir}: {message}")

    def test_rejects_missing_skill_file(self):
        with TemporaryDirectory() as temporary_directory:
            valid, message = validate_skill(Path(temporary_directory))
            self.assertFalse(valid)
            self.assertEqual(message, "SKILL.md not found")

    def test_rejects_invalid_name_unexpected_key_and_angle_brackets(self):
        with TemporaryDirectory() as temporary_directory:
            skill_dir = Path(temporary_directory)
            write_skill(skill_dir, "description: Find authors\n")
            valid, message = validate_skill(skill_dir)
            self.assertFalse(valid)
            self.assertIn("Missing 'name'", message)

            write_skill(
                skill_dir,
                "name: Researcher_Recruiting\ndescription: Find authors\n",
            )
            valid, message = validate_skill(skill_dir)
            self.assertFalse(valid)
            self.assertIn("kebab-case", message)

            write_skill(
                skill_dir,
                "name: researcher-recruiting-skill\n"
                "description: Find <authors>\n",
            )
            valid, message = validate_skill(skill_dir)
            self.assertFalse(valid)
            self.assertIn("angle brackets", message)

            write_skill(
                skill_dir,
                "name: researcher-recruiting-skill\n"
                "description: Find authors\n"
                "version: 1\n",
            )
            valid, message = validate_skill(skill_dir)
            self.assertFalse(valid)
            self.assertIn("Unexpected key", message)

    def test_cli_accepts_repository_root(self):
        self.assertEqual(main([str(ROOT)]), 0)

    def test_cli_rejects_a_directory_without_usage(self):
        self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
