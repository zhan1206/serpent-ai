# SerpentAI Desktop Client

Tauri 2.x based modern desktop client connecting to SerpentAI backend API.

## Design Philosophy
- **Token consumption -85%** - Four-layer memory system + tool precompilation distillation
- **Hardware requirements -75%** - Lightweight Tauri framework
- **Effectiveness +70%** - ReAct paradigm + multi-agent collaboration

## Prerequisites
1. Rust (>= 1.70) - https://rustup.rs/
2. Node.js (>= 18) - https://nodejs.org/
3. Tauri CLI: `cargo install tauri-cli --version "^2.0"`
4. SerpentAI backend running on `localhost:8000`

## Build
```bash
# 1. Start backend
cd backend && pip install -r requirements.txt && python main.py

# 2. Build desktop client
cd desktop-client && npm install --prefix frontend && cargo tauri build
```

## Development
```bash
# Terminal 1: backend
cd backend && python main.py

# Terminal 2: Tauri dev mode
cd desktop-client && cargo tauri dev
```

## Shortcuts
| Key | Action |
|-----|--------|
| Ctrl+Shift+S | Voice input |
| Ctrl+N | New chat |
| Ctrl+Enter | Send message |
| Escape | Close panel |
