/**
 * Chat functionality for VoiceFlow PoC
 * Handles conversation management and AI responses
 */

class ChatHandler {
    constructor() {
        this.conversationId = null;
        this.messages = [];
        this.isProcessing = false;
        
        this.init();
    }

    init() {
        // Initialize chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.processAudioBtn = document.getElementById('processAudioBtn');

        // Set up event listeners
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.processAudioBtn.addEventListener('click', () => this.processAudioTranscription());
        
        // Generate new conversation ID
        this.conversationId = this.generateConversationId();

        console.log('✅ Chat handler initialized with conversation:', this.conversationId);
    }

    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async sendMessage(messageText = null) {
        const message = messageText || this.messageInput.value.trim();
        
        if (!message) {
            this.showError('Por favor, escribe un mensaje');
            return;
        }

        if (this.isProcessing) {
            console.log('⏳ Message already processing, ignoring request');
            return;
        }

        try {
            this.isProcessing = true;
            this.setButtonsLoading(true);

            // Add user message to chat
            this.addMessage('user', message);
            
            // Clear input if it was used
            if (!messageText) {
                this.messageInput.value = '';
            }

            // Start pipeline animation if available
            const pipelineViz = window.VoiceFlowApp?.pipelineVisualizer;
            if (pipelineViz) pipelineViz.startAnimation(null);

            // Send to backend
            const response = await this.sendToBackend(message);

            if (response.status === 'success') {
                // Update pipeline with actual timings
                if (pipelineViz && response.pipeline_steps) {
                    pipelineViz.completeFromResponse(response);
                }

                // Add AI response with rich data
                this.addMessage('assistant', response.ai_response, {
                    processingTime: response.processing_time,
                    tourismData: response.tourism_data,
                    pipelineSteps: response.pipeline_steps,
                });

                console.log('✅ Message processed successfully');
            } else {
                throw new Error(response.message || 'Failed to get AI response');
            }

        } catch (error) {
            console.error('❌ Failed to send message:', error);
            this.addMessage('system', 'Error: No se pudo procesar el mensaje. ' + error.message);
            this.showError('Error al enviar mensaje: ' + error.message);
        } finally {
            this.isProcessing = false;
            this.setButtonsLoading(false);
            this.scrollToBottom();
        }
    }

    async processAudioTranscription() {
        if (!window.VoiceFlowApp?.audioHandler) {
            this.showError('Audio handler not available');
            return;
        }

        const transcription = window.VoiceFlowApp.audioHandler.getLastTranscription();
        
        if (!transcription) {
            this.showError('No hay transcripción disponible');
            return;
        }

        console.log('🎤 Processing audio transcription:', transcription);
        await this.sendMessage(transcription);
    }

    async sendToBackend(message) {
        const requestData = {
            message: message,
            conversation_id: this.conversationId,
            context: {
                timestamp: new Date().toISOString(),
                source: 'web_ui'
            }
        };

        const response = await fetch('/api/v1/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    addMessage(role, content, metadata = {}) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${role}`;

        // Expand width for rich cards
        if (role === 'assistant' && metadata.tourismData) {
            messageElement.classList.add('has-cards');
        }

        const timestamp = new Date().toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });

        let messageHtml = '';

        // If assistant message contains tourismData, render the rich cards prominently
        if (role === 'assistant' && metadata.tourismData && typeof CardRenderer !== 'undefined') {
            // Optionally include a short heading and hide the plain text to favour cards
            messageHtml += `<div class="assistant-cards-header small text-muted mb-2">Respuesta estructurada</div>`;
            messageHtml += CardRenderer.render(metadata.tourismData);
        } else {
            // Default behaviour: plain message text
            messageHtml = `
                <div class="message-content">${this.escapeHtml(content)}</div>
            `;
        }

        // Metadata line
        const processingTime = metadata.processingTime?.toFixed(2) || null;
        messageHtml += `
            <div class="message-meta">
                <span class="timestamp">${timestamp}</span>
                ${role === 'assistant' && processingTime ? `<span class="processing-time"><i class="bi bi-clock"></i> ${processingTime}s</span>` : ''}
            </div>
        `;

