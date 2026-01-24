/**
 * Audio handling functionality for VoiceFlow PoC
 * Handles recording, file upload, and real-time visualization
 */

class AudioHandler {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.audioContext = null;
        this.analyser = null;
        this.stream = null;
        this.visualizer = null;
        
        this.init();
    }

    async init() {
        try {
            // Initialize audio elements
            this.recordBtn = document.getElementById('recordBtn');
            this.recordingStatus = document.getElementById('recordingStatus');
            this.audioFile = document.getElementById('audioFile');
            this.languageSelect = document.getElementById('languageSelect');
            this.transcriptionResult = document.getElementById('transcriptionResult');
            this.transcriptionConfidence = document.getElementById('transcriptionConfidence');
            this.transcriptionTime = document.getElementById('transcriptionTime');
            this.processAudioBtn = document.getElementById('processAudioBtn');

            // Set up event listeners
            this.recordBtn.addEventListener('click', () => this.toggleRecording());
            this.audioFile.addEventListener('change', (e) => this.handleFileUpload(e));

            // Initialize audio visualizer
            this.initVisualizer();

            console.log('✅ Audio handler initialized');
        } catch (error) {
            console.error('❌ Failed to initialize audio handler:', error);
            this.showError('Failed to initialize audio system');
        }
    }

    initVisualizer() {
        const canvas = document.getElementById('visualizerCanvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.visualizer = { canvas, ctx };

        // Set canvas size
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

        // Draw initial state
        this.drawVisualizerIdle();
    }

    drawVisualizerIdle() {
        if (!this.visualizer) return;

        const { ctx, canvas } = this.visualizer;
        const width = canvas.width / window.devicePixelRatio;
        const height = canvas.height / window.devicePixelRatio;

        ctx.clearRect(0, 0, width, height);
        
        // Draw idle wave pattern
        ctx.strokeStyle = '#6c757d';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        for (let x = 0; x < width; x++) {
            const y = height / 2 + Math.sin(x * 0.02) * 10;
            if (x === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        
        ctx.stroke();

        // Add text
        ctx.fillStyle = '#6c757d';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Audio Visualizer', width / 2, height / 2 + 30);
    }

    drawVisualizerActive(dataArray) {
        if (!this.visualizer || !dataArray) return;

        const { ctx, canvas } = this.visualizer;
        const width = canvas.width / window.devicePixelRatio;
        const height = canvas.height / window.devicePixelRatio;

        ctx.clearRect(0, 0, width, height);

        // Draw frequency bars
        const barWidth = width / dataArray.length;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            const barHeight = (dataArray[i] / 255) * height * 0.8;
            
            // Create gradient
            const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight);
            gradient.addColorStop(0, '#0d6efd');
            gradient.addColorStop(1, '#0dcaf0');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight);
            
            x += barWidth;
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                } 
            });

            // Set up MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                await this.processRecording();
            };

            // Set up audio analysis for visualization
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            const source = this.audioContext.createMediaStreamSource(this.stream);
            source.connect(this.analyser);

            this.analyser.fftSize = 64;
            const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            // Start recording
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;

            // Update UI
            this.recordBtn.classList.add('recording');
            this.recordBtn.innerHTML = '<i class="bi bi-stop fs-1"></i>';
            this.recordingStatus.textContent = 'Grabando... Presiona para detener';
            this.recordingStatus.className = 'text-danger fw-bold';

            // Start visualization
            const visualize = () => {
                if (this.isRecording) {
                    requestAnimationFrame(visualize);
                    this.analyser.getByteFrequencyData(dataArray);
                    this.drawVisualizerActive(dataArray);
                }
            };
            visualize();

            console.log('🎤 Recording started');

        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            this.showError('No se pudo acceder al micrófono. Verifica los permisos.');
        }
    }

    async stopRecording() {
        if (!this.mediaRecorder || !this.isRecording) return;

        this.isRecording = false;
        this.mediaRecorder.stop();

        // Stop all tracks
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }

        // Close audio context
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }

        // Update UI
        this.recordBtn.classList.remove('recording');
        this.recordBtn.innerHTML = '<i class="bi bi-mic fs-1"></i>';
        this.recordingStatus.textContent = 'Procesando grabación...';
        this.recordingStatus.className = 'text-info';

        console.log('⏹️ Recording stopped');
    }

    async processRecording() {
        try {
            if (this.audioChunks.length === 0) {
                this.showError('No se grabó audio');
                return;
            }

            // Create audio blob
            const webmBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            console.log('📁 WebM blob created:', webmBlob.size, 'bytes');

            // Convert to WAV format for better Azure STT compatibility
            console.log('🔄 About to start WebM to WAV conversion...');
            try {
                const wavBlob = await this.convertWebmToWav(webmBlob);
                console.log('📁 WAV blob created:', wavBlob.size, 'bytes');
                console.log('📊 Conversion result - WebM:', webmBlob.size, 'vs WAV:', wavBlob.size);

                // Send for transcription
                await this.transcribeAudio(wavBlob);
            } catch (conversionError) {
                console.error('❌ Conversion failed, using original WebM:', conversionError);
                await this.transcribeAudio(webmBlob);
            }

        } catch (error) {
            console.error('❌ Failed to process recording:', error);
            this.showError('Error al procesar la grabación');
        } finally {
            this.recordingStatus.textContent = 'Presiona para grabar';
            this.recordingStatus.className = 'text-muted';
            this.drawVisualizerIdle();
        }
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        console.log('📁 File selected:', file.name, file.size, 'bytes');

        // Validate file type
        if (!file.type.startsWith('audio/')) {
            this.showError('Por favor selecciona un archivo de audio válido');
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showError('El archivo es demasiado grande. Máximo 10MB.');
            return;
        }

        await this.transcribeAudio(file);
    }

    async transcribeAudio(audioData) {
        try {
            this.showLoading('Transcribiendo audio...');

            const formData = new FormData();
            formData.append('audio_file', audioData, 'recording.wav');  // Changed extension to wav
            formData.append('language', this.languageSelect.value);

            const response = await fetch('/api/v1/audio/transcribe', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.displayTranscription(result);
                this.enableProcessButton();
                console.log('✅ Transcription successful:', result.transcription);
            } else {
                throw new Error(result.message || 'Transcription failed');
            }

        } catch (error) {
            console.error('❌ Transcription error:', error);
            this.showError('Error en la transcripción: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async convertWebmToWav(webmBlob) {
        console.log('🔄 Converting WebM to WAV in browser...');
        console.log('📊 WebM blob size:', webmBlob.size, 'bytes');
        
        try {
            // Create NEW audio context for processing (separate from recording context)
            console.log('🎵 Creating audio context...');
            const processingAudioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('✅ Audio context created successfully');
            
            // Convert blob to array buffer
            console.log('🔄 Converting blob to array buffer...');
            const arrayBuffer = await webmBlob.arrayBuffer();
            console.log('📊 Array buffer size:', arrayBuffer.byteLength, 'bytes');
            
            // Decode audio data
            console.log('🎵 Decoding audio data...');
            const audioBuffer = await processingAudioContext.decodeAudioData(arrayBuffer);
            console.log('📊 Audio buffer info:', {
                sampleRate: audioBuffer.sampleRate,
                channels: audioBuffer.numberOfChannels,
                duration: audioBuffer.duration,
                length: audioBuffer.length
            });
            
            // Get audio data as Float32Array
            console.log('🔄 Extracting audio data...');
            const audioData = audioBuffer.getChannelData(0); // Get mono channel
            console.log('📊 Audio data length:', audioData.length);
            
            // Convert to 16-bit PCM
            console.log('🔄 Converting to 16-bit PCM...');
            const pcmData = new Int16Array(audioData.length);
            for (let i = 0; i < audioData.length; i++) {
                pcmData[i] = Math.max(-32768, Math.min(32767, audioData[i] * 32768));
            }
            console.log('✅ PCM conversion completed');
            
            // Create WAV file header
            const sampleRate = audioBuffer.sampleRate;
            const numChannels = 1;
            const bitsPerSample = 16;
            const blockAlign = numChannels * bitsPerSample / 8;
            const byteRate = sampleRate * blockAlign;
            const dataSize = pcmData.length * 2;
            const fileSize = 36 + dataSize;
            
            console.log('📊 WAV file specs:', {
                sampleRate,
                numChannels,
                bitsPerSample,
                dataSize,
                fileSize
            });
            
            // Create WAV file buffer
            console.log('🔄 Creating WAV file buffer...');
            const wavBuffer = new ArrayBuffer(44 + dataSize);
            const view = new DataView(wavBuffer);
            
            // WAV header
            const writeString = (offset, string) => {
                for (let i = 0; i < string.length; i++) {
                    view.setUint8(offset + i, string.charCodeAt(i));
                }
            };
            
            console.log('🔄 Writing WAV header...');
            writeString(0, 'RIFF');
            view.setUint32(4, fileSize, true);
            writeString(8, 'WAVE');
            writeString(12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, numChannels, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, byteRate, true);
            view.setUint16(32, blockAlign, true);
            view.setUint16(34, bitsPerSample, true);
            writeString(36, 'data');
            view.setUint32(40, dataSize, true);
            
            // Write PCM data
            console.log('🔄 Writing PCM data...');
            const pcmView = new Int16Array(wavBuffer, 44);
            pcmView.set(pcmData);
            console.log('✅ PCM data written');
            
            // Close audio context
            console.log('🔄 Closing audio context...');
            await processingAudioContext.close();
            console.log('✅ Audio context closed');
            
            console.log('✅ WebM to WAV conversion completed');
            console.log('📊 Final WAV size:', wavBuffer.byteLength, 'bytes');
            
            const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
            console.log('📊 WAV blob size:', wavBlob.size, 'bytes');
            
            return wavBlob;
            
        } catch (error) {
            console.error('❌ WebM to WAV conversion failed at step:', error);
            console.error('❌ Error details:', error.message);
            console.error('❌ Error stack:', error.stack);
            console.log('🔄 Falling back to original WebM blob');
            return webmBlob;
        }
    }

    displayTranscription(result) {
        // Determine if this is real or simulated transcription
        const isRealTranscription = !result.transcription.includes('simulación') && 
                                   !result.transcription.includes('Error en la transcripción') &&
                                   result.confidence > 0.6;
        
        const statusIcon = isRealTranscription ? 'check-circle' : 'exclamation-triangle';
        const statusColor = isRealTranscription ? 'success' : 'warning';
        const statusText = isRealTranscription ? 'Transcripción completada' : 'Transcripción simulada';
        
        this.transcriptionResult.innerHTML = `
            <div class="fw-bold text-${statusColor} mb-2">
                <i class="bi bi-${statusIcon}"></i> ${statusText}
                ${!isRealTranscription ? '<small class="text-muted">(usando modo demo)</small>' : ''}
            </div>
            <div class="transcription-text">${result.transcription}</div>
            ${isRealTranscription ? '<small class="text-success mt-1 d-block"><i class="bi bi-mic"></i> Transcrito con Azure STT</small>' : ''}
        `;
        this.transcriptionResult.classList.add('has-content');

        this.transcriptionConfidence.textContent = Math.round(result.confidence * 100);
        this.transcriptionTime.textContent = result.processing_time.toFixed(2);

        // Store transcription for processing
        this.lastTranscription = result.transcription;
        
        // Log the result for debugging
        console.log(`🎯 Transcription result: ${isRealTranscription ? 'REAL' : 'SIMULATED'}`, {
            text: result.transcription,
            confidence: result.confidence,
            time: result.processing_time
        });
    }

    enableProcessButton() {
        this.processAudioBtn.disabled = false;
        this.processAudioBtn.classList.add('btn-success');
        this.processAudioBtn.classList.remove('btn-secondary');
    }

    async validateAudioFile(file) {
        try {
            const formData = new FormData();
            formData.append('audio_file', file);

            const response = await fetch('/api/v1/audio/validate', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            return result;

        } catch (error) {
            console.error('❌ Audio validation error:', error);
            return { valid: false, error: error.message };
        }
    }

    getLastTranscription() {
        return this.lastTranscription || '';
    }

    clearTranscription() {
        this.transcriptionResult.innerHTML = '<small class="text-muted">La transcripción aparecerá aquí...</small>';
        this.transcriptionResult.classList.remove('has-content');
        this.transcriptionConfidence.textContent = '-';
        this.transcriptionTime.textContent = '-';
        this.processAudioBtn.disabled = true;
        this.processAudioBtn.classList.remove('btn-success');
        this.processAudioBtn.classList.add('btn-secondary');
        this.lastTranscription = '';
        this.audioFile.value = '';
    }

    showLoading(message) {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        document.getElementById('loadingText').textContent = message;
        modal.show();
    }

    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) {
            modal.hide();
        }
    }

    showError(message) {
        console.error('💥 Audio Error:', message);
        document.getElementById('errorMessage').textContent = message;
        const modal = new bootstrap.Modal(document.getElementById('errorModal'));
        modal.show();
    }
}

// Export for use in main app
window.AudioHandler = AudioHandler;
