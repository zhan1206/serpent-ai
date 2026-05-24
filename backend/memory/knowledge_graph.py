"""
SerpentAI 知识图谱记忆召回
基于Neo4j或内存字典实现，支持优雅降级
"""
import re
import logging
import threading
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 基于规则的实体提取（简单版）
# ---------------------------------------------------------------------------

# 常见中文人名姓氏
_CN_FAMILY_NAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张"
    "孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎"
    "鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤"
    "滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
)

# 常见中文地名后缀
_CN_LOC_SUFFIXES = ("省", "市", "区", "县", "镇", "村", "路", "街", "山", "河", "湖", "海", "岛", "洲", "港", "桥")

# 常见组织后缀
_CN_ORG_SUFFIXES = ("公司", "集团", "大学", "学院", "医院", "银行", "研究院", "研究所", "部门", "中心", "政府", "局", "部", "委")

# 时间模式
_TIME_PATTERNS = [
    (r'\d{4}年\d{1,2}月\d{1,2}日', 'date'),
    (r'\d{4}-\d{1,2}-\d{1,2}', 'date'),
    (r'\d{1,2}月\d{1,2}日', 'date'),
    (r'(今天|昨天|明天|前天|后天|上周|下周|上个月|下个月|去年|今年|明年)', 'relative_time'),
    (r'\d{1,2}点\d{0,2}分?', 'time'),
]

# 常见概念关键词
_CONCEPT_KEYWORDS = (
    "人工智能", "机器学习", "深度学习", "自然语言处理", "大模型", "知识图谱",
    "数据库", "微服务", "容器", "云原生", "区块链", "物联网", "前端", "后端",
    "算法", "数据结构", "操作系统", "网络", "安全", "性能", "架构", "设计模式",
    "Python", "Java", "JavaScript", "Go", "Rust", "C++", "TypeScript",
)


class EntityExtractor:
    """基于规则的关键实体提取器"""

    @staticmethod
    def extract(text: str) -> List[Dict[str, str]]:
        """
        从文本中提取实体

        Returns:
            [{"text": "张三", "type": "person"}, ...]
        """
        entities: List[Dict[str, str]] = []
        seen: Set[str] = set()

        def _add(text_: str, type_: str):
            t = text_.strip()
            if t and t not in seen:
                seen.add(t)
                entities.append({"text": t, "type": type_})

        # 1. 时间
        for pattern, etype in _TIME_PATTERNS:
            for m in re.finditer(pattern, text):
                _add(m.group(), "time")

        # 2. 地名（带后缀的）
        for suffix in _CN_LOC_SUFFIXES:
            for m in re.finditer(rf'[\w]{{{1,6}}}{suffix}', text):
                _add(m.group(), "location")

        # 3. 组织（带后缀的）
        for suffix in _CN_ORG_SUFFIXES:
            for m in re.finditer(rf'[\w]{{{1,10}}}{suffix}', text):
                _add(m.group(), "organization")

        # 4. 人名（2-4字中文 + 姓氏开头 + 非上下文常见词）
        for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', text):
            word = m.group()
            if word[0] in _CN_FAMILY_NAMES and len(word) >= 2:
                _add(word, "person")

        # 5. 概念关键词
        for kw in _CONCEPT_KEYWORDS:
            if kw in text:
                _add(kw, "concept")

        return entities


# ---------------------------------------------------------------------------
# 内存字典后端（Neo4j 不可用时的降级方案）
# ---------------------------------------------------------------------------

