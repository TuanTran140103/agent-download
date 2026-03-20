import asyncio
import json
import base64
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
import httpx

from config import BASE_DIR, STATIC_DIR, ServerConfig, LoggingConfig
from agent_runner import start_job, get_job_status, JOBS, request_stop_job, get_job_log_file
from services.paperless_service import PaperlessService

app = FastAPI(title="Seabank Agent App")

# Enable CORS for SSE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chẩn đoán: Route kiểm tra Python thực sự thấy gì ở thư mục tĩnh
@app.get("/api/debug/files")
def debug_static_files():
    import os
    file_list = []
    if STATIC_DIR.exists():
        for file in STATIC_DIR.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(STATIC_DIR).as_posix()
                file_list.append(rel_path)
    return {
        "cwd": os.getcwd(),
        "static_dir": str(STATIC_DIR),
        "exists": STATIC_DIR.exists(),
        "files_count": len(file_list),
        "files": file_list
    }

# Serve static files manually - Fix FastAPI path encoding issue
@app.get("/static/css/{filename:path}")
async def serve_css(filename: str):
    file_path = os.path.join(str(STATIC_DIR), "css", filename.replace("/", os.sep))
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path, media_type="text/css")
    return {"error": f"CSS not found: {filename}"}, 404

@app.get("/static/js/{filename:path}")
async def serve_js(filename: str):
    file_path = os.path.join(str(STATIC_DIR), "js", filename.replace("/", os.sep))
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    return {"error": f"JS not found: {filename}"}, 404

@app.get("/static/{filename}")
async def serve_static_root(filename: str):
    file_path = os.path.join(str(STATIC_DIR), filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return {"error": f"File not found: {filename}"}, 404

class AgentRequest(BaseModel):
    url: str
    username: str
    password: str
    instruction: str

# Store last event ID for each job
LAST_EVENT_ID = {}

@app.get("/")
def read_root():
    # Sử dụng FileResponse trực tiếp cho index.html
    html_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(html_file):
        return {"error": f"Không tìm thấy index.html tại {html_file}. Hãy kiểm tra volume mount Docker."}
    return FileResponse(html_file)

@app.post("/api/run")
async def run_agent(req: AgentRequest):
    job_id = start_job(req.url, req.username, req.password, req.instruction)
    LAST_EVENT_ID[job_id] = 0
    return {"job_id": job_id, "status": "starting"}

@app.get("/api/status/{job_id}")
def check_status(job_id: str):
    return get_job_status(job_id)

@app.post("/api/stop/{job_id}")
def stop_agent(job_id: str):
    """Dừng một job đang chạy"""
    if job_id not in JOBS:
        return {"status": "error", "message": "Job not found"}

    # Đánh dấu yêu cầu dừng
    request_stop_job(job_id)

    # Cập nhật trạng thái ngay lập tức
    JOBS[job_id]["status"] = "stopping"

    # Ghi log yêu cầu dừng
    log_file = get_job_log_file(job_id)
    if os.path.exists(log_file):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n⏹️ Stop request received at {__import__('datetime').datetime.now()}\n")

    return {"status": "ok", "message": "Stop request sent. Agent will stop after completing current step."}

@app.get("/api/events/{job_id}")
async def stream_events(job_id: str, request: Request):
    """
    SSE endpoint - stream real-time updates for a job
    """
    last_event_id = int(request.query_params.get("last_event_id", 0))
    
    async def event_generator():
        nonlocal last_event_id
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Check if job exists
            if job_id not in JOBS:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                break
            
            status_data = get_job_status(job_id)
            current_event_id = last_event_id + 1

            # Send event with job status
            event_data = {
                "event_id": current_event_id,
                "job_id": job_id,
                "status": status_data["status"],
                "result": status_data["result"],
                "logs": status_data["logs"],
                "timestamp": time.time()
            }
            
            # Thêm Paperless results nếu có
            if "paperless_message" in status_data:
                event_data["paperless_message"] = status_data["paperless_message"]
            if "paperless_results" in status_data:
                event_data["paperless_results"] = status_data["paperless_results"]

            yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
            last_event_id = current_event_id
            
            # If job is completed/stopped/error, send final event and close
            if status_data["status"] in ["completed", "error", "stopped", "failed", "not_found"]:
                yield f"event: complete\ndata: {json.dumps(event_data)}\n\n"
                break
            
            # Wait before next update (500ms for responsive UI)
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.RELOAD,
    )