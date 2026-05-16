# SerpentAI 前端

本目录包含SerpentAI的Web前端和桌面客户端源代码。

## 技术栈

- **框架**: React 18.3 + TypeScript 5.4
- **UI组件**: shadcn/ui 0.8 + Tailwind CSS 3.4
- **状态管理**: Zustand 4.5
- **路由**: React Router 6.23
- **图表**: Recharts 2.12
- **桌面端**: Electron 30.0
- **HTTP**: Axios + React Query
- **WebSocket**: Socket.IO

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── components/      # React组件
│   │   ├── ui/          # shadcn/ui组件
│   │   ├── chat/        # 聊天组件
│   │   ├── memory/      # 记忆系统UI
│   │   ├── tools/       # 工具管理UI
│   │   └── settings/   # 设置页面
│   ├── pages/           # 页面组件
│   ├── hooks/          # 自定义Hooks
│   ├── lib/            # 工具函数
│   ├── stores/         # Zustand状态存储
│   ├── styles/         # 全局样式
│   └── types/          # TypeScript类型
├── electron/           # Electron主进程
├── tests/              # 前端测试
└── dist/              # 构建输出
```

## 开发指南

### 前置要求
- Node.js 18+
- npm 9+

### 安装依赖
```bash
npm install
```

### 开发模式
```bash
# Web开发
npm run web

# 桌面端开发
npm run desktop
```

### 构建
```bash
# Web构建
npm run build:web

# 桌面端构建
npm run build:desktop
```

### 测试
```bash
npm run test
npm run test:ui  # UI组件测试
```

## 功能页面

1. **首页** (`/`)
   - 项目介绍
   - 特性展示
   - 快速开始按钮

2. **控制台** (`/console`)
   - 系统状态监控
   - Token消耗统计
   - 内存使用情况
   -活跃会话列表

3. **聊天** (`/chat`)
   - 对话界面
   - 会话历史
   - 工具调用展示
   - 记忆状态

4. **记忆管理** (`/memory`)
   - 记忆可视化
   - 记忆搜索
   - 记忆编辑
   - 记忆导出

5. **工具库** (`/tools`)
   - 工具列表
   - 工具搜索
   - 工具详情
   - 自定义工具

6. **智能体** (`/agents`)
   - 智能体管理
   - 角色配置
   - 工作流编排

7. **设置** (`/settings`)
   - 模型配置
   - 通道配置
   - 安全设置
   - 效率引擎配置

## 设计规范

遵循 [shadcn/ui](https://ui.shadcn.com/) 设计规范：
- 使用深色主题（默认）
- 金色和深蓝色点缀
- 蛇形UI元素
- 响应式设计

## 待实现

- [ ] React组件开发
- [ ] 状态管理集成
- [ ] API对接
- [ ] WebSocket实时通信
- [ ] 桌面客户端打包
- [ ] 国际化支持