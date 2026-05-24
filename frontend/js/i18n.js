/**
 * SerpentAI 前端 i18n 模块
 * 支持多语言翻译，DOM 自动翻译（data-i18n 属性）
 * 内置中文/英文/日文默认翻译包
 */

(function () {
  'use strict';

  /* ---- 内置翻译包 ---- */
  const DEFAULT_TRANSLATIONS = {
    zh: {
      // 通用
      'app.name': '巨蛇AI',
      'app.tagline': '自托管AI智能体框架',
      'common.loading': '加载中...',
      'common.error': '错误',
      'common.success': '成功',
      'common.warning': '警告',
      'common.confirm': '确认',
      'common.cancel': '取消',
      'common.save': '保存',
      'common.delete': '删除',
      'common.edit': '编辑',
      'common.search': '搜索',
      'common.filter': '筛选',
      'common.refresh': '刷新',
      'common.settings': '设置',
      'common.back': '返回',
      'common.next': '下一步',
      'common.submit': '提交',
      'common.close': '关闭',
      'common.yes': '是',
      'common.no': '否',
      'common.all': '全部',
      'common.none': '无',
      // 聊天
      'chat.placeholder': '输入消息...',
      'chat.send': '发送',
      'chat.thinking': '思考中...',
      'chat.typing': '正在输入...',
      'chat.welcome': '欢迎使用巨蛇AI',
      'chat.offline': '当前处于离线模式',
      'chat.offline.queue': '您的消息已加入离线队列',
      'chat.history': '聊天记录',
      'chat.new': '新对话',
      'chat.clear': '清空记录',
      // 侧边栏
      'sidebar.home': '首页',
      'sidebar.chat': '对话',
      'sidebar.models': '模型管理',
      'sidebar.tools': '工具',
      'sidebar.plugins': '插件',
      'sidebar.skills': '技能',
      'sidebar.workflows': '工作流',
      'sidebar.settings': '系统设置',
      'sidebar.account': '账号管理',
      // 模型
      'model.select': '选择模型',
      'model.active': '当前模型',
      'model.router': '智能路由',
      'model.cost': 'Token消耗',
      'model.tokens': 'Token使用量',
      'model.response_time': '响应时间',
      'model.balance': '负载均衡',
      'model.failover': '故障转移',
      // 工具
      'tool.registered': '已注册工具',
      'tool.execute': '执行工具',
      'tool.sandbox': '沙箱环境',
      'tool.result': '执行结果',
      // 记忆
      'memory.short': '短期记忆',
      'memory.long': '长期记忆',
      'memory.archive': '归档记忆',
      'memory.graph': '知识图谱',
      // 插件
      'plugin.store': '插件商店',
      'plugin.installed': '已安装',
      'plugin.install': '安装',
      'plugin.uninstall': '卸载',
      'plugin.update': '更新',
      'plugin.share': '分享',
      // 状态
      'status.online': '在线',
      'status.offline': '离线',
      'status.connecting': '连接中',
      // 主题
      'theme.light': '浅色',
      'theme.dark': '深色',
      'theme.auto': '跟随系统',
      // 时间
      'time.just_now': '刚刚',
      'time.minutes_ago': '{n}分钟前',
      'time.hours_ago': '{n}小时前',
    },
    en: {
      'app.name': 'SerpentAI',
      'app.tagline': 'Self-Hosted AI Agent Framework',
      'common.loading': 'Loading...',
      'common.error': 'Error',
      'common.success': 'Success',
      'common.warning': 'Warning',
      'common.confirm': 'Confirm',
      'common.cancel': 'Cancel',
      'common.save': 'Save',
      'common.delete': 'Delete',
      'common.edit': 'Edit',
      'common.search': 'Search',
      'common.filter': 'Filter',
      'common.refresh': 'Refresh',
      'common.settings': 'Settings',
      'common.back': 'Back',
      'common.next': 'Next',
      'common.submit': 'Submit',
      'common.close': 'Close',
      'common.yes': 'Yes',
      'common.no': 'No',
      'common.all': 'All',
      'common.none': 'None',
      'chat.placeholder': 'Type a message...',
      'chat.send': 'Send',
      'chat.thinking': 'Thinking...',
      'chat.typing': 'Typing...',
      'chat.welcome': 'Welcome to SerpentAI',
      'chat.offline': 'Currently offline',
      'chat.offline.queue': 'Your message has been queued',
      'chat.history': 'Chat History',
      'chat.new': 'New Chat',
      'chat.clear': 'Clear History',
      'sidebar.home': 'Home',
      'sidebar.chat': 'Chat',
      'sidebar.models': 'Models',
      'sidebar.tools': 'Tools',
      'sidebar.plugins': 'Plugins',
      'sidebar.skills': 'Skills',
      'sidebar.workflows': 'Workflows',
      'sidebar.settings': 'Settings',
      'sidebar.account': 'Accounts',
      'model.select': 'Select Model',
      'model.active': 'Active Model',
      'model.router': 'Smart Router',
      'model.cost': 'Token Cost',
      'model.tokens': 'Token Usage',
      'model.response_time': 'Response Time',
      'model.balance': 'Load Balance',
      'model.failover': 'Failover',
      'tool.registered': 'Registered Tools',
      'tool.execute': 'Execute Tool',
      'tool.sandbox': 'Sandbox',
      'tool.result': 'Result',
      'memory.short': 'Short-term Memory',
      'memory.long': 'Long-term Memory',
      'memory.archive': 'Archive',
      'memory.graph': 'Knowledge Graph',
      'plugin.store': 'Plugin Store',
      'plugin.installed': 'Installed',
      'plugin.install': 'Install',
      'plugin.uninstall': 'Uninstall',
      'plugin.update': 'Update',
      'plugin.share': 'Share',
      'status.online': 'Online',
      'status.offline': 'Offline',
      'status.connecting': 'Connecting',
      'theme.light': 'Light',
      'theme.dark': 'Dark',
      'theme.auto': 'System',
      'time.just_now': 'Just now',
      'time.minutes_ago': '{n} min ago',
      'time.hours_ago': '{n}h ago',
    },
    ja: {
      'app.name': 'サーペントAI',
      'app.tagline': 'セルフホストAIエージェントフレームワーク',
      'common.loading': '読み込み中...',
      'common.error': 'エラー',
      'common.success': '成功',
      'common.warning': '警告',
      'common.confirm': '確認',
      'common.cancel': 'キャンセル',
      'common.save': '保存',
      'common.delete': '削除',
      'common.edit': '編集',
      'common.search': '検索',
      'common.filter': 'フィルター',
      'common.refresh': '更新',
      'common.settings': '設定',
      'common.back': '戻る',
      'common.next': '次へ',
      'common.submit': '送信',
      'common.close': '閉じる',
      'common.yes': 'はい',
      'common.no': 'いいえ',
      'common.all': 'すべて',
      'common.none': 'なし',
      'chat.placeholder': 'メッセージを入力...',
      'chat.send': '送信',
      'chat.thinking': '考え中...',
      'chat.typing': '入力中...',
      'chat.welcome': 'サーペントAIへようこそ',
      'chat.offline': 'オフラインモード',
      'chat.offline.queue': 'メッセージがキューに追加されました',
      'chat.history': 'チャット履歴',
      'chat.new': '新しいチャット',
      'chat.clear': '履歴をクリア',
      'sidebar.home': 'ホーム',
      'sidebar.chat': 'チャット',
      'sidebar.models': 'モデル',
      'sidebar.tools': 'ツール',
      'sidebar.plugins': 'プラグイン',
      'sidebar.skills': 'スキル',
      'sidebar.workflows': 'ワークフロー',
      'sidebar.settings': '設定',
      'sidebar.account': 'アカウント',
      'model.select': 'モデル選択',
      'model.active': '現在のモデル',
      'model.router': 'スマートルーター',
      'model.cost': 'トークン消費',
      'model.tokens': 'トークン使用量',
      'model.response_time': '応答時間',
      'model.balance': '負荷分散',
      'model.failover': 'フェイルオーバー',
      'tool.registered': '登録済みツール',
      'tool.execute': 'ツール実行',
      'tool.sandbox': 'サンドボックス',
      'tool.result': '実行結果',
      'memory.short': '短期記憶',
      'memory.long': '長期記憶',
      'memory.archive': 'アーカイブ',
      'memory.graph': 'ナレッジグラフ',
      'plugin.store': 'プラグインストア',
      'plugin.installed': 'インストール済み',
      'plugin.install': 'インストール',
      'plugin.uninstall': 'アンインストール',
      'plugin.update': '更新',
      'plugin.share': '共有',
      'status.online': 'オンライン',
      'status.offline': 'オフライン',
      'status.connecting': '接続中',
      'theme.light': 'ライト',
      'theme.dark': 'ダーク',
      'theme.auto': 'システム',
      'time.just_now': 'たった今',
      'time.minutes_ago': '{n}分前',
      'time.hours_ago': '{n}時間前',
    },
  };

  const STORAGE_KEY = 'serpent-lang';
  const FALLBACK_LANG = 'en';
  const SUPPORTED_LANGS = ['zh', 'en', 'ja'];
  const LANG_NAMES = { zh: '中文', en: 'English', ja: '日本語' };

  let currentLang = FALLBACK_LANG;
  let translations = JSON.parse(JSON.stringify(DEFAULT_TRANSLATIONS));

  /**
   * Translate a key with optional variable interpolation
   * @param {string} key - Translation key (e.g., 'chat.placeholder')
   * @param {Object} params - Variables to interpolate (e.g., {n: 5})
   * @returns {string} Translated string or the key itself
   */
  function t(key, params) {
    let text = (translations[currentLang] && translations[currentLang][key])
      || (translations[FALLBACK_LANG] && translations[FALLBACK_LANG][key])
      || key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        text = text.replace(new RegExp('\\{' + k + '\\}', 'g'), params[k]);
      });
    }
    return text;
  }

  /** Translate all DOM elements with data-i18n attribute */
  function translateDOM() {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var text = t(key);
      // data-i18n-attr: which attribute to set (default: textContent)
      var attr = el.getAttribute('data-i18n-attr');
      if (attr) {
        el.setAttribute(attr, text);
      } else {
        el.textContent = text;
      }
    });
    // Also translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    // And titles
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
  }

  /** Set language and update DOM */
  function setLanguage(lang) {
    if (!SUPPORTED_LANGS.includes(lang)) lang = FALLBACK_LANG;
    currentLang = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch {}
    translateDOM();
    document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-CN' : lang);
    if (typeof Event !== 'undefined') {
      window.dispatchEvent(new CustomEvent('languagechange', { detail: { lang: lang } }));
    }
  }

  /** Detect user language from browser or stored preference */
  function detectLanguage() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored && SUPPORTED_LANGS.includes(stored)) return stored;
    } catch {}
    var nav = navigator.language || navigator.userLanguage || '';
    if (nav.startsWith('zh')) return 'zh';
    if (nav.startsWith('ja')) return 'ja';
    return 'en';
  }

  /** Merge remote translations into local ones */
  function mergeTranslations(lang, remoteDict) {
    if (!translations[lang]) translations[lang] = {};
    Object.keys(remoteDict).forEach(function (k) {
      translations[lang][k] = remoteDict[k];
    });
  }

  /** Load translations from backend API */
  function loadFromAPI(baseUrl) {
    baseUrl = baseUrl || '/api';
    fetch(baseUrl + '/i18n/' + currentLang)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && typeof data === 'object') {
          mergeTranslations(currentLang, data);
          translateDOM();
        }
      })
      .catch(function () {
        // Silently fail, use built-in translations
      });
  }

  /** Render a simple language selector */
  function createLanguageSelector(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    SUPPORTED_LANGS.forEach(function (lang) {
      var btn = document.createElement('button');
      btn.textContent = LANG_NAMES[lang];
      btn.className = 'lang-btn' + (lang === currentLang ? ' active' : '');
      btn.setAttribute('data-lang', lang);
      btn.addEventListener('click', function () {
        setLanguage(lang);
        container.querySelectorAll('.lang-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
      });
      container.appendChild(btn);
    });
  }

  /* ---- Initialize ---- */
  function init() {
    currentLang = detectLanguage();
    document.documentElement.setAttribute('lang', currentLang === 'zh' ? 'zh-CN' : currentLang);
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        translateDOM();
      });
    } else {
      translateDOM();
    }
  }

  init();

  /* ---- Expose global API ---- */
  window.SerpentI18n = {
    t: t,
    setLanguage: setLanguage,
    getLanguage: function () { return currentLang; },
    getSupportedLangs: function () { return SUPPORTED_LANGS.slice(); },
    getLangNames: function () { return Object.assign({}, LANG_NAMES); },
    mergeTranslations: mergeTranslations,
    loadFromAPI: loadFromAPI,
    translateDOM: translateDOM,
    createLanguageSelector: createLanguageSelector,
    SUPPORTED_LANGS: SUPPORTED_LANGS,
    LANG_NAMES: LANG_NAMES,
  };
})();
