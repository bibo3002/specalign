import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import tempfile
import unittest
from pathlib import Path

from fixture import Repo
from specalign import inventory
from specalign.inventory import Endpoint, code_endpoints, norm_path, spec_endpoints

ROUTES = """export function register(app) {
  app.get('/api/things/:thingId', async () => 1)
  app.post("/api/things", async () => 1)
  app.delete(`/api/things/:id`, async () => 1)
  api.get('/api/frontend/call')          // a client call, not a registration
}
"""


def spec_with(section6: str, section5: str = "tables `things`") -> str:
    return ("# SPEC-F1 — T\n\n## §0 Card\n\n| Field | Value |\n|---|---|\n| Feature | F1 — T |\n| Status | Approved |\n"
            "| Version | v1.0.0 |\n| Tag | spec/F1-t-v1.0.0 |\n| Sources | `server/routes/things.ts` |\n\n"
            f"## §5 Data\n\n{section5}\n\n## §6 API\n\n{section6}\n\n## §7 Frontend\n\nx\n")


class ParsingTests(unittest.TestCase):
    def test_path_normalisation(self):
        self.assertEqual(norm_path("/a/:id/b/{x}/<y>/?q=1"), "/a/:p/b/:p/:p")
        self.assertEqual(norm_path("/"), "/")

    def test_code_endpoints_ignore_client_calls(self):
        eps = {str(e) for e, _ in code_endpoints(ROUTES)}
        self.assertEqual(eps, {"GET /api/things/:p", "POST /api/things", "DELETE /api/things/:p"})

    def test_python_decorators(self):
        eps = {str(e) for e, _ in code_endpoints('@router.get("/x/{id}")\n@bp.route("/y", methods=["POST", "PUT"])\n')}
        self.assertEqual(eps, {"GET /x/:p", "POST /y", "PUT /y"})

    def test_spec_endpoints_handle_ellipsis_escaped_pipes_and_removed_routes(self):
        text = spec_with("| `GET /api/things/:id` | x |\n| `POST …/:partyId/lawyers` | y |\n"
                         "~~`GET /api/old`~~ removed\n| `PUT \\| DELETE /api/z` | z |")
        eps = spec_endpoints(text)
        self.assertIn(Endpoint("GET", "/api/things/:p"), eps)
        lawyers = [e for e in eps if e.path.endswith("/lawyers")][0]
        self.assertTrue(lawyers.elided)
        self.assertNotIn(Endpoint("GET", "/api/old"), eps)

    def test_removed_context_does_not_leak_across_lines(self):
        eps = spec_endpoints(spec_with("This was removed in v1.\n| `GET /api/live` | ok |"))
        self.assertIn(Endpoint("GET", "/api/live"), eps)


class RepoTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.write("server/routes/things.ts", ROUTES + "const q = 'select * from things join owners on 1=1'\n")

    def run_inv(self, section6, section5="tables `things`", tables=("things", "owners")):
        self.repo.write("docs/specs/SPEC-F1-t.md", spec_with(section6, section5))
        self.repo.commit("spec")
        with tempfile.TemporaryDirectory() as td:
            tf = Path(td) / "tables.json"
            tf.write_text(json.dumps(list(tables)), encoding="utf-8")
            return inventory.run_inventory(self.repo.path, tables_file=tf)["features"][0]

    FULL = "| `GET /api/things/:thingId` | a |\n| `POST /api/things` | b |\n| `DELETE /api/things/:id` | c |"

    def test_documented_feature_is_clean_except_for_the_unnamed_table(self):
        f = self.run_inv(self.FULL)
        self.assertEqual((f["undocumented"], f["missing_in_code"]), ([], []))
        self.assertEqual(f["tables_undocumented"], ["owners"])

    def test_undocumented_and_missing_endpoints(self):
        f = self.run_inv("| `GET /api/things/:id` | a |\n| `POST /api/things` | b |\n| `GET /api/gone` | c |")
        self.assertEqual(len(f["undocumented"]), 1)
        self.assertIn("DELETE /api/things/:p", f["undocumented"][0])
        self.assertIn("server/routes/things.ts:4", f["undocumented"][0])
        self.assertEqual(f["missing_in_code"], ["GET /api/gone"])

    def test_route_documented_by_another_spec_is_not_a_gap(self):
        self.repo.write("docs/specs/SPEC-F2-other.md",
                        spec_with("| `DELETE /api/things/:id` | c |").replace("F1", "F2").replace("things.ts", "other.ts"))
        f = self.run_inv("| `GET /api/things/:id` | a |\n| `POST /api/things` | b |")
        self.assertEqual(f["undocumented"], [])

    def test_spec_route_served_by_a_dynamic_route_exists(self):
        self.repo.write("server/routes/lookups.ts", "const list = (p) => app.get(`/api/lookups/${p}`, h)\n")
        f = self.run_inv(self.FULL + "\n| `GET /api/lookups/governorates` | d |")
        self.assertEqual(f["missing_in_code"], [])

    def test_tables_check_is_optional(self):
        self.repo.write("docs/specs/SPEC-F1-t.md", spec_with(self.FULL))
        self.repo.commit("spec")
        out = inventory.run_inventory(self.repo.path)
        self.assertFalse(out["tables_checked"])
        self.assertNotIn("tables_undocumented", out["features"][0])


if __name__ == "__main__":
    unittest.main()
