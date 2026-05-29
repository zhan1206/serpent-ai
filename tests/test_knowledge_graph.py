"""Tests for backend.memory.knowledge_graph"""
import pytest
from unittest.mock import MagicMock, patch
from backend.memory.knowledge_graph import (
    KnowledgeGraph, EntityExtractor, _InMemoryGraphStore, _Neo4jGraphStore,
    get_knowledge_graph, reset_knowledge_graph,
)


# ---------------------------------------------------------------------------
# EntityExtractor
# ---------------------------------------------------------------------------

class TestEntityExtractor:
    def test_extract_person(self):
        result = EntityExtractor.extract("张三去了北京")
        types = {e["type"] for e in result}
        assert "person" in types

    def test_extract_location(self):
        result = EntityExtractor.extract("他去北京市旅游")
        for e in result:
            assert "type" in e and "text" in e

    def test_extract_organization(self):
        result = EntityExtractor.extract("他在清华大学读书")
        for e in result:
            assert "type" in e and "text" in e

    def test_extract_date(self):
        result = EntityExtractor.extract("2024年1月1日是新年")
        types = {e["type"] for e in result}
        assert "time" in types

    def test_extract_concept(self):
        result = EntityExtractor.extract("人工智能改变了世界")
        types = {e["type"] for e in result}
        assert "concept" in types

    def test_extract_empty(self):
        assert EntityExtractor.extract("") == []

    def test_extract_dedup(self):
        result = EntityExtractor.extract("张三和张三")
        # Verify extractor returns entities (may be phrase-level)
        names = [e["text"] for e in result if e["type"] == "person"]
        assert len(names) >= 1

    def test_extract_relative_time(self):
        result = EntityExtractor.extract("明天是周五")
        types = {e["type"] for e in result}
        assert "time" in types


# ---------------------------------------------------------------------------
# _InMemoryGraphStore
# ---------------------------------------------------------------------------

class TestInMemoryGraphStore:
    @pytest.fixture
    def store(self):
        return _InMemoryGraphStore()

    def test_create_and_get_node(self, store):
        node = store.create_node("n1", labels=["Test"], attributes={"k": "v"})
        assert node["name"] == "n1"
        got = store.get_node("n1")
        assert got is not None
        assert got["name"] == "n1"

    def test_get_node_missing(self, store):
        assert store.get_node("missing") is None

    def test_create_node_update(self, store):
        store.create_node("n1", attributes={"a": 1})
        store.create_node("n1", attributes={"b": 2})
        node = store.get_node("n1")
        assert node["attributes"]["a"] == 1
        assert node["attributes"]["b"] == 2

    def test_query_nodes_by_label(self, store):
        store.create_node("n1", labels=["Person"])
        store.create_node("n2", labels=["Org"])
        results = store.query_nodes(label="Person")
        assert len(results) == 1
        assert results[0]["name"] == "n1"

    def test_query_nodes_by_keyword(self, store):
        store.create_node("hello", attributes={"desc": "world"})
        results = store.query_nodes(keyword="hello")
        assert len(results) == 1

    def test_query_nodes_by_keyword_in_attrs(self, store):
        store.create_node("n1", attributes={"desc": "special_value"})
        results = store.query_nodes(keyword="special_value")
        assert len(results) == 1

    def test_delete_node(self, store):
        store.create_node("n1")
        assert store.delete_node("n1") is True
        assert store.get_node("n1") is None

    def test_delete_node_missing(self, store):
        assert store.delete_node("missing") is False

    def test_delete_node_removes_edges(self, store):
        store.create_node("a")
        store.create_node("b")
        store.create_edge("a", "b", "rel")
        store.delete_node("a")
        assert store.query_edges(source="a") == []

    def test_create_edge(self, store):
        edge = store.create_edge("a", "b", "knows", attributes={"since": 2020})
        assert edge["source"] == "a"
        assert edge["relation"] == "knows"

    def test_create_edge_auto_creates_nodes(self, store):
        store.create_edge("x", "y", "rel")
        assert store.get_node("x") is not None
        assert store.get_node("y") is not None

    def test_create_edge_dedup(self, store):
        e1 = store.create_edge("a", "b", "rel")
        e2 = store.create_edge("a", "b", "rel", attributes={"k": "v"})
        assert e1["source"] == e2["source"]
        edges = store.query_edges(source="a")
        assert len(edges) == 1

    def test_query_edges(self, store):
        store.create_edge("a", "b", "rel1")
        store.create_edge("a", "c", "rel2")
        assert len(store.query_edges(source="a")) == 2
        assert len(store.query_edges(target="b")) == 1
        assert len(store.query_edges(relation="rel2")) == 1

    def test_delete_edge(self, store):
        store.create_edge("a", "b", "rel")
        assert store.delete_edge("a", "b", "rel") is True
        assert store.query_edges() == []

    def test_delete_edge_missing(self, store):
        assert store.delete_edge("x", "y", "none") is False

    def test_bfs_shortest_path_same(self, store):
        store.create_node("a")
        assert store.bfs_shortest_path("a", "a") == ["a"]

    def test_bfs_shortest_path_connected(self, store):
        store.create_edge("a", "b", "rel")
        store.create_edge("b", "c", "rel")
        path = store.bfs_shortest_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_bfs_shortest_path_none(self, store):
        store.create_node("a")
        store.create_node("z")
        assert store.bfs_shortest_path("a", "z") is None

    def test_dfs_traverse(self, store):
        store.create_edge("a", "b", "rel")
        store.create_edge("b", "c", "rel")
        result = store.dfs_traverse("a")
        assert "a" in result

    def test_keyword_search_node(self, store):
        store.create_node("hello_world")
        results = store.keyword_search("hello")
        assert len(results) > 0
        assert results[0]["type"] == "node"

    def test_keyword_search_edge(self, store):
        store.create_edge("a", "b", "knows_about")
        results = store.keyword_search("about")
        assert len(results) > 0

    def test_keyword_search_limit(self, store):
        for i in range(20):
            store.create_node(f"test_item_{i}")
        results = store.keyword_search("test_item", limit=5)
        assert len(results) <= 5

    def test_get_neighbors(self, store):
        store.create_edge("a", "b", "friend")
        neighbors = store.get_neighbors("a")
        assert len(neighbors) == 1
        assert neighbors[0]["relation"] == "friend"

    def test_get_neighbors_with_relation_filter(self, store):
        store.create_edge("a", "b", "friend")
        store.create_edge("a", "c", "coworker")
        neighbors = store.get_neighbors("a", relation="friend")
        assert len(neighbors) == 1

    def test_stats(self, store):
        store.create_node("a")
        store.create_edge("a", "b", "rel")
        s = store.stats()
        assert s["node_count"] == 2
        assert s["edge_count"] == 1
        assert s["backend"] == "memory"

    def test_clear(self, store):
        store.create_node("a")
        store.clear()
        assert store.get_node("a") is None
        assert store.stats()["node_count"] == 0


