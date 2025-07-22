// Chat functionality
class ChatInterface {
    constructor() {
        this.apiBase = '/v1/threads';
        this.messages = [];
        this.isProcessing = false;
        this.currentMessageId = 0;
        this.apiStatus = null;

        this.initializeElements();
        this.bindEvents();
        this.loadApiStatus();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatForm = document.getElementById('chatForm');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        this.loadingMessage = document.getElementById('loadingMessage');
        this.charCount = document.getElementById('charCount');
        this.errorModal = document.getElementById('errorModal');
        this.errorMessage = document.getElementById('errorMessage');
    }

    bindEvents() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Textarea auto-resize and character count
        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.autoResizeTextarea();
        });

        // Keyboard shortcuts
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Clear input on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearInput();
            }
        });
    }

    async loadApiStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            if (response.ok) {
                const data = await response.json();
                this.apiStatus = data.payload;
                this.updateApiStatusDisplay();
            }
        } catch (error) {
            console.error('Failed to load API status:', error);
        }
    }

    updateApiStatusDisplay() {
        if (!this.apiStatus) return;

        // Add status indicator to header or input footer
        const statusContainer = document.querySelector('.input-footer-left');
        if (statusContainer) {
            // Remove existing status indicator
            const existingStatus = statusContainer.querySelector('.api-status-indicator');
            if (existingStatus) {
                existingStatus.remove();
            }

            // Create new status indicator
            const statusIndicator = document.createElement('div');
            statusIndicator.className = 'api-status-indicator';

            const mode = this.apiStatus.mode;
            const isLocal = mode === 'LOCAL';
            const statusClass = isLocal ? 'local' : 'remote';
            const statusIcon = isLocal ? 'fas fa-laptop' : 'fas fa-cloud';
            const statusText = isLocal ? 'Local Processing' : 'Remote API';

            statusIndicator.innerHTML = `
                <div class="status-badge ${statusClass}">
                    <i class="${statusIcon}"></i>
                    <span>${statusText}</span>
                </div>
            `;

            statusContainer.appendChild(statusIndicator);
        }
    }

    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;

        if (count > 800) {
            this.charCount.style.color = '#dc3545';
        } else if (count > 600) {
            this.charCount.style.color = '#ffc107';
        } else {
            this.charCount.style.color = '#6c757d';
        }
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async sendMessage(messageText = null, forceStreaming = null) {
        const text = messageText || this.messageInput.value.trim();

        if (!text || this.isProcessing) return;

        // Check streaming preference
        const streamingToggle = document.getElementById('streamingToggle');
        const useStreaming = forceStreaming !== null ? forceStreaming :
                           (streamingToggle ? streamingToggle.checked : false);

        this.isProcessing = true;
        this.updateUIState(true);

        try {
            // Hide welcome message
            if (this.welcomeMessage) {
                this.welcomeMessage.style.display = 'none';
            }

            // Add user message
            const userMessage = {
                role: 'user',
                content: text,
                id: ++this.currentMessageId
            };

            this.messages.push(userMessage);
            this.addMessageToChat(userMessage);

            // Clear input
            if (!messageText) {
                this.clearInput();
            }

            if (useStreaming) {
                await this.sendStreamingMessage(text);
            } else {
                await this.sendRegularMessage(text);
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideLoading();
            this.showError('Failed to send message. Please try again.');
        } finally {
            this.isProcessing = false;
            this.updateUIState(false);
        }
    }

    async sendRegularMessage(text) {
        // Show loading
        this.showLoading();

        // Send only the new message to API (not the entire conversation)
        const response = await fetch(`${this.apiBase}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                messages: [
                    {
                        role: 'user',
                        content: text
                    }
                ]
            })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        // Hide loading
        this.hideLoading();

        // Process response
        if (data.payload && data.payload.length > 0) {
            const lastMessage = data.payload[data.payload.length - 1];
            if (lastMessage.role === 'assistant') {
                const assistantMessage = {
                    role: 'assistant',
                    content: lastMessage.content,
                    id: ++this.currentMessageId,
                    judgeEvaluation: lastMessage.judge_evaluation,
                    improvedByJudge: lastMessage.improved_by_judge
                };

                this.messages.push(assistantMessage);
                this.addMessageToChat(assistantMessage);
            }
        }
    }

    async sendStreamingMessage(text) {
        // Create placeholder for assistant message
        const assistantMessage = {
            role: 'assistant',
            content: '',
            id: ++this.currentMessageId,
            streaming: true
        };

        this.messages.push(assistantMessage);
        const messageElement = this.addMessageToChat(assistantMessage);
        const contentElement = messageElement.querySelector('.message-content');

        // Add streaming indicator
        contentElement.innerHTML = '<div class="streaming-status"><div class="status-icon"><i class="fas fa-cog fa-spin"></i></div><span class="status-text">Initializing...</span></div>';

        try {
            // Use fetch for streaming
            const response = await fetch(`${this.apiBase}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: [
                        {
                            role: 'user',
                            content: text
                        }
                    ]
                })
            });

            if (!response.ok) {
                throw new Error(`Streaming API Error: ${response.status} ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedContent = '';

            contentElement.innerHTML = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6); // Remove 'data: ' prefix
                            if (dataStr.trim() === '') continue;

                            const data = JSON.parse(dataStr);

                            switch (data.type) {
                                case 'message_start':
                                    contentElement.innerHTML = '';
                                    break;

                                case 'status':
                                    // Show detailed status instead of generic "AI is thinking"
                                    contentElement.innerHTML = `<div class="streaming-status">
                                        <div class="status-icon"><i class="fas fa-cog fa-spin"></i></div>
                                        <span class="status-text">${data.message}</span>
                                    </div>`;
                                    this.scrollToBottom();
                                    break;

                                case 'content_delta':
                                    // Remove status indicator and start showing content
                                    if (contentElement.querySelector('.streaming-status')) {
                                        contentElement.innerHTML = '';
                                    }
                                    accumulatedContent += data.delta.content;
                                    contentElement.innerHTML = this.formatAssistantMessage(accumulatedContent);
                                    this.scrollToBottom();
                                    break;

                                case 'message_complete':
                                    assistantMessage.content = data.message.content;
                                    assistantMessage.streaming = false;
                                    assistantMessage.finishReason = data.message.finish_reason;
                                    contentElement.innerHTML = this.formatAssistantMessage(data.message.content);
                                    return;

                                case 'error':
                                    contentElement.innerHTML = '<div class="error-message">Error: ' + data.message.content + '</div>';
                                    return;
                            }
                        } catch (parseError) {
                            console.error('Error parsing streaming data:', parseError, 'Data:', line);
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Error setting up streaming:', error);
            contentElement.innerHTML = '<div class="error-message">Failed to start streaming. Please try again.</div>';
        }
    }

    addMessageToChat(message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.role}`;
        messageElement.dataset.messageId = message.id;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = message.role === 'user' ?
            '<i class="fas fa-user"></i>' :
            '<i class="fas fa-robot"></i>';

        const content = document.createElement('div');
        content.className = 'message-content';

        // Process markdown and format content
        if (message.role === 'assistant') {
            content.innerHTML = this.formatAssistantMessage(message.content);

            // Add judge evaluation indicator if available
            if (message.judgeEvaluation || message.improvedByJudge) {
                const judgeIndicator = document.createElement('div');
                judgeIndicator.className = message.improvedByJudge ?
                    'judge-indicator improved' : 'judge-indicator';

                if (message.improvedByJudge) {
                    judgeIndicator.innerHTML = '<i class="fas fa-magic"></i>Response improved by AI Judge';
                } else if (message.judgeEvaluation) {
                    const score = message.judgeEvaluation.quality_score || 'N/A';
                    judgeIndicator.innerHTML = `<i class="fas fa-check-circle"></i>Quality Score: ${score}/10`;
                }

                content.appendChild(judgeIndicator);
            }
        } else {
            content.textContent = message.content;
        }

        messageElement.appendChild(avatar);
        messageElement.appendChild(content);

        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();

        return messageElement;
    }

    formatAssistantMessage(content) {
        try {
            // Try using marked.js if available
            if (typeof marked !== 'undefined') {
                // Configure marked with custom renderer
                marked.setOptions({
                    highlight: function(code, lang) {
                        // Basic SQL syntax highlighting
                        if (lang === 'sql') {
                            return code
                                .replace(/\b(SELECT|FROM|WHERE|JOIN|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH|AS|PARTITION BY|OVER|RANK|ROW_NUMBER|LAG|LEAD|SUM|AVG|COUNT|MAX|MIN|ROUND|FIRST_VALUE|LAST_VALUE)\b/gi, '<span style="color: #0066cc; font-weight: bold;">$1</span>')
                                .replace(/\b(AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|DESC|ASC|LIMIT|DISTINCT|CASE|WHEN|THEN|ELSE|END)\b/gi, '<span style="color: #cc6600; font-weight: bold;">$1</span>')
                                .replace(/\b(INNER|LEFT|RIGHT|FULL|OUTER)\b/gi, '<span style="color: #009900; font-weight: bold;">$1</span>');
                        }
                        return code;
                    },
                    breaks: true,
                    gfm: true
                });

                // Parse markdown and then enhance it
                let parsed = marked.parse(content);
                return this.enhanceFormattedContent(parsed);
            } else {
                // Fallback formatting with better code block handling
                return this.enhanceFormattedContent(this.basicMarkdownFormat(content));
            }
        } catch (error) {
            console.error('Error formatting message:', error);
            return this.escapeHtml(content);
        }
    }

    enhanceFormattedContent(htmlContent) {
        // Add copy buttons to code blocks and improve formatting
        let enhanced = htmlContent;

        // Enhanced download section handling
        enhanced = this.processDownloadSection(enhanced);

        // Wrap tables in responsive containers with headers (like SQL code blocks)
        enhanced = enhanced.replace(/<table([^>]*)>([\s\S]*?)<\/table>/g, (match, tableAttrs, tableContent) => {
            // Generate unique ID for table actions
            const tableId = 'table-' + Math.random().toString(36).substr(2, 9);

            // Count rows to determine if we need special handling
            const rows = tableContent.split('<tr>').length - 1;
            const shouldTruncate = rows > 5;

            // Build table with header (similar to SQL code blocks)
            let result = `<div class="table-block-container">`;

            // Add table header with actions (like SQL header)
            result += `<div class="table-block-header">`;
            result += `<span class="table-language">Query Results (${rows} rows)</span>`;
            result += `<div class="table-actions-header">`;
            result += `<button class="view-table-btn" onclick="showDataPopup('${tableId}', '${rows} rows')" title="View in popup">`;
            result += `<i class="fas fa-table"></i> View Tabular Form</button>`;
            result += `<button class="download-csv-btn" onclick="downloadTableAsCSV('${tableId}', 'query_results.csv')" title="Download CSV">`;
            result += `<i class="fas fa-download"></i> CSV</button>`;
            result += `</div>`;
            result += `</div>`;

            // Add table container
            result += `<div class="table-container">`;

            if (shouldTruncate) {
                // Show only first 3 rows inline
                const tableRows = tableContent.split('<tr>');
                const headerRow = tableRows[1] || ''; // First row after split
                const dataRows = tableRows.slice(2, 5); // Next 3 rows
                const truncatedContent = headerRow + dataRows.join('<tr>');

                result += `<table${tableAttrs}>${truncatedContent}</table>`;
                result += `<div class="table-truncate-notice">`;
                result += `<i class="fas fa-info-circle"></i>`;
                result += `Showing first 3 rows of ${rows} total rows. Click "View Tabular Form" for all data.`;
                result += `</div>`;
            } else {
                result += `<table${tableAttrs}>${tableContent}</table>`;
            }

            result += `</div>`; // Close table-container
            result += `</div>`; // Close table-block-container

            // Add hidden full table data for popup
            result += `<div id="${tableId}" class="hidden-data" style="display: none;">`;
            result += `<table${tableAttrs}>${tableContent}</table>`;
            result += `</div>`;

            return result;
        });

        // Enhanced code block handling with popup for long SQL
        // Handle both language-sql and regular SQL code blocks
        enhanced = enhanced.replace(/<pre><code(?:\s+class="language-sql")?(?:\s+class="sql")?>([\s\S]*?)<\/code><\/pre>/g, (match, code) => {
            // Check if this is actually an SQL code block
            const isSQL = match.includes('language-sql') || match.includes('class="sql"') ||
                         code.toLowerCase().includes('select') || code.toLowerCase().includes('with') ||
                         code.toLowerCase().includes('from') || code.toLowerCase().includes('insert');

            if (!isSQL) return match; // Skip non-SQL blocks

            const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
            const cleanCode = code.replace(/<[^>]*>/g, '').trim(); // Remove HTML tags and trim
            const codeLines = cleanCode.split('\n').filter(line => line.trim() !== '');
            const lineCount = codeLines.length;

            console.log(`SQL Block detected: ${lineCount} lines, code preview:`, cleanCode.substring(0, 100)); // Debug log

            // If SQL is long (>15 lines), show in popup
            if (lineCount > 15) {
                const truncatedCode = codeLines.slice(0, 8).join('\n');
                return `
                    <div class="code-block-container long-sql">
                        <div class="code-block-header">
                            <span class="code-language">SQL (${lineCount} lines)</span>
                            <div class="code-actions">
                                <button class="view-button" onclick="showCodePopup('${codeId}', 'SQL Query')" title="View full code">
                                    <i class="fas fa-expand-alt"></i> View Full Code
                                </button>
                                <button class="copy-button" onclick="copyCode('${codeId}')" title="Copy code">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </div>
                        <div class="code-block sql-code truncated">
                            <pre><code id="${codeId}" data-code="${this.escapeHtml(cleanCode)}">${code.split('\n').slice(0, 8).join('\n')}</code></pre>
                            <div class="code-truncate-notice">
                                <i class="fas fa-info-circle"></i>
                                Code truncated. Click "View Full Code" to see complete SQL query.
                            </div>
                        </div>
                        <div class="hidden-full-code" id="${codeId}-full" style="display: none;">${code}</div>
                    </div>
                `;
            } else {
                // Regular short SQL block
                return `
                    <div class="code-block-container">
                        <div class="code-block-header">
                            <span class="code-language">SQL</span>
                            <button class="copy-button" onclick="copyCode('${codeId}')" title="Copy code">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                        <div class="code-block sql-code">
                            <pre><code id="${codeId}" data-code="${this.escapeHtml(cleanCode)}">${code}</code></pre>
                        </div>
                    </div>
                `;
            }
        });

        // Handle regular code blocks (non-SQL) that weren't processed above
        enhanced = enhanced.replace(/<pre><code(?:\s+class="[^"]*")?>([\s\S]*?)<\/code><\/pre>/g, (match, code) => {
            // Skip if already processed (contains code-block-container)
            if (enhanced.indexOf(match) !== enhanced.lastIndexOf(match)) return match;

            // Skip SQL blocks that should have been handled above
            const isSQL = code.toLowerCase().includes('select') || code.toLowerCase().includes('with') ||
                         code.toLowerCase().includes('from') || code.toLowerCase().includes('insert');
            if (isSQL) return match;

            const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
            const cleanCode = code.replace(/<[^>]*>/g, ''); // Remove HTML tags for copying
            return `
                <div class="code-block-container">
                    <div class="code-block-header">
                        <span class="code-language">Code</span>
                        <button class="copy-button" onclick="copyCode('${codeId}')" title="Copy code">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                    <div class="code-block">
                        <pre><code id="${codeId}" data-code="${this.escapeHtml(cleanCode)}">${code}</code></pre>
                    </div>
                </div>
            `;
        });

        // Improve list formatting with proper indentation
        enhanced = enhanced.replace(/<ul>([\s\S]*?)<\/ul>/g, (match, content) => {
            return `<ul class="formatted-list">${content}</ul>`;
        });

        enhanced = enhanced.replace(/<ol>([\s\S]*?)<\/ol>/g, (match, content) => {
            return `<ol class="formatted-list">${content}</ol>`;
        });

        // Enhanced nested list handling
        enhanced = enhanced.replace(/<li>([\s\S]*?)<\/li>/g, (match, content) => {
            // Check if this list item contains nested lists
            if (content.includes('<ul>') || content.includes('<ol>')) {
                return `<li class="list-item-nested">${content}</li>`;
            }
            return `<li class="list-item">${content}</li>`;
        });

        return enhanced;
    }

    processDownloadSection(htmlContent) {
        // Process download file sections but don't show them at the top
        // Users prefer inline download/copy options with code blocks
        let processed = htmlContent;

        // Remove download sections from display but keep the files generated
        processed = processed.replace(
            /## 📥 \*\*Download Files\*\*([\s\S]*?)(?=##|$)/g,
            '' // Remove the entire download section
        );

        return processed;
    }

    basicMarkdownFormat(text) {
        return text
            // Handle code blocks first (triple backticks)
            .replace(/```(sql|SQL)?\n?([\s\S]*?)```/g, (match, lang, code) => {
                const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
                const cleanCode = code.trim();
                const codeLines = cleanCode.split('\n').filter(line => line.trim() !== '');
                const lineCount = codeLines.length;
                const isSQL = (lang && lang.toLowerCase() === 'sql') ||
                             cleanCode.toLowerCase().includes('select') ||
                             cleanCode.toLowerCase().includes('with') ||
                             cleanCode.toLowerCase().includes('from') ||
                             cleanCode.toLowerCase().includes('insert') ||
                             cleanCode.toLowerCase().includes('update') ||
                             cleanCode.toLowerCase().includes('create');

                console.log(`Basic format SQL Block: ${lineCount} lines, isSQL: ${isSQL}, code preview:`, cleanCode.substring(0, 100)); // Debug log

                const formattedCode = code
                    .replace(/\b(SELECT|FROM|WHERE|JOIN|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH|AS|PARTITION BY|OVER|RANK|ROW_NUMBER|LAG|LEAD|SUM|AVG|COUNT|MAX|MIN|ROUND|FIRST_VALUE|LAST_VALUE)\b/gi, '<span style="color: #0066cc; font-weight: bold;">$1</span>')
                    .replace(/\b(AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|DESC|ASC|LIMIT|DISTINCT|CASE|WHEN|THEN|ELSE|END)\b/gi, '<span style="color: #cc6600; font-weight: bold;">$1</span>')
                    .replace(/\b(INNER|LEFT|RIGHT|FULL|OUTER)\b/gi, '<span style="color: #009900; font-weight: bold;">$1</span>');

                // If SQL is long (>15 lines), show in popup
                if (isSQL && lineCount > 15) {
                    const truncatedCode = codeLines.slice(0, 8).join('\n');
                    return `
                        <div class="code-block-container long-sql">
                            <div class="code-block-header">
                                <span class="code-language">SQL (${lineCount} lines)</span>
                                <div class="code-actions">
                                    <button class="view-button" onclick="showCodePopup('${codeId}', 'SQL Query')" title="View full code">
                                        <i class="fas fa-expand-alt"></i> View Full Code
                                    </button>
                                    <button class="copy-button" onclick="copyCode('${codeId}')" title="Copy code">
                                        <i class="fas fa-copy"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="code-block sql-code truncated">
                                <pre><code id="${codeId}" data-code="${this.escapeHtml(cleanCode)}">${formattedCode.split('\n').slice(0, 8).join('\n')}</code></pre>
                                <div class="code-truncate-notice">
                                    <i class="fas fa-info-circle"></i>
                                    Code truncated. Click "View Full Code" to see complete SQL query.
                                </div>
                            </div>
                            <div class="hidden-full-code" id="${codeId}-full" style="display: none;">${formattedCode}</div>
                        </div>
                    `;
                } else {
                    // Regular short code block
                    return `
                        <div class="code-block-container">
                            <div class="code-block-header">
                                <span class="code-language">${isSQL ? 'SQL' : 'Code'}</span>
                                <button class="copy-button" onclick="copyCode('${codeId}')" title="Copy code">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                            <div class="code-block sql-code">
                                <pre><code id="${codeId}" data-code="${this.escapeHtml(cleanCode)}">${formattedCode}</code></pre>
                            </div>
                        </div>
                    `;
                }
            })
            // Handle inline code
            .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
            // Enhanced list formatting
            .replace(/^(\d+\.\s+)(.+)$/gm, '<li class="list-item">$2</li>')
            .replace(/^(-|\*)\s+(.+)$/gm, '<li class="list-item">$2</li>')
            .replace(/^\s+(-|\*)\s+(.+)$/gm, '<li class="list-item-nested">$2</li>')
            // Handle bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Handle line breaks
            .replace(/\n/g, '<br>')
            // Handle table formatting with responsive wrapper
            .replace(/(\|.+\|(?:\r?\n|\r)*)+/g, (match) => {
                const lines = match.trim().split(/\r?\n|\r/);
                let tableHtml = '';
                let isHeaderProcessed = false;

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (!line || !line.includes('|')) continue;

                    // Skip separator lines (like |---|---|)
                    if (line.match(/^\|[\s\-\|]+\|$/)) continue;

                    const cells = line.split('|').filter(cell => cell.trim() !== '').map(cell => cell.trim());
                    if (cells.length === 0) continue;

                    const tag = !isHeaderProcessed ? 'th' : 'td';
                    const row = `<tr>${cells.map(cell => `<${tag}>${cell}</${tag}>`).join('')}</tr>`;
                    tableHtml += row;

                    if (!isHeaderProcessed) isHeaderProcessed = true;
                }

                if (tableHtml) {
                    return `<div class="table-container"><table class="data-table">${tableHtml}</table></div>`;
                }
                return match;
            });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showLoading() {
        this.loadingMessage.style.display = 'flex';
        this.scrollToBottom();
    }

    hideLoading() {
        this.loadingMessage.style.display = 'none';
    }

    updateUIState(processing) {
        this.sendButton.disabled = processing;
        this.messageInput.disabled = processing;

        if (processing) {
            this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }

    clearInput() {
        this.messageInput.value = '';
        this.updateCharCount();
        this.autoResizeTextarea();
        this.messageInput.focus();
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'flex';
    }

    hideError() {
        this.errorModal.style.display = 'none';
    }
}

