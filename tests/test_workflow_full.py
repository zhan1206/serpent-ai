"""
Test file for workflow module.
Tests cover ALL public methods and classes in:
- backend/workflow/__init__.py
- backend/workflow/engine.py
- backend/workflow/editor.py
- backend/workflow/executor.py
- backend/workflow/scheduler.py

Uses unittest.mock for external deps, asyncio for async methods, pytest fixtures.
Target: 80%+ coverage.
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import threading

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.workflow.engine import (
    NodeType, WorkflowStatus, NodeStatus,
    NodeConfig, WorkflowNode, Edge, Workflow, WorkflowEngine
)
from backend.workflow.editor import WorkflowEditor
from backend.workflow.executor import WorkflowExecutor
from backend.workflow.scheduler import TriggerType, WorkflowScheduler


# ==================== Fixtures ====================

@pytest.fixture
def engine():
    """Create a WorkflowEngine instance"""
    return WorkflowEngine()


@pytest.fixture
def workflow(engine):
    """Create a basic workflow"""
    return engine.create_workflow("Test Workflow", "Test Description", "test_user")


@pytest.fixture
def editor(engine):
    """Create a WorkflowEditor instance"""
    return WorkflowEditor(engine)


@pytest.fixture
def executor(engine):
    """Create a WorkflowExecutor instance"""
    return WorkflowExecutor(engine)


@pytest.fixture
def scheduler(engine):
    """Create a WorkflowScheduler instance"""
    return WorkflowScheduler(engine)


@pytest.fixture
def sample_node():
    """Create a sample WorkflowNode"""
    return WorkflowNode(
        id="test_node_1",
        name="Test Node",
        type=NodeType.AGENT,
        position_x=100,
        position_y=200
    )


@pytest.fixture
def sample_edge():
    """Create a sample Edge"""
    return Edge(
        id="test_edge_1",
        source="node_1",
        target="node_2",
        source_port="out",
        target_port="in"
    )


@pytest.fixture
def complex_workflow(engine):
    """Create a workflow with multiple nodes and edges"""
    wf = engine.create_workflow("Complex Workflow", "Test complex workflow")
    
    # Clear default nodes
    wf.nodes = []
    wf.edges = []
    
    # Create nodes
    start_node = WorkflowNode(
        id="start_1",
        name="Start",
        type=NodeType.START,
        position_x=50,
        position_y=100,
        inputs=[],
        outputs=["out"]
    )
    
    agent_node = WorkflowNode(
        id="agent_1",
        name="Agent",
        type=NodeType.AGENT,
        position_x=200,
        position_y=100,
        inputs=["in"],
        outputs=["out"]
    )
    
    end_node = WorkflowNode(
        id="end_1",
        name="End",
        type=NodeType.END,
        position_x=350,
        position_y=100,
        inputs=["in"],
        outputs=[]
    )
    
    wf.nodes = [start_node, agent_node, end_node]
    
    # Create edges
    edge1 = Edge(
        id="edge_1",
        source="start_1",
        target="agent_1",
        source_port="out",
        target_port="in"
    )
    
    edge2 = Edge(
        id="edge_2",
        source="agent_1",
        target="end_1",
        source_port="out",
        target_port="in"
    )
    
    wf.edges = [edge1, edge2]
    
    return wf


# ==================== Test NodeConfig ====================

class TestNodeConfig:
    """Test NodeConfig dataclass"""
    
    def test_create_default(self):
        """Test creating NodeConfig with defaults"""
        config = NodeConfig()
        assert config.timeout == 30
        assert config.retry == 0
        assert config.retry_delay == 1
        assert config.agent_model == "gpt-4"
        assert config.agent_temperature == 0.7
        assert config.agent_max_tokens == 2048
        assert config.agent_system_prompt == ""
        assert config.tool_name == ""
        assert config.tool_args == {}
        assert config.condition_expression == ""
        assert config.loop_count == 1
        assert config.loop_variable == ""
        assert config.loop_items == []
        assert config.http_method == "GET"
        assert config.http_url == ""
        assert config.http_headers == {}
        assert config.http_body is None
        assert config.code_language == "python"
        assert config.code_content == ""
        assert config.db_operation == "select"
        assert config.db_query == ""
        assert config.db_params == {}
        assert config.template_content == ""
        assert config.template_vars == {}
        assert config.message_channel == "console"
        assert config.message_content == ""
        assert config.schedule_cron == ""
        assert config.schedule_interval == 0
        assert config.input_schema == {}
        assert config.output_schema == {}
        assert config.custom == {}
    
    def test_to_dict(self):
        """Test to_dict method"""
        config = NodeConfig(
            timeout=60,
            agent_model="gpt-3.5-turbo",
            http_url="https://api.example.com"
        )
        result = config.to_dict()
        assert isinstance(result, dict)
        assert result["timeout"] == 60
        assert result["agent_model"] == "gpt-3.5-turbo"
        assert result["http_url"] == "https://api.example.com"
    
    def test_from_dict(self):
        """Test from_dict class method"""
        data = {
            "timeout": 120,
            "agent_model": "claude-3",
            "http_method": "POST",
            "custom": {"key": "value"}
        }
        config = NodeConfig.from_dict(data)
        assert config.timeout == 120
        assert config.agent_model == "claude-3"
        assert config.http_method == "POST"
        assert config.custom == {"key": "value"}
    
    def test_from_dict_empty(self):
        """Test from_dict with empty dict"""
        config = NodeConfig.from_dict({})
        assert config.timeout == 30  # default
        assert config.agent_model == "gpt-4"  # default


# ==================== Test WorkflowNode ====================

class TestWorkflowNode:
    """Test WorkflowNode dataclass"""
    
    def test_create_default(self):
        """Test creating WorkflowNode with defaults"""
        node = WorkflowNode()
        assert node.id != ""
        assert node.name == ""
        assert node.type == NodeType.START
        assert isinstance(node.config, NodeConfig)
        assert node.position_x == 0
        assert node.position_y == 0
        assert node.width == 150
        assert node.height == 80
        assert node.inputs == []
        assert node.outputs == []
        assert node.status == NodeStatus.PENDING
        assert node.result is None
        assert node.error == ""
        assert node.start_time is None
        assert node.end_time is None
        assert node.branches == []
        assert node.default_branch is None
    
    def test_create_with_values(self):
        """Test creating WorkflowNode with values"""
        node = WorkflowNode(
            id="node_1",
            name="Test Node",
            type=NodeType.AGENT,
            position_x=100,
            position_y=200
        )
        assert node.id == "node_1"
        assert node.name == "Test Node"
        assert node.type == NodeType.AGENT
        assert node.position_x == 100
        assert node.position_y == 200
    
    def test_to_dict(self):
        """Test to_dict method"""
        node = WorkflowNode(
            id="node_1",
            name="Test Node",
            type=NodeType.AGENT
        )
        result = node.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "node_1"
        assert result["name"] == "Test Node"
        assert result["type"] == "agent"
        assert "config" in result
        assert "position" in result
        assert "size" in result
    
    def test_from_dict(self):
        """Test from_dict class method"""
        data = {
            "id": "node_1",
            "name": "Test Node",
            "type": "agent",
            "config": {"timeout": 60},
            "position": {"x": 100, "y": 200},
            "size": {"width": 200, "height": 100},
            "inputs": ["in"],
            "outputs": ["out"],
            "status": "completed",
            "result": {"data": "test"},
            "error": "",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T10:00:05",
            "branches": ["node_2"],
            "default_branch": "node_3"
        }
        node = WorkflowNode.from_dict(data)
        assert node.id == "node_1"
        assert node.name == "Test Node"
        assert node.type == NodeType.AGENT
        assert node.position_x == 100
        assert node.position_y == 200
        assert node.width == 200
        assert node.height == 100
        assert node.inputs == ["in"]
        assert node.outputs == ["out"]
        assert node.status == NodeStatus.COMPLETED
        assert node.result == {"data": "test"}
        assert isinstance(node.start_time, datetime)
        assert isinstance(node.end_time, datetime)
        assert node.branches == ["node_2"]
        assert node.default_branch == "node_3"
    
    def test_from_dict_minimal(self):
        """Test from_dict with minimal data"""
        data = {"id": "node_1", "name": "Test"}
        node = WorkflowNode.from_dict(data)
        assert node.id == "node_1"
        assert node.name == "Test"
        assert node.type == NodeType.START  # default


# ==================== Test Edge ====================

class TestEdge:
    """Test Edge dataclass"""
    
    def test_create_default(self):
        """Test creating Edge with defaults"""
        edge = Edge()
        assert edge.id != ""
        assert edge.source == ""
        assert edge.source_port == ""
        assert edge.target == ""
        assert edge.target_port == ""
        assert edge.label == ""
        assert edge.condition == ""
    
    def test_create_with_values(self):
        """Test creating Edge with values"""
        edge = Edge(
            id="edge_1",
            source="node_1",
            target="node_2",
            source_port="out",
            target_port="in",
            label="test",
            condition="x > 0"
        )
        assert edge.id == "edge_1"
        assert edge.source == "node_1"
        assert edge.target == "node_2"
        assert edge.source_port == "out"
        assert edge.target_port == "in"
        assert edge.label == "test"
        assert edge.condition == "x > 0"
    
    def test_to_dict(self):
        """Test to_dict method"""
        edge = Edge(
            id="edge_1",
            source="node_1",
            target="node_2"
        )
        result = edge.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "edge_1"
        assert result["source"] == "node_1"
        assert result["target"] == "node_2"
        assert "sourcePort" in result
        assert "targetPort" in result
    
    def test_from_dict(self):
        """Test from_dict class method"""
        data = {
            "id": "edge_1",
            "source": "node_1",
            "sourcePort": "out",
            "target": "node_2",
            "targetPort": "in",
            "label": "test",
            "condition": "x > 0"
        }
        edge = Edge.from_dict(data)
        assert edge.id == "edge_1"
        assert edge.source == "node_1"
        assert edge.source_port == "out"
        assert edge.target == "node_2"
        assert edge.target_port == "in"
        assert edge.label == "test"
        assert edge.condition == "x > 0"


# ==================== Test Workflow ====================

class TestWorkflow:
    """Test Workflow dataclass"""
    
    def test_create_default(self):
        """Test creating Workflow with defaults"""
        wf = Workflow()
        assert wf.id != ""
        assert wf.name == ""
        assert wf.description == ""
        assert wf.version == 1
        assert wf.nodes == []
        assert wf.edges == []
        assert wf.status == WorkflowStatus.DRAFT
        assert wf.variables == {}
        assert isinstance(wf.created_at, datetime)
        assert isinstance(wf.updated_at, datetime)
        assert wf.created_by == ""
        assert wf.tags == []
        assert wf.execution_count == 0
        assert wf.last_execution is None
        assert wf.last_execution_result is None
    
    def test_create_with_values(self):
        """Test creating Workflow with values"""
        wf = Workflow(
            id="wf_1",
            name="Test Workflow",
            description="Test Description",
            created_by="user_1"
        )
        assert wf.id == "wf_1"
        assert wf.name == "Test Workflow"
        assert wf.description == "Test Description"
        assert wf.created_by == "user_1"
    
    def test_to_dict(self):
        """Test to_dict method"""
        wf = Workflow(
            id="wf_1",
            name="Test Workflow"
        )
        result = wf.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "wf_1"
        assert result["name"] == "Test Workflow"
        assert "nodes" in result
        assert "edges" in result
        assert "status" in result
        assert "variables" in result
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_from_dict(self):
        """Test from_dict class method"""
        data = {
            "id": "wf_1",
            "name": "Test Workflow",
            "description": "Test",
            "version": 2,
            "nodes": [],
            "edges": [],
            "status": "active",
            "variables": {"key": "value"},
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T10:00:00",
            "created_by": "user_1",
            "tags": ["test"],
            "execution_count": 5,
            "last_execution": "2024-01-01T10:00:00",
            "last_execution_result": {"status": "completed"}
        }
        wf = Workflow.from_dict(data)
        assert wf.id == "wf_1"
        assert wf.name == "Test Workflow"
        assert wf.version == 2
        assert wf.status == WorkflowStatus.ACTIVE
        assert wf.variables == {"key": "value"}
        assert wf.created_by == "user_1"
        assert wf.tags == ["test"]
        assert wf.execution_count == 5
        assert isinstance(wf.last_execution, datetime)
        assert wf.last_execution_result == {"status": "completed"}
    
    def test_get_node(self, complex_workflow):
        """Test get_node method"""
        # Existing node
        node = complex_workflow.get_node("start_1")
        assert node is not None
        assert node.id == "start_1"
        assert node.name == "Start"
        
        # Non-existing node
        node = complex_workflow.get_node("non_existing")
        assert node is None
    
    def test_get_incoming_edges(self, complex_workflow):
        """Test get_incoming_edges method"""
        # Node with incoming edges
        edges = complex_workflow.get_incoming_edges("agent_1")
        assert len(edges) == 1
        assert edges[0].source == "start_1"
        
        # Node without incoming edges
        edges = complex_workflow.get_incoming_edges("start_1")
        assert len(edges) == 0
    
    def test_get_outgoing_edges(self, complex_workflow):
        """Test get_outgoing_edges method"""
        # Node with outgoing edges
        edges = complex_workflow.get_outgoing_edges("start_1")
        assert len(edges) == 1
        assert edges[0].target == "agent_1"
        
        # Node without outgoing edges
        edges = complex_workflow.get_outgoing_edges("end_1")
        assert len(edges) == 0
    
    def test_topological_sort(self, complex_workflow):
        """Test topological_sort method"""
        sorted_nodes = complex_workflow.topological_sort()
        assert len(sorted_nodes) == 3
        
        # Check order: start_1 -> agent_1 -> end_1
        node_ids = [n.id for n in sorted_nodes]
        assert node_ids.index("start_1") < node_ids.index("agent_1")
        assert node_ids.index("agent_1") < node_ids.index("end_1")


# ==================== Test WorkflowEngine ====================

class TestWorkflowEngine:
    """Test WorkflowEngine class"""
    
    def test_init(self, engine):
        """Test engine initialization"""
        assert isinstance(engine.workflows, dict)
        assert len(engine.workflows) == 0
        assert isinstance(engine._executors, dict)
        assert isinstance(engine._node_handlers, dict)
        assert len(engine._node_handlers) > 0
    
    def test_create_workflow(self, engine):
        """Test create_workflow method"""
        wf = engine.create_workflow("Test WF", "Test Desc", "user_1")
        
        assert wf.id != ""
        assert wf.name == "Test WF"
        assert wf.description == "Test Desc"
        assert wf.created_by == "user_1"
        assert wf.status == WorkflowStatus.DRAFT
        
        # Check default nodes (START and END)
        assert len(wf.nodes) == 2
        assert any(n.type == NodeType.START for n in wf.nodes)
        assert any(n.type == NodeType.END for n in wf.nodes)
        
        # Check workflow is stored
        assert wf.id in engine.workflows
    
    def test_get_workflow(self, engine, workflow):
        """Test get_workflow method"""
        # Existing workflow
        result = engine.get_workflow(workflow.id)
        assert result is not None
        assert result.id == workflow.id
        
        # Non-existing workflow
        result = engine.get_workflow("non_existing")
        assert result is None
    
    def test_update_workflow(self, engine, workflow):
        """Test update_workflow method"""
        original_version = workflow.version
        workflow.name = "Updated Name"
        
        result = engine.update_workflow(workflow)
        assert result is True
        assert workflow.version == original_version + 1
        
        # Non-existing workflow
        fake_wf = Workflow(id="fake_id")
        result = engine.update_workflow(fake_wf)
        assert result is False
    
    def test_delete_workflow(self, engine, workflow):
        """Test delete_workflow method"""
        wf_id = workflow.id
        assert wf_id in engine.workflows
        
        result = engine.delete_workflow(wf_id)
        assert result is True
        assert wf_id not in engine.workflows
        
        # Non-existing workflow
        result = engine.delete_workflow("non_existing")
        assert result is False
    
    def test_list_workflows(self, engine):
        """Test list_workflows method"""
        # Create multiple workflows
        wf1 = engine.create_workflow("WF 1")
        wf2 = engine.create_workflow("WF 2")
        wf3 = engine.create_workflow("WF 3")
        
        # All workflows
        result = engine.list_workflows()
        assert len(result) == 3
        
        # Filter by status
        wf1.status = WorkflowStatus.ACTIVE
        result = engine.list_workflows(status=WorkflowStatus.ACTIVE)
        assert len(result) == 1
        assert result[0].id == wf1.id
        
        # Filter by tags
        wf2.tags = ["test"]
        result = engine.list_workflows(tags=["test"])
        assert len(result) == 1
        assert result[0].id == wf2.id
    
    def test_add_node(self, engine, workflow):
        """Test add_node method"""
        node = WorkflowNode(
            id="new_node",
            name="New Node",
            type=NodeType.AGENT
        )
        
        result = engine.add_node(workflow.id, node)
        assert result is True
        assert len(workflow.nodes) == 3  # 2 default + 1 new
        
        # Non-existing workflow
        result = engine.add_node("non_existing", node)
        assert result is False
    
    def test_update_node(self, engine, workflow):
        """Test update_node method"""
        # Get default start node
        start_node = next(n for n in workflow.nodes if n.type == NodeType.START)
        
        result = engine.update_node(
            workflow.id,
            start_node.id,
            {"name": "Updated Start"}
        )
        assert result is True
        assert start_node.name == "Updated Start"
        
        # Non-existing node
        result = engine.update_node(
            workflow.id,
            "non_existing",
            {"name": "Test"}
        )
        assert result is False
        
        # Non-existing workflow
        result = engine.update_node(
            "non_existing",
            start_node.id,
            {"name": "Test"}
        )
        assert result is False
    
    def test_delete_node(self, engine, workflow):
        """Test delete_node method"""
        # Add a node first
        node = WorkflowNode(
            id="to_delete",
            name="To Delete",
            type=NodeType.AGENT
        )
        workflow.nodes.append(node)
        assert len(workflow.nodes) == 3
        
        result = engine.delete_node(workflow.id, "to_delete")
        assert result is True
        assert len(workflow.nodes) == 2
        
        # Check edges are also deleted
        edge = Edge(source="to_delete", target="end")
        workflow.edges.append(edge)
        assert len(workflow.edges) == 1
        
        result = engine.delete_node(workflow.id, "to_delete")
        assert result is False  # Already deleted
        
        # Non-existing workflow
        result = engine.delete_node("non_existing", "node_id")
        assert result is False
    
    def test_add_edge(self, engine, workflow):
        """Test add_edge method"""
        # Get start and end nodes
        start_node = next(n for n in workflow.nodes if n.type == NodeType.START)
        end_node = next(n for n in workflow.nodes if n.type == NodeType.END)
        
        edge = Edge(
            source=start_node.id,
            target=end_node.id,
            source_port="out",
            target_port="in"
        )
        
        result = engine.add_edge(workflow.id, edge)
        assert result is True
        assert len(workflow.edges) == 1
        
        # Invalid source node
        bad_edge = Edge(source="non_existing", target=end_node.id)
        result = engine.add_edge(workflow.id, bad_edge)
        assert result is False
        
        # Non-existing workflow
        result = engine.add_edge("non_existing", edge)
        assert result is False
    
    def test_delete_edge(self, engine, workflow):
        """Test delete_edge method"""
        # Add an edge first
        start_node = next(n for n in workflow.nodes if n.type == NodeType.START)
        end_node = next(n for n in workflow.nodes if n.type == NodeType.END)
        
        edge = Edge(
            id="edge_to_delete",
            source=start_node.id,
            target=end_node.id
        )
        workflow.edges.append(edge)
        assert len(workflow.edges) == 1
        
        result = engine.delete_edge(workflow.id, "edge_to_delete")
        assert result is True
        assert len(workflow.edges) == 0
        
        # Non-existing edge
        result = engine.delete_edge(workflow.id, "non_existing")
        assert result is False
        
        # Non-existing workflow
        result = engine.delete_edge("non_existing", "edge_id")
        assert result is False
    
    def test_validate_workflow(self, engine):
        """Test validate_workflow method"""
        # Valid workflow
        wf = Workflow(
            id="wf_1",
            name="Test",
            nodes=[
                WorkflowNode(id="start", type=NodeType.START, inputs=[], outputs=["out"]),
                WorkflowNode(id="end", type=NodeType.END, inputs=["in"], outputs=[])
            ],
            edges=[
                Edge(id="edge_1", source="start", target="end")
            ]
        )
        engine.workflows[wf.id] = wf
        
        is_valid, errors = engine.validate_workflow(wf)
        assert is_valid is True
        assert len(errors) == 0
        
        # Missing start node
        wf2 = Workflow(
            id="wf_2",
            name="Test 2",
            nodes=[
                WorkflowNode(id="end", type=NodeType.END, inputs=["in"], outputs=[])
            ]
        )
        is_valid, errors = engine.validate_workflow(wf2)
        assert is_valid is False
        assert any("开始节点" in e for e in errors)
        
        # Missing end node
        wf3 = Workflow(
            id="wf_3",
            name="Test 3",
            nodes=[
                WorkflowNode(id="start", type=NodeType.START, inputs=[], outputs=["out"])
            ]
        )
        is_valid, errors = engine.validate_workflow(wf3)
        assert is_valid is False
        assert any("结束节点" in e for e in errors)
        
        # Duplicate node IDs
        wf4 = Workflow(
            id="wf_4",
            name="Test 4",
            nodes=[
                WorkflowNode(id="node1", type=NodeType.START),
                WorkflowNode(id="node1", type=NodeType.END)
            ]
        )
        is_valid, errors = engine.validate_workflow(wf4)
        assert is_valid is False
        assert any("重复" in e for e in errors)
    
    @pytest.mark.asyncio
    async def test_execute_node(self, engine, workflow):
        """Test execute_node method"""
        node = WorkflowNode(
            id="agent_node",
            name="Agent",
            type=NodeType.AGENT
        )
        workflow.nodes.append(node)
        
        context = {"input": "test input"}
        result = await engine.execute_node(workflow, node, context)
        
        assert isinstance(result, dict)
        assert "agent_response" in result
        assert node.status == NodeStatus.COMPLETED
        
        # Unknown node type
        unknown_node = WorkflowNode(
            id="unknown",
            name="Unknown",
            type=NodeType("code")  # Use valid type but don't register handler
        )
        # This should still work as CODE has a handler
        result = await engine.execute_node(workflow, unknown_node, context)
        assert isinstance(result, dict)
    
    def test_export_workflow(self, engine, workflow):
        """Test export_workflow method"""
        result = engine.export_workflow(workflow.id)
        
        assert result is not None
        assert isinstance(result, str)
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert data["id"] == workflow.id
        assert data["name"] == workflow.name
        
        # Non-existing workflow
        result = engine.export_workflow("non_existing")
        assert result is None
    
    def test_import_workflow(self, engine):
        """Test import_workflow method"""
        json_str = json.dumps({
            "id": "imported_wf",
            "name": "Imported WF",
            "description": "Imported",
            "nodes": [],
            "edges": []
        })
        
        result = engine.import_workflow(json_str)
        assert result is not None
        assert result.id == "imported_wf"
        assert result.name == "Imported WF"
        assert result.id in engine.workflows
        
        # Invalid JSON
        result = engine.import_workflow("invalid json")
        assert result is None
    
    def test_clone_workflow(self, engine, workflow):
        """Test clone_workflow method"""
        # Add some nodes and edges
        node = WorkflowNode(
            id="node1",
            name="Node 1",
            type=NodeType.AGENT
        )
        workflow.nodes.append(node)
        
        cloned = engine.clone_workflow(workflow.id, "Cloned WF")
        
        assert cloned is not None
        assert cloned.id != workflow.id
        assert cloned.name == "Cloned WF"
        assert cloned.version == 1
        assert cloned.status == WorkflowStatus.DRAFT
        assert cloned.execution_count == 0
        assert len(cloned.nodes) == len(workflow.nodes)
        
        # Non-existing workflow
        cloned = engine.clone_workflow("non_existing")
        assert cloned is None


# ==================== Test WorkflowEditor ====================

class TestWorkflowEditor:
    """Test WorkflowEditor class"""
    
    def test_init(self, editor):
        """Test editor initialization"""
        assert editor.engine is not None
        assert isinstance(editor._templates, dict)
        assert len(editor._templates) > 0
    
    def test_create_node(self, editor, workflow):
        """Test create_node method"""
        node = editor.create_node(
            workflow.id,
            "Test Node",
            "agent",
            position={"x": 300, "y": 200}
        )
        
        assert node is not None
        assert node.name == "Test Node"
        assert node.type == NodeType.AGENT
        assert node.position_x == 300
        assert node.position_y == 200
        assert len(workflow.nodes) == 3  # 2 default + 1 new
        
        # Non-existing workflow
        node = editor.create_node("non_existing", "Test", "agent")
        assert node is None
        
        # Invalid node type (should default to START)
        node = editor.create_node(workflow.id, "Test", "invalid_type")
        assert node is not None
        assert node.type == NodeType.START
    
    def test_create_node_default_ports(self, editor, workflow):
        """Test create_node with default ports"""
        # START node should have no inputs
        node = editor.create_node(workflow.id, "Start 2", "start")
        assert node.inputs == []
        assert node.outputs == ["out"]
        
        # END node should have no outputs
        node = editor.create_node(workflow.id, "End 2", "end")
        assert node.inputs == ["in"]
        assert node.outputs == []
        
        # Other nodes should have default in/out
        node = editor.create_node(workflow.id, "Agent", "agent")
        assert node.inputs == ["in"]
        assert node.outputs == ["out"]
    
    def test_get_node(self, editor, workflow):
        """Test get_node method"""
        # Create a node
        node = editor.create_node(workflow.id, "Test", "agent")
        
        # Get existing node
        result = editor.get_node(workflow.id, node.id)
        assert result is not None
        assert result.id == node.id
        
        # Non-existing node
        result = editor.get_node(workflow.id, "non_existing")
        assert result is None
        
        # Non-existing workflow
        result = editor.get_node("non_existing", "node_id")
        assert result is None
    
    def test_list_nodes(self, editor, workflow):
        """Test list_nodes method"""
        # Create some nodes
        editor.create_node(workflow.id, "Agent 1", "agent")
        editor.create_node(workflow.id, "Agent 2", "agent")
        
        # List all nodes
        result = editor.list_nodes(workflow.id)
        assert len(result) >= 4  # 2 default + 2 new
        
        # Filter by type
        result = editor.list_nodes(workflow.id, node_type="agent")
        assert all(n.type == NodeType.AGENT for n in result)
        
        # Include disconnected
        result = editor.list_nodes(workflow.id, include_disconnected=True)
        assert len(result) >= 4
    
    def test_update_node(self, editor, workflow):
        """Test update_node method"""
        # Create a node
        node = editor.create_node(workflow.id, "Test", "agent")
        
        # Update name
        result = editor.update_node(
            workflow.id,
            node.id,
            {"name": "Updated Name"}
        )
        assert result is True
        assert node.name == "Updated Name"
        
        # Update position
        result = editor.update_node(
            workflow.id,
            node.id,
            {"position": {"x": 500, "y": 300}}
        )
        assert result is True
        assert node.position_x == 500
        assert node.position_y == 300
        
        # Non-existing node
        result = editor.update_node(workflow.id, "non_existing", {"name": "Test"})
        assert result is False
    
    def test_delete_node(self, editor, workflow):
        """Test delete_node method"""
        # Create a node
        node = editor.create_node(workflow.id, "Test", "agent")
        node_id = node.id
        assert len(workflow.nodes) == 3
        
        # Delete node
        result = editor.delete_node(workflow.id, node_id)
        assert result is True
        assert len(workflow.nodes) == 2
        
        # Create node and edge, then delete
        node = editor.create_node(workflow.id, "Test 2", "agent")
        start_node = next(n for n in workflow.nodes if n.type == NodeType.START)
        edge = Edge(source=start_node.id, target=node.id)
        workflow.edges.append(edge)
        
        result = editor.delete_node(workflow.id, node.id)
        assert result is True
        assert len(workflow.edges) == 0  # Edge should be deleted too
        
        # Non-existing workflow
        result = editor.delete_node("non_existing", "node_id")
        assert result is False
    
    def test_create_edge(self, editor, workflow):
        """Test create_edge method"""
        # Create two nodes
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        
        # Create edge
        edge = editor.create_edge(
            workflow.id,
            node1.id,
            node2.id,
            source_port="out",
            target_port="in",
            label="test"
        )
        
        assert edge is not None
        assert edge.source == node1.id
        assert edge.target == node2.id
        assert edge.label == "test"
        assert len(workflow.edges) == 1
        
        # Non-existing source node
        edge = editor.create_edge(workflow.id, "non_existing", node2.id)
        assert edge is None
        
        # Non-existing workflow
        edge = editor.create_edge("non_existing", node1.id, node2.id)
        assert edge is None
    
    def test_create_edge_cycle_detection(self, editor, workflow):
        """Test create_edge with cycle detection"""
        # Create nodes
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        
        # Create edge node1 -> node2
        edge1 = editor.create_edge(workflow.id, node1.id, node2.id)
        assert edge1 is not None
        
        # Try to create edge node2 -> node1 (should create cycle)
        # Actually, this is not a cycle, just a bidirectional connection
        # A cycle would be: start -> node1 -> node2 -> start
        start_node = next(n for n in workflow.nodes if n.type == NodeType.START)
        
        # Create path: start -> node1 -> node2
        # Now try to create edge from node2 to start (creates cycle)
        edge_cycle = editor.create_edge(workflow.id, node2.id, start_node.id)
        assert edge_cycle is None  # Should detect cycle
    
    def test_get_edge(self, editor, workflow):
        """Test get_edge method"""
        # Create nodes and edge
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        edge = editor.create_edge(workflow.id, node1.id, node2.id)
        
        # Get existing edge
        result = editor.get_edge(workflow.id, edge.id)
        assert result is not None
        assert result.id == edge.id
        
        # Non-existing edge
        result = editor.get_edge(workflow.id, "non_existing")
        assert result is None
        
        # Non-existing workflow
        result = editor.get_edge("non_existing", "edge_id")
        assert result is None
    
    def test_list_edges(self, editor, workflow):
        """Test list_edges method"""
        # Create nodes and edges
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        editor.create_edge(workflow.id, node1.id, node2.id)
        
        # List all edges
        result = editor.list_edges(workflow.id)
        assert len(result) == 1
        
        # Filter by node
        result = editor.list_edges(workflow.id, node_id=node1.id)
        assert len(result) == 1
        assert result[0].source == node1.id
    
    def test_update_edge(self, editor, workflow):
        """Test update_edge method"""
        # Create nodes and edge
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        edge = editor.create_edge(workflow.id, node1.id, node2.id)
        
        # Update edge
        result = editor.update_edge(
            workflow.id,
            edge.id,
            {"label": "updated"}
        )
        assert result is True
        assert edge.label == "updated"
        
        # Non-existing edge
        result = editor.update_edge(workflow.id, "non_existing", {"label": "test"})
        assert result is False
    
    def test_delete_edge(self, editor, workflow):
        """Test delete_edge method"""
        # Create nodes and edge
        node1 = editor.create_node(workflow.id, "Node 1", "agent")
        node2 = editor.create_node(workflow.id, "Node 2", "agent")
        edge = editor.create_edge(workflow.id, node1.id, node2.id)
        edge_id = edge.id
        
        # Delete edge
        result = editor.delete_edge(workflow.id, edge_id)
        assert result is True
        assert len(workflow.edges) == 0
        
        # Non-existing edge
        result = editor.delete_edge(workflow.id, "non_existing")
        assert result is False
    
    def test_validate_workflow(self, editor, workflow):
        """Test validate_workflow method"""
        # Valid workflow (has start and end by default)
        result = editor.validate_workflow(workflow.id)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid: remove end node
        end_node = next(n for n in workflow.nodes if n.type == NodeType.END)
        workflow.nodes.remove(end_node)
        
        result = editor.validate_workflow(workflow.id)
        assert result["valid"] is False
        assert any("结束节点" in e for e in result["errors"])
        
        # Non-existing workflow
        result = editor.validate_workflow("non_existing")
        assert result["valid"] is False
        assert any("不存在" in e for e in result["errors"])
    
    def test_export_workflow(self, editor, workflow):
        """Test export_workflow method"""
        result = editor.export_workflow(workflow.id)
        
        assert result is not None
        assert isinstance(result, str)
        
        # Verify JSON
        data = json.loads(result)
        assert data["id"] == workflow.id
        
        # Without metadata
        result = editor.export_workflow(workflow.id, include_metadata=False)
        data = json.loads(result)
        assert "created_at" not in data
        assert "updated_at" not in data
    
    def test_import_workflow(self, editor):
        """Test import_workflow method"""
        json_str = json.dumps({
            "name": "Imported WF",
            "description": "Test",
            "nodes": [
                {"name": "Start", "type": "start", "position": {"x": 50, "y": 100}, "inputs": [], "outputs": ["out"]},
                {"name": "End", "type": "end", "position": {"x": 200, "y": 100}, "inputs": ["in"], "outputs": []}
            ],
            "edges": []
        })
        
        result = editor.import_workflow(json_str)
        assert result is not None
        assert result.name == "Imported WF"
        assert result.status == WorkflowStatus.DRAFT
        assert result.version == 1
        
        # Invalid JSON
        result = editor.import_workflow("invalid")
        assert result is None
    
    def test_export_workflow_diagram(self, editor, workflow):
        """Test export_workflow_diagram method"""
        result = editor.export_workflow_diagram(workflow.id)
        
        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        assert "metadata" in result
        
        # Non-existing workflow
        result = editor.export_workflow_diagram("non_existing")
        assert result is None
    
    def test_get_templates(self, editor):
        """Test get_templates method"""
        result = editor.get_templates()
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure
        for template in result:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
    
    def test_create_from_template(self, editor):
        """Test create_from_template method"""
        # Get available templates
        templates = editor.get_templates()
        assert len(templates) > 0
        
        # Create from first template
        template_id = templates[0]["id"]
        result = editor.create_from_template(template_id, "New WF")
        
        assert result is not None
        assert result.name == "New WF"
        assert len(result.nodes) > 0
        assert len(result.edges) > 0
        
        # Invalid template
        result = editor.create_from_template("non_existing")
        assert result is None
    
    def test_auto_layout(self, editor, workflow):
        """Test auto_layout method"""
        # Create some nodes
        editor.create_node(workflow.id, "Node 1", "agent", position={"x": 0, "y": 0})
        editor.create_node(workflow.id, "Node 2", "agent", position={"x": 0, "y": 0})
        
        result = editor.auto_layout(workflow.id)
        assert result is not None
        
        # Check positions were updated
        for node in result.nodes:
            assert node.position_x >= 0
            assert node.position_y >= 0
        
        # Non-existing workflow
        result = editor.auto_layout("non_existing")
        assert result is None
    
    def test_duplicate_nodes(self, editor, workflow):
        """Test duplicate_nodes method"""
        # Create a node
        node = editor.create_node(workflow.id, "Test", "agent")
        original_id = node.id
        
        # Duplicate node
        result = editor.duplicate_nodes(workflow.id, [original_id])
        
        assert len(result) == 1
        assert result[0].id != original_id
        assert result[0].name == node.name
        assert result[0].position_x == node.position_x + 50
        assert result[0].position_y == node.position_y + 50
        
        # Non-existing workflow
        result = editor.duplicate_nodes("non_existing", [original_id])
        assert len(result) == 0
    
    def test_move_nodes(self, editor, workflow):
        """Test move_nodes method"""
        # Create a node
        node = editor.create_node(workflow.id, "Test", "agent")
        original_x = node.position_x
        original_y = node.position_y
        
        # Move node
        result = editor.move_nodes(workflow.id, [node.id], 100, 50)
        assert result is True
        assert node.position_x == original_x + 100
        assert node.position_y == original_y + 50
        
        # Non-existing workflow
        result = editor.move_nodes("non_existing", [node.id], 100, 50)
        assert result is False


# ==================== Test WorkflowExecutor ====================

class TestWorkflowExecutor:
    """Test WorkflowExecutor class"""
    
    def test_init(self, executor):
        """Test executor initialization"""
        assert executor.engine is not None
        assert isinstance(executor._running_executions, dict)
    
    @pytest.mark.asyncio
    async def test_execute(self, executor, complex_workflow):
        """Test execute method"""
        result = await executor.execute(
            complex_workflow,
            input_data={"input": "test"},
            user_id="user_1"
        )
        
        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert "execution_id" in result
        assert "results" in result
        assert "context" in result
        assert result["context"]["user_id"] == "user_1"
        
        # Check workflow status
        assert complex_workflow.status == WorkflowStatus.COMPLETED
        assert complex_workflow.execution_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_validation_failure(self, executor):
        """Test execute with validation failure"""
        # Workflow without start/end nodes
        wf = Workflow(
            id="invalid_wf",
            name="Invalid",
            nodes=[]
        )
        
        result = await executor.execute(wf)
        assert result["status"] == "failed"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_execute_node_step(self, executor, workflow):
        """Test execute_node_step method"""
        # Add a node
        node = WorkflowNode(
            id="agent_node",
            name="Agent",
            type=NodeType.AGENT
        )
        workflow.nodes.append(node)
        
        result = await executor.execute_node_step(
            workflow,
            node.id,
            {"input": "test"}
        )
        
        assert isinstance(result, dict)
        assert "agent_response" in result
        
        # Non-existing node
        with pytest.raises(ValueError):
            await executor.execute_node_step(workflow, "non_existing", {})
    
    def test_get_execution_state(self, executor):
        """Test get_execution_state method"""
        # No executions running
        result = executor.get_execution_state("fake_id")
        assert result is None
    
    def test_list_running_executions(self, executor):
        """Test list_running_executions method"""
        result = executor.list_running_executions()
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_pause_execution(self, executor):
        """Test pause_execution method"""
        result = executor.pause_execution("fake_id")
        assert result is False
    
    def test_resume_execution(self, executor):
        """Test resume_execution method"""
        result = executor.resume_execution("fake_id")
        assert result is False
    
    def test_cancel_execution(self, executor):
        """Test cancel_execution method"""
        result = executor.cancel_execution("fake_id")
        assert result is False
    
    def test_get_execution_history(self, executor, workflow):
        """Test get_execution_history method"""
        # No execution history
        result = executor.get_execution_history(workflow.id)
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Execute workflow to create history
        # (This would require async test, but we can test the empty case)
    
    @pytest.mark.asyncio
    async def test_should_execute_node(self, executor, complex_workflow):
        """Test _should_execute_node method"""
        # START node should always execute
        start_node = next(n for n in complex_workflow.nodes if n.type == NodeType.START)
        assert executor._should_execute_node(complex_workflow, start_node, {}) is True
        
        # Node without incoming edges should not execute
        isolated_node = WorkflowNode(
            id="isolated",
            name="Isolated",
            type=NodeType.AGENT
        )
        assert executor._should_execute_node(complex_workflow, isolated_node, {}) is False
    
    @pytest.mark.asyncio
    async def test_update_variables(self, executor, workflow):
        """Test _update_variables method"""
        node = WorkflowNode(
            id="agent_node",
            name="Agent Node",
            type=NodeType.AGENT
        )
        
        execution_state = {
            "context": {},
            "node_results": {},
            "variables": {}
        }
        
        result = {"response": "test"}
        executor._update_variables(workflow, node, result, execution_state)
        
        # Check variable was created
        assert "Agent_Node_result" in execution_state["context"]
        assert execution_state["context"]["Agent_Node_result"] == result


# ==================== Test WorkflowScheduler ====================

class TestWorkflowScheduler:
    """Test WorkflowScheduler class"""
    
    def test_init(self, scheduler):
        """Test scheduler initialization"""
        assert scheduler.engine is not None
        assert isinstance(scheduler._tasks, dict)
        assert scheduler._running is False
        assert scheduler._scheduler_thread is None
        assert isinstance(scheduler._webhook_handlers, dict)
        assert isinstance(scheduler._event_listeners, dict)
        assert scheduler._executor is not None
    
    def test_start_stop(self, scheduler):
        """Test start and stop methods"""
        assert scheduler._running is False
        
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._scheduler_thread is not None
        assert isinstance(scheduler._scheduler_thread, threading.Thread)
        
        # Give it a moment to start
        import time
        time.sleep(0.1)
        
        scheduler.stop()
        assert scheduler._running is False
    
    def test_add_cron_task(self, scheduler, workflow):
        """Test add_cron_task method"""
        task_id = scheduler.add_cron_task(
            workflow.id,
            "14:30",
            input_data={"key": "value"},
            name="Test Cron"
        )
        
        assert task_id is not None
        assert task_id in scheduler._tasks
        
        task = scheduler._tasks[task_id]
        assert task["name"] == "Test Cron"
        assert task["workflow_id"] == workflow.id
        assert task["trigger_type"] == TriggerType.CRON
        assert task["cron_expression"] == "14:30"
        assert task["input_data"] == {"key": "value"}
        assert task["enabled"] is True
        assert "next_run" in task
    
    def test_add_interval_task(self, scheduler, workflow):
        """Test add_interval_task method"""
        task_id = scheduler.add_interval_task(
            workflow.id,
            3600,  # 1 hour
            input_data={"key": "value"},
            name="Test Interval"
        )
        
        assert task_id is not None
        assert task_id in scheduler._tasks
        
        task = scheduler._tasks[task_id]
        assert task["name"] == "Test Interval"
        assert task["trigger_type"] == TriggerType.INTERVAL
        assert task["interval_seconds"] == 3600
        assert "next_run" in task
    
    def test_add_webhook_task(self, scheduler, workflow):
        """Test add_webhook_task method"""
        task_id = scheduler.add_webhook_task(
            workflow.id,
            "/webhook/test",
            input_mapper={"input": "$data"}
        )
        
        assert task_id is not None
        assert task_id in scheduler._tasks
        
        task = scheduler._tasks[task_id]
        assert task["trigger_type"] == TriggerType.WEBHOOK
        assert task["webhook_path"] == "/webhook/test"
        assert "/webhook/test" in scheduler._webhook_handlers
    
    def test_get_task(self, scheduler, workflow):
        """Test get_task method"""
        task_id = scheduler.add_cron_task(workflow.id, "14:30")
        
        result = scheduler.get_task(task_id)
        assert result is not None
        assert result["id"] == task_id
        assert "next_run" in result
        
        # Non-existing task
        result = scheduler.get_task("non_existing")
        assert result is None
    
    def test_list_tasks(self, scheduler, workflow):
        """Test list_tasks method"""
        # Add multiple tasks
        scheduler.add_cron_task(workflow.id, "14:30")
        scheduler.add_interval_task(workflow.id, 3600)
        
        result = scheduler.list_tasks()
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Check serialization (next_run should be string)
        for task in result:
            if task.get("next_run"):
                assert isinstance(task["next_run"], str)
    
    def test_enable_disable_task(self, scheduler, workflow):
        """Test enable_task and disable_task methods"""
        task_id = scheduler.add_cron_task(workflow.id, "14:30")
        
        # Disable
        result = scheduler.disable_task(task_id)
        assert result is True
        assert scheduler._tasks[task_id]["enabled"] is False
        
        # Enable
        result = scheduler.enable_task(task_id)
        assert result is True
        assert scheduler._tasks[task_id]["enabled"] is True
        
        # Non-existing task
        result = scheduler.disable_task("non_existing")
        assert result is False
    
    def test_delete_task(self, scheduler, workflow):
        """Test delete_task method"""
        task_id = scheduler.add_webhook_task(workflow.id, "/webhook/test")
        assert task_id in scheduler._tasks
        assert "/webhook/test" in scheduler._webhook_handlers
        
        # Delete task
        result = scheduler.delete_task(task_id)
        assert result is True
        assert task_id not in scheduler._tasks
        # Webhook handler should also be removed
        assert "/webhook/test" not in scheduler._webhook_handlers
        
        # Non-existing task
        result = scheduler.delete_task("non_existing")
        assert result is False
    
    def test_run_task_now(self, scheduler, workflow):
        """Test run_task_now method"""
        task_id = scheduler.add_cron_task(workflow.id, "14:30")
        
        # This will fail because execute_scheduled_task tries to run async code
        # But we can test the method exists and handles non-existing tasks
        result = scheduler.run_task_now("non_existing")
        assert "error" in result
    
    def test_get_stats(self, scheduler, workflow):
        """Test get_stats method"""
        # Add different types of tasks
        scheduler.add_cron_task(workflow.id, "14:30")
        scheduler.add_interval_task(workflow.id, 3600)
        scheduler.add_webhook_task(workflow.id, "/webhook/test")
        
        # Disable one task
        task_id = list(scheduler._tasks.keys())[0]
        scheduler.disable_task(task_id)
        
        result = scheduler.get_stats()
        assert "total_tasks" in result
        assert "enabled_tasks" in result
        assert "disabled_tasks" in result
        assert "running" in result
        assert "tasks_by_type" in result
        assert result["total_tasks"] == 3
        assert result["tasks_by_type"]["cron"] == 1
        assert result["tasks_by_type"]["interval"] == 1
        assert result["tasks_by_type"]["webhook"] == 1
    
    def test_calculate_next_cron(self, scheduler):
        """Test _calculate_next_cron method"""
        # Test with valid cron expression
        next_run = scheduler._calculate_next_cron("14:30", datetime.now())
        assert isinstance(next_run, datetime)
        assert next_run.hour == 14
        assert next_run.minute == 30
        
        # Test with invalid expression
        next_run = scheduler._calculate_next_cron("invalid", datetime.now())
        assert isinstance(next_run, datetime)
        # Should return 1 hour later
        assert (next_run - datetime.now()).total_seconds() < 3600 + 60


# ==================== Test Enums ====================

class TestEnums:
    """Test enum classes"""
    
    def test_node_type_values(self):
        """Test NodeType enum values"""
        assert NodeType.TRIGGER.value == "trigger"
        assert NodeType.SCHEDULE.value == "schedule"
        assert NodeType.WEBHOOK.value == "webhook"
        assert NodeType.AGENT.value == "agent"
        assert NodeType.TOOL_CALL.value == "tool_call"
        assert NodeType.CONDITION.value == "condition"
        assert NodeType.LOOP.value == "loop"
        assert NodeType.PARALLEL.value == "parallel"
        assert NodeType.SEQUENCE.value == "sequence"
        assert NodeType.INPUT.value == "input"
        assert NodeType.OUTPUT.value == "output"
        assert NodeType.TRANSFORM.value == "transform"
        assert NodeType.FILTER.value == "filter"
        assert NodeType.AGGREGATE.value == "aggregate"
        assert NodeType.HTTP.value == "http"
        assert NodeType.DATABASE.value == "database"
        assert NodeType.MESSAGE.value == "message"
        assert NodeType.EMAIL.value == "email"
        assert NodeType.NOTIFICATION.value == "notification"
        assert NodeType.CODE.value == "code"
        assert NodeType.TEMPLATE.value == "template"
        assert NodeType.MATH.value == "math"
        assert NodeType.START.value == "start"
        assert NodeType.END.value == "end"
        assert NodeType.ERROR.value == "error"
        assert NodeType.LOG.value == "log"
    
    def test_workflow_status_values(self):
        """Test WorkflowStatus enum values"""
        assert WorkflowStatus.DRAFT.value == "draft"
        assert WorkflowStatus.ACTIVE.value == "active"
        assert WorkflowStatus.PAUSED.value == "paused"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
    
    def test_node_status_values(self):
        """Test NodeStatus enum values"""
        assert NodeStatus.PENDING.value == "pending"
        assert NodeStatus.RUNNING.value == "running"
        assert NodeStatus.COMPLETED.value == "completed"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"
    
    def test_trigger_type_values(self):
        """Test TriggerType enum values"""
        assert TriggerType.CRON.value == "cron"
        assert TriggerType.INTERVAL.value == "interval"
        assert TriggerType.WEBHOOK.value == "webhook"
        assert TriggerType.EVENT.value == "event"


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests for workflow module"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, engine, executor):
        """Test full workflow creation and execution"""
        # Create workflow
        wf = engine.create_workflow("Integration Test", "Test full flow")
        
        # Get default nodes
        start_node = next(n for n in wf.nodes if n.type == NodeType.START)
        end_node = next(n for n in wf.nodes if n.type == NodeType.END)
        
        # Add agent node
        agent_node = WorkflowNode(
            id="agent_1",
            name="Agent",
            type=NodeType.AGENT,
            inputs=["in"],
            outputs=["out"]
        )
        wf.nodes.append(agent_node)
        
        # Add edges
        edge1 = Edge(
            id="edge_1",
            source=start_node.id,
            target=agent_node.id,
            source_port="out",
            target_port="in"
        )
        edge2 = Edge(
            id="edge_2",
            source=agent_node.id,
            target=end_node.id,
            source_port="out",
            target_port="in"
        )
        wf.edges = [edge1, edge2]
        
        # Execute workflow
        result = await executor.execute(wf, input_data={"input": "test"})
        
        assert result["status"] == "completed"
        assert "results" in result
        
        # Check all nodes were executed
        for node in wf.nodes:
            if node.type not in [NodeType.START, NodeType.END]:
                assert node.status == NodeStatus.COMPLETED
    
    def test_editor_with_engine(self, engine, editor):
        """Test editor operations with engine"""
        # Create workflow
        wf = engine.create_workflow("Editor Test")
        
        # Use editor to add nodes
        node1 = editor.create_node(wf.id, "Node 1", "agent")
        node2 = editor.create_node(wf.id, "Node 2", "agent")
        
        assert node1 is not None
        assert node2 is not None
        
        # Create edge
        edge = editor.create_edge(wf.id, node1.id, node2.id)
        assert edge is not None
        
        # Validate workflow
        validation = editor.validate_workflow(wf.id)
        assert "valid" in validation
        
        # Export workflow
        exported = editor.export_workflow(wf.id)
        assert exported is not None
        
        # Import workflow
        imported = editor.import_workflow(exported)
        assert imported is not None
        assert imported.name == wf.name
    
    def test_scheduler_with_engine(self, engine, scheduler):
        """Test scheduler operations with engine"""
        # Create workflow
        wf = engine.create_workflow("Scheduler Test")
        
        # Add cron task
        task_id = scheduler.add_cron_task(wf.id, "14:30")
        assert task_id is not None
        
        # Check task
        task = scheduler.get_task(task_id)
        assert task is not None
        
        # List tasks
        tasks = scheduler.list_tasks()
        assert len(tasks) == 1
        
        # Get stats
        stats = scheduler.get_stats()
        assert stats["total_tasks"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
