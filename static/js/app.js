/**
 * Main Application Module
 * Handles form submission, job management, and UI updates
 */

// DOM Elements
const elements = {
    form: document.getElementById('agentForm'),
    submitBtn: document.getElementById('submitBtn'),
    stopBtn: document.getElementById('stopBtn'),
    terminal: document.getElementById('terminal'),
    statusBadge: document.getElementById('statusBadge'),
    resultBlock: document.getElementById('resultBlock'),
    resultText: document.getElementById('resultText'),
    urlInput: document.getElementById('url'),
    usernameInput: document.getElementById('username'),
    passwordInput: document.getElementById('password'),
    instructionInput: document.getElementById('instruction')
};

// State
let currentJobId = null;
let sseClient = null;
let isUserScrolling = false;  // Track if user is scrolling up
let autoScrollEnabled = true;  // Auto-scroll only when at bottom

/**
 * Initialize event listeners
 */
function init() {
    elements.form.addEventListener('submit', handleSubmit);
    elements.stopBtn.addEventListener('click', handleStop);
    
    // Initial terminal message
    elements.terminal.innerHTML = 'Mời bạn nhập thông tin ở khung bên trái và bấm Bắt đầu thực thi...';
}

/**
 * Handle form submission
 */
async function handleSubmit(e) {
    e.preventDefault();

    // UI Reset
    setSubmittingState();

    const payload = {
        url: elements.urlInput.value,
        username: elements.usernameInput.value,
        password: elements.passwordInput.value,
        instruction: elements.instructionInput.value
    };

    try {
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Show stop button
        setRunningState();

        // Start SSE connection
        startSSEConnection(currentJobId);

    } catch (error) {
        appendToTerminal(`\n❌ Lỗi gọi API: ${error.message}`);
        resetUI();
    }
}

/**
 * Handle stop button click
 */
async function handleStop() {
    if (!currentJobId) return;

    setStoppingState();

    try {
        const response = await fetch(`/api/stop/${currentJobId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        appendToTerminal(`\n⏹️ Yêu cầu dừng đã được gửi. Agent sẽ dừng sau khi hoàn thành thao tác hiện tại...`);
        scrollToBottom();

    } catch (error) {
        appendToTerminal(`\n❌ Lỗi khi dừng: ${error.message}`);
        setRunningState();
    }
}

/**
 * Start SSE connection for real-time updates
 */
function startSSEConnection(jobId) {
    // Close existing connection if any
    if (sseClient) {
        sseClient.close();
    }

    sseClient = new SSEClient(jobId, {
        onStatus: handleStatusUpdate,
        onComplete: handleJobComplete,
        onError: handleJobError,
        onDisconnected: handleDisconnected
    });

    sseClient.connect();
}

/**
 * Handle status update from SSE
 */
function handleStatusUpdate(data) {
    // Update terminal logs only if changed
    if (data.logs && data.logs !== elements.terminal.innerHTML) {
        const wasAtBottom = isAtBottom();
        elements.terminal.innerHTML = data.logs;
        
        // Only scroll if user was at bottom before update
        if (wasAtBottom) {
            scrollToBottom();
        }
    }

    // Update status badge
    updateStatusBadge(data.status);

    // Update stop button state if job is stopping
    if (data.status === 'stopping') {
        elements.stopBtn.disabled = true;
        elements.stopBtn.innerHTML = '<div class="spinner"></div> Đang dừng...';
    }
}

/**
 * Handle job completion
 */
function handleJobComplete(data) {
    updateStatusBadge(data.status);
    resetUI();

    // Show result block
    elements.resultBlock.style.display = 'block';

    // Parse result if it's JSON
    let resultDisplay = data.result || "Không có dữ liệu trả về từ AI.";
    try {
        if (typeof data.result === 'string') {
            // Strip markdown formatting if any
            let cleanStr = data.result.replace(/^```[a-z]*\n/i, '').replace(/\n```$/g, '').trim();
            const parsed = JSON.parse(cleanStr);
            resultDisplay = JSON.stringify(parsed, null, 2);
        }
    } catch (e) {
        // Keep as string if not JSON
    }

    elements.resultText.innerText = resultDisplay;

    // Hiển thị thông báo Paperless nếu có
    const paperlessStatusDiv = document.getElementById('paperlessUploadStatus');
    const paperlessListDiv = document.getElementById('paperlessResultsList');
    
    if (paperlessStatusDiv && paperlessListDiv) {
        if (data.paperless_results && data.paperless_results.length > 0) {
            paperlessStatusDiv.style.display = 'block';
            paperlessListDiv.innerHTML = '';
            
            data.paperless_results.forEach(r => {
                const item = document.createElement('div');
                item.style.padding = '10px';
                item.style.marginTop = '10px';
                item.style.borderRadius = '5px';
                item.style.border = '1px solid #ddd';
                
                if (r.success) {
                    item.style.backgroundColor = '#e8f5e9';
                    item.style.borderColor = '#c8e6c9';
                    item.innerHTML = `<strong>✅ Thành công</strong><br>
                                      Tên file: <span>${r.file}</span><br>
                                      Document ID: <strong>#${r.document_id}</strong><br>
                                      <small>${r.message}</small>`;
                } else {
                    item.style.backgroundColor = '#ffebee';
                    item.style.borderColor = '#ffcdd2';
                    item.innerHTML = `<strong>❌ Thất bại</strong><br>
                                      Tên file: <span>${r.file}</span><br>
                                      Lỗi: <span style="color:#c62828;">${r.error || 'Server không phản hồi'}</span>`;
                }
                paperlessListDiv.appendChild(item);
            });
        } else {
            paperlessStatusDiv.style.display = 'none';
            if (data.paperless_message) {
                paperlessStatusDiv.style.display = 'block';
                paperlessListDiv.innerHTML = `<div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">${data.paperless_message}</div>`;
            }
        }
    }

    // Set appropriate class based on status
    if (data.status === 'completed') {
        elements.resultBlock.className = 'result-card success';
    } else if (data.status === 'stopped') {
        elements.resultBlock.className = 'result-card stopped';
    } else {
        elements.resultBlock.className = 'result-card error';
    }

    scrollToBottom();
}

