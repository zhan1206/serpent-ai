/**
 * SerpentAI Voice Widget
 * 语音输入组件 - Web Speech API 实现
 */

class VoiceWidget {
    constructor(options = {}) {
        this.apiBase = options.apiBase || 'http://localhost:8000';
        this.container = options.container || document.body;
        this.onTranscript = options.onTranscript || (text => {});
        this.onError = options.onError || (err => console.error(err));
        this.onStateChange = options.onStateChange || (state => {});
        
        this.state = 'idle'; // idle, listening, processing, speaking
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.audioContext = null;
        this.analyser = null;
        
        this._init();
    }
    
    _init() {
        // 检查浏览器支持
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.onError(new Error('当前浏览器不支持语音识别'));
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'zh-CN';
        
        this.recognition.onstart = () => this._setState('listening');
        this.recognition.onend = () => {
            if (this.state === 'listening') this._setState('idle');
        };
        this.recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(r => r[0].transcript)
                .join('');
            
            if (event.results[0].isFinal) {
                this.onTranscript(transcript);
                this._setState('idle');
            }
        };
        this.recognition.onerror = (event) => {
            this.onError(new Error(event.error));
            this._setState('idle');
        };
    }
    
    _setState(state) {
        this.state = state;
        this.onStateChange(state);
    }
    
    start() {
        if (this.state !== 'idle') return;
        try {
            this.recognition.start();
        } catch (e) {
            this.onError(e);
        }
    }
    
    stop() {
        if (this.state !== 'listening') return;
        try {
            this.recognition.stop();
        } catch (e) {
            this.onError(e);
        }
    }
    
    toggle() {
        if (this.state === 'idle') {
            this.start();
        } else if (this.state === 'listening') {
            this.stop();
        }
    }
    
    // TTS: 文字转语音
    speak(text, options = {}) {
        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = options.lang || 'zh-CN';
            utterance.rate = options.rate || 1.0;
            utterance.pitch = options.pitch || 1.0;
            utterance.volume = options.volume || 1.0;
            
            // 选择中文语音
            const voices = this.synthesis.getVoices();
            const zhVoice = voices.find(v => v.lang.includes('zh')) || voices[0];
            if (zhVoice) utterance.voice = zhVoice;
            
            utterance.onend = () => resolve();
            utterance.onerror = (e) => reject(e);
            
            this.synthesis.cancel();
            this.synthesis.speak(utterance);
            this._setState('speaking');
        });
    }
    
    stopSpeaking() {
        this.synthesis.cancel();
        this._setState('idle');
    }
    
    // 音频波形可视化
    initWaveform(audioElement) {
        if (!audioElement) return;
        
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = this.audioContext.createMediaElementSource(audioElement);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        
        source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
        
        return this.analyser;
    }
    
    getWaveformData() {
        if (!this.analyser) return new Uint8Array(0);
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);
        return data;
    }
    
    destroy() {
        this.stop();
        this.stopSpeaking();
        if (this.recognition) {
            this.recognition.onstart = null;
            this.recognition.onend = null;
            this.recognition.onresult = null;
            this.recognition.onerror = null;
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceWidget;
}
