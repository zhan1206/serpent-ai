"""
SerpentAI 国际化管理器 (i18n Manager)
功能：多语言支持，支持中/英/日三种语言
版本：2.0.0
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache


class I18nManager:
    """
    国际化管理器类
    
    功能：
    - 语言包加载（JSON格式）
    - 支持中/英/日三种语言
    - 内置默认翻译（100+条常用UI字符串）
    - 动态语言切换
    - 翻译函数支持变量插值
    - 语言检测
    - 翻译缺失回退策略
    """
    
    # 支持的语言列表
    SUPPORTED_LANGUAGES = ['zh', 'en', 'ja']
    
    # 默认语言（回退语言）
    DEFAULT_LANGUAGE = 'en'
    
    # 内置默认翻译（100+条常用UI字符串）
    BUILTIN_TRANSLATIONS = {
        'en': {
            # 通用
            'app.title': 'SerpentAI',
            'app.version': 'v2.0.0',
            'app.loading': 'Loading...',
            'app.ready': 'Ready',
            'app.error': 'Error',
            'app.success': 'Success',
            'app.warning': 'Warning',
            'app.info': 'Info',
            'app.confirm': 'Confirm',
            'app.cancel': 'Cancel',
            'app.save': 'Save',
            'app.delete': 'Delete',
            'app.edit': 'Edit',
            'app.close': 'Close',
            'app.refresh': 'Refresh',
            'app.search': 'Search',
            'app.filter': 'Filter',
            'app.sort': 'Sort',
            'app.export': 'Export',
            'app.import': 'Import',
            'app.settings': 'Settings',
            'app.help': 'Help',
            'app.about': 'About',
            
            # 导航
            'nav.home': 'Home',
            'nav.chat': 'Chat',
            'nav.tools': 'Tools',
            'nav.plugins': 'Plugins',
            'nav.skills': 'Skills',
            'nav.workflow': 'Workflow',
            'nav.settings': 'Settings',
            
            # 聊天界面
            'chat.title': 'Chat',
            'chat.input_placeholder': 'Type a message... (Shift+Enter for new line)',
            'chat.send': 'Send',
            'chat.clear': 'Clear Chat',
            'chat.typing': 'Thinking...',
            'chat.no_messages': 'No messages yet',
            'chat.user': 'You',
            'chat.assistant': 'Assistant',
            'chat.error_send': 'Failed to send message',
            'chat.error_timeout': 'Request timed out',
            'chat.error_cancelled': 'Request cancelled',
            
            # 模型选择
            'model.select': 'Select Model',
            'model.current': 'Current Model',
            'model.loading': 'Loading models...',
            'model.none': 'No models available',
            'model.switch_success': 'Model switched to: {name}',
            
            # 工具管理
            'tools.title': 'Available Tools',
            'tools.enabled': 'Enabled',
            'tools.disabled': 'Disabled',
            'tools.none': 'No tools available',
            'tools.enable': 'Enable',
            'tools.disable': 'Disable',
            'tool.toggle_success': 'Tool "{name}" {action}',
            
            # 插件管理
            'plugins.title': 'Installed Plugins',
            'plugins.none': 'No plugins installed',
            'plugins.load': 'Load',
            'plugins.unload': 'Unload',
            'plugins.reload': 'Reload',
            'plugins.details': 'Details',
            'plugins.store': 'Plugin Store',
            'plugin.load_success': 'Plugin "{name}" loaded',
            'plugin.unload_success': 'Plugin "{name}" unloaded',
            'plugin.reload_success': 'Plugin "{name}" reloaded',
            'plugin.state_started': 'Started',
            'plugin.state_stopped': 'Stopped',
            'plugin.state_loaded': 'Loaded',
            'plugin.state_error': 'Error',
            
            # 技能管理
            'skills.title': 'Installed Skills',
            'skills.none': 'No skills installed',
            'skills.enable': 'Enable',
            'skills.disable': 'Disable',
            'skill.toggle_success': 'Skill "{name}" {action}',
            'skill.disabled': 'Disabled',
            
            # 工作流
            'workflow.title': 'Workflow Editor',
            'workflow.new': 'New Workflow',
            'workflow.save': 'Save',
            'workflow.execute': 'Execute',
            'workflow.validate': 'Validate',
            'workflow.clear': 'Clear',
            'workflow.templates': 'Templates',
            'workflow.nodes': 'Nodes',
            'workflow.edges': 'Connections',
            'workflow.status_running': 'Running',
            'workflow.status_completed': 'Completed',
            'workflow.status_failed': 'Failed',
            'workflow.node_start': 'Start',
            'workflow.node_end': 'End',
            'workflow.node_agent': 'AI Agent',
            'workflow.node_tool_call': 'Tool Call',
            'workflow.node_condition': 'Condition',
            'workflow.node_http': 'HTTP Request',
            'workflow.exec_success': 'Workflow executed successfully',
            'workflow.exec_failed': 'Workflow execution failed',
            'workflow.valid_success': 'Workflow validation passed',
            'workflow.valid_failed': 'Workflow validation failed',
            
            # 状态栏
            'status.connected': 'Connected',
            'status.disconnected': 'Disconnected',
            'status.reconnecting': 'Reconnecting...',
            'status.api': 'API',
            'status.model': 'Model',
            'status.tools_enabled': 'tools enabled',
            
            # 语音
            'voice.title': 'Voice',
            'voice.start': 'Start Recording',
            'voice.stop': 'Stop Recording',
            'voice.speak': 'Speak',
            'voice.listening': 'Listening...',
            'voice.processing': 'Processing...',
            'voice.error_not_supported': 'Voice not supported in this browser',
            
            # 设置
            'settings.title': 'Settings',
            'settings.theme': 'Theme',
            'settings.theme_light': 'Light',
            'settings.theme_dark': 'Dark',
            'settings.theme_auto': 'Auto',
            'settings.language': 'Language',
            'settings.api_base': 'API URL',
            'settings.auto_speak': 'Auto-speak responses',
            'settings.save_success': 'Settings saved',
            
            # 错误消息
            'error.generic': 'An error occurred: {message}',
            'error.connection': 'Connection failed',
            'error.timeout': 'Request timed out',
            'error.not_found': 'Not found',
            'error.unauthorized': 'Unauthorized access',
            'error.server': 'Server error',
            
            # 时间
            'time.now': 'Just now',
            'time.minutes_ago': '{n} minute(s) ago',
            'time.hours_ago': '{n} hour(s) ago',
            'time.days_ago': '{n} day(s) ago',
        },
        'zh': {
            # 通用
            'app.title': 'SerpentAI',
            'app.version': 'v2.0.0',
            'app.loading': '加载中...',
            'app.ready': '就绪',
            'app.error': '错误',
            'app.success': '成功',
            'app.warning': '警告',
            'app.info': '提示',
            'app.confirm': '确认',
            'app.cancel': '取消',
            'app.save': '保存',
            'app.delete': '删除',
            'app.edit': '编辑',
            'app.close': '关闭',
            'app.refresh': '刷新',
            'app.search': '搜索',
            'app.filter': '过滤',
            'app.sort': '排序',
            'app.export': '导出',
            'app.import': '导入',
            'app.settings': '设置',
            'app.help': '帮助',
            'app.about': '关于',
            
            # 导航
            'nav.home': '首页',
            'nav.chat': '聊天',
            'nav.tools': '工具',
            'nav.plugins': '插件',
            'nav.skills': '技能',
            'nav.workflow': '工作流',
            'nav.settings': '设置',
            
            # 聊天界面
            'chat.title': '聊天',
            'chat.input_placeholder': '输入消息... (Shift+Enter 换行)',
            'chat.send': '发送',
            'chat.clear': '清空聊天',
            'chat.typing': '正在思考...',
            'chat.no_messages': '暂无消息',
            'chat.user': '你',
            'chat.assistant': 'SerpentAI',
            'chat.error_send': '发送消息失败',
            'chat.error_timeout': '请求超时',
            'chat.error_cancelled': '请求已取消',
            
            # 模型选择
            'model.select': '选择模型',
            'model.current': '当前模型',
            'model.loading': '加载模型中...',
            'model.none': '无可用模型',
            'model.switch_success': '已切换到模型: {name}',
            
            # 工具管理
            'tools.title': '可用工具',
            'tools.enabled': '已启用',
            'tools.disabled': '已禁用',
            'tools.none': '暂无可用工具',
            'tools.enable': '启用',
            'tools.disable': '禁用',
            'tool.toggle_success': '工具 "{name}" 已{action}',
            
            # 插件管理
            'plugins.title': '已安装插件',
            'plugins.none': '暂无已安装插件',
            'plugins.load': '加载',
            'plugins.unload': '卸载',
            'plugins.reload': '重载',
            'plugins.details': '详情',
            'plugins.store': '插件商店',
            'plugin.load_success': '插件 "{name}" 已加载',
            'plugin.unload_success': '插件 "{name}" 已卸载',
            'plugin.reload_success': '插件 "{name}" 已重载',
            'plugin.state_started': '运行中',
            'plugin.state_stopped': '已停止',
            'plugin.state_loaded': '已加载',
            'plugin.state_error': '错误',
            
            # 技能管理
            'skills.title': '已安装技能',
            'skills.none': '暂无已安装技能',
            'skills.enable': '启用',
            'skills.disable': '禁用',
            'skill.toggle_success': '技能 "{name}" 已{action}',
            'skill.disabled': '已禁用',
            
            # 工作流
            'workflow.title': '工作流编辑器',
            'workflow.new': '新建工作流',
            'workflow.save': '保存',
            'workflow.execute': '执行',
            'workflow.validate': '验证',
            'workflow.clear': '清空',
            'workflow.templates': '模板',
            'workflow.nodes': '节点',
            'workflow.edges': '连接',
            'workflow.status_running': '运行中',
            'workflow.status_completed': '已完成',
            'workflow.status_failed': '失败',
            'workflow.node_start': '开始',
            'workflow.node_end': '结束',
            'workflow.node_agent': 'AI智能体',
            'workflow.node_tool_call': '工具调用',
            'workflow.node_condition': '条件分支',
            'workflow.node_http': 'HTTP请求',
            'workflow.exec_success': '工作流执行成功',
            'workflow.exec_failed': '工作流执行失败',
            'workflow.valid_success': '工作流验证通过',
            'workflow.valid_failed': '工作流验证失败',
            
            # 状态栏
            'status.connected': '已连接',
            'status.disconnected': '未连接',
            'status.reconnecting': '重新连接中...',
            'status.api': 'API',
            'status.model': '模型',
            'status.tools_enabled': '个工具已启用',
            
            # 语音
            'voice.title': '语音',
            'voice.start': '开始录音',
            'voice.stop': '停止录音',
            'voice.speak': '朗读',
            'voice.listening': '正在聆听...',
            'voice.processing': '正在处理...',
            'voice.error_not_supported': '当前浏览器不支持语音功能',
            
            # 设置
            'settings.title': '设置',
            'settings.theme': '主题',
            'settings.theme_light': '浅色',
            'settings.theme_dark': '深色',
            'settings.theme_auto': '自动',
            'settings.language': '语言',
            'settings.api_base': 'API地址',
            'settings.auto_speak': '自动朗读回复',
            'settings.save_success': '设置已保存',
            
            # 错误消息
            'error.generic': '发生错误: {message}',
            'error.connection': '连接失败',
            'error.timeout': '请求超时',
            'error.not_found': '未找到',
            'error.unauthorized': '未授权访问',
            'error.server': '服务器错误',
            
            # 时间
            'time.now': '刚刚',
            'time.minutes_ago': '{n}分钟前',
            'time.hours_ago': '{n}小时前',
            'time.days_ago': '{n}天前',
        },
        'ja': {
            # 一般
            'app.title': 'SerpentAI',
            'app.version': 'v2.0.0',
            'app.loading': '読み込み中...',
            'app.ready': '準備完了',
            'app.error': 'エラー',
            'app.success': '成功',
            'app.warning': '警告',
            'app.info': '情報',
            'app.confirm': '確認',
            'app.cancel': 'キャンセル',
            'app.save': '保存',
            'app.delete': '削除',
            'app.edit': '編集',
            'app.close': '閉じる',
            'app.refresh': '更新',
            'app.search': '検索',
            'app.filter': 'フィルター',
            'app.sort': '並び替え',
            'app.export': 'エクスポート',
            'app.import': 'インポート',
            'app.settings': '設定',
            'app.help': 'ヘルプ',
            'app.about': '概要',
            
            # ナビゲーション
            'nav.home': 'ホーム',
            'nav.chat': 'チャット',
            'nav.tools': 'ツール',
            'nav.plugins': 'プラグイン',
            'nav.skills': 'スキル',
            'nav.workflow': 'ワークフロー',
            'nav.settings': '設定',
            
            # チャットインターフェース
            'chat.title': 'チャット',
            'chat.input_placeholder': 'メッセージを入力... (Shift+Enterで改行)',
            'chat.send': '送信',
            'chat.clear': 'チャットをクリア',
            'chat.typing': '思考中...',
            'chat.no_messages': 'メッセージがありません',
            'chat.user': 'あなた',
            'chat.assistant': 'SerpentAI',
            'chat.error_send': 'メッセージの送信に失敗しました',
            'chat.error_timeout': 'リクエストがタイムアウトしました',
            'chat.error_cancelled': 'リクエストがキャンセルされました',
            
            # モデル選択
            'model.select': 'モデルを選択',
            'model.current': '現在のモデル',
            'model.loading': 'モデルを読み込み中...',
            'model.none': '利用可能なモデルがありません',
            'model.switch_success': 'モデルが切り替わりました: {name}',
            
            # ツール管理
            'tools.title': '利用可能なツール',
            'tools.enabled': '有効',
            'tools.disabled': '無効',
            'tools.none': '利用可能なツールがありません',
            'tools.enable': '有効化',
            'tools.disable': '無効化',
            'tool.toggle_success': 'ツール「{name}」を{action}しました',
            
            # プラグイン管理
            'plugins.title': 'インストール済みプラグイン',
            'plugins.none': 'インストール済みのプラグインがありません',
            'plugins.load': '読み込み',
            'plugins.unload': 'アンロード',
            'plugins.reload': '再読み込み',
            'plugins.details': '詳細',
            'plugins.store': 'プラグインストア',
            'plugin.load_success': 'プラグイン「{name}」を読み込みました',
            'plugin.unload_success': 'プラグイン「{name}」をアンロードしました',
            'plugin.reload_success': 'プラグイン「{name}」を再読み込みしました',
            'plugin.state_started': '実行中',
            'plugin.state_stopped': '停止',
            'plugin.state_loaded': '読み込み済み',
            'plugin.state_error': 'エラー',
            
            # スキル管理
            'skills.title': 'インストール済みスキル',
            'skills.none': 'インストール済みのスキルがありません',
            'skills.enable': '有効化',
            'skills.disable': '無効化',
            'skill.toggle_success': 'スキル「{name}」を{action}しました',
            'skill.disabled': '無効',
            
            # ワークフロー
            'workflow.title': 'ワークフローエディタ',
            'workflow.new': '新規ワークフロー',
            'workflow.save': '保存',
            'workflow.execute': '実行',
            'workflow.validate': '検証',
            'workflow.clear': 'クリア',
            'workflow.templates': 'テンプレート',
            'workflow.nodes': 'ノード',
            'workflow.edges': '接続',
            'workflow.status_running': '実行中',
            'workflow.status_completed': '完了',
            'workflow.status_failed': '失敗',
            'workflow.node_start': '開始',
            'workflow.node_end': '終了',
            'workflow.node_agent': 'AIエージェント',
            'workflow.node_tool_call': 'ツール呼び出し',
            'workflow.node_condition': '条件分岐',
            'workflow.node_http': 'HTTPリクエスト',
            'workflow.exec_success': 'ワークフローが正常に実行されました',
            'workflow.exec_failed': 'ワークフローの実行に失敗しました',
            'workflow.valid_success': 'ワークフローの検証に成功しました',
            'workflow.valid_failed': 'ワークフローの検証に失敗しました',
            
            # ステータスバー
            'status.connected': '接続済み',
            'status.disconnected': '未接続',
            'status.reconnecting': '再接続中...',
            'status.api': 'API',
            'status.model': 'モデル',
            'status.tools_enabled': 'ツールが有効',
            
            # 音声
            'voice.title': '音声',
            'voice.start': '録音開始',
            'voice.stop': '録音停止',
            'voice.speak': '読み上げ',
            'voice.listening': '聞いています...',
            'voice.processing': '処理中...',
            'voice.error_not_supported': 'このブラウザでは音声機能がサポートされていません',
            
            # 設定
            'settings.title': '設定',
            'settings.theme': 'テーマ',
            'settings.theme_light': 'ライト',
            'settings.theme_dark': 'ダーク',
            'settings.theme_auto': '自動',
            'settings.language': '言語',
            'settings.api_base': 'API URL',
            'settings.auto_speak': '応答を自動で読み上げる',
            'settings.save_success': '設定を保存しました',
            
            # エラーメッセージ
            'error.generic': 'エラーが発生しました: {message}',
            'error.connection': '接続に失敗しました',
            'error.timeout': 'リクエストがタイムアウトしました',
            'error.not_found': '見つかりません',
            'error.unauthorized': '認証されていません',
            'error.server': 'サーバーエラー',
            
            # 時間
            'time.now': 'たった今',
            'time.minutes_ago': '{n}分前',
            'time.hours_ago': '{n}時間前',
            'time.days_ago': '{n}日前',
        }
    }
    
    def __init__(
        self,
        language: Optional[str] = None,
        translations_dir: Optional[str] = None,
        fallback_language: str = 'en'
    ):
        """
        初始化国际化管理器
        
        Args:
            language: 初始语言代码 (zh/en/ja)
            translations_dir: 语言包文件目录
            fallback_language: 回退语言
        """
        self._current_language = self.DEFAULT_LANGUAGE
        self._fallback_language = fallback_language
        self._translations: Dict[str, Dict[str, str]] = {}
        self._translations_dir = Path(translations_dir) if translations_dir else None
        
        # 加载内置翻译
        self._load_builtin_translations()
        
        # 尝试加载外部语言包
        if self._translations_dir:
            self._load_translations_from_dir()
        
        # 设置语言
        if language:
            self.set_language(language)
        else:
            # 自动检测语言
            detected = self.detect_language()
            self.set_language(detected)
    
    def _load_builtin_translations(self) -> None:
        """加载内置默认翻译"""
        for lang, trans in self.BUILTIN_TRANSLATIONS.items():
            self._translations[lang] = trans.copy()
    
    def _load_translations_from_dir(self) -> None:
        """从目录加载语言包文件"""
        if not self._translations_dir or not self._translations_dir.exists():
            return
        
        for lang_file in self._translations_dir.glob('*.json'):
            lang_code = lang_file.stem
            if lang_code in self.SUPPORTED_LANGUAGES:
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 合并翻译（外部翻译优先）
                        if lang_code not in self._translations:
                            self._translations[lang_code] = {}
                        self._translations[lang_code].update(self._flatten_dict(data))
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load translation file {lang_file}: {e}")
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, str]:
        """展平嵌套字典为点号分隔的键"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, str(v)))
        return dict(items)
    
    def detect_language(self, accept_language: Optional[str] = None) -> str:
        """
        检测语言
        
        Args:
            accept_language: HTTP Accept-Language 头部值
            
        Returns:
            语言代码
        """
        # 优先使用传入的 Accept-Language
        if accept_language:
            # 解析 Accept-Language 头部
            languages = []
            for part in accept_language.split(','):
                part = part.strip()
                if ';' in part:
                    lang, q = part.split(';')[0], part.split(';')[1]
                    try:
                        q = float(q.split('=')[1])
                    except (IndexError, ValueError):
                        q = 1.0
                else:
                    lang, q = part, 1.0
                languages.append((lang.strip().lower()[:2], q))
            
            # 按权重排序
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # 返回第一个支持的语言
            for lang, _ in languages:
                if lang in self.SUPPORTED_LANGUAGES:
                    return lang
        
        # 回退到默认语言
        return self.DEFAULT_LANGUAGE
    
    def set_language(self, language: str) -> bool:
        """
        设置当前语言
        
        Args:
            language: 语言代码 (zh/en/ja)
            
        Returns:
            是否设置成功
        """
        if language not in self.SUPPORTED_LANGUAGES:
            # 尝试匹配语言前缀
            matched = next(
                (lang for lang in self.SUPPORTED_LANGUAGES if lang.startswith(language[:2])),
                None
            )
            if matched:
                language = matched
            else:
                return False
        
        self._current_language = language
        return True
    
    def get_language(self) -> str:
        """
        获取当前语言
        
        Returns:
            当前语言代码
        """
        return self._current_language
    
    def list_languages(self) -> List[Dict[str, str]]:
        """
        获取支持的语言列表
        
        Returns:
            语言信息列表
        """
        language_names = {
            'zh': {'code': 'zh', 'name': '简体中文', 'native': '简体中文'},
            'en': {'code': 'en', 'name': 'English', 'native': 'English'},
            'ja': {'code': 'ja', 'name': 'Japanese', 'native': '日本語'}
        }
        
        return [
            language_names.get(lang, {'code': lang, 'name': lang, 'native': lang})
            for lang in self.SUPPORTED_LANGUAGES
        ]
    
    def t(self, key: str, **kwargs) -> str:
        """
        翻译函数
        
        Args:
            key: 翻译键（点号分隔）
            **kwargs: 变量插值参数
            
        Returns:
            翻译后的文本
        """
        # 尝试获取当前语言的翻译
        text = self._translations.get(self._current_language, {}).get(key)
        
        # 回退到默认语言
        if text is None:
            text = self._translations.get(self.DEFAULT_LANGUAGE, {}).get(key)
        
        # 回退到键本身
        if text is None:
            return key
        
        # 变量插值
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                # 缺失变量时返回原文
                return text
        
        return text
    
    def get_translations(self, language: Optional[str] = None) -> Dict[str, str]:
        """
        获取指定语言的所有翻译
        
        Args:
            language: 语言代码，默认为当前语言
            
        Returns:
            翻译字典
        """
        lang = language or self._current_language
        return self._translations.get(lang, {}).copy()
    
    def add_translations(self, language: str, translations: Dict[str, str]) -> None:
        """
        添加自定义翻译
        
        Args:
            language: 语言代码
            translations: 翻译字典
        """
        if language not in self._translations:
            self._translations[language] = {}
        self._translations[language].update(translations)
    
    def reload_translations(self) -> None:
        """重新加载翻译"""
        self._translations.clear()
        self._load_builtin_translations()
        if self._translations_dir:
            self._load_translations_from_dir()


# 全局单例实例
_i18n_manager: Optional[I18nManager] = None


def get_i18n() -> I18nManager:
    """获取全局国际化管理器实例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def t(key: str, **kwargs) -> str:
    """
    便捷翻译函数
    
    Args:
        key: 翻译键
        **kwargs: 变量插值参数
        
    Returns:
        翻译后的文本
    """
    return get_i18n().t(key, **kwargs)
