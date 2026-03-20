"""
Configuration module for Seabank Agent App

Centralized configuration management for the entire system.
All configuration values are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ==============================================================================
# 📁 BASE DIRECTORY CONFIGURATION
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent
"""Thư mục gốc của dự án"""

LOGS_DIR = BASE_DIR / "logs"
"""Thư mục chứa log files"""

DOWNLOADS_DIR = BASE_DIR / "downloads"
"""Thư mục chứa downloads"""

STATIC_DIR = BASE_DIR / "static"
"""Thư mục chứa static files (HTML, CSS, JS)"""

# Đảm bảo các thư mục tồn tại
LOGS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)


# ==============================================================================
# 🔐 LLM / API CONFIGURATION
# ==============================================================================

class LLMConfig:
    """Cấu hình cho LLM (Large Language Model)"""
    
    API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    """API key cho LLM provider"""
    
    API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    """Base URL của LLM API server"""
    
    MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    """Tên model sử dụng"""
    
    TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.6"))
    """
    Temperature: 0.0-1.0
    - Cao = sáng tạo hơn, đa dạng hơn
    - Thấp = chắc chắn hơn, tập trung hơn
    """
    
    TOP_P: float = float(os.getenv("OPENAI_TOP_P", "0.9"))
    """
    Top_P: 0.0-1.0
    - Sampling probability threshold
    - Kiểm soát độ đa dạng của câu trả lời
    """
    
    TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
    """Timeout cho LLM API calls (seconds)"""
    
    MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    """Số lần retry tối đa khi gọi API"""


# ==============================================================================
# 🌐 BROWSER / CDP CONFIGURATION
# ==============================================================================

class BrowserConfig:
    """Cấu hình cho Browser và CDP connection"""
    
    CDP_URL: str = os.getenv("CHROME_CDP_URL", "http://chrome-cdp:3000")
    """
    Chrome DevTools Protocol URL
    - Docker: http://chrome-cdp:3000 (internal network)
    - Local: http://127.0.0.1:9223 hoặc http://host.docker.internal:9223
    """
    
    CDP_PORT: int = int(os.getenv("CHROME_CDP_PORT", "9223"))
    """CDP remote debugging port"""
    
    DOWNLOADS_PATH: str = str(DOWNLOADS_DIR)
    """Đường dẫn thư mục downloads mặc định"""
    
    USE_VISION: bool = os.getenv("BROWSER_USE_VISION", "false").lower() == "true"
    """Có sử dụng vision capabilities không"""
    
    MAX_STEPS: int = int(os.getenv("BROWSER_MAX_STEPS", "50"))
    """Số bước tối đa cho agent run"""


# ==============================================================================
# 🏃 AGENT RUNTIME CONFIGURATION
# ==============================================================================

class AgentConfig:
    """Cấu hình cho Agent runtime"""
    
    ACTION_TIMEOUT: int = int(os.getenv("BROWSER_USE_ACTION_TIMEOUT", "120"))
    """Timeout cho mỗi action (seconds)"""
    
    WATCHDOG_TIMEOUT: int = int(os.getenv("BROWSER_USE_WATCHDOG_TIMEOUT", "120"))
    """Timeout cho watchdog (seconds)"""
    
    ENABLE_TELEMETRY: bool = os.getenv("BROWSER_USE_TELEMETRY", "false").lower() == "true"
    """Có bật telemetry không"""
    
    ANONYMIZED_TELEMETRY: bool = os.getenv("ANONYMIZED_TELEMETRY", "false").lower() == "true"
    """Có bật anonymized telemetry không"""


# ==============================================================================
# 🖥️ SERVER CONFIGURATION
# ==============================================================================

class ServerConfig:
    """Cấu hình cho FastAPI server"""
    
    HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    """Server host"""
    
    PORT: int = int(os.getenv("SERVER_PORT", "5555"))
    """Server port"""
    
    RELOAD: bool = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    """Có bật auto-reload không (chỉ dùng cho development)"""
    
    WORKERS: int = int(os.getenv("SERVER_WORKERS", "1"))
    """Số lượng workers"""


# ==============================================================================
# 📊 PAPERLESS-NGX CONFIGURATION
# ==============================================================================

class PaperlessConfig:
    """Cấu hình cho Paperless-ngx API"""
    
    BASE_URL: str = os.getenv("PAPERLESS_BASE_URL", "")
    """Base URL của Paperless-ngx instance"""
    
    USERNAME: str = os.getenv("PAPERLESS_USERNAME", "")
    """Username cho Paperless-ngx"""
    
    PASSWORD: str = os.getenv("PAPERLESS_PASSWORD", "")
    """Password cho Paperless-ngx"""
    
    API_TOKEN: str = os.getenv("PAPERLESS_API_TOKEN", "")
    """API token cho Paperless-ngx (nếu dùng token auth)"""
    
    TIMEOUT: int = int(os.getenv("PAPERLESS_TIMEOUT", "30"))
    """Timeout cho Paperless API calls (seconds)"""
    
    VERIFY_SSL: bool = os.getenv("PAPERLESS_VERIFY_SSL", "true").lower() == "true"
    """Có xác thực SSL certificate không"""


# ==============================================================================
# 🏦 SEABANK DOMAIN CONFIGURATION
# ==============================================================================

class SeabankConfig:
    """Cấu hình domain-specific cho Seabank"""
    
    DOCUMENT_BASE_URL: str = os.getenv("SEABANK_DOCUMENT_URL", "https://vanban.seabank.com.vn")
    """URL của hệ thống văn bản Seabank"""
    
    LOGIN_REQUIRED: bool = os.getenv("SEABANK_LOGIN_REQUIRED", "true").lower() == "true"
    """Có yêu cầu login không"""
    
    DEFAULT_USERNAME: str = os.getenv("SEABANK_DEFAULT_USERNAME", "")
    """Username mặc định cho Seabank systems"""
    
    DEFAULT_PASSWORD: str = os.getenv("SEABANK_DEFAULT_PASSWORD", "")
    """Password mặc định cho Seabank systems"""


# ==============================================================================
# 📝 LOGGING CONFIGURATION
# ==============================================================================

class LoggingConfig:
    """Cấu hình cho logging"""
    
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    """Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"""
    
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """Logging format string"""
    
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    """Date format cho logging"""
    
    FILE_ENCODING: str = "utf-8"
    """Encoding cho log files"""


# ==============================================================================
# ⚙️ ENVIRONMENT HELPER FUNCTIONS
# ==============================================================================

def get_optional_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Lấy giá trị environment variable, trả về None nếu không tồn tại hoặc rỗng.
    
    Args:
        key: Tên environment variable
        default: Giá trị mặc định nếu không tìm thấy
        
    Returns:
        Giá trị của environment variable hoặc default/None
    """
    value = os.getenv(key, default)
    return value if value else None


