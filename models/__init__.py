"""
Models package
"""

from .paperless_models import (
    PaperlessAuthRequest,
    PaperlessUploadRequest,
    PaperlessTaskStatusRequest,
    PaperlessAuthResponse,
    PaperlessUploadResponse,
    PaperlessTaskStatusResponse,
    PaperlessListResponse
)

__all__ = [
    "PaperlessAuthRequest",
    "PaperlessUploadRequest",
    "PaperlessTaskStatusRequest",
    "PaperlessAuthResponse",
    "PaperlessUploadResponse",
    "PaperlessTaskStatusResponse",
    "PaperlessListResponse"
]
