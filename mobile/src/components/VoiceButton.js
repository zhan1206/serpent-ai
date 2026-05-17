/* VoiceButton - 语音输入按钮组件 */
class VoiceButton {
    constructor(container, options = {}) {
        this.container = container;
        this.onStart = options.onStart || (() => {});
        this.onStop = options.onStop || (() => {});
        this.onResult = options.onResult || (() => {});
        this.isRecording = false;
        this.isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        this.recognition = null;
        this.audioCtx = null;
        this.analyser = null;
        this.bars = [];
        this.animFrame = null;

        if (this.isSupported) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.lang = 'zh-CN';
            this.recognition.interimResults = true;
            this.recognition.continuous = true;

            this.recognition.onresult = (e) => {
                let final = '';
                let interim = '';
                for (let i = e.resultIndex; i < e.results.length; i++) {
                    if (e.results[i].isFinal) {
                        final += e.results[i][0].transcript;
                    } else {
                        interim += e.results[i][0].transcript;
                    }
                }
                if (final) this.onResult(final, true);
                else if (interim) this.onResult(interim, false);
            };

            this.recognition.onerror = (e) => {
                console.warn('语音识别错误:', e.error);
                if (e.error !== 'no-speech') {
                    this.stop();
                }
            };

            this.recognition.onend = () => {
                if (this.isRecording) this.stop();
            };
        }
    }

    create() {
        const wrapper = document.createElement('div');
        wrapper.className = 'voice-btn-wrapper';
        wrapper.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:16px;';

        this.btn = document.createElement('button');
        this.btn.className = 'voice-btn-large';
        this.btn.innerHTML = '&#x1F3A4;';
        this.btn.setAttribute('aria-label', '语音输入');

        this.waveform = document.createElement('div');
        this.waveform.className = 'waveform-container';
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'waveform-bar';
            bar.style.height = '4px';
            this.waveform.appendChild(bar);
            this.bars.push(bar);
        }

        if (this.isSupported) {
            this.btn.addEventListener('click', () => {
                this.isRecording ? this.stop() : this.start();
            });
        } else {
            this.btn.disabled = true;
            this.btn.style.opacity = '0.4';
            this.btn.title = '您的浏览器不支持语音识别';
        }

        wrapper.appendChild(this.btn);
        wrapper.appendChild(this.waveform);
        return wrapper;
    }

    async start() {
        if (!this.isSupported || this.isRecording) return;
        this.isRecording = true;
        this.btn.classList.add('recording');
        this.btn.innerHTML = '&#x23F9;';
        if (navigator.vibrate) navigator.vibrate(30);
        this.onStart();

        try {
            // Start waveform animation
            this._startWaveform();
            this.recognition.start();
        } catch (e) {
            console.error('启动语音识别失败:', e);
            this.stop();
        }
    }

    stop() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.btn.classList.remove('recording');
        this.btn.innerHTML = '&#x1F3A4;';
        this._stopWaveform();
        if (navigator.vibrate) navigator.vibrate(20);

        try {
            this.recognition.stop();
        } catch (e) {}
        this.onStop();
    }

    _startWaveform() {
        const animate = () => {
            this.bars.forEach((bar, i) => {
                const h = this.isRecording
                    ? Math.random() * 32 + 4
                    : 4;
                bar.style.height = h + 'px';
            });
            this.animFrame = requestAnimationFrame(animate);
        };
        animate();
    }

    _stopWaveform() {
        cancelAnimationFrame(this.animFrame);
        this.bars.forEach(bar => { bar.style.height = '4px'; });
    }

    destroy() {
        this.stop();
        if (this.audioCtx) this.audioCtx.close();
    }
}

window.VoiceButton = VoiceButton;
