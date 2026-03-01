"""Cloud Storage service for reading, uploading, and signing GCS objects."""

from __future__ import annotations

import datetime
import json
from pathlib import PurePosixPath

from google.cloud import storage

from app.config.settings import settings


class StorageService:
    """Thin wrapper around ``google.cloud.storage`` scoped to one bucket."""

    def __init__(self) -> None:
        self._client = storage.Client(project=settings.GCP_PROJECT_ID)
        self._bucket = self._client.bucket(settings.CLOUD_STORAGE_BUCKET)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_blob_name(gcs_url: str) -> str:
        """Parse ``gs://bucket/path/to/file`` and return ``path/to/file``."""
        if not gcs_url.startswith("gs://"):
            raise ValueError(f"Not a valid gs:// URL: {gcs_url}")
        # Remove the "gs://" prefix, then strip the bucket name.
        without_scheme = gcs_url[len("gs://"):]
        # The first path segment is the bucket name.
        parts = without_scheme.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            raise ValueError(f"No object path found in URL: {gcs_url}")
        return parts[1]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_pdf_bytes(self, gcs_url: str, timeout: int = 300) -> bytes:
        """Download the raw bytes of a PDF stored at *gcs_url* (``gs://...``).

        Parameters
        ----------
        timeout:
            Download timeout in seconds.  Default 300s (5 min) to handle
            large files (50-130 MB) over slower connections.
        """
        blob_name = self._parse_blob_name(gcs_url)
        blob = self._bucket.blob(blob_name)
        return blob.download_as_bytes(timeout=timeout)

    def upload_json(self, path: str, data: dict | list) -> str:
        """Serialize *data* as JSON and upload it to *path* inside the bucket.

        Parameters
        ----------
        path:
            Object path inside the bucket (e.g. ``results/output.json``).
        data:
            JSON-serialisable ``dict`` or ``list``.

        Returns
        -------
        str
            The ``gs://`` URL of the uploaded object.
        """
        blob = self._bucket.blob(path)
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        return f"gs://{settings.CLOUD_STORAGE_BUCKET}/{path}"

    def generate_signed_url(
        self,
        gcs_url: str,
        expiry_minutes: int | None = None,
    ) -> str:
        """Return a v4 signed URL granting temporary read access to the object.

        Parameters
        ----------
        gcs_url:
            Full ``gs://`` URL of the object.
        expiry_minutes:
            Lifetime of the signed URL in minutes.  Falls back to
            ``settings.SIGNED_URL_EXPIRY_MINUTES`` (default 15).
        """
        if expiry_minutes is None:
            expiry_minutes = settings.SIGNED_URL_EXPIRY_MINUTES

        blob_name = self._parse_blob_name(gcs_url)
        blob = self._bucket.blob(blob_name)
        url: str = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiry_minutes),
            method="GET",
        )
        return url

    @staticmethod
    def get_doc_id_from_url(gcs_url: str) -> str:
        """Extract the document ID (filename without extension) from a ``gs://`` URL.

        Example::

            gs://my-bucket/document_042.pdf  ->  document_042
        """
        blob_name = StorageService._parse_blob_name(gcs_url)
        return PurePosixPath(blob_name).stem

    def get_pdf_url(self, doc_id: str) -> str:
        """Build a ``gs://`` URL for a PDF stored at the bucket top level.

        Assumes the naming convention ``<doc_id>.pdf``.
        """
        return f"gs://{settings.CLOUD_STORAGE_BUCKET}/{doc_id}.pdf"


# Module-level singleton
storage_service = StorageService()
