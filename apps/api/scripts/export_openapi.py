from __future__ import annotations

import argparse
import json
from pathlib import Path

from apt_hunter.main import app


def render_contract() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify the APT Hunter OpenAPI contract")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "docs" / "openapi.json",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_contract()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"OpenAPI contract is stale: regenerate {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
