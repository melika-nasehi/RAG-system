"""Admin-only corpus management.

Uploading a document runs it through the same validate -> chunk -> index
pipeline the offline process uses (core.ingestion.pipeline), so a file
accepted here is indexed identically to one added by hand. Rejected files
never touch the store.

The ingest call is synchronous and embeds every chunk through Ollama, so the
request can take tens of seconds for a large PDF. That is acceptable for a
low-frequency admin action; moving it to a background worker is a later
concern.

A `Document` row is the one thing the ingestion pipeline itself doesn't
track (it only knows chunks and vectors, not "who uploaded this and when") —
it exists purely so this list/download/delete surface has something to
query and reference by a stable id.
"""

import tempfile
from pathlib import Path

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.ingestion.pipeline import RAW_DIR, ingest_pdf, remove_document
from core.ingestion.validation import validate_pdf

from .models import Document


class DocumentUploadView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """Every document currently in the corpus, newest first."""
        return Response(
            [
                {
                    "id": doc.id,
                    "source": doc.source,
                    "uploaded_at": doc.uploaded_at,
                    "uploaded_by": doc.uploaded_by.username if doc.uploaded_by else None,
                    "verdict": doc.verdict,
                    "chunk_count": doc.chunk_count,
                    "page_count": doc.page_count,
                }
                for doc in Document.objects.all()
            ]
        )

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "فایلی ارسال نشده است."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not upload.name.lower().endswith(".pdf"):
            return Response(
                {"detail": "تنها فایل PDF پذیرفته می‌شود.", "accepted": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate from a temp copy first; only a file that passes is kept.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            for chunk in upload.chunks():
                handle.write(chunk)
            temp_path = Path(handle.name)

        try:
            verdict = validate_pdf(temp_path)
            if not verdict.accepted:
                return Response(
                    {
                        "accepted": False,
                        "source": upload.name,
                        "reason": verdict.reason,
                        "verdict": verdict.verdict,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            RAW_DIR.mkdir(parents=True, exist_ok=True)
            destination = RAW_DIR / Path(upload.name).name
            destination.write_bytes(temp_path.read_bytes())

            result = ingest_pdf(destination)
        finally:
            temp_path.unlink(missing_ok=True)

        if not result.accepted:
            destination.unlink(missing_ok=True)
            return Response(
                {"accepted": False, "source": result.source, "reason": result.reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # update_or_create: re-uploading a source that's already indexed
        # (ingest_pdf is idempotent on chunk ids) replaces its record rather
        # than violating the source's unique constraint.
        document, _ = Document.objects.update_or_create(
            source=result.source,
            defaults={
                "uploaded_by": request.user,
                "verdict": verdict.verdict,
                "chunk_count": result.chunks_total,
                "page_count": (verdict.stats or {}).get("pages"),
            },
        )

        return Response(
            {
                "accepted": True,
                "id": document.id,
                "source": result.source,
                "reason": result.reason,
                "chunks_added": result.chunks_added,
                "chunks_total": result.chunks_total,
                "digits_repaired": result.digits_repaired,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    """GET downloads the original PDF; DELETE removes the document from
    every place it's indexed. Both 404 the same way for a missing id, same
    pattern as chat's conversation-detail view."""

    permission_classes = [IsAdminUser]

    def get(self, request, document_id):
        document = _get_or_404(document_id)
        pdf_path = RAW_DIR / document.source
        if not pdf_path.exists():
            return Response(
                {"detail": "فایل روی دیسک یافت نشد."}, status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            pdf_path.open("rb"), as_attachment=True, filename=document.source
        )

    def delete(self, request, document_id):
        document = _get_or_404(document_id)
        source = document.source

        remove_document(source)  # dense index, sparse index, chunk file
        (RAW_DIR / source).unlink(missing_ok=True)
        document.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_or_404(document_id):
    return get_object_or_404(Document, id=document_id)
