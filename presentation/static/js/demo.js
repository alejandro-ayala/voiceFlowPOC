/**
 * Demo Mode Handler for VoiceFlow PoC
 * Provides guided scenario buttons with typewriter effect and pipeline orchestration.
 */

class DemoModeHandler {
    constructor() {
        this.scenarios = [];
        this.isRunning = false;
        this.currentScenario = null;
        this.container = null;
    }

    async init() {
        await this.loadScenarios();
        this.buildDemoBar();
        this.setupNavbarToggle();
        console.log('✅ Demo mode handler initialized');
    }

    async loadScenarios() {
        try {
            const response = await fetch('/api/v1/chat/demo/scenarios');
            if (response.ok) {
                const data = await response.json();
                this.scenarios = data.scenarios || [];
            }
        } catch (error) {
            console.warn('⚠️ Failed to load demo scenarios, using fallback:', error);
        }

        if (this.scenarios.length === 0) {
            this.scenarios = this.getFallbackScenarios();
        }
    }

    getFallbackScenarios() {
        return [
            { id: 'prado_wheelchair', title: 'Museo del Prado accesible', icon: 'bi-building', query: 'Quiero visitar el Museo del Prado en silla de ruedas' },
            { id: 'reina_sofia_transport', title: 'Transporte al Reina Sofía', icon: 'bi-map', query: '¿Cómo llego al Museo Reina Sofía en transporte accesible?' },
            { id: 'restaurants_centro', title: 'Restaurantes accesibles', icon: 'bi-cup-hot', query: 'Recomiéndame restaurantes accesibles en el centro' },
            { id: 'concert_hearing', title: 'Conciertos accesibles', icon: 'bi-music-note-beamed', query: 'Quiero ir a un concierto, necesito acceso auditivo' },
        ];
    }

    buildDemoBar() {
        this.container = document.createElement('div');
        this.container.id = 'demoBar';
        this.container.className = 'row mb-4';
        this.container.innerHTML = `
            <div class="col-12">
                <div class="card demo-scenarios-card">
                    <div class="card-body py-3">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <h6 class="mb-0 demo-bar-title">
                                <i class="bi bi-play-circle"></i> Demo Scenarios
                            </h6>
                            <div class="d-flex align-items-center gap-2">
                                <div class="form-check form-switch mb-0">
                                    <input class="form-check-input" type="checkbox" id="realApiToggle">
                                    <label class="form-check-label small" for="realApiToggle">Real API</label>
                                </div>
                                <button class="btn btn-sm btn-outline-secondary" id="collapseDemoBar" title="Toggle demo bar">
                                    <i class="bi bi-chevron-up"></i>
                                </button>
                            </div>
                        </div>
                        <div class="demo-scenarios-buttons d-flex gap-2 flex-wrap" id="scenarioButtons"></div>
                    </div>
                </div>
            </div>
        `;

        // Insert after status bar, before main interface
        // Use child combinator to skip the .container inside <nav>
        const mainContainer = document.querySelector('.container-fluid > .container');
        if (!mainContainer) {
            console.warn('⚠️ Demo: main container not found');
            return;
        }
        const mainInterface = mainContainer.querySelector(':scope > .row:not(.mb-4)');
        if (mainInterface) {
            mainContainer.insertBefore(this.container, mainInterface);
        }

        // Populate scenario buttons
        const btnContainer = document.getElementById('scenarioButtons');
        this.scenarios.forEach((scenario, index) => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-outline-primary demo-scenario-btn';
            btn.dataset.scenarioIndex = index;
            btn.innerHTML = `<i class="bi ${scenario.icon}"></i> ${scenario.title}`;
            btn.addEventListener('click', () => this.runScenario(index));
            btnContainer.appendChild(btn);
        });