// Global functions for template interaction
let chatInterface;

function initializeChat() {
    chatInterface = new ChatInterface();

    // Focus on input
    if (chatInterface.messageInput) {
        chatInterface.messageInput.focus();
    }
}

function sendExampleQuery(query) {
    if (chatInterface && !chatInterface.isProcessing) {
        // Remove any extra quotes from the query
        const cleanQuery = query.replace(/^["']|["']$/g, '');
        chatInterface.sendMessage(cleanQuery);
    }
}

function closeErrorModal() {
    if (chatInterface) {
        chatInterface.hideError();
    }
}

// Global function for copying code
function copyCode(codeId) {
    const codeElement = document.getElementById(codeId);
    if (!codeElement) return;

    const code = codeElement.getAttribute('data-code') || codeElement.textContent;

    navigator.clipboard.writeText(code).then(() => {
        // Show feedback
        const button = codeElement.closest('.code-block-container').querySelector('.copy-button');
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.style.color = '#10a37f';

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = code;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
    });
}

// Global function for showing code popup
function showCodePopup(codeId, title) {
    console.log('Opening popup for:', codeId);

    const codeElement = document.getElementById(codeId);
    if (!codeElement) {
        alert('Code element not found: ' + codeId);
        return;
    }

    // Get code content with multiple fallback methods
    let codeContent = '';

    // Method 1: data-code attribute
    if (codeElement.dataset.code) {
        codeContent = codeElement.dataset.code;
        console.log('Got code from dataset, length:', codeContent.length);
    }

    // Method 2: textContent
    if (!codeContent) {
        codeContent = codeElement.textContent || '';
        console.log('Got code from textContent, length:', codeContent.length);
    }

    // Method 3: innerText
    if (!codeContent) {
        codeContent = codeElement.innerText || '';
        console.log('Got code from innerText, length:', codeContent.length);
    }

    // Method 4: hidden element
    const hiddenElement = document.getElementById(codeId + '-full');
    if (!codeContent && hiddenElement) {
        codeContent = hiddenElement.textContent || hiddenElement.innerText || '';
        console.log('Got code from hidden element, length:', codeContent.length);
    }

    // Method 5: parent element search
    if (!codeContent) {
        const parent = codeElement.closest('.code-block-container');
        if (parent) {
            const allText = parent.textContent || parent.innerText || '';
            // Try to extract SQL-like content
            if (allText.toLowerCase().includes('select') || allText.toLowerCase().includes('with')) {
                codeContent = allText;
                console.log('Got code from parent search, length:', codeContent.length);
            }
        }
    }

    // Last resort: use sample SQL if nothing found
    if (!codeContent || codeContent.trim().length < 10) {
        codeContent = `-- Sample SQL Query
SELECT
    "Sales Manager",
    COUNT(*) as customer_count
FROM customer
WHERE "Sales Manager" IS NOT NULL
GROUP BY "Sales Manager"
ORDER BY customer_count DESC;

-- Note: Original code content could not be extracted
-- This is a sample query for demonstration`;
        console.log('Using fallback sample code');
    }

    console.log('Final code content preview:', codeContent.substring(0, 100));

    // Create simple, bulletproof popup
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.8);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: Arial, sans-serif;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #1a1a2e;
        color: #ffffff;
        border-radius: 8px;
        width: 90vw;
        max-width: 1000px;
        max-height: 80vh;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    `;

    const header = document.createElement('div');
    header.style.cssText = `
        padding: 1rem;
        border-bottom: 1px solid #333;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f1419;
        color: #ffffff;
    `;

    const titleEl = document.createElement('h3');
    titleEl.style.cssText = `
        margin: 0;
        color: #ffffff;
        font-size: 1.1rem;
    `;
    titleEl.textContent = title || 'SQL Code';

    const closeBtn = document.createElement('button');
    closeBtn.style.cssText = `
        background: #ff4444;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9rem;
    `;
    closeBtn.textContent = 'Close';
    closeBtn.onclick = () => {
        document.body.removeChild(modal);
        document.body.style.overflow = '';
    };

    const copyBtn = document.createElement('button');
    copyBtn.style.cssText = `
        background: #10a37f;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9rem;
        margin-right: 0.5rem;
    `;
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(codeContent).then(() => {
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = 'Copy';
            }, 2000);
        }).catch(() => {
            // Fallback
            const textarea = document.createElement('textarea');
            textarea.value = codeContent;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = 'Copy';
            }, 2000);
        });
    };

    const buttons = document.createElement('div');
    buttons.appendChild(copyBtn);
    buttons.appendChild(closeBtn);

    header.appendChild(titleEl);
    header.appendChild(buttons);

    const body = document.createElement('div');
    body.style.cssText = `
        padding: 1rem;
        overflow-y: auto;
        max-height: 60vh;
        background: #1a1a2e;
    `;

    const pre = document.createElement('pre');
    pre.style.cssText = `
        margin: 0;
        padding: 1rem;
        background: #0f1419;
        color: #ffffff;
        border-radius: 4px;
        overflow-x: auto;
        font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        font-size: 14px;
        line-height: 1.4;
        white-space: pre-wrap;
        word-wrap: break-word;
        border: 1px solid #333;
    `;
    pre.textContent = codeContent;

    body.appendChild(pre);
    content.appendChild(header);
    content.appendChild(body);
    modal.appendChild(content);

    // Close on backdrop click
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
            document.body.style.overflow = '';
        }
    };

    // Close on ESC key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            document.body.removeChild(modal);
            document.body.style.overflow = '';
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    console.log('Popup created and displayed');
}

// Global function for closing code popup
function closeCodePopup() {
    const modal = document.querySelector('.code-popup-modal');
    if (modal) {
        document.body.removeChild(modal);
        document.body.style.overflow = '';
    }
}

// Global function for copying code from popup
function copyCodeFromPopup(codeId) {
    const codeElement = document.getElementById(codeId);
    if (!codeElement) return;

    const code = codeElement.getAttribute('data-code') || codeElement.textContent;

    navigator.clipboard.writeText(code).then(() => {
        // Show feedback
        const button = document.querySelector('.popup-copy-btn');
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.style.backgroundColor = '#10a37f';

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code: ', err);
    });
}

// Global function for downloading code
function downloadCode(codeElementId, filename = 'query.sql') {
    let code = '';

    if (typeof codeElementId === 'string' && codeElementId.includes('-popup')) {
        // Get code from popup element
        const codeElement = document.getElementById(codeElementId);
        if (codeElement) {
            code = codeElement.getAttribute('data-code') || codeElement.textContent;
        }
    } else {
        // Backward compatibility - if passed code directly
        code = codeElementId;
    }

    if (!code) {
        console.error('No code found to download');
        return;
    }

    const blob = new Blob([code], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Global function for downloading code from popup
function downloadCodeFromPopup(codeElementId, filename = 'query.sql') {
    const codeElement = document.getElementById(codeElementId);
    if (!codeElement) {
        console.error('Code element not found for download:', codeElementId);
        return;
    }

    const code = codeElement.getAttribute('data-code') || codeElement.textContent;

    if (!code) {
        console.error('No code found to download');
        return;
    }

    const blob = new Blob([code], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Function to convert markdown table to HTML
function convertMarkdownTableToHTML(markdownTable) {
    try {
        console.log('Converting markdown table:', markdownTable.substring(0, 200));

        const lines = markdownTable.trim().split(/\r?\n/).filter(line => line.trim());
        if (lines.length < 2) return markdownTable;

        let html = '<table class="excel-table">';
        let headerProcessed = false;
        let rowCount = 0;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();

            // Skip separator lines (like |---|---|)
            if (line.match(/^\|[\s\-\|\+\:]+\|$/)) {
                continue;
            }

            if (!line.includes('|')) continue;

            // Split by | and clean up cells
            let cells = line.split('|');

            // Remove empty cells from start and end (common in markdown)
            if (cells[0].trim() === '') cells.shift();
            if (cells[cells.length - 1].trim() === '') cells.pop();

            cells = cells.map(cell => cell.trim()).filter(cell => cell !== '');

            if (cells.length === 0) continue;

            const tag = !headerProcessed ? 'th' : 'td';
            const escapedCells = cells.map(cell => {
                // Basic HTML escaping
                return cell.replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;')
                          .replace(/"/g, '&quot;')
                          .replace(/'/g, '&#39;');
            });

            const row = `<tr>${escapedCells.map(cell => `<${tag}>${cell}</${tag}>`).join('')}</tr>`;
            html += row;
            rowCount++;

            if (!headerProcessed) headerProcessed = true;
        }

        html += '</table>';

        if (rowCount === 0) {
            console.log('No valid table rows found, returning original content');
            return markdownTable;
        }

        console.log(`Converted HTML table with ${rowCount} rows:`, html.substring(0, 200));
        return html;

    } catch (error) {
        console.error('Error converting markdown table:', error);
        return markdownTable; // Return original content on error
    }
}

// Global function for showing data popup
function showDataPopup(popupId, title) {
    console.log('Opening data popup for:', popupId);

    const dataElement = document.getElementById(popupId);
    if (!dataElement) {
        alert('Data element not found: ' + popupId);
        return;
    }

    // Get data content and convert markdown table to proper HTML
    let dataContent = dataElement.innerHTML || dataElement.textContent || '';

    if (!dataContent || dataContent.trim().length < 10) {
        dataContent = 'No data available';
        console.log('No data content found');
    }

    console.log('Raw data content preview:', dataContent.substring(0, 100));

    // Convert markdown table to HTML if needed
    if (dataContent.includes('|') && dataContent.includes('---')) {
        console.log('Converting markdown table to HTML');
        dataContent = convertMarkdownTableToHTML(dataContent);
    }

    console.log('Processed data content preview:', dataContent.substring(0, 100));

    // Create popup modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.8);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: Arial, sans-serif;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #ffffff;
        color: #333333;
        border-radius: 12px;
        width: 95vw;
        max-width: 1400px;
        max-height: 90vh;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
    `;

    const header = document.createElement('div');
    header.style.cssText = `
        padding: 1.25rem 1.5rem;
        border-bottom: 2px solid #e9ecef;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        color: #495057;
        border-radius: 12px 12px 0 0;
    `;

    const titleEl = document.createElement('h3');
    titleEl.style.cssText = `
        margin: 0;
        color: #495057;
        font-size: 1.2rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    `;
    titleEl.innerHTML = `<i class="fas fa-table" style="color: #10a37f;"></i>Query Results - ${title}`;

    const closeBtn = document.createElement('button');
    closeBtn.style.cssText = `
        background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 2px 4px rgba(108, 117, 125, 0.2);
    `;
    closeBtn.innerHTML = '<i class="fas fa-times"></i>Close';
    closeBtn.onclick = () => {
        document.body.removeChild(modal);
        document.body.style.overflow = '';
    };

    const exportBtn = document.createElement('button');
    exportBtn.style.cssText = `
        background: linear-gradient(135deg, #10a37f 0%, #0d8f72 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9rem;
        margin-right: 0.75rem;
        font-weight: 500;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 2px 4px rgba(16, 163, 127, 0.2);
    `;
    exportBtn.innerHTML = '<i class="fas fa-download"></i>Export CSV';
    exportBtn.onclick = () => {
        // Convert table data to CSV - simplified for now
        const tableText = dataElement.textContent || '';
        const blob = new Blob([tableText], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'query-results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        exportBtn.innerHTML = '<i class="fas fa-check"></i>Exported!';
        exportBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        setTimeout(() => {
            exportBtn.innerHTML = '<i class="fas fa-download"></i>Export CSV';
            exportBtn.style.background = 'linear-gradient(135deg, #10a37f 0%, #0d8f72 100%)';
        }, 2000);
    };

    // Add hover effects for buttons
    exportBtn.addEventListener('mouseenter', function() {
        this.style.background = 'linear-gradient(135deg, #0d8f72 0%, #0a7860 100%)';
        this.style.transform = 'translateY(-1px)';
        this.style.boxShadow = '0 4px 8px rgba(16, 163, 127, 0.3)';
    });

    exportBtn.addEventListener('mouseleave', function() {
        this.style.background = 'linear-gradient(135deg, #10a37f 0%, #0d8f72 100%)';
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 4px rgba(16, 163, 127, 0.2)';
    });

    closeBtn.addEventListener('mouseenter', function() {
        this.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
        this.style.transform = 'translateY(-1px)';
        this.style.boxShadow = '0 4px 8px rgba(220, 53, 69, 0.3)';
    });

    closeBtn.addEventListener('mouseleave', function() {
        this.style.background = 'linear-gradient(135deg, #6c757d 0%, #5a6268 100%)';
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 4px rgba(108, 117, 125, 0.2)';
    });

    const buttons = document.createElement('div');
    buttons.appendChild(exportBtn);
    buttons.appendChild(closeBtn);

    header.appendChild(titleEl);
    header.appendChild(buttons);

    const body = document.createElement('div');
    body.style.cssText = `
        padding: 1.5rem;
        overflow: auto;
        max-height: 75vh;
        background: #fafafa;
        border-radius: 0 0 12px 12px;
    `;

    // Create container for the data with proper table styling
    const dataContainer = document.createElement('div');
    dataContainer.style.cssText = `
        overflow: auto;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        max-height: 65vh;
        padding: 1rem;
    `;
    dataContainer.innerHTML = dataContent;

    // If no table elements found, try to create one from the text content
    if (!dataContainer.querySelector('table') && dataContent.includes('|')) {
        console.log('No table found, attempting to create from text content');
        const textContent = dataContainer.textContent || dataContainer.innerText || '';
        if (textContent.includes('|')) {
            const convertedHTML = convertMarkdownTableToHTML(textContent);
            dataContainer.innerHTML = convertedHTML;
        }
    }

        // Apply Enhanced Excel-like table styling to any tables in the data
    const tables = dataContainer.querySelectorAll('table, .excel-table');
    tables.forEach(table => {
        table.style.cssText = `
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 11px;
            font-family: 'Calibri', 'Segoe UI', 'Arial', sans-serif;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: 1px solid #d0d7de;
            border-radius: 0;
            overflow: hidden;
        `;

        // Style headers to look exactly like Excel
        const headers = table.querySelectorAll('th');
        headers.forEach((th, index) => {
            th.style.cssText = `
                background: linear-gradient(180deg, #f6f8fa 0%, #eef2f5 100%);
                padding: 8px 12px;
                border-right: 1px solid #d0d7de;
                border-bottom: 1px solid #d0d7de;
                font-weight: 600;
                text-align: center;
                color: #24292f;
                font-size: 11px;
                text-transform: none;
                letter-spacing: 0;
                position: sticky;
                top: 0;
                z-index: 10;
                min-width: 80px;
                white-space: nowrap;
                border-top: 1px solid #d0d7de;
            `;

            // Remove border-right from last header
            if (index === headers.length - 1) {
                th.style.borderRight = 'none';
            }
        });

        // Style data cells with Excel-like appearance
        const rows = table.querySelectorAll('tr');
        rows.forEach((row, rowIndex) => {
            if (rowIndex === 0) return; // Skip header row

            const isEven = rowIndex % 2 === 0;
            const cells = row.querySelectorAll('td');

            cells.forEach((td, cellIndex) => {
                td.style.cssText = `
                    padding: 6px 12px;
                    border-right: 1px solid #d0d7de;
                    border-bottom: 1px solid #d0d7de;
                    color: #24292f;
                    background: ${isEven ? '#ffffff' : '#f6f8fa'};
                    vertical-align: middle;
                    line-height: 1.2;
                    transition: all 0.1s ease;
                    font-size: 11px;
                    min-height: 20px;
                    position: relative;
                `;

                // Remove border-right from last cell
                if (cellIndex === cells.length - 1) {
                    td.style.borderRight = 'none';
                }

                // Add Excel-style selection effect
                td.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#dbeafe';
                    this.style.cursor = 'cell';
                    this.style.outline = '2px solid #2563eb';
                    this.style.outlineOffset = '-1px';
                });

                td.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = isEven ? '#ffffff' : '#f6f8fa';
                    this.style.outline = 'none';
                });

                // Enhanced numeric formatting
                const cellText = td.textContent.trim();
                if (/^[\d.,\-%$€£¥]+$/.test(cellText) || cellText.includes('%') || cellText.includes('$') || cellText.includes('€') || cellText.includes('£')) {
                    td.style.textAlign = 'right';
                    td.style.fontFamily = 'Consolas, "Courier New", monospace';
                    td.style.fontWeight = '400';
                    td.style.paddingRight = '16px';

                    // Color negative numbers red
                    if (cellText.includes('-') || (cellText.startsWith('(') && cellText.endsWith(')'))) {
                        td.style.color = '#dc3545';
                    }
                } else {
                    td.style.textAlign = 'left';
                }

                // Special formatting for dates
                if (/^\d{4}-\d{2}-\d{2}/.test(cellText) || /^\d{2}\/\d{2}\/\d{4}/.test(cellText)) {
                    td.style.fontFamily = 'Consolas, "Courier New", monospace';
                    td.style.textAlign = 'center';
                }
            });

            // Add Excel-style row selection effect
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#e6f3ff';
                cells.forEach(cell => {
                    cell.style.backgroundColor = '#e6f3ff';
                });
            });

            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
                cells.forEach((cell, cellIndex) => {
                    const isEven = rowIndex % 2 === 0;
                    cell.style.backgroundColor = isEven ? '#ffffff' : '#f6f8fa';
                });
            });

            // Add click selection effect
            row.addEventListener('click', function() {
                // Remove previous selections
                table.querySelectorAll('tr').forEach(r => r.classList.remove('selected-row'));
                this.classList.add('selected-row');

                cells.forEach(cell => {
                    cell.style.backgroundColor = '#cce7ff';
                    cell.style.borderColor = '#2563eb';
                });
            });
        });

        // Add Excel-style outer border
        table.style.border = '2px solid #8b949e';

        // Add selection styling
        const style = document.createElement('style');
        style.textContent = `
            .selected-row td {
                background-color: #cce7ff !important;
                border-color: #2563eb !important;
            }
        `;
        document.head.appendChild(style);
    });

    body.appendChild(dataContainer);
    content.appendChild(header);
    content.appendChild(body);
    modal.appendChild(content);

    // Close on backdrop click
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
            document.body.style.overflow = '';
        }
    };

    // Close on ESC key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            document.body.removeChild(modal);
            document.body.style.overflow = '';
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    console.log('Data popup created and displayed');
}

// Handle ESC key to close popup
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeCodePopup();
    }
});

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChat);
} else {
    initializeChat();
}

// Global function for downloading table as CSV
function downloadTableAsCSV(dataElementId, filename = 'data.csv') {
    const dataElement = document.getElementById(dataElementId);
    if (!dataElement) {
        console.error('Data element not found:', dataElementId);
        return;
    }

    // Get table content from the hidden element
    const tableContent = dataElement.textContent || dataElement.innerText || '';

    // Convert markdown table to CSV
    const lines = tableContent.trim().split('\n');
    let csvContent = '';

    for (const line of lines) {
        if (line.includes('|') && !line.match(/^\|[\s\-\|]+\|$/)) {
            // Process table row
            const cells = line.split('|').filter(cell => cell.trim() !== '').map(cell => cell.trim());
            if (cells.length > 0) {
                // Escape commas and quotes in CSV
                const csvRow = cells.map(cell => {
                    if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
                        return `"${cell.replace(/"/g, '""')}"`;
                    }
                    return cell;
                }).join(',');
                csvContent += csvRow + '\n';
            }
        }
    }

    // Create and download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');

    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } else {
        // Fallback for older browsers
        window.open('data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent));
    }
}