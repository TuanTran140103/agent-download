import asyncio
import os
import re
import sys
import threading
import uuid
import unicodedata
import logging
import time
import json
import ctypes

from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from config import LOGS_DIR, DOWNLOADS_DIR, LLMConfig, BrowserConfig, AgentConfig, LoggingConfig
from prompt import get_task_prompt

# Logging configuration
logging.basicConfig(
    level=getattr(logging, LoggingConfig.LEVEL),
    format=LoggingConfig.FORMAT,
    datefmt=LoggingConfig.DATE_FORMAT,
)

# { job_id: {"status": "running"|"completed"|"error"|"stopped"|"stopping", "result": str} }
JOBS = {}

# { job_id: True } - lưu các job đang yêu cầu dừng
STOP_REQUESTS = {}

# Pydantic models cho kết quả trả về
class DocumentGeneralInformation(BaseModel):
    document_number: str = Field(..., description="Số hiệu văn bản")
    document_name: str = Field(..., description="Tên văn bản")
    document_type: Optional[str] = Field(None, description="Loại văn bản")
    issue_date: str = Field(..., description="Ngày ban hành (DD/MM/YYYY)")
    effective_date: Optional[str] = Field(None, description="Ngày hiệu lực (DD/MM/YYYY)")
    expiry_date: Optional[str] = Field(None, description="Ngày hết hiệu lực")
    executing_unit: Optional[str] = Field(None, description="Đơn vị thực hiện")
    field: Optional[str] = Field(None, description="Lĩnh vực văn bản")
    issuing_authority: Optional[str] = Field(None, description="Đơn vị ban hành (Chức danh người ký)")
    security_level: Optional[str] = Field(None, description="Mức độ bảo mật của văn bản")
    status: str = Field(..., description="Trạng thái văn bản")
    replaces_document: Optional[str] = Field(None, description="Thay thế cho văn bản số hiệu nào")
    replaced_by: Optional[str] = Field(None, description="Bị thay thế bởi văn bản số hiệu nào")
    managing_unit: Optional[str] = Field(None, description="Đơn vị chủ quản")
    receiving_units: Optional[str] = Field(None, description="Đơn vị được tiếp cận văn bản")


def get_job_log_file(job_id: str) -> str:
    return os.path.join(LOGS_DIR, f"{job_id}.log")