class _InMemoryGraphStore:
    """纯内存的图存储实现"""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}       # entity_name -> properties
        self._edges: List[Dict[str, Any]] = []             # [{source, target, relation, ...}]
        self._adj: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # adjacency
        self._lock = threading.Lock()

    # --- nodes ---

    def create_node(self, name: str, labels: Optional[List[str]] = None,
                    attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if name not in self._nodes:
                self._nodes[name] = {
                    "name": name,
                    "labels": labels or ["Entity"],
                    "attributes": attributes or {},
                }
            else:
                if attributes:
                    self._nodes[name]["attributes"].update(attributes)
                if labels:
                    existing = set(self._nodes[name]["labels"])
                    existing.update(labels)
                    self._nodes[name]["labels"] = list(existing)
            return dict(self._nodes[name])

    def get_node(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._nodes[name]) if name in self._nodes else None

    def query_nodes(self, label: Optional[str] = None,
                    keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for node in self._nodes.values():
                if label and label not in node["labels"]:
                    continue
                if keyword:
                    if keyword.lower() not in node["name"].lower():
                        # also check attributes
                        attr_str = str(node["attributes"]).lower()
                        if keyword.lower() not in attr_str:
                            continue
                results.append(dict(node))
            return results

    def delete_node(self, name: str) -> bool:
        with self._lock:
            if name not in self._nodes:
                return False
            del self._nodes[name]
            # remove related edges
            self._edges = [e for e in self._edges
                           if e["source"] != name and e["target"] != name]
            self._adj.pop(name, None)
            for neighbor_edges in self._adj.values():
                neighbor_edges[:] = [e for e in neighbor_edges
                                     if e["source"] != name and e["target"] != name]
            return True

    # --- edges ---

    def create_edge(self, source: str, target: str, relation: str,
                    attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            # auto-create nodes
            for n in (source, target):
                if n not in self._nodes:
                    self._nodes[n] = {"name": n, "labels": ["Entity"], "attributes": {}}

            edge = {
                "source": source,
                "target": target,
                "relation": relation,
                "attributes": attributes or {},
            }
            # avoid duplicates
            for existing in self._edges:
                if (existing["source"] == source and existing["target"] == target
                        and existing["relation"] == relation):
                    if attributes:
                        existing["attributes"].update(attributes)
                    return dict(existing)

            self._edges.append(edge)
            self._adj[source].append(edge)
            # for undirected traversal
            reverse = dict(edge)
            reverse["_reverse"] = True
            self._adj[target].append(reverse)
            return dict(edge)

    def query_edges(self, source: Optional[str] = None,
                    target: Optional[str] = None,
                    relation: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for e in self._edges:
                if source and e["source"] != source:
                    continue
                if target and e["target"] != target:
                    continue
                if relation and e["relation"] != relation:
                    continue
                results.append(dict(e))
            return results

    def delete_edge(self, source: str, target: str, relation: str) -> bool:
        with self._lock:
            before = len(self._edges)
            self._edges = [e for e in self._edges
                           if not (e["source"] == source and e["target"] == target
                                   and e["relation"] == relation)]
            for neighbor_edges in self._adj.values():
                neighbor_edges[:] = [e for e in neighbor_edges
                                     if not (e["source"] == source and e["target"] == target
                                             and e["relation"] == relation)]
            return len(self._edges) < before

    # --- traversal ---

    def bfs_shortest_path(self, start: str, end: str, max_depth: int = 10) -> Optional[List[str]]:
        if start == end:
            return [start]
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for edge in self._adj.get(current, []):
                neighbor = edge["target"] if edge["source"] == current else edge["source"]
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == end:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        return None

    def dfs_traverse(self, start: str, max_depth: int = 5) -> List[str]:
        visited = []
        stack = [(start, 0)]
        seen: Set[str] = set()
        while stack:
            node, depth = stack.pop()
            if node in seen or depth > max_depth:
                continue
            seen.add(node)
            visited.append(node)
            for edge in self._adj.get(node, []):
                neighbor = edge["target"] if edge["source"] == node else edge["source"]
                if neighbor not in seen:
                    stack.append((neighbor, depth + 1))
        return visited

    # --- search ---

    def keyword_search(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        keyword_lower = keyword.lower()
        results = []
        # search nodes
        for node in self._nodes.values():
            score = 0.0
            if keyword_lower == node["name"].lower():
                score = 1.0
            elif keyword_lower in node["name"].lower():
                score = 0.7
            elif keyword_lower in str(node["attributes"]).lower():
                score = 0.4
            if score > 0:
                results.append({"type": "node", "data": dict(node), "score": score})
        # search edges
        for edge in self._edges:
            score = 0.0
            if keyword_lower in edge["relation"].lower():
                score = 0.6
            elif keyword_lower in str(edge["attributes"]).lower():
                score = 0.3
            if score > 0:
                results.append({"type": "edge", "data": dict(edge), "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_neighbors(self, name: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        neighbors = []
        for edge in self._adj.get(name, []):
            if edge.get("_reverse"):
                neighbor = edge["source"]
            else:
                neighbor = edge["target"]
            if relation and edge["relation"] != relation:
                continue
            neighbor_node = self._nodes.get(neighbor)
            if neighbor_node:
                result = dict(neighbor_node)
                result["relation"] = edge["relation"]
                neighbors.append(result)
        return neighbors

    def stats(self) -> Dict[str, Any]:
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "backend": "memory",
        }

    def clear(self):
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._adj.clear()


# ---------------------------------------------------------------------------
# Neo4j 后端
# ---------------------------------------------------------------------------

class _Neo4jGraphStore:
    """基于 Neo4j 的图存储实现"""

    def __init__(self, driver):
        self.driver = driver
        self._lock = threading.Lock()

    def create_node(self, name: str, labels: Optional[List[str]] = None,
                    attributes: Optional[Dict[str, Any]] = None):
        labels = labels or ["Entity"]
        label_str = ":".join(labels)
        props = {"name": name}
        if attributes:
            props.update(attributes)
        cypher = f"""
        MERGE (n:{label_str} {{name: $name}})
        ON CREATE SET n += $props
        ON MATCH SET n += $props
        RETURN n
        """
        with self.driver.session() as session:
            session.run(cypher, name=name, props=props)
        return {"name": name, "labels": labels, "attributes": attributes or {}}

    def get_node(self, name: str):
        cypher = "MATCH (n) WHERE n.name = $name RETURN n"
        with self.driver.session() as session:
            result = session.run(cypher, name=name)
            record = result.single()
            if record:
                node = record["n"]
                return {"name": node.get("name"), "labels": list(node.labels),
                        "attributes": dict(node)}
            return None

    def query_nodes(self, label=None, keyword=None):
        cypher = "MATCH (n)"
        params = {}
        if label:
            cypher = f"MATCH (n:`{label}`)"
        if keyword:
            cypher += " WHERE n.name CONTAINS $keyword"
            params["keyword"] = keyword
        cypher += " RETURN n LIMIT 50"
        results = []
        with self.driver.session() as session:
            for record in session.run(cypher, **params):
                node = record["n"]
                results.append({"name": node.get("name"), "labels": list(node.labels),
                                "attributes": dict(node)})
        return results

    def delete_node(self, name: str):
        cypher = "MATCH (n {name: $name}) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(cypher, name=name)
        return True

    def create_edge(self, source: str, target: str, relation: str,
                    attributes: Optional[Dict[str, Any]] = None):
        # auto-create nodes
        self.create_node(source)
        self.create_node(target)
        props = attributes or {}
        cypher = """
        MATCH (a {name: $source}), (b {name: $target})
        MERGE (a)-[r:RELATES_TO {relation: $relation}]->(b)
        ON CREATE SET r += $props
        ON MATCH SET r += $props
        RETURN r
        """
        with self.driver.session() as session:
            session.run(cypher, source=source, target=target, relation=relation, props=props)
        return {"source": source, "target": target, "relation": relation, "attributes": props}

    def query_edges(self, source=None, target=None, relation=None):
        cypher = "MATCH (a)-[r]->(b)"
        params = {}
        conditions = []
        if source:
            conditions.append("a.name = $source")
            params["source"] = source
        if target:
            conditions.append("b.name = $target")
            params["target"] = target
        if relation:
            conditions.append("r.relation = $relation")
            params["relation"] = relation
        if conditions:
            cypher += " WHERE " + " AND ".join(conditions)
        cypher += " RETURN a.name AS source, b.name AS target, r.relation AS relation, properties(r) AS attrs LIMIT 50"
        results = []
        with self.driver.session() as session:
            for record in session.run(cypher, **params):
                results.append({"source": record["source"], "target": record["target"],
                                "relation": record["relation"], "attributes": record.get("attrs", {})})
        return results

    def delete_edge(self, source: str, target: str, relation: str):
        cypher = """
        MATCH (a {name: $source})-[r:RELATES_TO {relation: $relation}]->(b {name: $target})
        DELETE r
        """
        with self.driver.session() as session:
            session.run(cypher, source=source, target=target, relation=relation)
        return True

    def bfs_shortest_path(self, start: str, end: str, max_depth: int = 10):
        cypher = """
        MATCH path = shortestPath((a {name: $start})-[*1..%(depth)d]-(b {name: $end}))
        RETURN [n IN nodes(path) | n.name] AS names
        """ % {"depth": max_depth}
        with self.driver.session() as session:
            result = session.run(cypher, start=start, end=end)
            record = result.single()
            if record:
                return record["names"]
        return None

    def dfs_traverse(self, start: str, max_depth: int = 5):
        # Neo4j variable-length path for traversal
        cypher = """
        MATCH (a {name: $start})-[*1..%(depth)d]-(b)
        RETURN DISTINCT b.name AS name
        """ % {"depth": max_depth}
        with self.driver.session() as session:
            result = session.run(cypher, start=start)
            return [record["name"] for record in result]

    def keyword_search(self, keyword: str, limit: int = 10):
        cypher = """
        CALL {
            MATCH (n) WHERE n.name CONTAINS $keyword
            RETURN n.name AS name, 'node' AS type, 0.7 AS score
            UNION
            MATCH ()-[r]->() WHERE r.relation CONTAINS $keyword
            RETURN r.relation AS name, 'edge' AS type, 0.5 AS score
        }
        RETURN type, name, score ORDER BY score DESC LIMIT $limit
        """
        results = []
        with self.driver.session() as session:
            for record in session.run(cypher, keyword=keyword, limit=limit):
                results.append({"type": record["type"], "data": {"name": record["name"]},
                                "score": record["score"]})
        return results

    def get_neighbors(self, name: str, relation: Optional[str] = None):
        cypher = "MATCH (a {name: $name})-[r]->(b)"
        params = {"name": name}
        if relation:
            cypher += " WHERE r.relation = $relation"
            params["relation"] = relation
        cypher += " RETURN b.name AS name, r.relation AS relation"
        results = []
        with self.driver.session() as session:
            for record in session.run(cypher, **params):
                node = self.get_node(record["name"])
                if node:
                    node["relation"] = record["relation"]
                    results.append(node)
        return results

    def stats(self):
        try:
            with self.driver.session() as session:
                r1 = session.run("MATCH (n) RETURN count(n) AS cnt").single()
                r2 = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()
                return {"node_count": r1["cnt"], "edge_count": r2["cnt"], "backend": "neo4j"}
        except Exception:
            return {"node_count": 0, "edge_count": 0, "backend": "neo4j", "error": "query failed"}

    def clear(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


# ---------------------------------------------------------------------------
# KnowledgeGraph 公共接口
# ---------------------------------------------------------------------------

class KnowledgeGraph:
    """
    知识图谱：Neo4j 优先，内存字典优雅降级。
    所有方法在 Neo4j 不可用时安全回退到内存实现。
    """

    def __init__(self, neo4j_driver=None):
        if neo4j_driver is not None:
            self._store: Any = _Neo4jGraphStore(neo4j_driver)
            self._backend = "neo4j"
            logger.info("知识图谱使用 Neo4j 后端")
        else:
            self._store = _InMemoryGraphStore()
            self._backend = "memory"
            logger.info("知识图谱使用内存后端（Neo4j 不可用）")

    # --- 尝试从现有连接初始化 ---

    @classmethod
    def from_config(cls) -> "KnowledgeGraph":
        """尝试读取配置连接 Neo4j，失败则降级"""
        try:
            from backend.core.database import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver is not None:
                return cls(neo4j_driver=driver)
        except Exception as e:
            logger.warning(f"Neo4j 连接失败，降级到内存图谱: {e}")
        return cls()

    # --- 属性 ---

    @property
    def backend(self) -> str:
        return self._backend

    # --- 实体节点 ---

    def create_entity(self, name: str, labels: Optional[List[str]] = None,
                      attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建实体节点，已存在则更新属性"""
        return self._store.create_node(name, labels, attributes)

    def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """获取实体节点"""
        return self._store.get_node(name)

    def query_entities(self, label: Optional[str] = None,
                       keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询实体节点"""
        return self._store.query_nodes(label, keyword)

    def delete_entity(self, name: str) -> bool:
        """删除实体节点及其关系"""
        return self._store.delete_node(name)

    # --- 关系边 ---

    def create_relation(self, source: str, target: str, relation: str,
                        attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建关系边"""
        return self._store.create_edge(source, target, relation, attributes)

    def query_relations(self, source: Optional[str] = None,
                        target: Optional[str] = None,
                        relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询关系边"""
        return self._store.query_edges(source, target, relation)

    def delete_relation(self, source: str, target: str, relation: str) -> bool:
        """删除关系边"""
        return self._store.delete_edge(source, target, relation)

    # --- 图遍历 ---

    def shortest_path(self, start: str, end: str, max_depth: int = 10) -> Optional[List[str]]:
        """BFS 最短路径"""
        return self._store.bfs_shortest_path(start, end, max_depth)

    def traverse(self, start: str, max_depth: int = 5) -> List[str]:
        """DFS 遍历"""
        return self._store.dfs_traverse(start, max_depth)

    def get_neighbors(self, name: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取邻居节点"""
        return self._store.get_neighbors(name, relation)

    # --- 搜索 ---

    def keyword_search(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """关键词搜索实体和关系"""
        return self._store.keyword_search(keyword, limit)

    # --- 实体提取 ---

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取关键实体"""
        return EntityExtractor.extract(text)

    def ingest_text(self, text: str, default_relation: str = "mentions") -> List[Dict[str, Any]]:
        """
        摄取文本：提取实体，自动建立关系链。
        相邻实体按出现顺序用 default_relation 连接。
        """
        entities = self.extract_entities(text)
        created = []
        for ent in entities:
            node = self.create_entity(ent["text"], labels=[ent["type"]])
            created.append(node)

        # 链接相邻实体
        for i in range(len(entities) - 1):
            src = entities[i]["text"]
            tgt = entities[i + 1]["text"]
            self.create_relation(src, tgt, default_relation)

        return created

    # --- 记忆召回 ---

    def recall(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        记忆精准召回：先提取查询中的实体，再搜索图谱匹配，
        最后返回相关实体及其邻居上下文。
        """
        # 1. 提取查询实体
        query_entities = self.extract_entities(query)
        entity_names = [e["text"] for e in query_entities]

        results: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        def _add_result(item: Dict[str, Any], score: float):
            key = item.get("name", str(item))
            if key not in seen:
                seen.add(key)
                results.append({**item, "score": score})

        # 2. 精确匹配提取的实体
        for name in entity_names:
            node = self.get_entity(name)
            if node:
                _add_result(node, 1.0)
                # 带入邻居上下文
                for neighbor in self.get_neighbors(name):
                    _add_result(neighbor, 0.7)

        # 3. 关键词搜索补充
        if not entity_names:
            search_results = self.keyword_search(query, limit=limit)
            for sr in search_results:
                _add_result(sr["data"], sr["score"])

        # 4. 关系路径召回
        if len(entity_names) >= 2:
            for i in range(len(entity_names) - 1):
                path = self.shortest_path(entity_names[i], entity_names[i + 1])
                if path and len(path) > 2:
                    for node_name in path:
                        node = self.get_entity(node_name)
                        if node:
                            _add_result(node, 0.5)

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    # --- 统计 ---

    def stats(self) -> Dict[str, Any]:
        return self._store.stats()

    def clear(self):
        """清空图谱"""
        self._store.clear()


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_knowledge_graph_instance: Optional[KnowledgeGraph] = None
_knowledge_graph_lock = threading.Lock()


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph_instance
    if _knowledge_graph_instance is None:
        with _knowledge_graph_lock:
            if _knowledge_graph_instance is None:
                _knowledge_graph_instance = KnowledgeGraph.from_config()
    return _knowledge_graph_instance


def reset_knowledge_graph():
    global _knowledge_graph_instance
    _knowledge_graph_instance = None
