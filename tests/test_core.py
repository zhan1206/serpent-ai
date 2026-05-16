"""
核心模块测试
"""
import pytest
from pathlib import Path


class TestConfig:
    """配置模块测试"""
    
    def test_settings_load(self):
        """测试设置加载"""
        from core.config import get_settings
        
        settings = get_settings()
        assert settings.APP_NAME == "SerpentAI"
        assert settings.APP_VERSION is not None
    
    def test_settings_validation(self):
        """测试设置验证"""
        from pydantic import ValidationError
        from core.config import Settings
        
        # 缺少必需字段应该报错
        with pytest.raises(ValidationError):
            Settings()
    
    def test_debug_mode(self):
        """测试调试模式"""
        from core.config import get_settings
        
        settings = get_settings()
        assert isinstance(settings.DEBUG, bool)


class TestDatabase:
    """数据库模块测试"""
    
    @pytest.mark.asyncio
    async def test_init_db(self):
        """测试数据库初始化"""
        from core.database import init_db, check_db_health
        
        # 初始化数据库
        await init_db()
        
        # 检查健康状态
        is_healthy = await check_db_health()
        assert isinstance(is_healthy, bool)
    
    @pytest.mark.asyncio
    async def test_session_create(self, test_db_dir):
        """测试会话创建"""
        from core.database import create_session, get_session
        
        # 创建测试会话
        session_id = await create_session(user_id="test_user")
        assert session_id is not None
        
        # 获取会话
        session = await get_session(session_id)
        assert session is not None


class TestCache:
    """缓存模块测试"""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, test_cache_dir):
        """测试缓存设置和获取"""
        from core.cache import CacheManager
        
        cache = CacheManager(cache_dir=str(test_cache_dir))
        
        # 设置缓存
        await cache.set("test_key", {"data": "test_value"})
        
        # 获取缓存
        value = await cache.get("test_key")
        assert value is not None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, test_cache_dir):
        """测试缓存删除"""
        from core.cache import CacheManager
        
        cache = CacheManager(cache_dir=str(test_cache_dir))
        
        # 设置然后删除
        await cache.set("test_key", {"data": "test_value"})
        await cache.delete("test_key")
        
        # 验证已删除
        value = await cache.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_expire(self, test_cache_dir):
        """测试缓存过期"""
        from core.cache import CacheManager
        
        cache = CacheManager(cache_dir=str(test_cache_dir))
        
        # 设置1秒过期
        await cache.set("test_key", {"data": "test_value"}, expire=1)
        
        import asyncio
        await asyncio.sleep(1.5)
        
        # 验证已过期
        value = await cache.get("test_key")
        assert value is None


class TestEncryption:
    """加密模块测试"""
    
    def test_generate_key(self):
        """测试密钥生成"""
        from core.encryption import generate_key, generate_key_pair
        
        # 测试对称密钥
        key = generate_key()
        assert key is not None
        assert len(key) > 0
        
        # 测试非对称密钥对
        public_key, private_key = generate_key_pair()
        assert public_key is not None
        assert private_key is not None
    
    def test_encrypt_decrypt(self):
        """测试加密解密"""
        from core.encryption import encrypt, decrypt, generate_key
        
        key = generate_key()
        original_data = "测试数据Hello World"
        
        # 加密
        encrypted = encrypt(original_data, key)
        assert encrypted != original_data
        
        # 解密
        decrypted = decrypt(encrypted, key)
        assert decrypted == original_data
    
    def test_hash_password(self):
        """测试密码哈希"""
        from core.encryption import hash_password, verify_password
        
        password = "test_password_123"
        
        # 哈希
        hashed = hash_password(password)
        assert hashed != password
        
        # 验证
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_generate_token(self):
        """测试令牌生成"""
        from core.encryption import generate_token, verify_token
        
        user_id = "test_user"
        token = generate_token(user_id)
        assert token is not None
        
        # 验证
        result = verify_token(token)
        assert result is not None