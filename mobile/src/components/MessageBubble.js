/* MessageBubble - 聊天消息气泡组件 */
class MessageBubble {
    constructor(container, options = {}) {
        this.container = container;
        this.onAction = options.onAction || (() => {});
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.swipeThreshold = 60;
    }

    create(msg) {
        const div = document.createElement('div');
        div.className = `message ${msg.role}`;
        div.dataset.id = msg.id || Date.now().toString();

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        const content = document.createElement('div');
        content.className = 'bubble-content';
        content.innerHTML = this._formatContent(msg.content);
        bubble.appendChild(content);

        if (msg.timestamp) {
            const time = document.createElement('div');
            time.className = 'msg-time';
            const d = new Date(msg.timestamp);
            time.textContent = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            bubble.appendChild(time);
        }

        div.appendChild(bubble);

        // Swipe gestures on assistant messages
        if (msg.role === 'assistant') {
            this._addSwipeGesture(div, msg);
        }

        // Haptic feedback
        div.addEventListener('touchstart', () => {
            if (navigator.vibrate) navigator.vibrate(3);
        }, { passive: true });

        return div;
    }

    _formatContent(text) {
        if (!text) return '';
        // Code blocks
        text = text.replace(/```(\w*)\n([\s\S]*?)```/g,
            '<pre><code>$2</code></pre>');
        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Italic
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // Line breaks
        text = text.replace(/\n/g, '<br>');
        return text;
    }

    _addSwipeGesture(el, msg) {
        el.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        el.addEventListener('touchend', (e) => {
            const dx = e.changedTouches[0].clientX - this.touchStartX;
            const dy = e.changedTouches[0].clientY - this.touchStartY;
            if (Math.abs(dx) > this.swipeThreshold && Math.abs(dy) < 40) {
                if (navigator.vibrate) navigator.vibrate(15);
                if (dx > 0) {
                    this.onAction('copy', msg);
                } else {
                    this.onAction('delete', msg);
                }
            }
        }, { passive: true });
    }

    createTyping() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.id = 'typing-indicator';
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.innerHTML = '<span></span><span></span><span></span>';
        bubble.appendChild(typing);
        div.appendChild(bubble);
        return div;
    }
}

window.MessageBubble = MessageBubble;
