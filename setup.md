# Hướng dẫn Khởi chạy Seabank Agent App trên Ubuntu Server (Đã có Conda/Python)

Tài liệu này hướng dẫn cách setup và cấu hình tự động chạy nền (systemd) cho ứng dụng **Seabank Agent App**, với giả định Server Ubuntu của bạn đã được cài sẵn Python và Conda, và bạn đã copy thư mục chứa mã nguồn (thư mục hiện tại) lên Server.

---

## Bước 1: Di chuyển vào thư mục dự án

Mở Terminal kết nối SSH tới server Ubuntu, truy cập thẳng vào thư mục mã nguồn bạn vừa copy lên (ví dụ: `seabank_agent_app` nằm ở đường dẫn `/opt/seabank_agent_app` hoặc trong thư mục user của bạn `/home/ubuntu/seabank_agent_app`).

```bash
# Thay đổi đường dẫn này theo vị trí thực tế trên Server của bạn
cd /path/to/your/seabank_agent_app
```

---

## Bước 2: Khởi tạo và kích hoạt Conda Environment

Sử dụng Conda để tạo một môi trường Python 3.10 hoàn toàn mới cho dự án này để không xung đột với các ứng dụng khác:

```bash
# Tạo môi trường tên 'seabank_agent' với Python 3.10
conda create -n seabank_agent python=3.10 -y

# Kích hoạt môi trường vừa tạo
conda activate seabank_agent
```

---

## Bước 3: Cài đặt Thư viện và Playwright

Đảm bảo bạn vẫn đang ở trong thư mục `seabank_agent_app` và môi trường `seabank_agent` đang được kích hoạt.

1. **Cài đặt các gói Python phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Cài đặt trình duyệt Chromium cho Playwright:**
   Vì `browser-use` chạy web tự động (headless) nên Playwright cần tải trình duyệt riêng của nó và cài đặt các thư viện hệ thống cần thiết trên Linux:
   ```bash
   # Cài đặt file chạy của Chromium
   playwright install chromium
   
   # Cài đặt các thư viện hệ thống Linux đi kèm (có thể yêu cầu nhập sudo password)
   sudo playwright install-deps chromium
   ```

---

## Bước 4: Chạy thử thủ công (Tùy chọn)

Nếu bạn muốn chạy test xem code có hoạt động không trước khi treo nền:
```bash
# Chú ý: Hãy chắc chắn Ollama local của bạn đang chạy ở port mặc định (11434)
python main.py
```
> Nếu bạn thấy "Uvicorn running on http://0.0.0.0:5555" (Bấm `Ctrl+C` để tắt) thì ứng dụng đã sẵn sàng.

---

## Bước 5: Cấu hình tự chạy nền (Systemd Service)

Để đảm bảo Server tắt đi bật lại hoặc lỡ tắt terminal thì ứng dụng vẫn chạy ở Port 5555, chúng ta cài đặt 1 Systemd Service.

1. **Kiểm tra đường dẫn tới python của Conda:**
   Gõ lệnh sau và lưu/copy lại đường dẫn hiển thị ra trên màn hình (để lát dán vào file service):
   ```bash
   which python
   # Ví dụ nó sẽ in ra: /home/ubuntu/miniconda3/envs/seabank_agent/bin/python
   
   which uvicorn
   # Ví dụ in ra: /home/ubuntu/miniconda3/envs/seabank_agent/bin/uvicorn
   ```

2. **Tạo file service:**
   ```bash
   sudo nano /etc/systemd/system/seabank-agent.service
   ```

