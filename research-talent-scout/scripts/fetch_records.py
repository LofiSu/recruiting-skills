#!/usr/bin/env python3
"""Fetch public OpenAlex or Semantic Scholar metadata into talent-scout JSONL.

The output is suitable for ``import_records.py``. Rows keep ``graduation_state``
as ``unknown``. ``--degree`` is an index label supplied by the caller, not an
API fact. The client never asks for or stores email addresses.

Examples:

    python3 scripts/fetch_records.py \
      --source openalex --venue NeurIPS --year 2024 --degree phd \
      --output data/openalex.jsonl

    python3 scripts/fetch_records.py \
      --source semanticscholar --author-id 1234567 --degree phd \
      --output data/s2.jsonl

Environment:

    OPENALEX_API_KEY   optional here, required for real OpenAlex use
    S2_API_KEY         optional Semantic Scholar key (x-api-key)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.connectors.http import ConnectorError, JsonClient, UrllibTransport
    from scripts.connectors.openalex import fetch_openalex
    from scripts.connectors.semanticscholar import fetch_semanticscholar
except ModuleNotFoundError:
    from connectors.http import ConnectorError, JsonClient, UrllibTransport
    from connectors.openalex import fetch_openalex
    from connectors.semanticscholar import fetch_semanticscholar


OPENALEX_DELAY = 0.2
SEMANTIC_SCHOLAR_DELAY = 1.1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch OpenAlex or Semantic Scholar records into talent-scout JSONL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Keys are read from the environment, not from argv. "
            "OPENALEX_API_KEY is sent as a bearer token. "
            "S2_API_KEY is sent as x-api-key. "
            "Default pauses: OpenAlex 0.2s, Semantic Scholar 1.1s."
        ),
    )
    parser.add_argument("--source", required=True, choices=("openalex", "semanticscholar"))
    parser.add_argument("--venue", help="Supported conference short name, for example NeurIPS")
    parser.add_argument("--year", type=int, help="Publication year. Required with --venue.")
    parser.add_argument("--author", help="Author name search. Results are not merged by name.")
    parser.add_argument("--author-id", help="Stable source author id, with or without its URL")
    parser.add_argument("--degree", required=True, choices=("phd", "masters"))
    parser.add_argument(
        "--graduation-year",
        type=int,
        help="Optional caller label. Stored with graduation_state unknown, never confirmed.",
    )
    parser.add_argument("--output", required=True, help="JSONL path to write")
    parser.add_argument("--max-works", type=int, default=25)
    parser.add_argument("--max-authors", type=int, default=3)
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds between HTTP calls. Default 0.2 for OpenAlex and 1.1 for Semantic Scholar.",
    )
    parser.add_argument("--retrieved-at", help="ISO date stored on the records. Default: today, UTC.")
    return parser


def run(
    args: argparse.Namespace,
    client: JsonClient | None = None,
    api_key_present: bool | None = None,
) -> dict:
    retrieved_at = args.retrieved_at or datetime.now(timezone.utc).date().isoformat()
    if args.year is not None and not 1900 <= args.year <= 2100:
        raise ValueError("--year is out of range")
    if args.graduation_year is not None and not 1900 <= args.graduation_year <= 2100:
        raise ValueError("--graduation-year is out of range")
    if client is None:
        api_key_present, client = _live_client(args)
    elif api_key_present is None:
        api_key_present = False
    common = dict(
        degree=args.degree,
        retrieved_at=retrieved_at,
        api_key_present=api_key_present,
        venue=args.venue,
        year=args.year,
        author=args.author,
        author_id=args.author_id,
        graduation_year=args.graduation_year,
        max_works=args.max_works,
        max_authors=args.max_authors,
    )
    if args.source == "openalex":
        records, warnings = fetch_openalex(client, **common)
    else:
        records, warnings = fetch_semanticscholar(client, **common)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    output.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
    publications = sum(len(record["publications"]) for record in records)
    return {
        "source": args.source,
        "records": len(records),
        "publications": publications,
        "output": str(output),
        "warnings": warnings,
    }


def _live_client(args: argparse.Namespace) -> tuple:
    if args.source == "openalex":
        secret = os.environ.get("OPENALEX_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        default_delay = OPENALEX_DELAY
    else:
        secret = os.environ.get("S2_API_KEY", "").strip()
        headers = {"x-api-key": secret} if secret else {}
        default_delay = SEMANTIC_SCHOLAR_DELAY
    live = JsonClient(
        UrllibTransport(),
        delay=default_delay if args.delay is None else args.delay,
        default_headers=headers,
        secrets=(secret,),
    )
    return bool(secret), live


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run(args)
    except (ConnectorError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
