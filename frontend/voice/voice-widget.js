/**
 * SerpentAI Voice Widget
 * 语音输入/输出组件 - Web Speech API 实现
 * 功能：语音识别、文字转语音、音频波形可视化
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 */

class VoiceWidget {
    /**
     * 构造函数
     * @param {Object} options - 配置选项
     * @param {string} options.apiBase - API 基础 URL
     * @param {HTMLElement} options.container - 容器元素
     * @param {Function} options.onTranscript - 语音识别结果回调
     * @param {Function} options.onError - 错误回调
     * @param {Function} options.onStateChange - 状态变化回调
     */
    constructor(options = {}) {
        this.apiBase = options.apiBase || 'http://localhost:8000';
        this.container = options.container || document.body;
        this.onTranscript = options.onTranscript || (text => {
            console.log('Transcript:', text);
        });
        this.onError = options.onError || (err => {
            console.error('VoiceWidget Error:', err);
        });
        this.onStateChange = options.onStateChange || (state => {
            console.log('VoiceWidget State:', state);
        });
        
        this.state = 'idle'; // idle, listening, processing, speaking, error
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.audioContext = null;
        this.analyser = null;
        this.isInitialized = false;
        this.isDestroyed = false;
        
        this._init();
    }
    
    /**
     * 初始化语音组件
     * @private
     */
    _init() {
        // 检查浏览器支持
        const hasSpeechRecognition = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        const hasSpeechSynthesis = 'speechSynthesis' in window;
        
        if (!hasSpeechRecognition && !hasSpeechSynthesis) {
            const error = new Error('当前浏览器不支持语音功能（需要 Web Speech API）');
            this.onError(error);
            this._setState('error');
            return;
        }
        
        if (hasSpeechRecognition) {
            this._initRecognition();
        }
        
        if (hasSpeechSynthesis) {
            // 确保语音列表已加载
            if (this.synthesis.getVoices().length === 0) {
                this.synthesis.onvoiceschanged = () => {
                    // 语音列表加载完成
                };
            }
        }
        
        this.isInitialized = true;
        this._renderUI();
    }
    
    /**
     * 初始化语音识别
     * @private
     */
    _initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'zh-CN';
        this.recognition.maxAlternatives = 1;
        
        this.recognition.onstart = () => {
            if (this.isDestroyed) return;
            this._setState('listening');
            this._updateUI();
        };
        
        this.recognition.onend = () => {
            if (this.isDestroyed) return;
            if (this.state === 'listening') {
                this._setState('idle');
                this._updateUI();
            }
        };
        
        this.recognition.onresult = (event) => {
            if (this.isDestroyed) return;
            
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = 0; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }
            
            // 显示临时结果
            if (interimTranscript) {
                this._showInterimText(interimTranscript);
            }
            
