# SerpentAI 移动端

本目录包含SerpentAI的iOS和Android移动客户端源代码。

## 技术栈

- **框架**: React Native 0.74
- **语言**: TypeScript 5.4
- **状态管理**: Zustand 4.5
- **导航**: React Navigation 6
- **UI组件**: React Native Paper
- **HTTP**: Axios
- **离线存储**: AsyncStorage + WatermelonDB
- **语音**: react-native-voice + react-native-tts

## 项目结构

```
mobile/
├── src/
│   ├── components/      # 组件
│   ├── screens/        # 页面
│   ├── navigation/     # 导航配置
│   ├── stores/        # 状态管理
│   ├── services/      # API服务
│   ├── hooks/         # 自定义Hooks
│   ├── utils/         # 工具函数
│   └── types/         # 类型定义
├── ios/               # iOS原生代码
├── android/           # Android原生代码
└── tests/             # 测试
```

## 功能特性

1. **即时通讯**
   - 实时AI对话
   - 消息历史同步
   - 离线消息

2. **多平台支持**
   - iOS 13+
   - Android 8+

3. **推送通知**
   - 消息通知
   - 任务完成通知

4. **语音交互**
   - 语音输入
   - 语音输出
   - 语音唤醒

5. **离线支持**
   - 离线对话缓存
   - 本地记忆存储

## 开发指南

### 前置要求
- Node.js 18+
- npm 9+
- Xcode 15+ (iOS)
- Android Studio (Android)
- React Native CLI

### 安装
```bash
npm install
```

### 运行
```bash
# iOS
npm run ios

# Android
npm run android
```

### 构建
```bash
# iOS
npm run build:ios

# Android
npm run build:android
```

## 待实现

- [ ] React Native项目初始化
- [ ] 核心UI组件开发
- [ ] API服务集成
- [ ] 离线存储实现
- [ ] 推送通知
- [ ] 语音交互
- [ ] App Store/Google Play上架