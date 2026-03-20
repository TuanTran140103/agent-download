"""
Script test độc lập cho PaperlessService upload

Usage:
    python test_paperless_upload.py

Hoặc chỉ định file cụ thể:
    python test_paperless_upload.py path/to/your/file.pdf
"""
import asyncio
import os
import sys
from pathlib import Path
from services.paperless_service import PaperlessService
from helpers.paperless_helper import PaperlessMetadataHelper

# Import DocumentGeneralInformation từ agent_runner
try:
    from agent_runner import DocumentGeneralInformation
    # Set model class cho helper
    PaperlessMetadataHelper.set_metadata_model(DocumentGeneralInformation)
except ImportError:
    print("⚠️ Could not import DocumentGeneralInformation, using default schema")
    DocumentGeneralInformation = None


async def test_upload(file_path: str):
    """Test upload file lên Paperless-ngx"""

    print("=" * 60)
    print("🧪 PAPERLESS-NGX UPLOAD TEST")
    print("=" * 60)

    # 1. Kiểm tra file tồn tại
    if not os.path.exists(file_path):
        print(f"\n❌ File not found: {file_path}")
        print("\n💡 Available files in downloads/:")
        downloads_dir = "downloads"
        if os.path.exists(downloads_dir):
            for f in os.listdir(downloads_dir):
                print(f"   - {f}")
        return

    file_size = os.path.getsize(file_path)
    print(f"\n📁 File: {file_path}")
    print(f"📏 Size: {file_size:,} bytes")

    # 2. Khởi tạo service
    print("\n🔧 Initializing PaperlessService...")
    service = PaperlessService()
    print(f"   Base URL: {service.base_url}")
    print(f"   Username: {service.username}")
    print(f"   Auth Method: {'Token' if service.api_token else 'Basic'}")
    print(f"   Timeout: {service.timeout}s")

    # 3. Test authentication trước
    print("\n🔐 Testing authentication...")
    auth_result = await service.check_auth()

    if auth_result.authenticated:
        print(f"   ✅ Auth successful! User: {auth_result.user}")
    else:
        print(f"   ❌ Auth failed: {auth_result.message}")
        print("\n💡 Check your .env file:")
        print("   - PAPERLESS_BASE_URL")
        print("   - PAPERLESS_USERNAME")
        print("   - PAPERLESS_PASSWORD")
        return

    # 4. Khởi tạo custom fields từ model schema (chỉ chạy 1 lần duy nhất)
    print("\n📝 Setting up custom fields from schema (runs only once)...")
    if DocumentGeneralInformation:
        print(f"   Using model: DocumentGeneralInformation")
        field_ids = await PaperlessMetadataHelper.initialize_fields(
            service, 
            DocumentGeneralInformation
        )
    else:
        field_ids = await PaperlessMetadataHelper.initialize_fields(service)
    print(f"   ✅ Initialized {len(field_ids)} custom fields")

    # 5. Tạo metadata từ model
    print("\n🤖 Generating metadata from model...")
    file_name = os.path.basename(file_path)
    if DocumentGeneralInformation:
        metadata = PaperlessMetadataHelper.generate_metadata(
            file_name, 
            DocumentGeneralInformation
        )
    else:
        metadata = PaperlessMetadataHelper.generate_metadata(file_name)
    print(f"   ✅ Metadata: {metadata}")

    # 6. Upload document với custom fields (service xử lý tất cả)
    print(f"\n📤 Uploading document with custom fields...")

    result = await service.upload_document_with_custom_fields(
        file_path=file_path,
        title=file_name,
        metadata=metadata,
        field_ids=field_ids,
        wait_seconds=5
    )

    # 7. In kết quả
    print(f"\n� Upload Result:")
    print(f"   Success: {result.get('success')}")
    if result.get('document_id'):
        print(f"   Document ID: {result['document_id']}")
        print(f"   Custom Fields Updated: {result.get('custom_fields_updated')}")
        
        if result.get('custom_fields_update'):
            update = result['custom_fields_update']
            if update.get('success'):
                print(f"   ✅ Custom fields updated successfully!")
                doc = update.get('document', {})
                for cf in doc.get('custom_fields', []):
                    print(f"      - Field {cf.get('field')}: {cf.get('value')}")
            else:
                print(f"   ❌ Failed: {update.get('error')}")
    else:
        if result.get('error'):
            print(f"   ❌ Error: {result['error']}")
        if result.get('upload'):
            print(f"   Upload Message: {result['upload'].get('message')}")
            if result['upload'].get('task_uuid'):
                print(f"   Task UUID: {result['upload'].get('task_uuid')}")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETED")
    print("=" * 60)


async def main():
    """Main entry point"""

    # Lấy file path từ argument hoặc dùng default
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Tìm file PDF đầu tiên trong downloads folder (bao gồm cả thư mục con)
        downloads_dir = Path("downloads")
        if downloads_dir.exists():
            pdf_files = list(downloads_dir.rglob("*.xlsx")) + list(downloads_dir.rglob("*.PDF"))
            if pdf_files:
                file_path = str(pdf_files[0])
                print(f"💡 Using first PDF found: {file_path}")
            else:
                print("⚠️  No PDF files found in downloads/")
                print("\nUsage: python test_paperless_upload.py <path_to_file>")
                return
        else:
            print("⚠️  downloads/ folder does not exist")
            print("\nUsage: python test_paperless_upload.py <path_to_file>")
            return

    # Chạy test upload
    await test_upload(file_path)


if __name__ == "__main__":
    asyncio.run(main())
