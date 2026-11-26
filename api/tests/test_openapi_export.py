import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase


class ExportOpenApiTests(TestCase):
    def test_export_openapi_command_outputs_valid_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "openapi.json"
            call_command("export_openapi", output=str(out_file))

            self.assertTrue(out_file.exists())
            schema = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertTrue(schema["openapi"].startswith("3.1"))

            paths = schema["paths"]
            self.assertIn("/v1/auth/login", paths)
            self.assertIn("/v1/ladder/seasons/current/overview", paths)
            self.assertIn("/v1/players/search/", paths)
            self.assertIn("/v1/account/", paths)
