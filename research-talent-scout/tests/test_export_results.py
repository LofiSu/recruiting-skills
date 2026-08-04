import unittest

from scripts.export_results import render_markdown


class ExportTests(unittest.TestCase):
    def test_render_includes_sections_evidence_papers_coverage_and_warnings(self):
        result = {
            "generated_at": "2026-08-04T00:00:00+00:00",
            "confirmed": [{
                "candidate_id": "candidate-1",
                "name": "Alice | Example",
                "degree": "phd",
                "institution": "Example University",
                "lab": "AI Lab",
                "graduation_year": 2027,
                "graduation_state": "confirmed",
                "qualifying_count": 6,
                "counts_by_category": {"main_first": 5, "co_first": 1},
                "qualifying_publications": [{
                    "title": "Paper One", "normalized_venue": "ACL", "year": 2026,
                    "category": "main_first", "url": "https://papers.example/1",
                }],
                "evidence": [{
                    "field": "graduation_year", "state": "confirmed",
                    "source_type": "personal_cv", "url": "https://example.edu/cv.pdf",
                    "excerpt": "Expected | graduation: 2027", "retrieved_at": "2026-08-04",
                }],
                "verified_at": "2026-08-04",
            }],
            "likely_needs_verification": [],
            "coverage": [{"scope": "Example University", "last_verified_at": "2026-08-04", "gaps": ""}],
            "warnings": ["Coverage is partial."],
        }
        markdown = render_markdown(result)
        self.assertIn("## 已确认", markdown)
        self.assertIn("## 高概率待确认", markdown)
        self.assertIn("Alice \\| Example", markdown)
        self.assertIn("[Paper One](https://papers.example/1)", markdown)
        self.assertIn("[Expected \\| graduation: 2027](https://example.edu/cv.pdf)", markdown)
        self.assertIn("Example University", markdown)
        self.assertIn("Coverage is partial.", markdown)

    def test_all_candidate_rows_appear_before_candidate_details(self):
        base = {
            "degree": "phd", "institution": "U", "lab": "L",
            "graduation_year": 2027, "graduation_state": "confirmed",
            "qualifying_count": 1, "counts_by_category": {"main_first": 1},
            "qualifying_publications": [], "evidence": [], "verified_at": "2026-08-04",
        }
        result = {
            "generated_at": "2026-08-04", "likely_needs_verification": [],
            "coverage": [], "warnings": [],
            "confirmed": [
                {**base, "candidate_id": "a", "name": "Alice"},
                {**base, "candidate_id": "b", "name": "Bob"},
            ],
        }
        markdown = render_markdown(result)
        self.assertLess(markdown.index("| Bob |"), markdown.index("**Alice 的符合论文**"))


if __name__ == "__main__":
    unittest.main()