        messageElement.innerHTML = messageHtml;

        // Add to messages container
        this.chatMessages.appendChild(messageElement);

        // Store in message history
        this.messages.push({
            role,
            content,
            timestamp: new Date().toISOString(),
            metadata
        });

        // Auto-scroll to bottom
        this.scrollToBottom();
    }

    clearChat() {
        // Clear the UI
        this.chatMessages.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                ¡Hola! Soy tu asistente turístico virtual. Puedes grabar audio o escribir tu pregunta sobre turismo.
            </div>
        `;

        // Clear message history
        this.messages = [];

        // Generate new conversation ID
        this.conversationId = this.generateConversationId();

        // Clear audio transcription if available
        if (window.VoiceFlowApp?.audioHandler) {
            window.VoiceFlowApp.audioHandler.clearTranscription();
        }

        console.log('🧹 Chat cleared, new conversation:', this.conversationId);
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    setButtonsLoading(loading) {
        const buttons = [this.sendBtn, this.processAudioBtn];
        
        buttons.forEach(btn => {
            if (loading) {
                btn.classList.add('loading');
                btn.disabled = true;
            } else {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        });

        // Re-disable process audio button if no transcription
        if (!loading && window.VoiceFlowApp?.audioHandler && !window.VoiceFlowApp.audioHandler.getLastTranscription()) {
            this.processAudioBtn.disabled = true;
        }
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    async loadConversationHistory(conversationId) {
        try {
            const response = await fetch(`/api/v1/chat/conversation/${conversationId}`);
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    this.messages = result.messages || [];
                    this.renderMessages();
                    console.log('✅ Conversation history loaded');
                }
            }
        } catch (error) {
            console.error('❌ Failed to load conversation history:', error);
        }
    }

    renderMessages() {
        this.chatMessages.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                Conversación restaurada
            </div>
        `;

        this.messages.forEach(msg => {
            this.addMessage(msg.role, msg.content, msg.metadata || {});
        });
    }

    async getConversationList() {
        try {
            const response = await fetch('/api/v1/chat/conversations?limit=20');
            
            if (response.ok) {
                const result = await response.json();
                return result.conversations || [];
            }
        } catch (error) {
            console.error('❌ Failed to get conversations:', error);
        }
        
        return [];
    }

    showError(message) {
        console.error('💥 Chat Error:', message);
        document.getElementById('errorMessage').textContent = message;
        const modal = new bootstrap.Modal(document.getElementById('errorModal'));
        modal.show();
    }

    // Demo methods for testing
    async getDemoResponses() {
        try {
            const response = await fetch('/api/v1/chat/demo/responses');
            
            if (response.ok) {
                const result = await response.json();
                return result.sample_responses || [];
            }
        } catch (error) {
            console.error('❌ Failed to get demo responses:', error);
        }
        
        return [];
    }

    async runDemo() {
        console.log('🎭 Running chat demo...');
        
        const demoResponses = await this.getDemoResponses();
        
        for (let i = 0; i < demoResponses.length; i++) {
            const demo = demoResponses[i];
            
            // Add user message
            setTimeout(() => {
                this.addMessage('user', demo.input);
            }, i * 4000);
            
            // Add AI response
            setTimeout(() => {
                this.addMessage('assistant', demo.response, {
                    confidence: demo.confidence,
                    processingTime: 1.2
                });
            }, i * 4000 + 2000);
        }
    }
}

// Make available globally for form handling
window.handleMessageKeyPress = function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (window.VoiceFlowApp?.chatHandler) {
            window.VoiceFlowApp.chatHandler.sendMessage();
        }
    }
};

window.sendMessage = function() {
    if (window.VoiceFlowApp?.chatHandler) {
        window.VoiceFlowApp.chatHandler.sendMessage();
    }
};

window.processTranscription = function() {
    if (window.VoiceFlowApp?.chatHandler) {
        window.VoiceFlowApp.chatHandler.processAudioTranscription();
    }
};

// Export for use in main app
window.ChatHandler = ChatHandler;
