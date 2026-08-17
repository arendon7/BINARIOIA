import json
import tempfile
import unittest
from pathlib import Path

from scripts import r27_mac_uat_evidence as uat


class R27MacUATEvidenceTests(unittest.TestCase):
    def test_normalize_arch(self):
        self.assertEqual(uat.normalize_arch("aarch64"), "arm64")
        self.assertEqual(uat.normalize_arch("arm64"), "arm64")
        self.assertEqual(uat.normalize_arch("x86_64"), "x86_64")

    def test_provenance_is_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="r27-evidence-") as td:
            root = Path(td)
            missing = uat.load_build_provenance(root)
            self.assertEqual(missing["status"], "FAIL")

            (root / "R27_UAT_BUILD.json").write_text(
                json.dumps({
                    "schema": "sbia-r27-uat-build-1.1",
                    "cycle": "R27",
                    "channel": "uat",
                    "source_sha": "a" * 40,
                    "baseline_sha256": "b" * 64,
                    "release_status": "UAT_ONLY_PENDING_PHYSICAL_MAC_SMOKE",
                }),
                encoding="utf-8",
            )
            ok = uat.load_build_provenance(root)
            self.assertEqual(ok["status"], "PASS")
            self.assertEqual(ok["source_sha"], "a" * 40)

    def test_project_storage_requires_real_project_structure(self):
        with tempfile.TemporaryDirectory(prefix="r27-projects-") as td:
            root = Path(td)
            empty = uat.project_storage_check(root)
            self.assertEqual(empty["status"], "PENDING")

            project = root / "prj-demo"
            project.mkdir()
            for name in uat.REQUIRED_PROJECT_DIRS:
                (project / name).mkdir()
            ready = uat.project_storage_check(root)
            self.assertEqual(ready["status"], "PASS")
            self.assertEqual(ready["complete_project_count"], 1)

    def test_summary_never_claims_uat_pass_with_manual_pending(self):
        checks = [{"name": "x", "status": "PASS"}]
        manual = [{"id": "m", "status": "PENDING", "step": "manual"}]
        self.assertEqual(uat.summarize(checks, manual), "PRECHECK_PASS_MANUAL_PENDING")
        checks.append({"name": "bad", "status": "FAIL"})
        self.assertEqual(uat.summarize(checks, manual), "PRECHECK_FAIL")

    def test_report_markdown_contains_release_rule(self):
        report = {
            "generated_at": "2026-08-17T00:00:00+00:00",
            "overall": "PRECHECK_PASS_MANUAL_PENDING",
            "root": "/tmp/r27",
            "checks": [{"name": "build_provenance", "status": "PASS"}],
            "manual_steps": [{"id": "video_real_render", "status": "PENDING", "step": "render"}],
        }
        text = uat.render_markdown(report)
        self.assertIn("PRECHECK_PASS_MANUAL_PENDING", text)
        self.assertIn(".release-blocked", text)
        self.assertIn("video_real_render", text)

    def test_builder_compiles_and_packages_evidence_command(self):
        repo = Path(__file__).resolve().parents[1]
        builder = repo / "scripts" / "build_r27_uat.py"
        source = builder.read_text(encoding="utf-8")
        compile(source, str(builder), "exec")
        self.assertIn("EJECUTAR_UAT_R27_MAC.command", source)
        self.assertIn("r27_mac_uat_evidence.py", source)


if __name__ == "__main__":
    unittest.main()