        // Collapse toggle
        document.getElementById('collapseDemoBar').addEventListener('click', () => this.toggleDemoBar());
    }

    setupNavbarToggle() {
        const navbarNav = document.querySelector('.navbar-nav.ms-auto');
        if (!navbarNav) return;

        const demoToggle = document.createElement('span');
        demoToggle.className = 'nav-link text-light';
        demoToggle.id = 'navbarDemoToggle';
        demoToggle.innerHTML = '<small><i class="bi bi-play-circle"></i> Demo</small>';
        demoToggle.style.cursor = 'pointer';
        demoToggle.addEventListener('click', () => this.toggleDemoBar());
        navbarNav.insertBefore(demoToggle, navbarNav.firstChild);
    }

    toggleDemoBar() {
        const buttonsContainer = document.getElementById('scenarioButtons');
        const icon = document.querySelector('#collapseDemoBar i');
        if (buttonsContainer) {
            buttonsContainer.classList.toggle('d-none');
            if (icon) {
                icon.className = buttonsContainer.classList.contains('d-none')
                    ? 'bi bi-chevron-down'
                    : 'bi bi-chevron-up';
            }
        }
    }

    async runScenario(index) {
        if (this.isRunning) return;
        this.isRunning = true;

        const scenario = this.scenarios[index];
        this.currentScenario = scenario;

        // Highlight active button
        document.querySelectorAll('.demo-scenario-btn').forEach(btn => {
            btn.disabled = true;
            btn.classList.remove('active');
        });
        const activeBtn = document.querySelector(`[data-scenario-index="${index}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        try {
            const chatHandler = window.VoiceFlowApp?.chatHandler;
            const pipelineViz = window.VoiceFlowApp?.pipelineVisualizer;

            // Step 1: Clear previous state
            if (chatHandler) chatHandler.clearChat();
            if (pipelineViz) pipelineViz.reset();

            // Step 2: Typewriter effect in transcription box
            await this.typewriterEffect(scenario.query);

            // Step 3: Add user message to chat
            if (chatHandler) {
                chatHandler.addMessage('user', scenario.query);
            }

            // Step 4: Start pipeline + get response
            const useRealApi = document.getElementById('realApiToggle')?.checked || false;

            if (useRealApi) {
                // Start pipeline animation with default timings
                const animationPromise = pipelineViz?.startAnimation(null);

                // Send to real backend
                const response = await chatHandler.sendToBackend(scenario.query);

                // Complete pipeline from response
                if (pipelineViz && response.pipeline_steps) {
                    pipelineViz.completeFromResponse(response);
                } else if (animationPromise) {
                    await animationPromise;
                }

                if (chatHandler) {
                    chatHandler.addMessage('assistant', response.ai_response, {
                        processingTime: response.processing_time,
                        tourismData: response.tourism_data,
                        pipelineSteps: response.pipeline_steps,
                    });
                }
            } else {
                // Send to backend (simulation mode) but animate pipeline in parallel
                const responsePromise = chatHandler.sendToBackend(scenario.query);

                // Start pipeline animation
                const animationPromise = pipelineViz?.startAnimation(null);

                // Wait for both
                const [response] = await Promise.all([responsePromise, animationPromise]);

                // Update pipeline with actual data from response
                if (pipelineViz && response.pipeline_steps) {
                    pipelineViz.completeFromResponse(response);
                }

                if (chatHandler) {
                    chatHandler.addMessage('assistant', response.ai_response, {
                        processingTime: response.processing_time,
                        tourismData: response.tourism_data,
                        pipelineSteps: response.pipeline_steps,
                    });
                }
            }

        } catch (error) {
            console.error('❌ Demo scenario failed:', error);
            if (window.VoiceFlowApp?.chatHandler) {
                window.VoiceFlowApp.chatHandler.addMessage('system', 'Error running demo: ' + error.message);
            }
        } finally {
            this.isRunning = false;
            this.currentScenario = null;
            document.querySelectorAll('.demo-scenario-btn').forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('active');
            });
        }
    }

    async typewriterEffect(text) {
        const transcriptionDiv = document.getElementById('transcriptionResult');
        if (!transcriptionDiv) return;

        transcriptionDiv.classList.add('has-content');
        transcriptionDiv.innerHTML = '<span class="typewriter-cursor"></span>';

        const words = text.split(' ');
        for (let i = 0; i < words.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 60));
            const cursor = transcriptionDiv.querySelector('.typewriter-cursor');
            const wordSpan = document.createElement('span');
            wordSpan.className = 'typewriter-word';
            wordSpan.textContent = (i > 0 ? ' ' : '') + words[i];
            if (cursor) {
                transcriptionDiv.insertBefore(wordSpan, cursor);
            }
        }

        // Remove cursor after typing
        await new Promise(resolve => setTimeout(resolve, 300));
        const cursor = transcriptionDiv.querySelector('.typewriter-cursor');
        if (cursor) cursor.remove();
    }
}

window.DemoModeHandler = DemoModeHandler;
