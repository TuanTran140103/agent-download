"""
Paperless-ngx API Service
Handles document upload and authentication
"""

import base64
import httpx
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import PaperlessConfig
from models.paperless_models import (
    PaperlessAuthResponse,
    PaperlessUploadResponse,
    PaperlessTaskStatusResponse,
    PaperlessListResponse
)


class PaperlessService:
    """Service for interacting with Paperless-ngx API"""

    # MIME type mapping for common document formats
    MIME_TYPES = {
        # PDF
        '.pdf': 'application/pdf',
        # Microsoft Word
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        # Microsoft Excel
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        # Microsoft PowerPoint
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        # OpenDocument
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp',
        # Text
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.rtf': 'application/rtf',
        # HTML
        '.html': 'text/html',
        '.htm': 'text/html',
        # XML
        '.xml': 'application/xml',
        # JSON
        '.json': 'application/json',
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = None
    ):
        """
        Initialize Paperless service

        Args:
            base_url: Base URL of Paperless instance (e.g., https://paperless.example.com)
            username: Paperless username
            password: Paperless password
            api_token: Paperless API token (optional, overrides username/password)
            timeout: Request timeout in seconds
        """
        # Use config values if not provided
        self.base_url = (base_url or PaperlessConfig.BASE_URL).rstrip("/")
        self.username = username or PaperlessConfig.USERNAME
        self.password = password or PaperlessConfig.PASSWORD
        self.api_token = api_token or PaperlessConfig.API_TOKEN
        self.timeout = timeout if timeout is not None else PaperlessConfig.TIMEOUT
        self.verify_ssl = PaperlessConfig.VERIFY_SSL

        # Set up auth header (Token auth preferred, fallback to Basic Auth)
        if self.api_token:
            self.auth_header = f"Token {self.api_token}"
        else:
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.auth_header = f"Basic {encoded_credentials}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        return {
            "Authorization": self.auth_header,
        }

    @staticmethod
    def _get_mime_type(file_path: str) -> str:
        """
        Get MIME type based on file extension

        Args:
            file_path: Path to the file

        Returns:
            MIME type string (e.g., 'application/pdf')
        """
        import mimetypes

        # First try Python's built-in mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type:
            return mime_type

        # Fallback to our custom mapping
        ext = os.path.splitext(file_path)[1].lower()
        return PaperlessService.MIME_TYPES.get(ext, 'application/octet-stream')
    
    async def check_auth(self) -> PaperlessAuthResponse:
        """
        Check if authentication is valid

        Returns:
            PaperlessAuthResponse with auth status and user info
        """
        url = f"{self.base_url}/api/users/"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                # Debug info
                print(f"   Request URL: {url}")
                print(f"   Auth Header: {headers.get('Authorization', 'MISSING')}")
                
                response = await client.get(url, headers=headers)
                
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response.text[:200]}")

                if response.status_code == 200:
                    users_data = response.json()
                    # Get first user or current user info
                    if isinstance(users_data, list) and len(users_data) > 0:
                        user = users_data[0]
                        return PaperlessAuthResponse(
                            success=True,
                            authenticated=True,
                            user=user.get("username", "unknown"),
                            user_id=user.get("id"),
                            message="Authentication successful"
                        )
                    return PaperlessAuthResponse(
                        success=True,
                        authenticated=True,
                        user="unknown",
                        message="Authentication successful"
                    )
                elif response.status_code == 401:
                    return PaperlessAuthResponse(
                        success=False,
                        authenticated=False,
                        message="Invalid credentials"
                    )
                else:
                    return PaperlessAuthResponse(
                        success=False,
                        authenticated=False,
                        status_code=response.status_code,
                        message=f"Auth check failed: {response.text}"
                    )
        except httpx.RequestError as e:
            return PaperlessAuthResponse(
                success=False,
                authenticated=False,
                error=str(e),
                message=f"Connection error: {str(e)}"
            )
    
    async def upload_document(
        self,
        file_path: str,
        title: Optional[str] = None,
        created: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        storage_path_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        archive_serial_number: Optional[int] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaperlessUploadResponse:
        """
        Upload a document to Paperless

        Args:
            file_path: Path to the file to upload
            title: Optional document title
            created: Optional DateTime string (e.g., "2024-03-19" or "2024-03-19 10:30:00+07:00")
            correspondent_id: Optional correspondent ID
            document_type_id: Optional document type ID
            storage_path_id: Optional storage path ID
            tag_ids: Optional list of tag IDs
            archive_serial_number: Optional archive serial number
            custom_fields: Optional dict mapping field_id -> value
            metadata: Optional dict with extracted metadata (document_number, document_name, etc.)

        Returns:
            PaperlessUploadResponse with upload status and task UUID
        """
        url = f"{self.base_url}/api/documents/post_document/"

        if not os.path.exists(file_path):
            print(f"   ❌ File not found: {file_path}")
            return PaperlessUploadResponse(
                success=False,
                message="File not found",
                file_path=file_path
            )

        # Detect MIME type based on file extension
        mime_type = self._get_mime_type(file_path)
        print(f"   📋 Detected MIME type: {mime_type}")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    
                    # Debug: print first few bytes to see if it's actually a PDF
                    file_header = file_content[:32]
                    print(f"   🔢 File headers: {file_header!r}")
                    
                    # 🛡️ VALIDATION: Check if it's a real PDF when the extension says so
                    if mime_type == 'application/pdf' and not file_header.startswith(b'%PDF-'):
                        print(f"   ❌ ERROR: Downloaded file is HTML/Text, not a valid PDF!")
                        return {
                            "success": False,
                            "error": f"Downloaded file is invalid (received HTML/Text instead of PDF). It might be an error or preview page. Starts with: {file_header[:20]!r}",
                            "file_path": file_path
                        }
                    
                    # Sanitize filename for the multipart header to avoid issues with non-ASCII
                    # Paperless prefers the 'title' field anyway, or correctly handles the filename.
                    safe_filename = os.path.basename(file_path).encode('ascii', 'ignore').decode('ascii') or "document.pdf"
                    
                    files = {
                        "document": (safe_filename, file_content, mime_type)
                    }
                    
                    data = {}

                    if title:
                        data["title"] = title

                    if created:
                        data["created"] = created

                    if correspondent_id is not None:
                        data["correspondent"] = str(correspondent_id)

                    if document_type_id is not None:
                        data["document_type"] = str(document_type_id)

                    if storage_path_id is not None:
                        data["storage_path"] = str(storage_path_id)

                    if tag_ids:
                        # For multipart, we need to send tags as multiple fields
                        data["tags"] = [str(tid) for tid in tag_ids]

                    if archive_serial_number is not None:
                        data["archive_serial_number"] = str(archive_serial_number)

                    if custom_fields:
                        data["custom_fields"] = custom_fields

                    print(f"   📤 POST {url}")
                    print(f"   File: {file_path} ({len(file_content)} bytes)")
                    print(f"   Multipart Filename: {safe_filename}")
                    print(f"   Title: {title}")
                    print(f"   MIME Type: {mime_type}")

                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        files=files,
                        data=data if data else None
                    )

                    print(f"   Response status: {response.status_code}")
                    print(f"   Response body: {response.text[:500]}")

                if response.status_code == 200:
                    result = response.json()
                    print(f"   Upload response type: {type(result)}")
                    print(f"   Upload response: {result}")

                    # Handle both dict and string responses
                    if isinstance(result, dict):
                        task_uuid = result.get("uuid") or result.get("id")
                    elif isinstance(result, str):
                        task_uuid = result  # UUID returned as string
                    else:
                        task_uuid = str(result)

                    return {
                        "success": True,
                        "task_uuid": task_uuid,
                        "message": "Document upload started successfully",
                        "file_path": file_path,
                        "title": title,
                        "metadata": metadata  # Return metadata for later use
                    }
                else:
                    print(f"   ❌ Upload failed: {response.status_code}")
                    print(f"   Error response: {response.text}")
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text,
                        "file_path": file_path
                    }

        except httpx.RequestError as e:
            print(f"   ❌ Connection error: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    async def get_task_status(self, task_uuid: str) -> Dict[str, Any]:
        """
        Check the status of a consumption task

        Args:
            task_uuid: UUID of the consumption task

        Returns:
            Dict with task status and document ID if completed
        """
        url = f"{self.base_url}/api/tasks/"
        params = {"task_id": task_uuid}

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"   Task status response: {result}")
                    
                    # API returns a list, get the first item
                    if isinstance(result, list) and len(result) > 0:
                        task = result[0]
                    else:
                        task = result
                    
                    return {
                        "success": True,
                        "task": task
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_correspondents(self) -> Dict[str, Any]:
        """Get list of correspondents"""
        url = f"{self.base_url}/api/correspondents/"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}
    
    async def get_document_types(self) -> Dict[str, Any]:
        """Get list of document types"""
        url = f"{self.base_url}/api/document_types/"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}
    
    async def get_tags(self) -> Dict[str, Any]:
        """Get list of tags"""
        url = f"{self.base_url}/api/tags/"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}

    async def get_custom_fields(self) -> Dict[str, Any]:
        """
        Get list of all custom fields

        Returns:
            Dict with list of custom fields
        """
        url = f"{self.base_url}/api/custom_fields/"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}

    async def get_or_create_custom_fields(self, fields_config: Dict[str, str]) -> Dict[str, int]:
        """
        Get or create multiple custom fields and return mapping of name -> ID

        Args:
            fields_config: Dict mapping field_name -> data_type
                          e.g., {"document_number": "string", "issue_date": "date"}

        Returns:
            Dict mapping field_name -> field_id
        """
        # First, get all existing fields
        existing_fields_result = await self.get_custom_fields()
        existing_fields = {}
        
        if existing_fields_result.get('success'):
            fields_data = existing_fields_result.get('data', {})
            results = fields_data.get('results', [])
            
            # Build map of name -> id for existing fields
            for field in results:
                existing_fields[field.get('name')] = field.get('id')
        
        # Now check which fields need to be created
        field_ids = {}
        fields_to_create = []
        
        for field_name, data_type in fields_config.items():
            if field_name in existing_fields:
                print(f"   ℹ️ Found existing field '{field_name}' with ID {existing_fields[field_name]}")
                field_ids[field_name] = existing_fields[field_name]
            else:
                fields_to_create.append((field_name, data_type))
        
        # Create missing fields
        for field_name, data_type in fields_to_create:
            field_id = await self._create_custom_field(field_name, data_type)
            if field_id:
                field_ids[field_name] = field_id
        
        return field_ids

    async def _create_custom_field(self, name: str, data_type: str) -> int:
        """
        Create a new custom field

        Args:
            name: Field name
            data_type: Field data type (string, integer, boolean, date, url, document)

        Returns:
            Field ID
        """
        url = f"{self.base_url}/api/custom_fields/"
        create_data = {
            "name": name,
            "data_type": data_type
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=create_data
                )
                
                if response.status_code == 201:
                    field_id = response.json().get("id")
                    print(f"   ✅ Created new field '{name}' with ID {field_id}")
                    return field_id
                else:
                    print(f"   ⚠️ Could not create field '{name}': {response.status_code} - {response.text}")
                    return None
                    
        except httpx.RequestError as e:
            print(f"   ⚠️ Error creating field: {e}")
            return None

    async def update_document_custom_fields(
        self, 
        document_id: int, 
        field_ids: Dict[str, int], 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update document custom fields using field name -> ID mapping

        Args:
            document_id: Document ID
            field_ids: Dict mapping field_name -> field_id
            metadata: Dict mapping field_name -> value

        Returns:
            Dict with update status
        """
        # Build custom_fields array for API
        custom_fields_data = [
            {"field": field_ids[key], "value": value}
            for key, value in metadata.items()
            if key in field_ids
        ]
        
        if not custom_fields_data:
            return {
                "success": False,
                "error": "No valid custom fields to update"
            }
        
        print(f"   📝 Updating custom fields for document {document_id}...")
        print(f"   Custom fields data: {custom_fields_data}")
        
        # Use PATCH to update document
        return await self.update_document(document_id, custom_fields=custom_fields_data)

    async def upload_document_with_custom_fields(
        self,
        file_path: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        field_ids: Optional[Dict[str, int]] = None,
        wait_seconds: int = 5,
        max_retries: int = 5
    ) -> Dict[str, Any]:
        """
        Upload a document and add custom fields metadata.
        
        This is a high-level business logic method that:
        1. Uploads the document
        2. Waits for processing (with polling)
        3. Gets the document ID
        4. Updates custom fields with metadata

        Args:
            file_path: Path to file to upload
            title: Optional document title (defaults to filename)
            metadata: Dict mapping field_name -> value for custom fields
            field_ids: Dict mapping field_name -> field_id
            wait_seconds: Seconds to wait between polling
            max_retries: Maximum number of polling attempts

        Returns:
            Dict with upload result, document_id, and custom_fields_update status
        """
        import os
        
        filename = os.path.basename(file_path)
        doc_title = title or filename
        
        # Step 1: Upload document
        upload_result = await self.upload_document(
            file_path=file_path,
            title=doc_title
        )
        
        result = {
            "success": upload_result.get('success', False),
            "upload": upload_result,
            "document_id": None,
            "custom_fields_updated": False,
            "custom_fields_update": None
        }
        
        # Check if document already exists
        if not upload_result.get('success'):
            error_msg = upload_result.get('error', '')
            if 'already exists' in error_msg.lower():
                # Try to find existing document by title
                print(f"   ℹ️ Document already exists, searching for existing...")
                existing_doc_id = await self._find_document_by_title(doc_title)
                
                if existing_doc_id:
                    print(f"   ✅ Found existing document ID: {existing_doc_id}")
                    result["document_id"] = existing_doc_id
                    result["already_exists"] = True
                    result["success"] = True
                    
                    # Update custom fields for existing document
                    if metadata and field_ids:
                        update_result = await self.update_document_custom_fields(
                            existing_doc_id,
                            field_ids,
                            metadata
                        )
                        
                        result["custom_fields_updated"] = update_result.get('success', False)
                        result["custom_fields_update"] = update_result
                    else:
                        result["custom_fields_updated"] = True
                    
                    return result
            
            return result
        
        # Step 2: Poll for document ID (wait for processing)
        import asyncio
        document_id = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"   ⏳ Waiting {wait_seconds}s for processing (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_seconds)
            
            status_result = await self.get_task_status(upload_result['task_uuid'])
            
            if not status_result.get('success'):
                result["error"] = f"Could not get task status: {status_result.get('error')}"
                return result
            
            task = status_result.get('task', {})
            
            # Try to get document_id from multiple possible fields
            # Paperless returns it in different fields depending on version
            document_id = task.get('document_id') or task.get('related_document')
            
            # If still None, try to parse from result string
            if not document_id:
                result_str = task.get('result')
                if result_str and 'id' in result_str:
                    try:
                        # Parse "Success. New document id 6 created" -> 6
                        document_id = int(result_str.split('id ')[-1].split()[0])
                    except (ValueError, IndexError):
                        document_id = None
            
            # Convert to int if it's a string
            if document_id and isinstance(document_id, str):
                try:
                    document_id = int(document_id)
                except ValueError:
                    document_id = None
            
            if document_id:
                print(f"   ✅ Document processed successfully! ID: {document_id}")
                break
            else:
                task_status = task.get('status', 'unknown')
                print(f"   ⏳ Task status: {task_status}")
        
        if not document_id:
            result["error"] = f"Document not processed after {max_retries} attempts"
            return result
        
        result["document_id"] = document_id
        
        # Step 3: Update custom fields if metadata and field_ids provided
        if metadata and field_ids:
            # Send ALL fields to Paperless (including None values)
            # Paperless uses null to clear/reset field values
            update_result = await self.update_document_custom_fields(
                document_id,
                field_ids,
                metadata
            )
            
            result["custom_fields_updated"] = update_result.get('success', False)
            result["custom_fields_update"] = update_result
        else:
            result["custom_fields_updated"] = True  # No custom fields to update
        
        return result

    async def _find_document_by_title(self, title: str) -> Optional[int]:
        """
        Find existing document by title.
        
        Args:
            title: Document title to search for
        
        Returns:
            Document ID if found, None otherwise
        """
        url = f"{self.base_url}/api/documents/"
        params = {"title__icontains": title}
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results = result.get('results', [])
                    if results:
                        return results[0].get('id')
        except Exception:
            pass
        
        return None

    async def get_document(self, document_id: int) -> Dict[str, Any]:
        """
        Get document details by ID

        Args:
            document_id: Document ID

        Returns:
            Dict with document information
        """
        url = f"{self.base_url}/api/documents/{document_id}/"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.get(url, headers=self._get_headers())

                if response.status_code == 200:
                    return {
                        "success": True,
                        "document": response.json(),
                        "message": "Document retrieved successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get document: {response.status_code}",
                        "status_code": response.status_code
                    }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }

    async def add_note(self, document_id: int, note: str) -> Dict[str, Any]:
        """
        Add a note to a document

        Args:
            document_id: Document ID
            note: Note content

        Returns:
            Dict with note creation status
        """
        url = f"{self.base_url}/api/notes/"
        data = {
            "note": note,
            "document": document_id
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=data
                )

                if response.status_code == 201:
                    return {
                        "success": True,
                        "note": response.json(),
                        "message": "Note added successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to add note: {response.status_code}",
                        "status_code": response.status_code
                    }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }

    async def update_document(self, document_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update document fields

        Args:
            document_id: Document ID
            **kwargs: Fields to update (title, correspondent, document_type, tags, custom_fields, etc.)

        Returns:
            Dict with update status
        """
        url = f"{self.base_url}/api/documents/{document_id}/"

        # Get current document data first
        current_result = await self.get_document(document_id)
        if not current_result.get('success'):
            return current_result

        current_data = current_result.get('document', {})

        # Merge with new data
        update_data = {**current_data, **kwargs}

        # Remove fields that shouldn't be updated
        for key in ['notes', 'user_can_change', 'is_shared_by_requester', 'permissions', 'owner']:
            update_data.pop(key, None)

        print(f"   📝 PATCH request to: {url}")
        print(f"   Custom fields to update: {kwargs.get('custom_fields', [])}")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.patch(
                    url,
                    headers=self._get_headers(),
                    json=update_data
                )

                print(f"   Response status: {response.status_code}")
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "document": response.json(),
                        "message": "Document updated successfully"
                    }
                else:
                    # Log detailed error for debugging
                    print(f"   ❌ Error response: {response.status_code}")
                    print(f"   Response body: {response.text[:500]}")
                    
                    return {
                        "success": False,
                        "error": f"Failed to update document: {response.status_code} - {response.text}",
                        "status_code": response.status_code
                    }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }


# Convenience function for quick usage
async def test_paperless_connection(
    base_url: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """Test Paperless connection and auth"""
    service = PaperlessService(base_url, username, password)
    return await service.check_auth()
