"""
SerpentAI 数据库管理模块
支持 SQLite（配置/用户/长期记忆）、ChromaDB（向量数据库）、Neo4j（知识图谱）
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 可选依赖 - 使用try/except处理
try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

from typing import Generator, Any
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

# ==================== SQLite 数据库 ====================
SQLALCHEMY_DATABASE_URL = settings.SQLITE_URL

# 创建SQLite引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.DEBUG
)

# 启用外键约束
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # 提升并发性能
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """数据库会话依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from backend.models.base import Base
    logger.info("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")

# ==================== ChromaDB 向量数据库 ====================
_chroma_client = None

def get_chroma_client():
    """获取ChromaDB客户端（单例）"""
    global _chroma_client
    if chromadb is None:
        logger.warning("ChromaDB未安装，跳过初始化")
        return None
    if _chroma_client is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=chromadb.Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        logger.info(f"ChromaDB客户端初始化完成: {persist_dir}")
    
    return _chroma_client

def get_or_create_collection(name: str, metadata: dict = None):
    """获取或创建向量集合"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata=metadata or {"hnsw:space": "cosine"}
    )

# ==================== Neo4j 知识图谱数据库 ====================
_neo4j_driver = None

def get_neo4j_driver():
    """获取Neo4j驱动（单例）"""
    global _neo4j_driver
    if GraphDatabase is None:
        logger.warning("Neo4j未安装，跳过初始化")
        return None
    if _neo4j_driver is None:
        try:
            _neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # 验证连接
            with _neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Neo4j驱动初始化完成: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            return None
    
    return _neo4j_driver

def close_neo4j_driver():
    """关闭Neo4j驱动"""
    global _neo4j_driver
    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j驱动已关闭")

def init_neo4j_constraints():
    """初始化Neo4j约束和索引"""
    driver = get_neo4j_driver()
    with driver.session() as session:
        # 创建约束（如果不存在）
        try:
            session.run("""
                CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """)
            session.run("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """)
            logger.info("Neo4j约束和索引创建完成")
        except Exception as e:
            logger.warning(f"Neo4j约束创建失败（可能已存在）: {e}")

# ==================== 数据库连接健康检查 ====================
def check_db_health() -> dict:
    """检查所有数据库连接状态"""
    health = {
        "sqlite": False,
        "chromadb": False,
        "neo4j": False
    }
    
    # SQLite检查
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health["sqlite"] = True
    except Exception as e:
        logger.error(f"SQLite健康检查失败: {e}")
    
    # ChromaDB检查
    if chromadb is not None:
        try:
            client = get_chroma_client()
            if client:
                client.heartbeat()
                health["chromadb"] = True
        except Exception as e:
            logger.error(f"ChromaDB健康检查失败: {e}")
    
    # Neo4j检查
    if GraphDatabase is not None:
        try:
            driver = get_neo4j_driver()
            if driver:
                with driver.session() as session:
                    session.run("RETURN 1")
                health["neo4j"] = True
        except Exception as e:
            logger.error(f"Neo4j健康检查失败: {e}")
    
    return health
