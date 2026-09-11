"""Backfill Document rows for sources that exist in the chunk file but have
no row yet — i.e. everything ingested before the Document model existed.

Usage:
    python manage.py backfill_documents            # apply
    python manage.py backfill_documents --dry-run   # preview only

Safe to re-run: sources that already have a Document row are skipped
(update_or_create on `source`, same idempotency rule ingest_pdf itself uses).
"""

import json
from collections import defaultdict

from django.core.management.base import BaseCommand

from api.models import Document
from core.ingestion.pipeline import CHUNKS_DIR
from core.retrieval.retriever import DEFAULT_COLLECTION


class Command(BaseCommand):
    help = "Create Document rows for sources present in the chunk file but missing from the DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection",
            default=DEFAULT_COLLECTION,
            help="Collection name whose chunk file to read (default: %(default)s).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing to the DB.",
        )

    def handle(self, *args, **options):
        collection_name = options["collection"]
        dry_run = options["dry_run"]

        path = CHUNKS_DIR / f"{collection_name}.jsonl"
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Chunk file not found: {path}"))
            return

        # Group chunk rows by source: chunk_count, page_count (distinct
        # pages seen), and whether any chunk in the source needed digit
        # repair.
        per_source = defaultdict(lambda: {"chunks": 0, "pages": set(), "digits_repaired": False})

        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                info = per_source[row["source"]]
                info["chunks"] += 1
                if "page" in row and row["page"] is not None:
                    info["pages"].add(row["page"])
                if row.get("digits_repaired"):
                    info["digits_repaired"] = True

        existing = set(Document.objects.values_list("source", flat=True))
        missing = {s: info for s, info in per_source.items() if s not in existing}

        if not missing:
            self.stdout.write(self.style.SUCCESS("Nothing to backfill — every source already has a Document row."))
            return

        for source, info in missing.items():
            page_count = len(info["pages"]) or None
            self.stdout.write(
                f"{'[dry-run] ' if dry_run else ''}{source}: "
                f"chunks={info['chunks']} pages={page_count}"
            )
            if not dry_run:
                # verdict is unknown for pre-existing documents (it was never
                # stored before this model existed) — "ACCEPT" is the
                # honest default since only accepted files ever reached the
                # chunk file in the first place; digits_repaired tags the
                # repaired case where relevant, but the model has no
                # separate field for it, so verdict stays "ACCEPT" either
                # way and chunk_count/page_count carry the real signal.
                Document.objects.update_or_create(
                    source=source,
                    defaults={
                        "uploaded_by": None,
                        "verdict": "ACCEPT",
                        "chunk_count": info["chunks"],
                        "page_count": page_count,
                    },
                )

        verb = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"{verb} {len(missing)} Document row(s)."))