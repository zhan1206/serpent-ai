/* VoiceView - 语音交互视图 */
class VoiceView {
    constructor(api) {
        this.api = api;
        this.voiceBtn = new VoiceButton(null, {
            onStart: () => this._onStart(),
            onStop: () => this._onStop(),
            onResult: (text, isFinal) => this._onResult(text, isFinal)
        });
        this.fullTranscript = '';
        this.isProcessing = false;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'voice-view';

        // Status
        this.statusEl = document.createElement('div');
        this.statusEl.className = 'voice-status';
        this.statusEl.textContent = '点击麦克风开始说话';
        view.appendChild(this.statusEl);

        // Voice button
        const btnWrapper = this.voiceBtn.create();
        view.appendChild(btnWrapper);

        // Transcript
        this.transcriptEl = document.createElement('div');
        this.transcriptEl.className = 'voice-transcript';
        this.transcriptEl.textContent = '识别到的文字将显示在这里...';
        view.appendChild(this.transcriptEl);

        // AI Response
        this.resultEl = document.createElement('div');
        this.resultEl.className = 'voice-result hidden';
        view.appendChild(this.resultEl);

        // Submit button (for sending voice text to chat)
        this.submitBtn = document.createElement('button');
        this.submitBtn.className = 'send-btn';
        this.submitBtn.innerHTML = '&#x27A4; 发送到聊天';
        this.submitBtn.style.cssText = 'width:auto;padding:12px 24px;border-radius:24px;font-size:15px;';
        this.submitBtn.disabled = true;
        this.submitBtn.addEventListener('click', () => this._sendToChat());
        view.appendChild(this.submitBtn);

        return view;
    }

    _onStart() {
        this.statusEl.textContent = '正在聆听...';
        this.fullTranscript = '';
        this.transcriptEl.textContent = '正在识别...';
        this.resultEl.classList.add('hidden');
        this.submitBtn.disabled = true;
    }

    _onStop() {
        if (!this.fullTranscript.trim()) {
            this.statusEl.textContent = '未检测到语音，请重试';
            return;
        }
        this.statusEl.textContent = '识别完成';
        this.submitBtn.disabled = false;
    }

    _onResult(text, isFinal) {
        if (isFinal) {
            this.fullTranscript += text;
            this.transcriptEl.textContent = this.fullTranscript;
        } else {
            this.transcriptEl.textContent = this.fullTranscript + text;
        }
    }

    async _sendToChat() {
        if (!this.fullTranscript.trim() || this.isProcessing) return;
        this.isProcessing = true;
        this.submitBtn.disabled = true;
        this.statusEl.textContent = '正在思考...';

        try {
            const response = await this.api.chat(
                localStorage.getItem('serpent_session_id') || 'mobile_voice',
                this.fullTranscript
            );
            this.resultEl.classList.remove('hidden');
            this.resultEl.innerHTML = `
                <h3>&#x1F40D; SerpentAI 回复</h3>
                <p>${this._formatContent(response.response || response.content || '无响应')}</p>`;
            this.statusEl.textContent = '回复完成';

            // Speak the response if available
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(response.response || response.content || '');
                utterance.lang = 'zh-CN';
                utterance.rate = 1.1;
                speechSynthesis.speak(utterance);
            }
        } catch (e) {
            this.statusEl.textContent = `请求失败: ${e.message}`;
        }

        this.isProcessing = false;
    }

    _formatContent(text) {
        return text
            .replace(/```[\s\S]*?```/g, '<pre style="font-size:12px;overflow-x:auto;padding:8px;background:rgba(0,0,0,0.1);border-radius:6px;margin:4px 0">$&</pre>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
}

window.VoiceView = VoiceView;