def format_file_size(size_bytes: int) -> str:
    """Format file size từ bytes sang KB/MB/GB."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def sanitize_filename(name: str) -> str:
    """Giữ tiếng Việt, xóa ký tự nguy hiểm, cắt nếu quá dài."""
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    if len(name) > 200:
        base, ext = os.path.splitext(name)
        name = base[:200 - len(ext)] + ext
    return name.strip()


# ==============================================================================
# 🛠️ MONKEY-PATCH BROWSER-USE (Sửa lỗi "AI lưu file có ký tự /")
# ==============================================================================
try:
    import browser_use.browser.watchdogs.downloads_watchdog as dw
    
    # 1. Patch os.path.join trong module downloads_watchdog (Catch-all)
    _orig_os_join = dw.os.path.join
    def _safe_os_join(a, *p):
        safe_parts = [part.replace('/', '_').replace('\\', '_') if isinstance(part, str) else part for part in p]
        return _orig_os_join(a, *safe_parts)
    dw.os.path.join = _safe_os_join
    
    # 2. Patch _get_unique_filename để bảo vệ việc tạo tên file Playwright
    _orig_dw_get_unique = dw.DownloadsWatchdog._get_unique_filename
    async def _patched_dw_get_unique(directory, filename):
        return await _orig_dw_get_unique(directory, sanitize_filename(filename))
    dw.DownloadsWatchdog._get_unique_filename = _patched_dw_get_unique
    
    # 3. Patch download_file_from_url (CHẶN cơ chế tự tải bằng httpx của browser-use)
    # Nguyên nhân: download_file_from_url dùng httpx độc lập, bị mất Cookie/Session 
    # dẫn đến việc tải nhầm trang HTML login thay vì file PDF.
    async def _patched_dw_download(self, url, target_id, content_type=None, suggested_filename=None):
        logging.info(f"🚀 Bypassing manual download for {url} to prevent GET fetch() from downloading HTML")
        # Trả về None để ép browser-use dùng cơ chế native download của Playwright
        return None
    dw.DownloadsWatchdog.download_file_from_url = _patched_dw_download
    
    # Bổ sung: Patch cả trigger_pdf_download vì nó cũng dùng fetch(URL) bằng GET,
    # gây ra lỗi tải file HTML đối với các trang ASP.NET
    async def _patched_trigger_pdf_download(self, target_id):
        logging.info(f"🚀 Bypassing trigger_pdf_download to prevent GET fetch() from downloading HTML")
        return None
    dw.DownloadsWatchdog.trigger_pdf_download = _patched_trigger_pdf_download
    
    # 4. Patch CDP download events
    _orig_dw_handle_cdp = dw.DownloadsWatchdog._handle_cdp_download
    async def _patched_dw_handle_cdp(self, event, target_id, session_id):
        if 'suggestedFilename' in event:
            event['suggestedFilename'] = sanitize_filename(event['suggestedFilename'])
        return await _orig_dw_handle_cdp(self, event, target_id, session_id)
    dw.DownloadsWatchdog._handle_cdp_download = _patched_dw_handle_cdp
    
    logging.info("✅ Successfully applied filename sanitization and download bypass patch to browser-use")
except Exception as e:
    logging.warning(f"⚠️ Could not patch browser-use: {e}")
# ==============================================================================



async def run_browser_task(
    job_id: str, url: str, username: str, password: str, instruction: str
):
    JOBS[job_id] = {"status": "running", "result": None}

    file_handler = logging.FileHandler(
        get_job_log_file(job_id), mode="w", encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    bu_logger = logging.getLogger("browser_use")
    bu_logger.setLevel(logging.INFO)
    bu_logger.addHandler(file_handler)

    try:
        # /app/downloads/{job_id} tồn tại trong CẢ HAI container nhờ shared volume:
        #   seabank-agent:      ./downloads:/app/downloads
        #   browser-use-exec:   ../seabank_agent_app/seabank_agent_app/downloads:/app/downloads
        job_download_dir = os.path.join(DOWNLOADS_DIR, job_id)
        os.makedirs(job_download_dir, exist_ok=True)
        
        # Sửa lỗi Permission Denied khi Browserless tải file:
        # Browserless chạy dưới quyền non-root, trong khi thu mục được tạo bởi app chạy quyền root.
        # Cần cấp quyền 777 để Browserless có thể lưu file vào đây.
        try:
            os.chmod(job_download_dir, 0o777)
        except Exception as chmod_e:
            bu_logger.warning(f"⚠️ Could not chmod 777 on {job_download_dir}: {chmod_e}")

        # ── 1. LLM ──────────────────────────────────────────────────────────
        llm = ChatOpenAI(
            model       = LLMConfig.MODEL,
            api_key     = LLMConfig.API_KEY,
            base_url    = LLMConfig.API_BASE,
            temperature = LLMConfig.TEMPERATURE,
            top_p       = LLMConfig.TOP_P,
        )

        # ── 2. Browser ───────────────────────────────────────────────────────
        cdp_url = BrowserConfig.CDP_URL
        bu_logger.info(f"🔗 Kết nối CDP: {cdp_url}")

        # Test kết nối CDP trước khi khởi tạo Browser
        import urllib.request
        try:
            test_url = cdp_url + "/json/version"
            bu_logger.info(f"📡 Testing CDP connection: {test_url}")
            with urllib.request.urlopen(test_url, timeout=5) as response:
                version_info = json.loads(response.read().decode())
                bu_logger.info(f"✅ CDP Connected! Browser: {version_info.get('Browser', 'Unknown')}")
        except Exception as e:
            bu_logger.error(f"❌ Cannot connect to CDP: {e}")
            bu_logger.error("💡 Hint: Ensure browserless Chrome is running")
            bu_logger.error("💡 Run: docker-compose up -d chrome-cdp")
            raise Exception(f"Cannot connect to Chrome CDP at {cdp_url}: {e}")

        browser = Browser(
            cdp_url=cdp_url,
            downloads_path=job_download_dir,
        )

        # ── 3. Task Prompt ──────────────────────────────────────────────────
        task_prompt = get_task_prompt(url, username, password, instruction, job_id)

        # ── 4. Agent ─────────────────────────────────────────────────────────
        agent = Agent(
            task       = task_prompt,
            llm        = llm,
            browser    = browser,
            use_vision = BrowserConfig.USE_VISION,
        )


        # ── 6. Run ───────────────────────────────────────────────────────────
        bu_logger.info(f"🚀 Job {job_id} bắt đầu...")
        bu_logger.info(f"📍 URL: {url}")
        bu_logger.info(f"📝 Instruction: {instruction}")

        # Run agent với check stop request
        result = await agent.run(max_steps=BrowserConfig.MAX_STEPS)

        # Chờ trình duyệt xử lý xong tác vụ tải file ngầm (nếu có)
        bu_logger.info("⏳ Chờ Playwright hoàn tất tải file chạy ngầm...")
        import asyncio
        start_wait = 0
        
        # Đợi 5s đầu tiên để Playwright kịp bắt sự kiện tải và đẩy file vào thư mục
        await asyncio.sleep(5)
        
        # Tiếp tục chờ nếu có file đang tải dở dạng .crdownload hoặc .tmp
        download_wait = 0
        max_download_wait = 120  # Tối đa chờ 2 phút
        while download_wait < max_download_wait:
            files_in_dir = os.listdir(job_download_dir)
            if any(f.endswith('.crdownload') or f.endswith('.tmp') for f in files_in_dir):
                if download_wait % 10 == 0:
                    bu_logger.info(f"⏳ File vẫn đang tải, giữ nguyên trình duyệt... (đã chờ {download_wait}s)")
                await asyncio.sleep(2)
                download_wait += 2
            else:
                break

        # Check stop request sau khi run xong
        if is_stop_requested(job_id):
            bu_logger.info(f"⏹️ Job {job_id} đã được dừng theo yêu cầu")
            JOBS[job_id]["status"] = "stopped"
            JOBS[job_id]["result"] = "Agent đã được người dùng dừng."
            cleanup_stop_request(job_id)
            return  # Exit early, không xử lý tiếp

        bu_logger.info(f"✅ Job {job_id} hoàn thành")

        # Kiểm tra nội dung thư mục download
        downloaded_files = os.listdir(job_download_dir)
        if downloaded_files:
            bu_logger.info(f"📁 Đã tải các file: {', '.join(downloaded_files)}")
        else:
            bu_logger.warning("⚠️ Không tìm thấy file nào được tải xuống trong thư mục đích.")

        # Đánh dấu job hoàn thành
        JOBS[job_id]["status"] = "completed"

        # ── 5. Upload lên Paperless-ngx (nếu có file download) ──────────────────
        paperless_results = []
        downloaded_files = os.listdir(job_download_dir)
        if downloaded_files:
            bu_logger.info(f"📁 Files downloaded: {', '.join(downloaded_files)}")
            
            # Upload từng file lên Paperless
            for filename in downloaded_files:
                file_path = os.path.join(job_download_dir, filename)
                if os.path.isfile(file_path):
                    # Bỏ phần timestamp _103839 ở cuối filename để Paperless báo duplicate chính xác
                    import re
                    new_filename = re.sub(r'_\d{6}(\.[a-zA-Z0-9]+)$', r'\1', filename)
                    if new_filename != filename:
                        new_file_path = os.path.join(job_download_dir, new_filename)
                        try:
                            if os.path.exists(new_file_path):
                                os.remove(new_file_path)
                            os.rename(file_path, new_file_path)
                            filename = new_filename
                            file_path = new_file_path
                            bu_logger.info(f"🔄 Đã đổi tên chuẩn hóa: {filename}")
                        except Exception as e:
                            bu_logger.warning(f"⚠️ Lỗi đổi tên file: {e}")
                
                    bu_logger.info(f"🚀 Uploading {filename} to Paperless...")
                    
                    try:
                        # Import service và helper
                        from services.paperless_service import PaperlessService
                        from helpers.paperless_helper import PaperlessMetadataHelper
                        
                        # Khởi tạo service
                        paperless_service = PaperlessService()
                        
                        # Check auth trước
                        auth_result = await paperless_service.check_auth()
                        if not auth_result.authenticated:
                            bu_logger.warning(f"⚠️ Paperless auth failed: {auth_result.message}")
                            paperless_results.append({
                                "file": filename,
                                "success": False,
                                "error": "Paperless authentication failed"
                            })
                            continue
                        
                        # Initialize custom fields (chỉ chạy 1 lần)
                        field_ids = await PaperlessMetadataHelper.initialize_fields(
                            paperless_service,
                            DocumentGeneralInformation
                        )
                        bu_logger.info(f"✅ Initialized {len(field_ids)} custom fields")
                        
                        # Generate metadata từ filename
                        metadata = PaperlessMetadataHelper.generate_metadata(
                            filename,
                            DocumentGeneralInformation
                        )
                        bu_logger.info(f"📝 Generated metadata: {metadata}")
                        
                        # Upload với custom fields
                        upload_result = await paperless_service.upload_document_with_custom_fields(
                            file_path=file_path,
                            title=filename,
                            metadata=metadata,
                            field_ids=field_ids,
                            wait_seconds=5,
                            max_retries=10
                        )
                        
                        if upload_result.get('success'):
                            doc_id = upload_result.get('document_id')
                            cf_updated = upload_result.get('custom_fields_updated')
                            bu_logger.info(f"✅ Uploaded successfully! Document ID: {doc_id}, Custom fields updated: {cf_updated}")
                            paperless_results.append({
                                "file": filename,
                                "success": True,
                                "document_id": doc_id,
                                "custom_fields_updated": cf_updated,
                                "message": f"Uploaded to Paperless as Document #{doc_id}"
                            })
                        else:
                            error_msg = upload_result.get('error', 'Unknown error')
                            bu_logger.error(f"❌ Upload failed: {error_msg}")
                            paperless_results.append({
                                "file": filename,
                                "success": False,
                                "error": error_msg
                            })

                    except Exception as e:
                        bu_logger.error(f"❌ Error uploading {filename} to Paperless: {e}", exc_info=True)
                        paperless_results.append({
                            "file": filename,
                            "success": False,
                            "error": str(e)
                        })
            
            # Xóa thư mục job sau khi upload xong
            bu_logger.info(f"🗑️ Cleaning up job directory: {job_download_dir}")
            try:
                import shutil
                shutil.rmtree(job_download_dir)
                bu_logger.info(f"✅ Deleted job directory: {job_download_dir}")
            except Exception as e:
                bu_logger.error(f"⚠️ Failed to delete job directory: {e}")
            
            # Thêm paperless_results vào JOBS để client có thể lấy
            if paperless_results:
                JOBS[job_id]["paperless_results"] = paperless_results
                success_count = sum(1 for r in paperless_results if r.get('success'))
                total_count = len(paperless_results)
                if success_count == total_count:
                    JOBS[job_id]["paperless_message"] = f"✅ Successfully uploaded {total_count} file(s) to Paperless"
                elif success_count > 0:
                    JOBS[job_id]["paperless_message"] = f"⚠️ Uploaded {success_count}/{total_count} file(s) to Paperless"
                else:
                    JOBS[job_id]["paperless_message"] = f"❌ Failed to upload any files to Paperless"
        else:
            bu_logger.warning("⚠️ No files to upload to Paperless")
            JOBS[job_id]["paperless_message"] = "⚠️ No files downloaded to upload to Paperless" 
        # # Lấy last action để xem AI đã làm gì
        # if hasattr(result, 'last_action') and result.last_action:
        #     print(f"  result.last_action: {result.last_action}")
        # 
        # # Lấy structured output nếu có
        # if hasattr(result, 'structured_output') and result.structured_output:
        #     print(f"  result.structured_output: {result.structured_output}")
        # 
        # print(f"  result.history length: {len(result.history) if result and hasattr(result, 'history') else 'N/A'}")
        # print("=" * 80)

        # --- PHASE 2: PARSE & NORMALIZE RESULT ---
        # Lấy kết quả từ AI (AI luôn trả JSON trong final_result)
        ai_response = ""
        if result:
            try:
                ai_response = result.final_result() or ""
                bu_logger.info(f"📝 Extracted from result.final_result(): {ai_response[:200]}...")
            except Exception as e:
                bu_logger.warning(f"⚠️ Error calling result.final_result(): {e}")

        bu_logger.info(f"📊 Analyzing AI response: {ai_response[:200]}...")
        final_json_obj = None

        # 1. Thử tìm trong code block ```json ... ```
        json_markdown_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        if json_markdown_match:
            try:
                final_json_obj = json.loads(json_markdown_match.group(1))
                bu_logger.info("✅ Extracted JSON from markdown code block")
            except: pass

        # 2. Thử parse toàn bộ chuỗi response (AI thường trả về JSON thuần trong 'done' tool)
        if not final_json_obj:
            try:
                cleaned_resp = ai_response.strip()
                if cleaned_resp.startswith('{') and cleaned_resp.endswith('}'):
                    final_json_obj = json.loads(cleaned_resp)
                    bu_logger.info("✅ Parsed raw JSON successfully from AI response")
            except: pass

        # Lưu kết quả cuối cùng (luôn bọc markdown)
        if final_json_obj:
            formatted_json = json.dumps(final_json_obj, indent=2, ensure_ascii=False)
            JOBS[job_id]["result"] = f"```json\n{formatted_json}\n```"
        else:
            bu_logger.warning("⚠️ No JSON structure found in AI response")
            error_data = {"error": "Could not parse result", "message": ai_response[:500]}
            JOBS[job_id]["result"] = f"```json\n{json.dumps(error_data, indent=2, ensure_ascii=False)}\n```"
        
        # Thử parse sang DocumentGeneralInformation object (Python object)
        JOBS[job_id]["data"] = None
        if final_json_obj:
            try:
                structured_data = DocumentGeneralInformation(**final_json_obj)
                JOBS[job_id]["data"] = structured_data.model_dump()
                bu_logger.info("✅ Đã parse kết quả sang DocumentGeneralInformation object!")
            except Exception as e:
                bu_logger.warning(f"⚠️ Validation error for DocumentGeneralInformation: {e}")

    except Exception as e:
        bu_logger.error(f"❌ Job {job_id} lỗi: {e}", exc_info=True)
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["result"] = f"Lỗi: {e}"

    finally:
        bu_logger.removeHandler(file_handler)
        if "browser" in locals():
            try:
                await browser.stop()
            except Exception:
                pass


def _run_in_thread(job_id: str, url: str, username: str, password: str, instruction: str):
    """
    Chạy browser task trong thread riêng với event loop riêng biệt.
    Giống hệt cách local_download_agent.py dùng asyncio.run() — tránh
    xung đột với event loop của uvicorn khiến Playwright không khởi tạo được.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Tạo event loop mới, sạch, riêng cho thread này
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            run_browser_task(job_id, url, username, password, instruction)
        )
    finally:
        loop.close()


