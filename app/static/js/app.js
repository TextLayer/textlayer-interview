class TextLayerChat {
    constructor() {
        this.currentThreadId = null;
        this.threads = [];
        this.messages = [];
        this.apiBase = '/v1';
        
        this.initializeElements();
        this.bindEvents();
        this.loadThreads();
    }

    initializeElements() {
        // UI Elements
        this.threadsContainer = document.getElementById('threads-list');
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        // this.newThreadBtn = document.getElementById('new-thread-btn'); // Removed
        this.clearChatBtn = document.getElementById('clear-chat-btn');
        this.currentThreadTitle = document.getElementById('current-thread-title');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.threadsLoading = document.getElementById('threads-loading');
    }

    bindEvents() {
        // Send message events
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });

        // Thread management - New Chat functionality removed
        this.clearChatBtn.addEventListener('click', () => this.clearCurrentChat());
    }

    async loadThreads() {
        try {
            this.threadsLoading.style.display = 'block';
            const response = await fetch(`${this.apiBase}/threads/`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.threads = data.threads || [];
            this.renderThreads();
        } catch (error) {
            console.error('Error loading threads:', error);
            this.showError('Failed to load threads. Please refresh the page.');
        } finally {
            this.threadsLoading.style.display = 'none';
        }
    }

    renderThreads() {
        if (this.threads.length === 0) {
            this.threadsContainer.innerHTML = `
                <div class="loading">
                    <i class="fas fa-comments"></i> Ready to chat with AI!
                </div>
            `;
            // Enable input for direct chatting without thread management
            this.enableInput();
            this.currentThreadTitle.textContent = 'AI Chat';
            this.currentThreadId = 'default-thread'; // Use a default thread ID
            return;
        }

        this.threadsContainer.innerHTML = this.threads.map(thread => `
            <div class="thread-item" data-thread-id="${thread.id}" onclick="app.selectThread('${thread.id}')">
                <div class="thread-title">${this.truncateText(thread.title || 'Chat', 25)}</div>
                <div class="thread-preview">${this.truncateText(thread.preview || 'No messages yet', 35)}</div>
                <div class="thread-date">${this.formatDate(thread.created_at)}</div>
            </div>
        `).join('');
        
        // Auto-select first thread if none is selected
        if (!this.currentThreadId && this.threads.length > 0) {
            this.selectThread(this.threads[0].id);
        }
    }

    async createNewThread() {
        try {
            this.showLoading(true);
            const response = await fetch(`${this.apiBase}/threads/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: 'New Chat',
                    metadata: {}
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const newThread = data.thread;
            
            this.threads.unshift(newThread);
            this.renderThreads();
            this.selectThread(newThread.id);
            
        } catch (error) {
            console.error('Error creating thread:', error);
            this.showError('Failed to create new thread. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    selectThread(threadId) {
        this.currentThreadId = threadId;
        const thread = this.threads.find(t => t.id === threadId);
        
        // Update UI
        document.querySelectorAll('.thread-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-thread-id="${threadId}"]`)?.classList.add('active');
        
        // Update header
        this.currentThreadTitle.textContent = thread?.title || 'Chat';
        
        // Enable input and controls
        this.enableInput();
        this.clearChatBtn.disabled = false;
        
        // Load messages for this thread
        this.loadMessages(threadId);
    }

    async loadMessages(threadId) {
        try {
            // For now, we'll start with empty messages since the API doesn't have message history
            // In a real implementation, you'd fetch messages from the thread
            this.messages = [];
            this.renderMessages();
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Failed to load messages.');
        }
    }

    renderMessages() {
        if (this.messages.length === 0) {
            this.messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h3>Start a conversation</h3>
                    <p>Type a message below to begin chatting with the AI.</p>
                </div>
            `;
            return;
        }

        this.messagesContainer.innerHTML = this.messages.map(message => `
            <div class="message ${message.role}">
                <div class="message-avatar">
                    <i class="fas fa-${message.role === 'user' ? 'user' : 'robot'}"></i>
                </div>
                <div class="message-content">
                    ${this.formatMessageContent(message.content)}
                    <div class="message-time">${this.formatTime(message.timestamp)}</div>
                </div>
            </div>
        `).join('');

        this.scrollToBottom();
    }

    async sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content || !this.currentThreadId) return;

        // Add user message to UI
        const userMessage = {
            role: 'user',
            content: content,
            timestamp: new Date()
        };
        
        this.messages.push(userMessage);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.renderMessages();

        // Disable input while processing
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;
        this.showLoading(true);

        try {
            // Prepare messages in the correct schema format
            const messagesForAPI = [
                ...this.messages.map(msg => ({
                    role: msg.role,
                    content: msg.content
                })),
                {
                    role: 'user',
                    content: content
                }
            ];

            const response = await fetch(`${this.apiBase}/threads/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: messagesForAPI
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // The backend returns the full conversation history
            // Extract the latest assistant message from the response
            const responseMessages = data.payload || data;
            const latestMessage = responseMessages[responseMessages.length - 1];
            
            if (latestMessage && latestMessage.role === 'assistant') {
                const aiMessage = {
                    role: 'assistant',
                    content: latestMessage.content || 'Sorry, I couldn\'t generate a response.',
                    timestamp: new Date()
                };
                
                this.messages.push(aiMessage);
                this.renderMessages();
            } else {
                // Fallback if response format is unexpected
                const aiMessage = {
                    role: 'assistant',
                    content: 'Sorry, I couldn\'t generate a response.',
                    timestamp: new Date()
                };
                
                this.messages.push(aiMessage);
                this.renderMessages();
            }
            
            // Update thread preview
            this.updateThreadPreview(this.currentThreadId, content);

        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
            
            // Remove the user message if sending failed
            this.messages.pop();
            this.renderMessages();
        } finally {
            // Re-enable input
            this.enableInput();
            this.showLoading(false);
        }
    }

    updateThreadPreview(threadId, lastMessage) {
        const thread = this.threads.find(t => t.id === threadId);
        if (thread) {
            thread.preview = this.truncateText(lastMessage, 35);
            this.renderThreads();
            // Re-select current thread to maintain active state
            document.querySelector(`[data-thread-id="${threadId}"]`)?.classList.add('active');
        }
    }

    clearCurrentChat() {
        if (!this.currentThreadId) return;
        
        if (confirm('Are you sure you want to clear this chat? This action cannot be undone.')) {
            this.messages = [];
            this.renderMessages();
        }
    }

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('show');
        } else {
            this.loadingOverlay.classList.remove('show');
        }
    }

    showError(message) {
        // Simple error display - in production, you'd want a proper toast/notification system
        alert(message);
    }

    enableInput() {
        // Enable input controls
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        this.messageInput.placeholder = "Type your message here...";
        this.messageInput.focus();
    }

    disableInput() {
        // Disable input controls
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;
        this.messageInput.placeholder = "Select a thread to start chatting...";
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    formatMessageContent(content) {
        // Basic formatting - convert line breaks to <br>
        return content.replace(/\n/g, '<br>');
    }

    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) return 'Today';
        if (diffDays === 2) return 'Yesterday';
        if (diffDays <= 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TextLayerChat();
});

// Handle connection errors gracefully
window.addEventListener('online', () => {
    console.log('Connection restored');
});

window.addEventListener('offline', () => {
    console.log('Connection lost');
});