3. **Dán nội dung cấu hình:** (Sửa lại 2 tham số `User` và các đường dẫn `/path/to/...` cho khớp với thực tế máy bạn)

   ```ini
   [Unit]
   Description=Seabank Browser Agent Application
   After=network.target

   [Service]
   # Điền tên User của Server bạn vào đây (VD: ubuntu, hoặc root)
   User=root
   
   # Thư mục gốc chứa source code (Nơi để file main.py)
   WorkingDirectory=/path/to/your/seabank_agent_app

   # Cung cấp đường dẫn môi trường (Lấy đường dẫn lúc nãy gõ "which python", bỏ chữ "/python" đi)
   Environment="PATH=/home/ubuntu/miniconda3/envs/seabank_agent/bin"

   # Lệnh thực thi: [Đường dẫn Uvicorn] main:app --host 0.0.0.0 --port 5555
   ExecStart=/home/ubuntu/miniconda3/envs/seabank_agent/bin/uvicorn main:app --host 0.0.0.0 --port 5555

   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```
   *(Nhấn `Ctrl+O` -> `Enter` để lưu file, rồi `Ctrl+X` để đóng Nano)*

4. **Kích hoạt và chạy Service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start seabank-agent
   sudo systemctl enable seabank-agent
   ```

---

## Bước 6: Hoàn tất & Kiểm tra

1. Mở xem trạng thái Service:
   ```bash
   sudo systemctl status seabank-agent
   ```
   Nếu có chữ **`active (running)`** màu xanh là thành công.

2. **Xem Live Logs (Khi có lỗi):**
   ```bash
   journalctl -u seabank-agent -f
   ```

3. **Mở Tường lửa (Firewall) cho Port 5555** (nếu dùng UFW trên Ubuntu):
   ```bash
   sudo ufw allow 5555/tcp
   sudo ufw reload
   ```


---

## Cách 2: Chạy Bằng Docker (Sử dụng Image chính thức của `browser-use`)

Nếu bạn đã cài đặt Docker và muốn môi trường sạch nhất, bạn có thể build Image kế thừa từ Image `browser-use` chính thức (đã có sẵn thư viện, Python và Chromium).

### 1. Tạo file Dockerfile
Hoặc đảm bảo file `Dockerfile` nằm trong thư mục `seabank_agent_app` của bạn có nội dung sau:

```dockerfile
# Sử dụng base image chuẩn của browser-use
# Thay đổi tag (như :latest) nếu cần thiết
FROM docker.io/browseruse/browser-use:latest

# Di chuyển vị trí làm việc
WORKDIR /app

# Copy các file mã nguồn vào image
COPY requirements.txt main.py agent_runner.py ./
COPY static/ ./static/

# Tự động cài thêm các gói nâng cao cần cho Web Agent của chúng ta
RUN pip install --no-cache-dir -r requirements.txt

# Mở port 5555
EXPOSE 5555

# Chạy Server FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5555"]
```

### 2. Build Docker Image
Trong thư mục `seabank_agent_app` (nơi chứa `Dockerfile` vừa tạo), tiến hành build image:

```bash
docker build -t seabank-agent-app .
```

### 3. Chạy Container (Có kết nối Ollama Local)
Lệnh sau sẽ chạy ứng dụng web ở port 5555. 

**LƯU Ý QUAN TRỌNG VỀ OLLAMA**: Nếu bạn chạy Ollama ở cùng Server Ubuntu bên ngoài lớp Docker (localhost), Container Docker bên trong không thể kết nối tới `http://127.0.0.1:11434`. Do đó, cần thiết lập network hoặc biến môi trường `OLLAMA_HOST` thích hợp cho `browser-use`.

Khởi chạy bằng `--network host` (Cách dễ nhất trên Linux để Container dùng chung IP gốc với Ollama):
```bash
docker run -d \
  --name seabank_agent \
  --network host \
  --restart unless-stopped \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  seabank-agent-app
```

> **Giải thích lệnh**:
> - `-v $(pwd)/downloads:/app/downloads`: Mount (chia sẻ) thư mục downloads từ Docker ra ngoài để bạn dễ dàng lấy tài liệu tải về.
> - `--network host`: Cho phép ứng dụng bên trong Docker có thể gọi các API Ollama trên `localhost` của Server dễ dàng.
> - `--restart unless-stopped`: Giống hệt Systemd, nó giúp Docker app tự động bật lên khi khởi động máy chủ.

### 4. Kiểm tra Logs
Nếu cấu hình không chạy được, bạn có thể check logs Docker ngay:
```bash
docker logs -f seabank_agent
```