/**
 * Handle job error
 */
function handleJobError(data) {
    appendToTerminal(`\n❌ Lỗi: ${data.message || 'Unknown error'}`);
    updateStatusBadge('error');
    resetUI();
}

/**
 * Handle disconnection
 */
function handleDisconnected() {
    console.log('SSE disconnected');
    // Optionally attempt reconnection
}

/**
 * Update status badge text and class
 */
function updateStatusBadge(status) {
    const statusMap = {
        'starting': { text: 'Khởi tạo...', class: 'badge' },
        'running': { text: 'Đang chạy...', class: 'badge badge-running' },
        'stopping': { text: 'Đang dừng...', class: 'badge badge-stopping' },
        'completed': { text: 'Hoàn thành', class: 'badge badge-completed' },
        'stopped': { text: 'Đã dừng', class: 'badge badge-stopped' },
        'error': { text: 'Lỗi', class: 'badge badge-error' },
        'failed': { text: 'Thất bại', class: 'badge badge-error' },
        'not_found': { text: 'Không tìm thấy', class: 'badge badge-error' }
    };

    const config = statusMap[status] || { text: status, class: 'badge' };
    elements.statusBadge.className = config.class;
    elements.statusBadge.innerText = config.text;
}

/**
 * Set UI to submitting state
 */
function setSubmittingState() {
    elements.submitBtn.disabled = true;
    elements.submitBtn.innerHTML = '<div class="spinner"></div> Đang khởi tạo...';
    elements.terminal.innerHTML = 'Đang kết nối tới Agent...';
    elements.resultBlock.style.display = 'none';
    elements.statusBadge.className = 'badge';
    elements.statusBadge.innerText = 'Khởi tạo...';
}

/**
 * Set UI to running state
 */
function setRunningState() {
    elements.stopBtn.style.display = 'inline-block';
    elements.stopBtn.disabled = false;
    elements.stopBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg> Dừng Agent';
}

/**
 * Set UI to stopping state
 */
function setStoppingState() {
    elements.stopBtn.disabled = true;
    elements.stopBtn.innerHTML = '<div class="spinner"></div> Đang dừng...';
}

/**
 * Reset UI to initial state
 */
function resetUI() {
    elements.submitBtn.disabled = false;
    elements.submitBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Bắt đầu chạy lại';
    elements.stopBtn.style.display = 'none';
    elements.stopBtn.disabled = true;
    
    // Close SSE connection
    if (sseClient) {
        sseClient.close();
        sseClient = null;
    }
}

/**
 * Append text to terminal
 */
function appendToTerminal(text) {
    elements.terminal.innerHTML += text;
}

/**
 * Scroll terminal to bottom
 */
function scrollToBottom() {
    // Only auto-scroll if user is at bottom (not scrolling up)
    if (autoScrollEnabled) {
        elements.terminal.scrollTop = elements.terminal.scrollHeight;
    }
}

/**
 * Check if user is at bottom of terminal
 */
function isAtBottom() {
    const threshold = 50; // pixels from bottom
    const position = elements.terminal.scrollTop + elements.terminal.clientHeight;
    const height = elements.terminal.scrollHeight;
    return position > height - threshold;
}

/**
 * Set example values for testing
 */
window.setExample = function(url, instruction) {
    elements.urlInput.value = url;
    elements.instructionInput.value = instruction;
};

// Initialize scroll event listener
function initScrollListener() {
    elements.terminal.addEventListener('scroll', () => {
        // Check if user scrolled up
        isUserScrolling = !isAtBottom();
        autoScrollEnabled = isAtBottom();
    });
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        init();
        initScrollListener();
    });
} else {
    init();
    initScrollListener();
}
