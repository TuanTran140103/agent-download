"""
Pydantic models for Paperless-ngx API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PaperlessAuthRequest(BaseModel):
    """Request model for Paperless authentication"""
    base_url: str = Field(..., description="Base URL of Paperless instance")
    username: str = Field(..., description="Paperless username")
    password: str = Field(..., description="Paperless password")


class PaperlessUploadRequest(BaseModel):
    """Request model for uploading document to Paperless"""
    base_url: str = Field(..., description="Base URL of Paperless instance")
    username: str = Field(..., description="Paperless username")
    password: str = Field(..., description="Paperless password")
    file_path: str = Field(..., description="Path to the file to upload")
    title: Optional[str] = Field(None, description="Document title")
    created: Optional[str] = Field(None, description="Document creation DateTime")
    correspondent_id: Optional[int] = Field(None, description="Correspondent ID")
    document_type_id: Optional[int] = Field(None, description="Document type ID")
    storage_path_id: Optional[int] = Field(None, description="Storage path ID")
    tag_ids: Optional[List[int]] = Field(None, description="List of tag IDs")
    archive_serial_number: Optional[int] = Field(None, description="Archive serial number")
    custom_fields: Optional[Dict[int, Any]] = Field(None, description="Custom fields mapping")


class PaperlessTaskStatusRequest(BaseModel):
    """Request model for checking task status"""
    base_url: str = Field(..., description="Base URL of Paperless instance")
    username: str = Field(..., description="Paperless username")
    password: str = Field(..., description="Paperless password")
    task_uuid: str = Field(..., description="UUID of the consumption task")


class PaperlessAuthResponse(BaseModel):
    """Response model for authentication check"""
    success: bool
    authenticated: bool
    message: str
    user: Optional[str] = None
    user_id: Optional[int] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


class PaperlessUploadResponse(BaseModel):
    """Response model for document upload"""
    success: bool
    task_uuid: Optional[str] = None
    message: str
    file_path: Optional[str] = None
    title: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


class PaperlessTaskStatusResponse(BaseModel):
    """Response model for task status check"""
    success: bool
    task: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PaperlessListResponse(BaseModel):
    """Response model for list endpoints (correspondents, document types, tags)"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
