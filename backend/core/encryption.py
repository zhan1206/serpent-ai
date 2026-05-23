"""
SerpentAI 加密管理模块
支持AES-256-GCM加密、RSA-4096非对称加密、SHA-256哈希
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import hashlib
import base64
import os
from typing import Optional, Tuple, Union
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

class EncryptionManager:
    """
    加密管理器（单例模式）
    提供统一的加密、解密、哈希功能
    """
    
    _instance = None
    _fernet = None
    _rsa_private_key = None
    _rsa_public_key = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._fernet is None:
            self._init_symmetric_encryption()
        if self._rsa_private_key is None:
            self._init_asymmetric_encryption()
    
    def _init_symmetric_encryption(self):
        """初始化对称加密（AES-256-GCM）"""
        key = settings.ENCRYPTION_KEY
        
        if key is None:
            # 从SECRET_KEY派生密钥
            secret_key = settings.SECRET_KEY.encode()
            key = base64.urlsafe_b64encode(
                hashlib.sha256(secret_key).digest()
            )
            logger.warning("使用SECRET_KEY派生加密密钥，建议在配置中设置ENCRYPTION_KEY")
        
        if isinstance(key, str):
            key = key.encode()
        
        self._fernet = Fernet(key)
        logger.info("对称加密初始化完成 (AES-256-GCM)")
    
    def _init_asymmetric_encryption(self):
        """初始化非对称加密（RSA-4096）"""
        keys_dir = settings.DATA_DIR / "keys"
        private_key_path = keys_dir / "rsa_private.pem"
        public_key_path = keys_dir / "rsa_public.pem"
        
        keys_dir.mkdir(parents=True, exist_ok=True)
        
        if private_key_path.exists() and public_key_path.exists():
            # 加载现有密钥
            with open(private_key_path, "rb") as f:
                self._rsa_private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            with open(public_key_path, "rb") as f:
                self._rsa_public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            
            logger.info("RSA密钥对已加载")
        else:
            # 生成新密钥对
            self._rsa_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            self._rsa_public_key = self._rsa_private_key.public_key()
            
            # 保存密钥
            with open(private_key_path, "wb") as f:
                f.write(
                    self._rsa_private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                )
            
            with open(public_key_path, "wb") as f:
                f.write(
                    self._rsa_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                )
            
            logger.info(f"RSA-4096密钥对已生成并保存到: {keys_dir}")
    
    # ==================== 对称加密方法 ====================
    
    def encrypt_symmetric(self, data: Union[str, bytes]) -> bytes:
        """
        对称加密（AES-256-GCM via Fernet）
        适用于：用户数据、配置文件、数据库字段
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self._fernet.encrypt(data)
        logger.debug(f"对称加密完成: {len(data)} bytes -> {len(encrypted)} bytes")
        return encrypted
    
    def decrypt_symmetric(self, encrypted_data: bytes) -> bytes:
        """
        对称解密
        """
        try:
            decrypted = self._fernet.decrypt(encrypted_data)
            logger.debug(f"对称解密完成: {len(encrypted_data)} bytes -> {len(decrypted)} bytes")
            return decrypted
        except Exception as e:
            logger.error(f"对称解密失败: {e}")
            raise
    
    def encrypt_file_symmetric(self, file_path: Union[str, Path]) -> Path:
        """
        加密文件（对称加密）
        返回加密后的文件路径
        """
        file_path = Path(file_path)
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = self.encrypt_symmetric(data)
        
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"文件加密完成: {file_path} -> {encrypted_path}")
        return encrypted_path
    
    def decrypt_file_symmetric(self, encrypted_path: Union[str, Path]) -> Path:
        """
        解密文件（对称加密）
        返回解密后的文件路径
        """
        encrypted_path = Path(encrypted_path)
        
        if not encrypted_path.suffix == '.enc':
            raise ValueError("文件必须是 .enc 后缀的加密文件")
        
        decrypted_path = encrypted_path.with_suffix('').with_suffix('')  # 移除 .enc
        
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.decrypt_symmetric(encrypted_data)
        
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"文件解密完成: {encrypted_path} -> {decrypted_path}")
        return decrypted_path
    
    # ==================== 非对称加密方法 ====================
    
    def encrypt_asymmetric(self, data: Union[str, bytes]) -> bytes:
        """
        非对称加密（RSA-4096）
        适用于：密钥交换、数字签名
        注意：RSA加密有长度限制，不适合大文件
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if len(data) > 446:  # RSA-4096 最大加密长度
            raise ValueError("数据过长，RSA不适合加密大文件")
        
        encrypted = self._rsa_public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        logger.debug(f"非对称加密完成: {len(data)} bytes -> {len(encrypted)} bytes")
        return encrypted
    
    def decrypt_asymmetric(self, encrypted_data: bytes) -> bytes:
        """
        非对称解密
        """
        try:
            decrypted = self._rsa_private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            logger.debug(f"非对称解密完成: {len(encrypted_data)} bytes -> {len(decrypted)} bytes")
            return decrypted
        except Exception as e:
            logger.error(f"非对称解密失败: {e}")
            raise
    
    def sign(self, data: Union[str, bytes]) -> bytes:
        """
        数字签名（RSA）
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        signature = self._rsa_private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        logger.debug(f"数字签名完成: {len(data)} bytes -> {len(signature)} bytes")
        return signature
    
    def verify(self, data: Union[str, bytes], signature: bytes) -> bool:
        """
        验证数字签名
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        try:
            self._rsa_public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logger.debug("数字签名验证通过")
            return True
        except Exception as e:
            logger.error(f"数字签名验证失败: {e}")
            return False
    
    # ==================== 哈希方法 ====================
    
    @staticmethod
    def hash_sha256(data: Union[str, bytes]) -> str:
        """
        SHA-256哈希
        适用于：密码存储、数据完整性验证
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_value = hashlib.sha256(data).hexdigest()
        logger.debug(f"SHA-256哈希完成")
        return hash_value
    
    @staticmethod
    def hash_file_sha256(file_path: Union[str, Path]) -> str:
        """
        计算文件的SHA-256哈希值
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        
        hash_value = sha256_hash.hexdigest()
        logger.debug(f"文件SHA-256哈希完成: {file_path}")
        return hash_value
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        密码哈希（使用bcrypt）
        返回：(hash, salt)
        """
        import bcrypt
        
        if salt is None:
            salt = bcrypt.gensalt()
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        logger.debug("密码哈希完成")
        return password_hash.decode('utf-8'), salt.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        验证密码
        """
        import bcrypt
        
        try:
            result = bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
            logger.debug(f"密码验证: {'通过' if result else '失败'}")
            return result
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False

# 全局加密管理器实例
encryption_manager = EncryptionManager()

# ==================== 便捷函数 ====================

def encrypt_data(data: Union[str, bytes]) -> bytes:
    """快捷加密函数"""
    return encryption_manager.encrypt_symmetric(data)

def decrypt_data(encrypted_data: bytes) -> bytes:
    """快捷解密函数"""
    return encryption_manager.decrypt_symmetric(encrypted_data)

def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """快捷密码哈希函数"""
    return encryption_manager.hash_password(password, salt)

def verify_password(password: str, password_hash: str) -> bool:
    """快捷密码验证函数"""
    return encryption_manager.verify_password(password, password_hash)

def hash_data(data: Union[str, bytes]) -> str:
    """快捷哈希函数"""
    return EncryptionManager.hash_sha256(data)

def verify_data_integrity(data: Union[str, bytes], expected_hash: str) -> bool:
    """
    验证数据完整性
    """
    actual_hash = EncryptionManager.hash_sha256(data)
    return actual_hash == expected_hash


def generate_key() -> bytes:
    """生成Fernet对称加密密钥"""
    return Fernet.generate_key()


def encrypt(data: Union[str, bytes]) -> bytes:
    """快捷加密（对称）"""
    return encryption_manager.encrypt_symmetric(data)


def decrypt(encrypted_data: bytes) -> bytes:
    """快捷解密（对称）"""
    return encryption_manager.decrypt_symmetric(encrypted_data)


def generate_token(data: Union[str, bytes]) -> str:
    """生成Token（加密后base64编码）"""
    encrypted = encryption_manager.encrypt_symmetric(data)
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def verify_token(token: str) -> Optional[bytes]:
    """验证并解密Token"""
    try:
        encrypted = base64.urlsafe_b64decode(token.encode('utf-8'))
        return encryption_manager.decrypt_symmetric(encrypted)
    except Exception:
        return None
