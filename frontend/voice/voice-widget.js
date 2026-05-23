/**
 * SerpentAI Voice Widget
 * 语音输入/输出组件 - Web Speech API 实现
 * 功能：语音识别、文字转语音、音频波形可视化、语音录制
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 * 版本：2.0.0
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
     * @param {Object} options.recognitionOptions - 语音识别配置
     * @param {string} options.recognitionOptions.lang - 语言（默认 'zh-CN'）
     * @param {boolean} options.recognitionOptions.continuous - 是否连续识别
     * @param {boolean} options.recognitionOptions.interimResults - 是否返回中间结果
     * @param {Object} options.synthesisOptions - 语音合成配置
     * @param {number} options.synthesisOptions.rate - 语速 (0.1-10)
     * @param {number} options.synthesisOptions.pitch - 音高 (0-2)
     * @param {number} options.synthesisOptions.volume - 音量 (0-1)
     */
    constructor(options = {}) {
        // 配置
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
        
        // 语音识别配置
        const recOptions = options.recognitionOptions || {};
        this.recognitionLang = recOptions.lang || 'zh-CN';
        this.recognitionContinuous = recOptions.continuous || false;
        this.recognitionInterimResults = recOptions.interimResults || true;
        
        // 语音合成配置
        const synOptions = options.synthesisOptions || {};
        this.synthesisRate = Math.max(0.1, Math.min(10, synOptions.rate || 1.0));
        this.synthesisPitch = Math.max(0, Math.min(2, synOptions.pitch || 1.0));
        this.synthesisVolume = Math.max(0, Math.min(1, synOptions.volume || 1.0));
        
        // 状态
        this.state = 'idle'; // idle, listening, processing, speaking, error, not_supported
        this.previousState = 'idle';
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.audioContext = null;
        this.analyser = null;
        this.analyserTime = null;
        this.isInitialized = false;
        this.isDestroyed = false;
        this.isSupported = {
            recognition: false,
            synthesis: false,
            audioContext: false
        };
        
        // UI 元素
        this.btn = null;
        this.indicator = null;
        this.interimEl = null;
        this.wrapper = null;
        this.waveformCanvas = null;
        this.waveformCtx = null;
        this.animationId = null;
        
        // 录音支持
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.isRecording = false;
        
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
        const hasAudioContext = 'AudioContext' in window || 'webkitAudioContext' in window;
        
        this.isSupported.recognition = hasSpeechRecognition;
        this.isSupported.synthesis = hasSpeechSynthesis;
        this.isSupported.audioContext = hasAudioContext;
        
        if (!hasSpeechRecognition && !hasSpeechSynthesis) {
            const error = new Error('当前浏览器不支持语音功能（需要 Web Speech API）');
            this.onError(error);
            this._setState('not_supported');
            this._renderNotSupported();
            return;
        }
        
        // 初始化语音识别
        if (hasSpeechRecognition) {
            this._initRecognition();
        }
        
        // 初始化语音合成
        if (hasSpeechSynthesis) {
            // 确保语音列表已加载
            if (this.synthesis.getVoices().length === 0) {
                this.synthesis.onvoiceschanged = () => {
                    console.log('语音列表已加载');
                };
            }
        }
        
        // 初始化音频上下文
        if (hasAudioContext) {
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                this.isSupported.audioContext = true;
            } catch (e) {
                console.warn('音频上下文初始化失败:', e);
                this.isSupported.audioContext = false;
            }
        }
        
        this.isInitialized = true;
        this._renderUI();
        this._updateUI();
    }
    
    /**
     * 渲染不支持提示
     * @private
     */
    _renderNotSupported() {
        this.container.innerHTML = `
            <div style="padding: 12px; color: #888; text-align: center;">
                <p>⚠️ 当前浏览器不支持语音功能</p>
                <small>请使用 Chrome、Edge 或 Safari 浏览器</small>
            </div>
        `;
    }
    
    /**
     * 初始化语音识别
     * @private
     */
    _initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = this.recognitionContinuous;
        this.recognition.interimResults = this.recognitionInterimResults;
        this.recognition.lang = this.recognitionLang;
        this.recognition.maxAlternatives = 1;
        
        this.recognition.onstart = () => {
            if (this.isDestroyed) return;
            this._setState('listening');
            this._updateUI();
            this._startWaveformVisualization();
        };
        
        this.recognition.onend = () => {
            if (this.isDestroyed) return;
            
            // 如果正在录音，不更新状态
            if (this.isRecording) return;
            
            if (this.state === 'listening') {
                this._setState('idle');
                this._updateUI();
                this._stopWaveformVisualization();
            }
        };
        
        this.recognition.onresult = (event) => {
            if (this.isDestroyed) return;
            
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
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
                this._stopWaveformVisualization();
            }
        };
        
        this.recognition.onerror = (event) => {
            if (this.isDestroyed) return;
            
            let errorMessage = '语音识别错误';
            let shouldShowError = true;
            
            switch (event.error) {
                case 'not-allowed':
                    errorMessage = '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风';
                    break;
                case 'no-speech':
                    errorMessage = '未检测到语音，请重试';
                    shouldShowError = false; // 不显示错误提示
                    break;
                case 'network':
                    errorMessage = '网络错误，请检查网络连接';
                    break;
                case 'aborted':
                    errorMessage = '语音识别已中止';
                    shouldShowError = false; // 用户主动中止
                    break;
                case 'audio-capture':
                    errorMessage = '无法捕获音频，请检查麦克风';
                    break;
                case 'bad-grammar':
                    errorMessage = '语法错误';
                    break;
                default:
                    errorMessage = `语音识别错误: ${event.error}`;
            }
            
            if (shouldShowError) {
                this.onError(new Error(errorMessage));
            }
            
            this._setState('error');
            setTimeout(() => {
                if (this.state === 'error') {
                    this._setState('idle');
                }
            }, 2000);
            this._updateUI();
            this._stopWaveformVisualization();
        };
    }
    
    /**
     * 设置状态
     * @param {string} state - 新状态
     * @private
     */
    _setState(state) {
        if (this.state === state) return;
        
        this.previousState = this.state;
        this.state = state;
        this.onStateChange(state, this.previousState);
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
        btn.title = this._getStateTooltip();
        btn.style.cssText = `
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 2px solid #3a3a5a;
            background: #252540;
            color: white;
            font-size: 20px;
            cursor: ${this.isSupported.recognition || this.isSupported.synthesis ? 'pointer' : 'not-allowed'};
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            outline: none;
            position: relative;
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
            transition: background 0.3s;
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
            z-index: 1000;
        `;
        wrapper.appendChild(interimEl);
        
        // 创建波形可视化画布
        const canvas = document.createElement('canvas');
        canvas.className = 'vw-waveform';
        canvas.width = 200;
        canvas.height = 60;
        canvas.style.cssText = `
            position: absolute;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a2e;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            display: none;
            z-index: 999;
        `;
        wrapper.appendChild(canvas);
        
        // 事件监听
        btn.addEventListener('click', () => this.toggle());
        btn.addEventListener('mouseenter', () => {
            if (!btn.disabled) {
                btn.style.transform = 'scale(1.1)';
            }
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
        });
        
        // 右键菜单（高级选项）
        btn.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this._showContextMenu(e);
        });
        
        this.container.appendChild(wrapper);
        this.btn = btn;
        this.indicator = indicator;
        this.interimEl = interimEl;
        this.wrapper = wrapper;
        this.waveformCanvas = canvas;
        this.waveformCtx = canvas.getContext('2d');
        
        this._updateUI();
    }
    
    /**
     * 显示右键菜单
     * @param {MouseEvent} event - 鼠标事件
     * @private
     */
    _showContextMenu(event) {
        // 移除已有的菜单
        const existingMenu = document.querySelector('.vw-context-menu');
        if (existingMenu) existingMenu.remove();
        
        const menu = document.createElement('div');
        menu.className = 'vw-context-menu';
        menu.style.cssText = `
            position: fixed;
            top: ${event.clientY}px;
            left: ${event.clientX}px;
            background: #1a1a2e;
            border: 1px solid #3a3a5a;
            border-radius: 6px;
            padding: 4px 0;
            z-index: 10002;
            min-width: 150px;
        `;
        
        const items = [
            {
                label: this.isRecording ? '停止录音' : '开始录音',
                action: () => this.toggleRecording()
            },
            {
                label: '可视化设置',
                action: () => this._showVisualizationSettings()
            },
            {
                label: '语音设置',
                action: () => this._showVoiceSettings()
            }
        ];
        
        items.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.textContent = item.label;
            menuItem.style.cssText = `
                padding: 8px 16px;
                cursor: pointer;
                font-size: 13px;
                color: #e0e0e0;
                transition: background 0.2s;
            `;
            menuItem.addEventListener('mouseenter', () => {
                menuItem.style.background = '#2a2a4a';
            });
            menuItem.addEventListener('mouseleave', () => {
                menuItem.style.background = 'transparent';
            });
            menuItem.addEventListener('click', () => {
                item.action();
                menu.remove();
            });
            menu.appendChild(menuItem);
        });
        
        document.body.appendChild(menu);
        
        // 点击其他地方关闭菜单
        setTimeout(() => {
            const closeMenu = (e) => {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            };
            document.addEventListener('click', closeMenu);
        }, 0);
    }
    
    /**
     * 显示可视化设置
     * @private
     */
    _showVisualizationSettings() {
        // 创建设置面板
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10003;
        `;
        
        modal.innerHTML = `
            <div style="background: #1a1a2e; border: 1px solid #3a3a5a; border-radius: 12px; padding: 24px; max-width: 400px; width: 90%;">
                <h3 style="color: #00d4ff; margin-bottom: 16px;">可视化设置</h3>
                
                <div style="margin-bottom: 12px;">
                    <label style="display: block; margin-bottom: 4px; font-size: 13px;">波形颜色:</label>
                    <input type="color" id="vw-waveform-color" value="#00d4ff" style="width: 100%;">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 4px; font-size: 13px;">背景颜色:</label>
                    <input type="color" id="vw-bg-color" value="#1a1a2e" style="width: 100%;">
                </div>
                
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button class="vw-btn-secondary" onclick="this.closest('div').parentElement.remove()">取消</button>
                    <button class="vw-btn-primary" onclick="this.closest('div').parentElement.remove()">确定</button>
                </div>
            </div>
        `;
        
        // 添加按钮样式
        if (!document.querySelector('#vw-modal-styles')) {
            const style = document.createElement('style');
            style.id = 'vw-modal-styles';
            style.textContent = `
                .vw-btn-secondary {
                    background: #2a2a4a;
                    border: 1px solid #3a3a5a;
                    color: #e0e0e0;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 13px;
                }
                .vw-btn-primary {
                    background: #00d4ff;
                    color: #0a0a1e;
                    border: 1px solid #00d4ff;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 13px;
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(modal);
        
        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
    
    /**
     * 显示语音设置
     * @private
     */
    _showVoiceSettings() {
        // 创建设置面板
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10003;
        `;
        
        modal.innerHTML = `
            <div style="background: #1a1a2e; border: 1px solid #3a3a5a; border-radius: 12px; padding: 24px; max-width: 400px; width: 90%;">
                <h3 style="color: #00d4ff; margin-bottom: 16px;">语音设置</h3>
                
                <div style="margin-bottom: 12px;">
                    <label style="display: block; margin-bottom: 4px; font-size: 13px;">语速 (${this.synthesisRate.toFixed(1)}):</label>
                    <input type="range" id="vw-rate" min="0.1" max="10" step="0.1" value="${this.synthesisRate}" style="width: 100%;">
                </div>
                
                <div style="margin-bottom: 12px;">
                    <label style="display: block; margin-bottom: 4px; font-size: 13px;">音高 (${this.synthesisPitch.toFixed(1)}):</label>
                    <input type="range" id="vw-pitch" min="0" max="2" step="0.1" value="${this.synthesisPitch}" style="width: 100%;">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 4px; font-size: 13px;">音量 (${this.synthesisVolume.toFixed(1)}):</label>
                    <input type="range" id="vw-volume" min="0" max="1" step="0.1" value="${this.synthesisVolume}" style="width: 100%;">
                </div>
                
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button class="vw-btn-secondary" onclick="this.closest('div').parentElement.remove()">取消</button>
                    <button class="vw-btn-primary" id="vw-save-settings">确定</button>
                </div>
            </div>
        `;
        
        // 保存设置
        modal.querySelector('#vw-save-settings').addEventListener('click', () => {
            this.synthesisRate = parseFloat(modal.querySelector('#vw-rate').value);
            this.synthesisPitch = parseFloat(modal.querySelector('#vw-pitch').value);
            this.synthesisVolume = parseFloat(modal.querySelector('#vw-volume').value);
            
            this.showToast('语音设置已保存', 'success');
            modal.remove();
        });
        
        document.body.appendChild(modal);
        
        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
    
    /**
     * 更新 UI 状态
     * @private
     */
    _updateUI() {
        if (!this.btn || !this.indicator) return;
        
        // 更新按钮
        switch (this.state) {
            case 'idle':
                this.btn.innerHTML = '🎤';
                this.btn.style.background = '#252540';
                this.btn.style.borderColor = '#3a3a5a';
                this.btn.disabled = false;
                this.btn.title = this._getStateTooltip();
                this.indicator.style.background = '#888';
                this.indicator.style.animation = 'none';
                break;
            case 'listening':
                this.btn.innerHTML = '🔴';
                this.btn.style.background = '#3a1a1a';
                this.btn.style.borderColor = '#ff4757';
                this.btn.disabled = false;
                this.btn.title = '点击停止录音';
                this.indicator.style.background = '#ff4757';
                this.indicator.style.animation = 'vw-pulse 1s infinite';
                break;
            case 'processing':
                this.btn.innerHTML = '⏳';
                this.btn.style.background = '#2a2a1a';
                this.btn.style.borderColor = '#ffd93d';
                this.btn.disabled = true;
                this.btn.title = '处理中...';
                this.indicator.style.background = '#ffd93d';
                this.indicator.style.animation = 'vw-pulse 0.5s infinite';
                break;
            case 'speaking':
                this.btn.innerHTML = '🔊';
                this.btn.style.background = '#1a3a2a';
                this.btn.style.borderColor = '#6bcb77';
                this.btn.disabled = false;
                this.btn.title = '点击停止朗读';
                this.indicator.style.background = '#6bcb77';
                this.indicator.style.animation = 'vw-pulse 0.8s infinite';
                break;
            case 'error':
                this.btn.innerHTML = '⚠️';
                this.btn.style.background = '#3a1a1a';
                this.btn.style.borderColor = '#ff4757';
                this.btn.disabled = false;
                this.btn.title = '发生错误，点击重试';
                this.indicator.style.background = '#ff4757';
                this.indicator.style.animation = 'none';
                break;
            case 'not_supported':
                this.btn.innerHTML = '🚫';
                this.btn.style.background = '#2a2a2a';
                this.btn.style.borderColor = '#555';
                this.btn.disabled = true;
                this.btn.title = '浏览器不支持语音功能';
                this.indicator.style.background = '#555';
                this.indicator.style.animation = 'none';
                break;
        }
        
        // 添加动画样式
        if (!document.querySelector('#vw-style')) {
            const style = document.createElement('style');
            style.id = 'vw-style';
            style.textContent = `
                @keyframes vw-pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * 获取状态提示文本
     * @returns {string} 提示文本
     * @private
     */
    _getStateTooltip() {
        switch (this.state) {
            case 'idle': return '点击说话';
            case 'listening': return '正在听取...';
            case 'processing': return '处理中...';
            case 'speaking': return '正在朗读...';
            case 'error': return '发生错误，点击重试';
            case 'not_supported': return '浏览器不支持语音功能';
            default: return '语音组件';
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
     * 开始波形可视化
     * @private
     */
    _startWaveformVisualization() {
        if (!this.isSupported.audioContext || !this.analyser) return;
        
        // 显示画布
        if (this.waveformCanvas) {
            this.waveformCanvas.style.display = 'block';
        }
        
        // 开始动画
        const draw = () => {
            if (this.state !== 'listening') {
                this._stopWaveformVisualization();
                return;
            }
            
            this._drawWaveform();
            this.animationId = requestAnimationFrame(draw);
        };
        
        draw();
    }
    
    /**
     * 停止波形可视化
     * @private
     */
    _stopWaveformVisualization() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        // 隐藏画布
        if (this.waveformCanvas) {
            this.waveformCanvas.style.display = 'none';
        }
    }
    
    /**
     * 绘制波形
     * @private
     */
    _drawWaveform() {
        if (!this.analyser || !this.waveformCtx || !this.waveformCanvas) return;
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteFrequencyData(dataArray);
        
        this.waveformCtx.fillStyle = '#1a1a2e';
        this.waveformCtx.fillRect(0, 0, this.waveformCanvas.width, this.waveformCanvas.height);
        
        const barWidth = (this.waveformCanvas.width / bufferLength) * 2.5;
        let barHeight;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            barHeight = (dataArray[i] / 255) * this.waveformCanvas.height;
            
            this.waveformCtx.fillStyle = `rgb(${Math.floor(barHeight + 100)}, 50, 50)`;
            this.waveformCtx.fillRect(x, this.waveformCanvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
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
        } else if (this.state === 'speaking') {
            this.stopSpeaking();
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
            utterance.lang = options.lang || this.recognitionLang;
            utterance.rate = Math.max(0.1, Math.min(10, options.rate || this.synthesisRate));
            utterance.pitch = Math.max(0, Math.min(2, options.pitch || this.synthesisPitch));
            utterance.volume = Math.max(0, Math.min(1, options.volume || this.synthesisVolume));
            
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
     * 切换录音状态
     */
    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    /**
     * 开始录音
     */
    async startRecording() {
        if (this.isRecording) return;
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordedChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.recordedChunks, { type: 'audio/webm' });
                this._onRecordingComplete(blob);
                
                // 停止所有轨道
                stream.getTracks().forEach(track => track.stop());
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            this.showToast('开始录音', 'info');
        } catch (e) {
            console.error('开始录音失败:', e);
            this.onError(new Error(`开始录音失败: ${e.message}`));
        }
    }
    
    /**
     * 停止录音
     */
    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        try {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.showToast('录音已停止', 'info');
        } catch (e) {
            console.error('停止录音失败:', e);
            this.onError(new Error(`停止录音失败: ${e.message}`));
        }
    }
    
    /**
     * 录音完成回调
     * @param {Blob} blob - 录音数据
     * @private
     */
    _onRecordingComplete(blob) {
        // 创建音频播放器
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        
        // 可以 here 上传到服务器或进行其他处理
        console.log('录音完成:', blob);
        this.showToast(`录音完成 (${(blob.size / 1024).toFixed(1)} KB)`, 'success');
        
        // 示例：自动播放
        // audio.play();
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
        
        if (!this.isSupported.audioContext) {
            this.onError(new Error('AudioContext 不可用'));
            return null;
        }
        
        try {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            const source = this.audioContext.createMediaElementSource(audioElement);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            
            source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            
            // 创建时域分析器
            this.analyserTime = this.audioContext.createAnalyser();
            this.analyserTime.fftSize = 256;
            source.connect(this.analyserTime);
            
            return this.analyser;
        } catch (e) {
            this.onError(new Error(`初始化波形可视化失败: ${e.message}`));
            return null;
        }
    }
    
    /**
     * 获取波形数据（频域）
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
        if (!this.analyserTime) return new Uint8Array(0);
        
        const data = new Uint8Array(this.analyserTime.fftSize);
        this.analyserTime.getByteTimeDomainData(data);
        return data;
    }
    
    /**
     * 显示 toast 通知
     * @param {string} message - 通知消息
     * @param {string} type - 类型：success, error, info, warning
     */
    showToast(message, type = 'info') {
        // 移除已有的 toast
        const existingToast = document.body.querySelector('.vw-toast');
        if (existingToast) existingToast.remove();

        const toast = document.createElement('div');
        toast.className = `vw-toast vw-toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-size: 14px;
            z-index: 10000;
            animation: vw-slideIn 0.3s ease;
            background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : type === 'warning' ? '#ffd93d' : '#00d4ff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            max-width: 400px;
            word-break: break-word;
        `;
        
        // 添加动画样式
        if (!document.querySelector('#vw-toast-style')) {
            const style = document.createElement('style');
            style.id = 'vw-toast-style';
            style.textContent = `
                @keyframes vw-slideIn {
                    from { transform: translateX(100px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes vw-slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'vw-slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * 销毁组件
     */
    destroy() {
        this.isDestroyed = true;
        
        // 停止语音识别
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                // 忽略错误
            }
            this.recognition.onstart = null;
            this.recognition.onend = null;
            this.recognition.onresult = null;
            this.recognition.onerror = null;
        }
        
        // 停止语音合成
        if (this.synthesis) {
            this.synthesis.cancel();
        }
        
        // 停止录音
        if (this.isRecording) {
            this.stopRecording();
        }
        
        // 关闭音频上下文
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        // 停止动画
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        // 移除 DOM 元素
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }
        
        // 移除事件监听器
        if (this.btn) {
            this.btn.removeEventListener('click', this.toggle);
        }
        
        // 清理引用
        this.btn = null;
        this.indicator = null;
        this.interimEl = null;
        this.wrapper = null;
        this.waveformCanvas = null;
        this.waveformCtx = null;
        this.recognition = null;
        this.analyser = null;
        this.analyserTime = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        
        console.log('VoiceWidget 已销毁');
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceWidget;
}
