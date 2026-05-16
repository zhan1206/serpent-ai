# SerpentAI Rust核心

本目录包含用Rust编写的高性能核心模块。

## 为什么使用Rust

- **性能**: 比Python快10-100倍
- **内存安全**: 避免缓冲区溢出等问题
- **并发安全**: 无锁并发原语

## 模块说明

### 1. tool_sandbox (工具沙箱)
- 基于WebAssembly的隔离执行环境
- 资源限制（CPU、内存、网络）
- 沙箱状态管理

### 2. token_optimizer (Token优化器)
- 高效字符串处理
- Token计数算法优化
- 压缩算法实现

### 3. crypto_module (加密模块)
- AES-256-GCM硬件加速
- 高效哈希函数
- 密钥派生

### 4. memory_index (记忆索引)
- 高效向量搜索
- 近似最近邻算法
- 内存映射优化

## 项目结构

```
rust_core/
├── src/
│   ├── tool_sandbox/    # 工具沙箱
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── runner.rs
│   │       └── limits.rs
│   ├── token_optimizer/ # Token优化器
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── counter.rs
│   │       └── compressor.rs
│   ├── crypto_module/   # 加密模块
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── aes.rs
│   │       └── kdf.rs
│   └── memory_index/   # 记忆索引
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── index.rs
│           └── search.rs
├── tests/               # 集成测试
├── benches/             # 性能基准测试
└── build.rs            # 构建配置
```

## 开发指南

### 前置要求
- Rust 1.78+
- Cargo
- wasm-pack (用于WebAssembly)

### 构建
```bash
# 本地构建
cargo build --release

# WebAssembly构建
wasm-pack build --target web tool_sandbox
```

### 测试
```bash
cargo test
cargo test --release  # 优化模式测试
```

### 性能基准
```bash
cargo bench
```

## Python集成

通过PyO3绑定Python:

```python
# 安装
pip install serpent-ai-core

# 使用
from serpent_ai_core import ToolSandbox, TokenOptimizer

sandbox = ToolSandbox(memory_limit="100MB")
result = sandbox.run("python", "print('hello')")
```

## 待实现

- [ ] tool_sandbox模块开发
- [ ] token_optimizer模块开发
- [ ] crypto_module模块开发
- [ ] memory_index模块开发
- [ ] PyO3 Python绑定
- [ ] 性能测试和优化