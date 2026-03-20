/**
 * SSE Client Module
 * Handles Server-Sent Events connection for real-time job status updates
 */

class SSEClient {
    constructor(jobId, callbacks = {}) {
        this.jobId = jobId;
        this.eventSource = null;
        this.callbacks = {
            onStatus: callbacks.onStatus || (() => {}),
            onComplete: callbacks.onComplete || (() => {}),
            onError: callbacks.onError || (() => {}),
            onDisconnected: callbacks.onDisconnected || (() => {})
        };
        this.isConnected = false;
        this.lastEventId = 0;
    }

    /**
     * Connect to SSE endpoint
     */
    connect() {
        const url = `/api/events/${this.jobId}?last_event_id=${this.lastEventId}`;
        
        this.eventSource = new EventSource(url);
        this.isConnected = true;

        // Handle status updates
        this.eventSource.addEventListener('status', (event) => {
            try {
                const data = JSON.parse(event.data);
                this.lastEventId = data.event_id;
                this.callbacks.onStatus(data);
            } catch (err) {
                console.error('Error parsing status event:', err);
            }
        });

        // Handle completion
        this.eventSource.addEventListener('complete', (event) => {
            try {
                const data = JSON.parse(event.data);
                this.lastEventId = data.event_id;
                this.callbacks.onComplete(data);
                this.close();
            } catch (err) {
                console.error('Error parsing complete event:', err);
            }
        });

        // Handle errors
        this.eventSource.addEventListener('error', (event) => {
            try {
                const data = JSON.parse(event.data);
                this.callbacks.onError(data);
                this.close();
            } catch (err) {
                console.error('Error parsing error event:', err);
                this.callbacks.onError({ message: 'SSE connection error' });
            }
        });

        // Handle connection errors
        this.eventSource.onerror = (err) => {
            console.error('SSE connection error:', err);
            
            if (this.eventSource.readyState === EventSource.CLOSED) {
                this.callbacks.onDisconnected();
            }
        };

        // Handle open connection
        this.eventSource.onopen = () => {
            console.log(`SSE connected to job: ${this.jobId}`);
        };

        return this;
    }

    /**
     * Close SSE connection
     */
    close() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            this.isConnected = false;
            console.log(`SSE disconnected from job: ${this.jobId}`);
        }
    }

    /**
     * Get current connection status
     */
    getStatus() {
        if (!this.eventSource) return 'closed';
        
        switch (this.eventSource.readyState) {
            case EventSource.CONNECTING:
                return 'connecting';
            case EventSource.OPEN:
                return 'open';
            case EventSource.CLOSED:
                return 'closed';
            default:
                return 'unknown';
        }
    }
}

// Export for use in other modules
window.SSEClient = SSEClient;
