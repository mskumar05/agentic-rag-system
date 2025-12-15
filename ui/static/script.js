// Agentic RAG System - Frontend JavaScript

class AgenticRAGUI {
    constructor() {
        this.uploadedFiles = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateStats();
        this.autoResizeTextarea();
    }

    setupEventListeners() {
        // Upload area
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');

        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
            this.handleFileSelect(files);
        });

        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            this.handleFileSelect(files);
        });

        uploadBtn.addEventListener('click', () => this.uploadFiles());

        // Clear button
        document.getElementById('clear-btn').addEventListener('click', () => this.clearDocuments());

        // Chat input
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');

        userInput.addEventListener('input', () => {
            sendBtn.disabled = !userInput.value.trim();
        });

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (userInput.value.trim()) {
                    this.sendMessage();
                }
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());
    }

    handleFileSelect(files) {
        this.uploadedFiles = files;
        const uploadBtn = document.getElementById('upload-btn');

        if (files.length > 0) {
            uploadBtn.textContent = `Upload ${files.length} PDF${files.length > 1 ? 's' : ''}`;
            uploadBtn.disabled = false;
        } else {
            uploadBtn.textContent = 'Upload PDFs';
            uploadBtn.disabled = true;
        }
    }

    async uploadFiles() {
        if (this.uploadedFiles.length === 0) return;

        const uploadProgress = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const uploadBtn = document.getElementById('upload-btn');

        uploadProgress.classList.remove('hidden');
        uploadBtn.disabled = true;

        const formData = new FormData();
        for (const file of this.uploadedFiles) {
            formData.append('files', file);
        }

        try {
            progressText.textContent = 'Uploading files...';
            progressFill.style.width = '30%';

            const response = await fetch('/ingest/upload', {
                method: 'POST',
                body: formData
            });

            progressFill.style.width = '60%';
            progressText.textContent = 'Processing PDFs...';

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();

            progressFill.style.width = '100%';
            progressText.textContent = 'Complete!';

            // Show success message
            this.showNotification(
                `Successfully uploaded ${result.documents_processed} document(s) with ${result.total_chunks} chunks`,
                'success'
            );

            // Update UI
            await this.updateStats();
            this.uploadedFiles = [];
            document.getElementById('file-input').value = '';
            uploadBtn.textContent = 'Upload PDFs';

            // Enable chat if documents are loaded
            document.getElementById('user-input').disabled = false;

            setTimeout(() => {
                uploadProgress.classList.add('hidden');
                progressFill.style.width = '0%';
            }, 2000);

        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
            progressFill.style.width = '0%';
            uploadProgress.classList.add('hidden');
        } finally {
            uploadBtn.disabled = false;
        }
    }

    async updateStats() {
        try {
            const response = await fetch('/ingest/stats');
            const stats = await response.json();

            document.getElementById('stat-docs').textContent = stats.total_documents;
            document.getElementById('stat-chunks').textContent = stats.total_chunks;

            // Update document list
            const docList = document.getElementById('document-list');

            if (stats.total_documents > 0) {
                docList.innerHTML = '';
                for (const [docId, chunkCount] of Object.entries(stats.documents)) {
                    const docItem = document.createElement('div');
                    docItem.className = 'document-item';
                    docItem.textContent = `${docId} (${chunkCount} chunks)`;
                    docList.appendChild(docItem);
                }
            } else {
                docList.innerHTML = '<p class="empty-state">No documents uploaded yet</p>';
            }

            // Enable/disable send button based on documents
            const hasDocuments = stats.total_documents > 0;
            if (!hasDocuments) {
                document.getElementById('send-btn').disabled = true;
            }

        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    async clearDocuments() {
        if (!confirm('Are you sure you want to clear all documents?')) {
            return;
        }

        try {
            const response = await fetch('/ingest/clear', {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to clear documents');

            this.showNotification('All documents cleared', 'success');
            await this.updateStats();

            // Clear chat
            const chatContainer = document.getElementById('chat-container');
            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome to Agentic RAG</h2>
                    <p>Upload PDF documents and ask questions. The system will:</p>
                    <ul>
                        <li>Search your documents intelligently</li>
                        <li>Reason through complex queries</li>
                        <li>Provide citations and evidence</li>
                        <li>Verify answers for accuracy</li>
                    </ul>
                    <p class="hint">Start by uploading some PDF documents!</p>
                </div>
            `;

        } catch (error) {
            console.error('Error clearing documents:', error);
            this.showNotification('Error clearing documents', 'error');
        }
    }

    async sendMessage() {
        const userInput = document.getElementById('user-input');
        const query = userInput.value.trim();

        if (!query) return;

        // Add user message to chat
        this.addMessage(query, 'user');
        userInput.value = '';
        userInput.style.height = 'auto';

        // Show loading indicator
        const loadingId = this.addLoadingMessage();

        // Get settings
        const topK = parseInt(document.getElementById('top-k').value);
        const includeCitations = document.getElementById('citations-toggle').checked;

        try {
            const response = await fetch('/query/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    top_k: topK,
                    include_citations: includeCitations
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Query failed');
            }

            const result = await response.json();

            // Remove loading message
            this.removeMessage(loadingId);

            // Add bot response
            this.addBotMessage(result);

        } catch (error) {
            console.error('Query error:', error);
            this.removeMessage(loadingId);
            this.addMessage(`Error: ${error.message}`, 'bot');
        }
    }

    addMessage(text, sender) {
        const chatContainer = document.getElementById('chat-container');

        // Remove welcome message if present
        const welcomeMsg = chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(text)}</div>
            </div>
        `;

        chatContainer.appendChild(messageDiv);
        this.scrollToBottom();

        return messageDiv;
    }

    addBotMessage(result) {
        const chatContainer = document.getElementById('chat-container');

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';

        let confidenceClass = 'confidence-low';
        let confidenceText = 'Low';

        if (result.confidence >= 0.8) {
            confidenceClass = 'confidence-high';
            confidenceText = 'High';
        } else if (result.confidence >= 0.5) {
            confidenceClass = 'confidence-medium';
            confidenceText = 'Medium';
        }

        let html = `
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(result.answer)}</div>
                <span class="confidence-badge ${confidenceClass}">
                    Confidence: ${confidenceText} (${(result.confidence * 100).toFixed(0)}%)
                </span>
        `;

        // Add warning if present
        if (result.warning) {
            html += `<div class="warning-badge">WARNING: ${this.escapeHtml(result.warning)}</div>`;
        }

        // Add citations if present
        if (result.citations && result.citations.length > 0) {
            html += `
                <div class="citations">
                    <div class="citations-title">📚 Citations:</div>
            `;

            for (const citation of result.citations) {
                html += `
                    <div class="citation">
                        <div class="citation-source">
                            ${this.escapeHtml(citation.document_name)}
                            ${citation.page_number ? ` - Page ${citation.page_number}` : ''}
                        </div>
                        <div class="citation-text">"${this.escapeHtml(citation.chunk_text)}"</div>
                        <div class="citation-score">
                            Relevance: ${(citation.relevance_score * 100).toFixed(0)}%
                        </div>
                    </div>
                `;
            }

            html += '</div>';
        }

        // Add reasoning steps if enabled
        if (document.getElementById('reasoning-toggle').checked && result.reasoning_steps && result.reasoning_steps.length > 0) {
            html += `
                <div class="reasoning-steps">
                    <div class="reasoning-title" onclick="this.nextElementSibling.classList.toggle('hidden')">
                        🧠 Reasoning Steps (click to expand)
                    </div>
                    <div>
            `;

            for (const step of result.reasoning_steps) {
                html += `
                    <div class="reasoning-step">
                        <div class="step-header">Step ${step.step_number}: ${this.escapeHtml(step.action)}</div>
                        <div class="step-detail">💭 ${this.escapeHtml(step.thought)}</div>
                        <div class="step-detail">👁️ ${this.escapeHtml(step.observation)}</div>
                    </div>
                `;
            }

            html += '</div></div>';
        }

        html += '</div>';
        messageDiv.innerHTML = html;

        chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addLoadingMessage() {
        const chatContainer = document.getElementById('chat-container');

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.id = `loading-${Date.now()}`;

        loadingDiv.innerHTML = `
            <div class="message-content">
                <div class="loading">
                    <span>Thinking</span>
                    <div class="loading-dots">
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                    </div>
                </div>
            </div>
        `;

        chatContainer.appendChild(loadingDiv);
        this.scrollToBottom();

        return loadingDiv.id;
    }

    removeMessage(messageId) {
        const message = document.getElementById(messageId);
        if (message) {
            message.remove();
        }
    }

    scrollToBottom() {
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    autoResizeTextarea() {
        const textarea = document.getElementById('user-input');

        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Simple notification - could be enhanced with a toast library
        console.log(`[${type.toUpperCase()}] ${message}`);
        alert(message);
    }
}

// Initialize the UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AgenticRAGUI();
});