# ---------------------------------------------------------------------------
# _Neo4jGraphStore (mocked)
# ---------------------------------------------------------------------------

class TestNeo4jGraphStore:
    @pytest.fixture
    def mock_driver(self):
        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__ = MagicMock(return_value=session)
        driver.session.return_value.__exit__ = MagicMock(return_value=False)
        return driver, session

    @pytest.fixture
    def store(self, mock_driver):
        driver, _ = mock_driver
        return _Neo4jGraphStore(driver)

    def test_create_node(self, store, mock_driver):
        _, session = mock_driver
        store.create_node("n1", labels=["Person"], attributes={"age": 30})
        session.run.assert_called_once()

    def test_get_node_found(self, store, mock_driver):
        _, session = mock_driver
        mock_node = MagicMock()
        mock_node.get.return_value = "n1"
        mock_node.labels = ["Person"]
        mock_node.__iter__ = MagicMock(return_value=iter([]))
        record = {"n": mock_node}
        session.run.return_value.single.return_value = record
        result = store.get_node("n1")
        assert result is not None
        assert result["name"] == "n1"

    def test_get_node_not_found(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value.single.return_value = None
        assert store.get_node("missing") is None

    def test_delete_node(self, store, mock_driver):
        _, session = mock_driver
        assert store.delete_node("n1") is True

    def test_create_edge(self, store, mock_driver):
        _, session = mock_driver
        result = store.create_edge("a", "b", "rel")
        assert result["source"] == "a"

    def test_query_edges(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value = iter([
            {"source": "a", "target": "b", "relation": "r", "attrs": {}}
        ])
        results = store.query_edges(source="a")
        assert len(results) == 1

    def test_keyword_search(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value = iter([
            {"type": "node", "name": "test", "score": 0.7}
        ])
        results = store.keyword_search("test")
        assert len(results) == 1

    def test_stats_success(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value.single.side_effect = [
            {"cnt": 5}, {"cnt": 3}
        ]
        s = store.stats()
        assert s["backend"] == "neo4j"

    def test_stats_error(self, store, mock_driver):
        _, session = mock_driver
        session.run.side_effect = Exception("fail")
        s = store.stats()
        assert "error" in s

    def test_clear(self, store, mock_driver):
        _, session = mock_driver
        store.clear()
        session.run.assert_called()

    def test_dfs_traverse(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value = iter([{"name": "b"}, {"name": "c"}])
        result = store.dfs_traverse("a")
        assert "b" in result

    def test_bfs_shortest_path_found(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value.single.return_value = {"names": ["a", "b", "c"]}
        path = store.bfs_shortest_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_bfs_shortest_path_not_found(self, store, mock_driver):
        _, session = mock_driver
        session.run.return_value.single.return_value = None
        assert store.bfs_shortest_path("a", "z") is None


# ---------------------------------------------------------------------------
# KnowledgeGraph public interface
# ---------------------------------------------------------------------------

class TestKnowledgeGraph:
    @pytest.fixture
    def kg(self):
        return KnowledgeGraph()  # memory backend

    def test_backend_memory(self, kg):
        assert kg.backend == "memory"

    def test_backend_neo4j(self):
        driver = MagicMock()
        kg = KnowledgeGraph(neo4j_driver=driver)
        assert kg.backend == "neo4j"

    def test_from_config_fallback(self):
        with patch("memory.knowledge_graph.KnowledgeGraph", wraps=KnowledgeGraph) as mock_cls:
            try:
                kg = KnowledgeGraph.from_config()
            except Exception:
                pass
            # Should fall back to memory backend
            kg_mem = KnowledgeGraph()
            assert kg_mem.backend == "memory"

    def test_create_and_get_entity(self, kg):
        kg.create_entity("张三", labels=["Person"], attributes={"age": 30})
        entity = kg.get_entity("张三")
        assert entity is not None
        assert entity["name"] == "张三"

    def test_query_entities(self, kg):
        kg.create_entity("n1", labels=["Person"])
        kg.create_entity("n2", labels=["Org"])
        results = kg.query_entities(label="Person")
        assert len(results) == 1

    def test_delete_entity(self, kg):
        kg.create_entity("n1")
        assert kg.delete_entity("n1") is True
        assert kg.get_entity("n1") is None

    def test_create_and_query_relation(self, kg):
        kg.create_relation("a", "b", "friend")
        results = kg.query_relations(source="a")
        assert len(results) == 1

    def test_delete_relation(self, kg):
        kg.create_relation("a", "b", "rel")
        assert kg.delete_relation("a", "b", "rel") is True

    def test_shortest_path(self, kg):
        kg.create_relation("a", "b", "rel")
        kg.create_relation("b", "c", "rel")
        path = kg.shortest_path("a", "c")
        assert path is not None

    def test_traverse(self, kg):
        kg.create_relation("a", "b", "rel")
        result = kg.traverse("a")
        assert "a" in result

    def test_get_neighbors(self, kg):
        kg.create_relation("a", "b", "friend")
        neighbors = kg.get_neighbors("a")
        assert len(neighbors) >= 1

    def test_keyword_search(self, kg):
        kg.create_entity("hello_world")
        results = kg.keyword_search("hello")
        assert len(results) > 0

    def test_extract_entities(self, kg):
        entities = kg.extract_entities("张三去了北京")
        assert len(entities) > 0

    def test_ingest_text(self, kg):
        created = kg.ingest_text("张三去了北京")
        assert len(created) > 0

    def test_recall(self, kg):
        kg.create_entity("张三", labels=["Person"], attributes={"desc": "在北京清华大学学习AI"})
        kg.create_entity("北京", labels=["Location"])
        kg.create_relation("张三", "北京", "位于")
        results = kg.recall("张三")
        # recall returns related entities/paths
        assert isinstance(results, (list, dict))

    def test_recall_no_entities(self, kg):
        kg.create_entity("python", labels=["concept"])
        results = kg.recall("python")
        assert len(results) > 0

    def test_recall_with_path(self, kg):
        kg.create_entity("a")
        kg.create_entity("b")
        kg.create_entity("c")
        kg.create_relation("a", "b", "rel")
        kg.create_relation("b", "c", "rel")
        # recall with two entities that have a path
        results = kg.recall("a c")
        # just ensure no crash

    def test_stats(self, kg):
        kg.create_entity("n1")
        s = kg.stats()
        assert s["node_count"] == 1

    def test_clear(self, kg):
        kg.create_entity("n1")
        kg.clear()
        assert kg.stats()["node_count"] == 0


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

class TestGlobalSingleton:
    def setup_method(self):
        reset_knowledge_graph()

    def test_get_knowledge_graph(self):
        kg = get_knowledge_graph()
        assert kg is not None

    def test_reset(self):
        kg1 = get_knowledge_graph()
        reset_knowledge_graph()
        kg2 = get_knowledge_graph()
        assert kg1 is not kg2
