/**
 * Main VoiceFlow PoC Application
 * Coordinates audio recording, chat, and UI interactions
 */

window.VoiceFlowApp = {
    // Global state
    audioHandler: null,
    chatHandler: null,
    pipelineVisualizer: null,
    demoHandler: null,
    isInitialized: false,

    /**
     * Initialize the entire application
     */
    async init() {
        try {
            console.log('🚀 Initializing VoiceFlow PoC Application');
            
            // Initialize components
            await this.initializeComponents();
            
            // Set up global event handlers
            this.setupGlobalEventHandlers();
            
            // Show welcome message
            this.showWelcomeMessage();
            
            this.isInitialized = true;
            console.log('✅ VoiceFlow PoC Application initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize VoiceFlow PoC Application:', error);
            this.showError('Failed to initialize application. Please refresh the page.');
        }
    },

    /**
     * Initialize audio and chat components
     */
    async initializeComponents() {
        // Initialize Audio Handler
        try {
            if (typeof AudioHandler !== 'undefined') {
                this.audioHandler = new AudioHandler();
                console.log('✅ Audio handler initialized');
            } else {
                console.warn('⚠️ AudioHandler not found');
            }
        } catch (e) {
            console.error('❌ AudioHandler init failed:', e);
        }

        // Initialize Chat Handler
        try {
            if (typeof ChatHandler !== 'undefined') {
                this.chatHandler = new ChatHandler();
                console.log('✅ Chat handler initialized');
            } else {
                console.warn('⚠️ ChatHandler not found');
            }
        } catch (e) {
            console.error('❌ ChatHandler init failed:', e);
        }

        // Initialize Pipeline Visualizer
        try {
            if (typeof PipelineVisualizer !== 'undefined') {
                this.pipelineVisualizer = new PipelineVisualizer();
                this.pipelineVisualizer.init();
                console.log('✅ Pipeline visualizer initialized');
            }
        } catch (e) {
            console.error('❌ PipelineVisualizer init failed:', e);
        }

        // Initialize Demo Mode Handler
        try {
            if (typeof DemoModeHandler !== 'undefined') {
                // Only initialize demo handler when enabled by server-side flag
                if (window.DEMO_SCENARIOS) {
                    this.demoHandler = new DemoModeHandler();
                    await this.demoHandler.init();
                    console.log('✅ Demo mode handler initialized');
                } else {
                    console.log('ℹ️ Demo mode disabled (DEMO_SCENARIOS=false)');
                }
            }
        } catch (e) {
            console.error('❌ DemoModeHandler init failed:', e);
        }

        // Wait a moment for components to fully initialize
        await new Promise(resolve => setTimeout(resolve, 100));
    },

    /**
     * Set up global event handlers
     */
    setupGlobalEventHandlers() {
        // Handle connection status
        window.addEventListener('online', () => {
            console.log('🌐 Connection restored');
            this.showSuccess('Connection restored');
        });

        window.addEventListener('offline', () => {
            console.log('🔌 Connection lost');
            this.showWarning('Connection lost - some features may not work');
        });

        // Handle errors globally
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
        });

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
        });
    },

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        const statusDiv = document.getElementById('transcriptionResult');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <strong>¡Bienvenido al VoiceFlow PoC!</strong><br>
                    Presiona el botón de grabación para comenzar a transcribir audio con Azure STT.
                    <br><small>Asegúrate de permitir el acceso al micrófono cuando se solicite.</small>
                </div>
            `;
        }
    },

    /**
     * Utility methods for showing messages
     */
    showError(message) {
        this.showMessage(message, 'danger', 'exclamation-triangle');
    },

    showSuccess(message) {
        this.showMessage(message, 'success', 'check-circle');
    },

    showWarning(message) {
        this.showMessage(message, 'warning', 'exclamation-triangle');
    },

    showInfo(message) {
        this.showMessage(message, 'info', 'info-circle');
    },

    showMessage(message, type, icon) {
        // Try to show in transcription result area
        const resultDiv = document.getElementById('transcriptionResult');
        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="alert alert-${type}">
                    <i class="bi bi-${icon}"></i>
                    ${message}
                </div>
            `;
        }

        // Also log to console
        console.log(`${type.toUpperCase()}: ${message}`);
    },

    /**
     * Get application status
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            audioHandler: this.audioHandler ? 'loaded' : 'not loaded',
            chatHandler: this.chatHandler ? 'loaded' : 'not loaded',
            online: navigator.onLine
        };
    }
};

// Global utility functions
window.showError = (message) => VoiceFlowApp.showError(message);
window.showSuccess = (message) => VoiceFlowApp.showSuccess(message);
window.showWarning = (message) => VoiceFlowApp.showWarning(message);
window.showInfo = (message) => VoiceFlowApp.showInfo(message);

// Export for debugging
window.DEBUG = {
    app: () => VoiceFlowApp.getStatus(),
    audio: () => VoiceFlowApp.audioHandler,
    chat: () => VoiceFlowApp.chatHandler
};

console.log('📄 VoiceFlow PoC Application script loaded');