def start_job(url: str, username: str, password: str, instruction: str) -> str:
    job_id = str(uuid.uuid4())

    with open(get_job_log_file(job_id), "w", encoding="utf-8") as f:
        f.write(f"Job Initialized: {job_id}\n")

    JOBS[job_id] = {"status": "starting", "result": None}

    t = threading.Thread(
        target=_run_in_thread,
        args=(job_id, url, username, password, instruction),
        daemon=True,
    )
    t.start()
    
    # Lưu thread reference để có thể kill nếu cần
    JOBS[job_id]["thread"] = t

    return job_id


def get_job_status(job_id: str) -> dict:
    status_info = JOBS.get(job_id, {"status": "not_found", "result": None, "data": None})
    logs = ""
    log_file = get_job_log_file(job_id)
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            logs = f.read()

    return {
        "job_id": job_id,
        "status": status_info["status"],
        "result": status_info["result"],
        "data":   status_info.get("data"),
        "logs":   logs,
        "paperless_message": status_info.get("paperless_message"),
        "paperless_results": status_info.get("paperless_results"),
    }


def _async_raise(tid, exctype):
    """Raise exception in thread by ID"""
    if not isinstance(exctype, type) and issubclass(exctype, Exception):
        raise TypeError('Only types can be raised (not instances)')
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def request_stop_job(job_id: str):
    """Đánh dấu job cần được dừng và kill thread"""
    if job_id not in JOBS:
        return False
    
    # Đánh dấu yêu cầu dừng
    STOP_REQUESTS[job_id] = True
    
    # Cập nhật trạng thái ngay
    JOBS[job_id]["status"] = "stopping"
    
    # Thử kill thread
    thread = JOBS[job_id].get("thread")
    if thread and thread.is_alive():
        try:
            _async_raise(thread.ident, KeyboardInterrupt)
            logging.info(f"⏹️ Sent interrupt to job {job_id}")
        except Exception as e:
            logging.error(f"❌ Failed to kill thread for job {job_id}: {e}")
    
    return True


def cleanup_stop_request(job_id: str):
    """Xóa yêu cầu dừng sau khi hoàn tất"""
    STOP_REQUESTS.pop(job_id, None)


def is_stop_requested(job_id: str) -> bool:
    """Kiểm tra xem job có yêu cầu dừng không"""
    return STOP_REQUESTS.get(job_id, False)