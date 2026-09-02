import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ModuleEmbedContractTests(unittest.TestCase):
    def test_manifest_embed_and_paper_only(self):
        manifest = json.loads((ROOT / "inneros.module.json").read_text())
        self.assertEqual(manifest["schema_version"], "inneros.module.v1")
        self.assertEqual(manifest["module_id"], "alpha.trading.alpaca")
        self.assertTrue(manifest["security"]["paper_only"])
        self.assertFalse(manifest["security"]["real_money_allowed"])
        self.assertTrue(manifest["security"]["auth_required_when_embedded"])
        self.assertTrue(manifest["security"]["console_never_submits_fills"])
        self.assertEqual(manifest["security"]["embed_post_message"], "inneros.module.ready")
        self.assertEqual(manifest["entrypoints"]["health"], "/health")
        self.assertIn("embed", manifest["routes"]["embed_query"])
        self.assertIn("require_gateway", manifest["routes"]["embed_query"])

    def test_console_never_posts_execute(self):
        client = (ROOT / "apps/console/api-client.js").read_text()
        console = (ROOT / "apps/console/console.js").read_text()
        self.assertIn("execute=false", client)
        self.assertIn("console_never_submits_fills", client)
        self.assertNotIn("/api/execute", console)
        self.assertIn("execute=false", console)


if __name__ == "__main__":
    unittest.main()
