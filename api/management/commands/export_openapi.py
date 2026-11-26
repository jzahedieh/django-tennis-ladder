import json
from pathlib import Path

from django.core.management.base import BaseCommand

from api.api import api


class Command(BaseCommand):
    help = "Export the Django Ninja OpenAPI 3.1 schema as JSON without running a server."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output",
            default="",
            help="Optional file path to write the OpenAPI JSON schema (prints to stdout if omitted).",
        )

    def handle(self, *args, **options):
        schema = api.get_openapi_schema()
        serialized = json.dumps(schema, indent=2) + "\n"
        output_path = (options.get("output") or "").strip()

        if output_path:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(serialized, encoding="utf-8")
            self.stdout.write(
                self.style.SUCCESS(f"Exported OpenAPI schema to {target}")
            )
        else:
            self.stdout.write(serialized)
