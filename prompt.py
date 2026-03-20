"""
Prompt templates for Seabank Agent
"""


def get_task_prompt(url: str, username: str, password: str, instruction: str, job_id: str) -> str:
    """
    Generate the task prompt for the agent.
    
    Args:
        url: Target URL to navigate to
        username: Login username
        password: Login password
        instruction: Task instruction from user
        job_id: Current job ID for download directory
    
    Returns:
        Complete prompt string for the agent
    """
    return f"""[Environment]
URL: {url}
Auth: {username} / {password}
Download Directory: /app/downloads/{job_id}

[Task Instruction]
{instruction}

[Standard Operation Procedure]
1. Navigate to {url}.
2. If the page requires login, use the provided Auth credentials (username and password).
3. Once logged in, identify and click on the link of the file/document you need to download.
4. On the document details page, find and click the tab labeled "Thông tin chung" (General Information).
5. **Extract Information**: From the "Thông tin chung" tab, extract all relevant fields to match the required JSON schema (see below).
6. Locate and click the "Tải về" (Download) button. **Note: Click action may timeout for large files - this is expected.**
7. **If click times out**, DO NOT retry multiple times. Instead:
   - Wait 5-10 seconds for the download to initiate in background.
   - Check if files appear in /app/downloads/{job_id} directory.
   - If files exist, consider the task SUCCESS even if click reported timeout.
8. **VERIFY download success**: Check if files appear in /app/downloads/{job_id} directory.

[⚠️ CRITICAL OUTPUT REQUIREMENT - READ CAREFULLY]
Your final response MUST be provided using the 'done' tool.
The 'text' parameter of the 'done' tool MUST contain ONLY a JSON object wrapped in a markdown code block.
The JSON must strictly follow the JSON Schema below based on the information extracted in step 5.
NO plain text before or after the code block. NO explanations.

[JSON Schema Requirement]
You MUST extract data according to this schema:
```json
{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DocumentGeneralInformation",
  "type": "object",
  "properties": {{
    "document_number": {{
      "type": "string",
      "description": "Số hiệu văn bản (Ví dụ: 2786/2026/TB-TGĐ)"
    }},
    "document_name": {{
      "type": "string",
      "description": "Tên văn bản"
    }},
    "document_type": {{
      "type": "string",
      "description": "Loại văn bản"
    }},
    "issue_date": {{
      "type": "string",
      "format": "date",
      "description": "Ngày ban hành (DD/MM/YYYY)"
    }},
    "effective_date": {{
      "type": "string",
      "format": "date",
      "description": "Ngày hiệu lực (DD/MM/YYYY)"
    }},
    "expiry_date": {{
      "type": ["string", "null"],
      "format": "date",
      "description": "Ngày hết hiệu lực"
    }},
    "executing_unit": {{
      "type": "string",
      "description": "Đơn vị thực hiện"
    }},
    "field": {{
      "type": "string",
      "description": "Lĩnh vực văn bản"
    }},
    "issuing_authority": {{
      "type": "string",
      "description": "Đơn vị ban hành (Chức danh người ký)"
    }},
    "security_level": {{
      "type": "string",
      "description": "Mức độ bảo mật của văn bản"
    }},
    "status": {{
      "type": "string",
      "description": "Trạng thái văn bản"
    }},
    "replaces_document": {{
      "type": ["string", "null"],
      "description": "Thay thế cho văn bản số hiệu nào"
    }},
    "replaced_by": {{
      "type": ["string", "null"],
      "description": "Bị thay thế bởi văn bản số hiệu nào"
    }},
    "managing_unit": {{
      "type": "string",
      "description": "Đơn vị chủ quản"
    }},
    "receiving_units": {{
      "type": "string",
      "description": "Đơn vị được tiếp cận văn bản"
    }}
  }},
  "required": [
    "document_number",
    "document_name",
    "issue_date",
    "status"
  ]
}}
```

[Example Output Format]
Your output should look like this (replace with actual extracted data):
```json
{{
  "document_number": "2786/2026/TB-TGĐ",
  "document_name": "Các giới hạn cấp tín dụng của SeABank",
  "document_type": "Thông báo",
  "issue_date": "13/03/2026",
  "effective_date": "13/03/2026",
  "expiry_date": null,
  "executing_unit": "Toàn hệ thống SeABank",
  "field": "Quản trị rủi ro",
  "issuing_authority": "Phó Tổng Giám đốc",
  "security_level": "Thông thường",
  "status": "Hiệu lực",
  "replaces_document": "1904/2026/TB-TGĐ",
  "replaced_by": null,
  "managing_unit": "Khối Quản trị rủi ro, Pháp chế và Tuân thủ",
  "receiving_units": "Tất cả các đơn vị"
}}
```

[Constraints]
- **Click actions may timeout for large files - this is NORMAL.**
- **DO NOT retry click multiple times if it times out.**
- **YOUR FINAL MESSAGE IN THE 'done' TOOL MUST BE JSON WRAPPED IN ```json ``` CODE BLOCK - NO OTHER TEXT.**
- **CRITICAL**: All date formats MUST be DD/MM/YYYY. Use null for missing optional fields.
- **CRITICAL**: Follow the JSON Schema exactly - only the 4 fields in "required" are mandatory; others can be null if not found.
"""
