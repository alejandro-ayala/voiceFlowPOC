/**
 * Pipeline Visualizer for VoiceFlow PoC
 * Displays a horizontal step indicator showing agent processing progress.
 */

class PipelineVisualizer {
    constructor() {
        this.steps = [
            { name: 'NLU', icon: 'bi-brain', tool: 'tourism_nlu' },
            { name: 'Accessibility', icon: 'bi-universal-access', tool: 'accessibility_analysis' },
            { name: 'Routes', icon: 'bi-map', tool: 'route_planning' },
            { name: 'Venue Info', icon: 'bi-info-circle', tool: 'tourism_info' },
            { name: 'Response', icon: 'bi-chat-square-text', tool: 'llm_synthesis' },
        ];
        this.container = null;
        this.currentStep = -1;
        this._animationResolve = null;
    }

    init() {
        this.buildUI();
        console.log('✅ Pipeline visualizer initialized');
    }

    buildUI() {
        this.container = document.createElement('div');
        this.container.id = 'pipelineVisualizer';
        this.container.className = 'row mb-4 d-none';

        const stepsHtml = this.steps.map((step, i) => {
            const connector = i < this.steps.length - 1
                ? '<div class="pipeline-connector"><div class="pipeline-connector-fill"></div></div>'
                : '';
            return `
                <div class="pipeline-step idle" data-step="${i}" id="pipeline-step-${i}">
                    <div class="pipeline-step-icon">
                        <i class="bi ${step.icon}"></i>
                    </div>
                    <div class="pipeline-step-label">${step.name}</div>
                    <div class="pipeline-step-time" id="pipeline-time-${i}"></div>
                </div>
                ${connector}
            `;
        }).join('');

        this.container.innerHTML = `
            <div class="col-12">
                <div class="pipeline-container">
                    <div class="pipeline-steps d-flex align-items-center justify-content-center" id="pipelineSteps">
                        ${stepsHtml}
                    </div>
                </div>
            </div>
        `;

        // Insert into DOM: after demoBar (or status bar), before main interface
        // Use child combinator to skip the .container inside <nav>
        const mainContainer = document.querySelector('.container-fluid > .container');
        if (!mainContainer) {
            console.warn('⚠️ Pipeline: main container not found');
            return;
        }
        const mainInterface = mainContainer.querySelector(':scope > .row:not(.mb-4)');
        if (mainInterface) {
            mainContainer.insertBefore(this.container, mainInterface);
        }
    }

    reset() {
        this.currentStep = -1;
        this.steps.forEach((_, i) => {
            const stepEl = document.getElementById(`pipeline-step-${i}`);
            if (stepEl) stepEl.className = 'pipeline-step idle';
            const timeEl = document.getElementById(`pipeline-time-${i}`);
            if (timeEl) timeEl.textContent = '';
        });
        if (this.container) {
            this.container.querySelectorAll('.pipeline-connector-fill').forEach(el => {
                el.style.width = '0%';
            });
        }
    }

    /**
     * Animate the pipeline step by step.
     * @param {Array|null} pipelineSteps - Optional server-provided steps with duration_ms
     * @returns {Promise} resolves when animation completes
     */
    async startAnimation(pipelineSteps) {
        this.reset();

        // Show the visualizer
        if (this.container) {
            this.container.classList.remove('d-none');
        }

        const timings = pipelineSteps
            ? pipelineSteps.map(s => s.duration_ms || 500)
            : [450, 620, 880, 540, 710];

        const animationPromise = new Promise(resolve => {
            this._animationResolve = resolve;
        });

        for (let i = 0; i < this.steps.length; i++) {
            const stepEl = document.getElementById(`pipeline-step-${i}`);
            if (stepEl) stepEl.className = 'pipeline-step processing';
            this.currentStep = i;

            const duration = timings[i] || 500;
            await new Promise(resolve => setTimeout(resolve, duration));

            if (stepEl) stepEl.className = 'pipeline-step completed';

            const timeEl = document.getElementById(`pipeline-time-${i}`);
            if (timeEl) timeEl.textContent = `${(duration / 1000).toFixed(1)}s`;

            // Fill connector
            if (i < this.steps.length - 1 && this.container) {
                const connectors = this.container.querySelectorAll('.pipeline-connector-fill');
                if (connectors[i]) connectors[i].style.width = '100%';
            }
        }

        if (this._animationResolve) {
            this._animationResolve();
            this._animationResolve = null;
        }

        return animationPromise;
    }

    /**
     * Instantly complete all steps from a server response.
     */
    completeFromResponse(response) {
        if (!response.pipeline_steps) return;

        // Show the visualizer
        if (this.container) {
            this.container.classList.remove('d-none');
        }

        response.pipeline_steps.forEach((step, i) => {
            const stepEl = document.getElementById(`pipeline-step-${i}`);
            if (stepEl) stepEl.className = 'pipeline-step completed';

            const timeEl = document.getElementById(`pipeline-time-${i}`);
            if (timeEl && step.duration_ms) {
                timeEl.textContent = `${(step.duration_ms / 1000).toFixed(1)}s`;
            }
        });

        if (this.container) {
            this.container.querySelectorAll('.pipeline-connector-fill').forEach(el => {
                el.style.width = '100%';
            });
        }

        // Resolve any pending animation
        if (this._animationResolve) {
            this._animationResolve();
            this._animationResolve = null;
        }
    }
}

window.PipelineVisualizer = PipelineVisualizer;
