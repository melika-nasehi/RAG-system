from django.conf import settings
from django.db import models


class Document(models.Model):
    """One entry per PDF accepted into the corpus. The `source` filename is
    the join key to everything else — chunk records, Chroma metadata, and
    the file on disk in data/raw/ — matching how the ingestion pipeline
    already identifies a document everywhere else."""

    source = models.CharField(max_length=255, unique=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    verdict = models.CharField(max_length=20)  # "ACCEPT" | "REPAIR"
    chunk_count = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.source
