document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const modelSelect = document.getElementById('model-select');
    const streamToggle = document.getElementById('stream-toggle');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages');
    const chatContainer = document.getElementById('chat-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const dismissErrorBtn = document.getElementById('dismiss-error');
    
    // State
    let conversationHistory = [];
    let isWaitingForResponse = false;
    let abortController = null;
    
    // Initialize config values
    streamToggle.checked = CONFIG.DEFAULT_STREAM;
    
    // Initialize App
    init();
    
    async function init() {
        await fetchModels();
        setupEventListeners();
    }
    
    // API Functions
    async function fetchModels() {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/v1/models`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch models (${response.status})`);
            }
            
            const data = await response.json();
            
            if (data && data.data && Array.isArray(data.data)) {
                populateModelSelect(data.data);
            } else {
                throw new Error('Invalid models response format');
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            showError('Could not connect to server to load models.');
            
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
            modelSelect.disabled = true;
            messageInput.disabled = true;
            sendButton.disabled = true;
        }
    }
    
    function populateModelSelect(models) {
        modelSelect.innerHTML = '';
        
        if (models.length === 0) {
            modelSelect.innerHTML = '<option value="">No models available</option>';
            modelSelect.disabled = true;
            return;
        }
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.id;
            modelSelect.appendChild(option);
        });
        
        modelSelect.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
    
    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text || isWaitingForResponse) return;
        
        const selectedModel = modelSelect.value;
        if (!selectedModel) {
            showError('Please select a model first.');
            return;
        }
        
        const isStream = streamToggle.checked;
        
        // Add user message to UI and history
        addMessageToUI('user', text);
        conversationHistory.push({ role: 'user', content: text });
        
        // Reset input
        messageInput.value = '';
        resizeTextarea();
        
        // Set loading state
        setWaitingState(true);
        
        try {
            abortController = new AbortController();
            
            const requestBody = {
                model: selectedModel,
                messages: conversationHistory,
                stream: isStream
            };
            
            const response = await fetch(`${CONFIG.API_BASE_URL}/v1/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody),
                signal: abortController.signal
            });
            
            if (!response.ok) {
                let errorText = `HTTP Error: ${response.status}`;
                try {
                    const errObj = await response.json();
                    if (errObj.error && errObj.error.message) {
                        errorText = errObj.error.message;
                    }
                } catch (e) {
                    errorText = await response.text() || errorText;
                }
                throw new Error(errorText);
            }
            
            if (isStream) {
                await handleStreamResponse(response);
            } else {
                await handleNormalResponse(response);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request aborted');
            } else {
                console.error('Chat error:', error);
                showError(error.message || 'An error occurred during communication.');
            }
        } finally {
            setWaitingState(false);
            messageInput.focus();
        }
    }
    
    async function handleNormalResponse(response) {
        const data = await response.json();
        const content = data.choices[0]?.message?.content || '';
        
        addMessageToUI('assistant', content);
        conversationHistory.push({ role: 'assistant', content: content });
    }
    
    async function handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        let assistantMessageElement = createMessageElement('assistant', '');
        messagesContainer.appendChild(assistantMessageElement);
        scrollToBottom();
        
        // Hide typing indicator immediately when streaming starts
        typingIndicator.classList.add('hidden');
        
        let fullContent = '';
        let contentContainer = assistantMessageElement.querySelector('.message-content');
        
        try {
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                
                // Keep the last partial line in the buffer
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;
                    
                    const dataStr = trimmedLine.substring(6);
                    
                    if (dataStr === '[DONE]') {
                        continue;
                    }
                    
                    try {
                        const data = JSON.parse(dataStr);
                        const contentDelta = data.choices[0]?.delta?.content || '';
                        
                        if (contentDelta) {
                            fullContent += contentDelta;
                            contentContainer.innerHTML = formatMessage(fullContent);
                            scrollToBottom();
                        }
                    } catch (e) {
                        console.warn('Error parsing stream data chunk:', dataStr, e);
                    }
                }
            }
            
            // Add final complete message to history
            conversationHistory.push({ role: 'assistant', content: fullContent });
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                throw error;
            }
        }
    }
    
    // UI Helpers
    function addMessageToUI(role, content) {
        const msgEl = createMessageElement(role, content);
        messagesContainer.appendChild(msgEl);
        scrollToBottom();
    }
    
    function createMessageElement(role, content) {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = formatMessage(content);
        
        div.appendChild(contentDiv);
        return div;
    }
    
    // Simple markdown-like formatter
    function formatMessage(text) {
        if (!text) return '';
        
        // Escape HTML
        let formatted = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
        // Code blocks
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Bold
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Italic
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // Newlines to <br> outside of <pre> tags
        const parts = formatted.split(/(<pre>[\s\S]*?<\/pre>)/g);
        for (let i = 0; i < parts.length; i++) {
            if (!parts[i].startsWith('<pre>')) {
                parts[i] = parts[i].replace(/\n/g, '<br>');
            }
        }
        return parts.join('');
    }
    
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function setWaitingState(isWaiting) {
        isWaitingForResponse = isWaiting;
        messageInput.disabled = isWaiting;
        sendButton.disabled = isWaiting || !messageInput.value.trim();
        
        if (isWaiting) {
            typingIndicator.classList.remove('hidden');
            scrollToBottom();
        } else {
            typingIndicator.classList.add('hidden');
        }
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('hidden');
        setTimeout(() => {
            errorContainer.classList.add('hidden');
        }, 5000); // Auto-hide after 5s
    }
    
    function resizeTextarea() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
        
        // Update button state based on content
        if (!isWaitingForResponse) {
            sendButton.disabled = !messageInput.value.trim();
        }
    }
    
    // Event Listeners
    function setupEventListeners() {
        sendButton.addEventListener('click', sendMessage);
        
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        messageInput.addEventListener('input', resizeTextarea);
        
        dismissErrorBtn.addEventListener('click', () => {
            errorContainer.classList.add('hidden');
        });
        
        // Optional: cancel request if ESC is pressed while waiting
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isWaitingForResponse && abortController) {
                abortController.abort();
            }
        });
    }
});
