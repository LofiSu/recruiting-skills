from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_pages_index import discover_reports, render_index, write_index


class BuildPagesIndexTests(unittest.TestCase):
    def test_discovers_only_safe_report_directories_in_sorted_order(self):
        with TemporaryDirectory() as temporary_directory:
            pages_dir = Path(temporary_directory)
            for report_id in ("2502.00002v2", "2401.00001"):
                report_dir = pages_dir / report_id
                report_dir.mkdir()
                (report_dir / "index.html").write_text("report", encoding="utf-8")

            hidden = pages_dir / ".hidden"
            hidden.mkdir()
            (hidden / "index.html").write_text("hidden", encoding="utf-8")
            (pages_dir / "missing-index").mkdir()
            (pages_dir / "notes.txt").write_text("notes", encoding="utf-8")

            self.assertEqual(
                discover_reports(pages_dir),
                ["2401.00001", "2502.00002v2"],
            )

    def test_renders_installation_first_home_with_report_links(self):
        rendered = render_index(["2401.00001", "2502.00002v2"])

        self.assertIn("researcher-recruiting-skill", rendered)
        self.assertIn("research-talent-scout", rendered)
        self.assertLess(rendered.index("安装与使用"), rendered.index("已发布报告"))
        self.assertIn('href="2401.00001/"', rendered)
        self.assertIn('href="2502.00002v2/"', rendered)

    def test_renders_empty_state_without_reports(self):
        rendered = render_index([])

        self.assertIn("暂无已发布报告", rendered)

    def test_escapes_report_identifiers_before_rendering(self):
        rendered = render_index(['2401.00001&quot; onclick=&quot;alert(1)'])

        self.assertNotIn('onclick="alert(1)', rendered)
        self.assertIn("&amp;quot;", rendered)

    def test_writes_index_without_modifying_existing_reports(self):
        with TemporaryDirectory() as temporary_directory:
            pages_dir = Path(temporary_directory)
            report = pages_dir / "2401.00001" / "index.html"
            report.parent.mkdir()
            report.write_text("original report", encoding="utf-8")

            output = write_index(pages_dir)

            self.assertEqual(output, pages_dir / "index.html")
            self.assertTrue(output.is_file())
            self.assertEqual(report.read_text(encoding="utf-8"), "original report")


if __name__ == "__main__":
    unittest.main()
