import re
import unittest

from scripts.render_demo_report import AUTHORS, DEFAULT_OUTPUT, render_demo_report


class DemoReportTests(unittest.TestCase):
    def test_committed_demo_matches_the_renderer_and_omits_email(self):
        rendered = render_demo_report()
        self.assertEqual(DEFAULT_OUTPUT.read_text(encoding="utf-8"), rendered)
        body = rendered.split("</style>", 1)[1]
        self.assertNotIn("{{", rendered)
        self.assertNotIn("mailto:", rendered)
        self.assertNotIn("@", body)
        self.assertIsNone(
            re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", rendered)
        )
        self.assertNotIn("<script", rendered.lower())
        self.assertIn("Attention Is All You Need", rendered)
        self.assertIn("演示样本 · DEMO", rendered)
        self.assertIn("https://arxiv.org/abs/1706.03762", rendered)
        self.assertIn("https://arxiv.org/html/1706.03762", rendered)
        self.assertIn('rel="noreferrer noopener"', rendered)
        self.assertIn("暂未找到", rendered)
        for name, institution in AUTHORS:
            self.assertIn(name, rendered)
            self.assertIn(institution, rendered)
        self.assertLess(
            rendered.index("Ashish Vaswani"),
            rendered.index("Illia Polosukhin"),
        )


if __name__ == "__main__":
    unittest.main()