            // 最终结果
            if (finalTranscript) {
                this.onTranscript(finalTranscript);
                this._hideInterimText();
                this._setState('idle');
                this._updateUI();
            }
        };
        
        this.recognition.onerror = (event) => {
            if (this.isDestroyed) return;
            
            let errorMessage = '语音识别错误';
            switch (event.error) {
                case 'not-allowed':
                    errorMessage = '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风';
                    break;
                case 'no-speech':
                    errorMessage = '未检测到语音，请重试';
                    break;
                case 'network':
                    errorMessage = '网络错误，请检查网络连接';
                    break;
                case 'aborted':
                    errorMessage = '语音识别已中止';
                    break;
                default:
                    errorMessage = `语音识别错误: ${event.error}`;
            }
            
            this.onError(new Error(errorMessage));
            this._setState('error');
            setTimeout(() => {
                if (this.state === 'error') {
                    this._setState('idle');
                }
            }, 2000);
            this._updateUI();
        };
    }
    
    /**
     * 设置状态
     * @param {string} state - 新状态
     * @private
     */
    _setState(state) {
        this.state = state;
        this.onStateChange(state);
        this._updateUI();
    }
    
    /**
     * 渲染 UI
     * @private
     */
    _renderUI() {
        // 创建语音按钮
        const btn = document.createElement('button');
        btn.className = 'vw-btn';
        btn.innerHTML = '🎤';
        btn.title = '点击说话';
        btn.style.cssText = `
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 2px solid #3a3a5a;
            background: #252540;
            color: white;
            font-size: 20px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            outline: none;
        `;
        
        // 创建状态指示器
        const indicator = document.createElement('div');
        indicator.className = 'vw-indicator';
        indicator.style.cssText = `
            position: absolute;
            bottom: -4px;
            right: -4px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #888;
            border: 2px solid #252540;
        `;
        
        // 创建容器
        const wrapper = document.createElement('div');
        wrapper.className = 'vw-wrapper';
        wrapper.style.cssText = 'position: relative; display: inline-block;';
        wrapper.appendChild(btn);
        wrapper.appendChild(indicator);
        
        // 创建临时文本显示区域
        const interimEl = document.createElement('div');
        interimEl.className = 'vw-interim';
        interimEl.style.cssText = `
            position: absolute;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a2e;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            color: #e0e0e0;
            max-width: 300px;
            min-width: 100px;
            text-align: center;
            display: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        wrapper.appendChild(interimEl);
        
        // 事件监听
        btn.addEventListener('click', () => this.toggle());
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.1)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
        });
        
        this.container.appendChild(wrapper);
        this.btn = btn;
        this.indicator = indicator;
        this.interimEl = interimEl;
        this.wrapper = wrapper;
        
        this._updateUI();
    }
    
    /**
     * 更新 UI 状态
     * @private
     */
    _updateUI() {
        if (!this.btn || !this.indicator) return;
        
        switch (this.state) {
            case 'idle':
                this.btn.innerHTML = '🎤';
                this.btn.style.background = '#252540';
                this.btn.style.borderColor = '#3a3a5a';
                this.btn.disabled = false;
                this.indicator.style.background = '#888';
                break;
            case 'listening':
                this.btn.innerHTML = '🔴';
                this.btn.style.background = '#3a1a1a';
                this.btn.style.borderColor = '#ff4757';
                this.btn.disabled = false;
                this.indicator.style.background = '#ff4757';
                this.indicator.style.animation = 'vw-pulse 1s infinite';
                break;
            case 'processing':
                this.btn.innerHTML = '⏳';
                this.btn.style.background = '#2a2a1a';
                this.btn.style.borderColor = '#ffd93d';
                this.btn.disabled = true;
                this.indicator.style.background = '#ffd93d';
                this.indicator.style.animation = 'vw-pulse 0.5s infinite';
                break;
            case 'speaking':
                this.btn.innerHTML = '🔊';
                this.btn.style.background = '#1a3a2a';
                this.btn.style.borderColor = '#6bcb77';
                this.btn.disabled = false;
                this.indicator.style.background = '#6bcb77';
                this.indicator.style.animation = 'vw-pulse 0.8s infinite';
                break;
            case 'error':
                this.btn.innerHTML = '⚠️';
                this.btn.style.background = '#3a1a1a';
                this.btn.style.borderColor = '#ff4757';
                this.btn.disabled = false;
                this.indicator.style.background = '#ff4757';
                this.indicator.style.animation = 'none';
                break;
        }
        
        // 添加动画样式
        if (!document.querySelector('#vw-style')) {
            const style = document.createElement('style');
            style.id = 'vw-style';
            style.textContent = `
                @keyframes vw-pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * 显示临时识别文本
     * @param {string} text - 临时文本
     * @private
     */
    _showInterimText(text) {
        if (!this.interimEl) return;
        this.interimEl.textContent = text;
        this.interimEl.style.display = 'block';
    }
    
    /**
     * 隐藏临时识别文本
     * @private
     */
    _hideInterimText() {
        if (!this.interimEl) return;
        this.interimEl.style.display = 'none';
    }

    /**
     * 开始语音识别
     */
    start() {
        if (this.state !== 'idle') {
            console.warn('VoiceWidget: 当前状态不允许开始识别');
            return;
        }
        
        if (!this.recognition) {
            this.onError(new Error('语音识别不可用'));
            return;
        }
        
        try {
            this.recognition.start();
        } catch (e) {
            // 如果已经在运行，先停止再开始
            if (e.message.includes('already started')) {
                this.recognition.stop();
                setTimeout(() => this.recognition.start(), 200);
            } else {
                this.onError(e);
            }
        }
    }
    
    /**
     * 停止语音识别
     */
    stop() {
        if (this.state !== 'listening') return;
        
        try {
            this.recognition.stop();
            this._hideInterimText();
        } catch (e) {
            this.onError(e);
        }
    }
    
    /**
     * 切换语音识别状态
     */
    toggle() {
        if (this.state === 'idle') {
            this.start();
        } else if (this.state === 'listening') {
            this.stop();
        }
    }
    
    /**
     * 文字转语音
     * @param {string} text - 要朗读的文本
     * @param {Object} options - 配置选项
     * @param {string} options.lang - 语言
     * @param {number} options.rate - 语速 (0.1-10)
     * @param {number} options.pitch - 音高 (0-2)
     * @param {number} options.volume - 音量 (0-1)
     * @returns {Promise} 朗读完成的 Promise
     */
    speak(text, options = {}) {
        return new Promise((resolve, reject) => {
            if (!this.synthesis) {
                reject(new Error('语音合成不可用'));
                return;
            }
            
            // 停止当前朗读
            this.stopSpeaking();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = options.lang || 'zh-CN';
            utterance.rate = Math.max(0.1, Math.min(10, options.rate || 1.0));
            utterance.pitch = Math.max(0, Math.min(2, options.pitch || 1.0));
            utterance.volume = Math.max(0, Math.min(1, options.volume || 1.0));
            
            // 选择语音
            const voices = this.synthesis.getVoices();
            const zhVoice = voices.find(v => v.lang.includes('zh')) || 
                           voices.find(v => v.lang.includes('CN')) ||
                           voices[0];
            if (zhVoice) utterance.voice = zhVoice;
            
            utterance.onstart = () => {
                this._setState('speaking');
            };
            
            utterance.onend = () => {
                if (this.state === 'speaking') {
                    this._setState('idle');
                }
                resolve();
            };
            
            utterance.onerror = (e) => {
                // 忽略中断错误
                if (e.error === 'interrupted' || e.error === 'canceled') {
                    resolve();
                    return;
                }
                
                let errorMessage = '语音合成错误';
                switch (e.error) {
                    case 'network':
                        errorMessage = '网络错误，无法合成语音';
                        break;
                    case 'synthesis-unavailable':
                        errorMessage = '语音合成不可用';
                        break;
                    default:
                        errorMessage = `语音合成错误: ${e.error}`;
                }
                
                this._setState('error');
                setTimeout(() => {
                    if (this.state === 'error') {
                        this._setState('idle');
                    }
                }, 2000);
                
                reject(new Error(errorMessage));
            };
            
            this.synthesis.speak(utterance);
        });
    }
    
    /**
     * 停止朗读
     */
    stopSpeaking() {
        if (this.synthesis) {
            this.synthesis.cancel();
            if (this.state === 'speaking') {
                this._setState('idle');
            }
        }
    }
    
    /**
     * 初始化音频波形可视化
     * @param {HTMLAudioElement} audioElement - 音频元素
     * @returns {AnalyserNode|null} 分析器节点
     */
    initWaveform(audioElement) {
        if (!audioElement) {
            this.onError(new Error('audioElement 不能为空'));
            return null;
        }
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioContext.createMediaElementSource(audioElement);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            
            source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            
            return this.analyser;
        } catch (e) {
            this.onError(new Error(`初始化波形可视化失败: ${e.message}`));
            return null;
        }
    }
    
    /**
     * 获取波形数据
     * @returns {Uint8Array} 频率数据
     */
    getWaveformData() {
        if (!this.analyser) return new Uint8Array(0);
        
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);
        return data;
    }
    
    /**
     * 获取波形数据（时域）
     * @returns {Uint8Array} 时域数据
     */
    getWaveformTimeData() {
        if (!this.analyser) return new Uint8Array(0);
        
        const data = new Uint8Array(this.analyser.fftSize);
        this.analyser.getByteTimeDomainData(data);
        return data;
    }
    
    /**
     * 销毁组件
     */
    destroy() {
        this.isDestroyed = true;
        this.stop();
        this.stopSpeaking();
        
        if (this.recognition) {
            this.recognition.onstart = null;
            this.recognition.onend = null;
            this.recognition.onresult = null;
            this.recognition.onerror = null;
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        // 移除 DOM 元素
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }
        
        this.btn = null;
        this.indicator = null;
        this.interimEl = null;
        this.wrapper = null;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceWidget;
}