def is_env_truthy(key: str, default: bool = False) -> bool:
    """
    Kiểm tra environment variable có giá trị truthy (true, 1, yes, on).
    
    Args:
        key: Tên environment variable
        default: Giá trị mặc định nếu không tìm thấy
        
    Returns:
        True nếu giá trị là truthy
    """
    value = os.getenv(key, "").lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


def validate_config() -> bool:
    """
    Validate cấu hình hiện tại.
    
    Returns:
        True nếu cấu hình hợp lệ
    """
    # Kiểm tra LLM API key
    if not LLMConfig.API_KEY:
        print("⚠️  WARNING: OPENAI_API_KEY is not set")
    
    # Kiểm tra CDP URL
    if not BrowserConfig.CDP_URL:
        print("⚠️  WARNING: CHROME_CDP_URL is not set")
    
    # Kiểm tra thư mục
    for directory in [LOGS_DIR, DOWNLOADS_DIR, STATIC_DIR]:
        if not directory.exists():
            print(f"⚠️  WARNING: Directory does not exist: {directory}")
            directory.mkdir(exist_ok=True)
    
    return True


# ==============================================================================
# 🚀 INITIALIZATION
# ==============================================================================

# Set environment variables from config
if not AgentConfig.ENABLE_TELEMETRY:
    os.environ["BROWSER_USE_TELEMETRY"] = "false"
if not AgentConfig.ANONYMIZED_TELEMETRY:
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["BROWSER_USE_ACTION_TIMEOUT"] = str(AgentConfig.ACTION_TIMEOUT)
os.environ["BROWSER_USE_WATCHDOG_TIMEOUT"] = str(AgentConfig.WATCHDOG_TIMEOUT)


# ==============================================================================
# 📋 EXPORTS
# ==============================================================================

__all__ = [
    # Directories
    "BASE_DIR",
    "LOGS_DIR",
    "DOWNLOADS_DIR",
    "STATIC_DIR",
    
    # Config classes
    "LLMConfig",
    "BrowserConfig",
    "AgentConfig",
    "ServerConfig",
    "PaperlessConfig",
    "SeabankConfig",
    "LoggingConfig",
    
    # Helper functions
    "get_optional_env",
    "is_env_truthy",
    "validate_config",
]
