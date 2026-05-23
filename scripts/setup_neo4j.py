#!/usr/bin/env python3
"""
Neo4j Database Setup Script for SerpentAI

This script initializes the Neo4j database with required constraints,
indexes, and initial nodes for the SerpentAI project.

Usage:
    python scripts/setup_neo4j.py [--config config.yaml] [--dry-run]

Features:
    - Create constraints for data integrity
    - Create indexes for performance optimization
    - Initialize base nodes (Agent, Skill, Tool)
    - Verify connection and configuration
    - Support reading from config.yaml or environment variables
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Try to import neo4j driver
try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("neo4j driver not installed. Install with: pip install neo4j")


# Try to import yaml for config file support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Install with: pip install pyyaml")


class Neo4jSetup:
    """
    Neo4j database setup and initialization class.
    
    Handles:
    - Connection verification
    - Constraint creation
    - Index creation
    - Initial data seeding
    """
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j setup with connection parameters.
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Username for authentication
            password: Password for authentication
            database: Database name (default: neo4j)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not NEO4J_AVAILABLE:
            logger.error("Neo4j driver not available. Cannot connect.")
            return False
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            self.driver.verify_connectivity()
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed.")
    
    def verify_configuration(self) -> Dict[str, Any]:
        """
        Verify Neo4j configuration and return database info.
        
        Returns:
            dict: Database information and configuration status
        """
        if not self.driver:
            logger.error("Not connected to Neo4j. Call connect() first.")
            return {}
        
        info = {}
        try:
            with self.driver.session(database=self.database) as session:
                # Get Neo4j version
                result = session.run("CALL dbms.components() YIELD name, versions")
                for record in result:
                    if record["name"] == "Neo4j Kernel":
                        info["version"] = record["versions"][0]
                
                # Get database name
                result = session.run("CALL db.info()")
                for record in result:
                    info["database"] = record.get("name", self.database)
                
                # Get node counts
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                info["node_count"] = result.single()["node_count"]
                
                logger.info(f"Neo4j Version: {info.get('version', 'Unknown')}")
                logger.info(f"Database: {info.get('database', self.database)}")
                logger.info(f"Existing Nodes: {info.get('node_count', 0)}")
                
        except Exception as e:
            logger.error(f"Failed to verify configuration: {e}")
        
        return info
    
    def create_constraints(self) -> List[str]:
        """
        Create necessary constraints for data integrity.
        
        Constraints ensure uniqueness and existence of critical properties.
        
        Returns:
            list: List of created constraint names
        """
        if not self.driver:
            logger.error("Not connected to Neo4j.")
            return []
        
        created = []
        constraints = [
            # Agent constraints
            {
                "name": "agent_id_unique",
                "query": "CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE"
            },
            {
                "name": "agent_name_unique",
                "query": "CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE"
            },
            # Skill constraints
            {
                "name": "skill_id_unique",
                "query": "CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE"
            },
            # Tool constraints
            {
                "name": "tool_name_unique",
                "query": "CREATE CONSTRAINT tool_name_unique IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE"
            },
            # Memory constraints
            {
                "name": "memory_id_unique",
                "query": "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE"
            },
            # Session constraints
            {
                "name": "session_id_unique",
                "query": "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE"
            },
        ]
        
        with self.driver.session(database=self.database) as session:
            for constraint in constraints:
                try:
                    logger.info(f"Creating constraint: {constraint['name']}")
                    session.run(constraint["query"])
                    created.append(constraint["name"])
                    logger.info(f"  -> Success")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"  -> Already exists")
                        created.append(constraint["name"])
                    else:
                        logger.error(f"  -> Failed: {e}")
        
        logger.info(f"Created {len(created)} constraints")
        return created
    
    def create_indexes(self) -> List[str]:
        """
        Create indexes for performance optimization.
        
        Indexes speed up queries on frequently accessed properties.
        
        Returns:
            list: List of created index names
        """
        if not self.driver:
            logger.error("Not connected to Neo4j.")
            return []
        
        created = []
        indexes = [
            # Agent indexes
            {
                "name": "agent_mode_idx",
                "query": "CREATE INDEX agent_mode_idx IF NOT EXISTS FOR (a:Agent) ON (a.mode)"
            },
            {
                "name": "agent_status_idx",
                "query": "CREATE INDEX agent_status_idx IF NOT EXISTS FOR (a:Agent) ON (a.status)"
            },
            # Skill indexes
            {
                "name": "skill_category_idx",
                "query": "CREATE INDEX skill_category_idx IF NOT EXISTS FOR (s:Skill) ON (s.category)"
            },
            # Tool indexes
            {
                "name": "tool_type_idx",
                "query": "CREATE INDEX tool_type_idx IF NOT EXISTS FOR (t:Tool) ON (t.type)"
            },
            # Memory indexes
            {
                "name": "memory_session_idx",
                "query": "CREATE INDEX memory_session_idx IF NOT EXISTS FOR (m:Memory) ON (m.session_id)"
            },
            {
                "name": "memory_timestamp_idx",
                "query": "CREATE INDEX memory_timestamp_idx IF NOT EXISTS FOR (m:Memory) ON (m.timestamp)"
            },
            # Session indexes
            {
                "name": "session_updated_idx",
                "query": "CREATE INDEX session_updated_idx IF NOT EXISTS FOR (s:Session) ON (s.updated_at)"
            },
        ]
        
        with self.driver.session(database=self.database) as session:
            for index in indexes:
                try:
                    logger.info(f"Creating index: {index['name']}")
                    session.run(index["query"])
                    created.append(index["name"])
                    logger.info(f"  -> Success")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"  -> Already exists")
                        created.append(index["name"])
                    else:
                        logger.error(f"  -> Failed: {e}")
        
        logger.info(f"Created {len(created)} indexes")
        return created
    
    def create_initial_nodes(self) -> Dict[str, int]:
        """
        Create initial nodes for the knowledge graph.
        
        Creates base nodes for:
        - Agent (default Serpent agent)
        - Skills (builtin skills)
        - Tools (builtin tools)
        
        Returns:
            dict: Count of created nodes by type
        """
        if not self.driver:
            logger.error("Not connected to Neo4j.")
            return {}
        
        counts = {
            "agents": 0,
            "skills": 0,
            "tools": 0,
            "relations": 0
        }
        
        with self.driver.session(database=self.database) as session:
            # Create default Agent node
            try:
                result = session.run("""
                    MERGE (a:Agent {id: 'serpent_default'})
                    ON CREATE SET 
                        a.name = 'Serpent',
                        a.model = 'gpt-4o',
                        a.mode = 'auto',
                        a.status = 'active',
                        a.created_at = datetime(),
                        a.updated_at = datetime()
                    RETURN a
                """)
                if result.single():
                    counts["agents"] += 1
                    logger.info("Created/Merged default Agent node")
            except Exception as e:
                logger.error(f"Failed to create Agent node: {e}")
            
            # Create builtin Skill nodes
            builtin_skills = [
                {"id": "code_assistant", "name": "Code Assistant", "category": "coding"},
                {"id": "data_analyst", "name": "Data Analyst", "category": "analysis"},
                {"id": "web_researcher", "name": "Web Researcher", "category": "research"},
                {"id": "writer", "name": "Writer", "category": "writing"},
            ]
            
            for skill in builtin_skills:
                try:
                    result = session.run("""
                        MERGE (s:Skill {id: $id})
                        ON CREATE SET 
                            s.name = $name,
                            s.category = $category,
                            s.builtin = true,
                            s.enabled = true,
                            s.created_at = datetime()
                        RETURN s
                    """, id=skill["id"], name=skill["name"], category=skill["category"])
                    if result.single():
                        counts["skills"] += 1
                        logger.info(f"Created/Merged Skill node: {skill['name']}")
                except Exception as e:
                    logger.error(f"Failed to create Skill node {skill['id']}: {e}")
            
            # Create builtin Tool nodes
            builtin_tools = [
                {"name": "fs_read", "type": "file", "description": "Read file content"},
                {"name": "fs_write", "type": "file", "description": "Write file content"},
                {"name": "fs_list", "type": "file", "description": "List directory contents"},
                {"name": "shell_exec", "type": "system", "description": "Execute shell command"},
                {"name": "web_search", "type": "web", "description": "Search the web"},
                {"name": "web_fetch", "type": "web", "description": "Fetch web page content"},
            ]
            
            for tool in builtin_tools:
                try:
                    result = session.run("""
                        MERGE (t:Tool {name: $name})
                        ON CREATE SET 
                            t.type = $type,
                            t.description = $description,
                            t.builtin = true,
                            t.enabled = true,
                            t.created_at = datetime()
                        RETURN t
                    """, name=tool["name"], type=tool["type"], description=tool["description"])
                    if result.single():
                        counts["tools"] += 1
                        logger.info(f"Created/Merged Tool node: {tool['name']}")
                except Exception as e:
                    logger.error(f"Failed to create Tool node {tool['name']}: {e}")
            
            # Create relationships (Agent -> Skill, Agent -> Tool)
            try:
                result = session.run("""
                    MATCH (a:Agent {id: 'serpent_default'})
                    MATCH (s:Skill)
                    MERGE (a)-[r:HAS_SKILL]->(s)
                    RETURN count(r) as rel_count
                """)
                record = result.single()
                if record:
                    counts["relations"] += record["rel_count"]
                    logger.info(f"Created {record['rel_count']} Agent-Skill relationships")
            except Exception as e:
                logger.error(f"Failed to create Agent-Skill relationships: {e}")
        
        logger.info(f"Initial nodes creation complete: {counts}")
        return counts
    
    def setup_all(self, dry_run: bool = False) -> bool:
        """
        Run complete setup process.
        
        Args:
            dry_run: If True, only print what would be done without executing
        
        Returns:
            bool: True if all steps successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Neo4j Setup for SerpentAI")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("")
            logger.info("Would create:")
            logger.info("  - 6 constraints (Agent, Skill, Tool, Memory, Session)")
            logger.info("  - 7 indexes (for performance optimization)")
            logger.info("  - Initial nodes (Agent, Skills, Tools)")
            logger.info("  - Relationships (Agent -> Skills)")
            return True
        
        # Step 1: Connect
        logger.info("\nStep 1: Connecting to Neo4j...")
        if not self.connect():
            return False
        
        # Step 2: Verify configuration
        logger.info("\nStep 2: Verifying configuration...")
        info = self.verify_configuration()
        if not info:
            logger.warning("Could not verify configuration, but continuing...")
        
        # Step 3: Create constraints
        logger.info("\nStep 3: Creating constraints...")
        constraints = self.create_constraints()
        logger.info(f"Processed {len(constraints)} constraints")
        
        # Step 4: Create indexes
        logger.info("\nStep 4: Creating indexes...")
        indexes = self.create_indexes()
        logger.info(f"Processed {len(indexes)} indexes")
        
        # Step 5: Create initial nodes
        logger.info("\nStep 5: Creating initial nodes...")
        counts = self.create_initial_nodes()
        logger.info(f"Created nodes: {counts}")
        
        # Step 6: Final verification
        logger.info("\nStep 6: Final verification...")
        final_info = self.verify_configuration()
        logger.info(f"Total nodes in database: {final_info.get('node_count', 0)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Setup complete!")
        logger.info("=" * 60)
        
        self.close()
        return True


def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
    """
    Load Neo4j configuration from YAML file.
    
    Expected YAML structure:
        neo4j:
            uri: bolt://localhost:7687
            user: neo4j
            password: your_password
            database: neo4j
    
    Args:
        config_path: Path to the YAML configuration file
    
    Returns:
        dict: Configuration dictionary
    """
    if not YAML_AVAILABLE:
        logger.error("PyYAML not installed. Cannot load config from YAML.")
        return {}
    
    config_path = Path(config_path)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Navigate to neo4j config
        neo4j_config = config.get("neo4j", {})
        if not neo4j_config:
            logger.warning("No 'neo4j' section found in config file")
        
        logger.info(f"Loaded configuration from {config_path}")
        return neo4j_config
    
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}


def load_config_from_env() -> Dict[str, Any]:
    """
    Load Neo4j configuration from environment variables.
    
    Expected environment variables:
        NEO4J_URI
        NEO4J_USER
        NEO4J_PASSWORD
        NEO4J_DATABASE (optional, default: neo4j)
    
    Returns:
        dict: Configuration dictionary
    """
    config = {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", ""),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }
    
    logger.info("Loaded configuration from environment variables")
    return config


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="Setup Neo4j database for SerpentAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run setup with default config (reads from environment)
  python scripts/setup_neo4j.py
  
  # Run setup with custom config file
  python scripts/setup_neo4j.py --config config.yaml
  
  # Dry run (print what would be done)
  python scripts/setup_neo4j.py --dry-run
  
  # Verbose output
  python scripts/setup_neo4j.py --verbose
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to YAML configuration file (default: config/config.yaml)"
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Print what would be done without making changes"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--uri",
        type=str,
        help="Neo4j URI (overrides config file and environment)"
    )
    
    parser.add_argument(
        "--user",
        type=str,
        help="Neo4j username (overrides config file and environment)"
    )
    
    parser.add_argument(
        "--password",
        type=str,
        help="Neo4j password (overrides config file and environment)"
    )
    
    parser.add_argument(
        "--database",
        type=str,
        help="Neo4j database name (overrides config file and environment)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = {}
    
    if args.config:
        # Load from specified config file
        config = load_config_from_yaml(args.config)
    else:
        # Try default config path
        default_config = Path("config/config.yaml")
        if default_config.exists():
            config = load_config_from_yaml(default_config)
        else:
            logger.info("No config file found, using environment variables")
    
    # Environment variables override config file
    env_config = load_config_from_env()
    config = {**config, **env_config}  # Env vars take precedence
    
    # Command line arguments override everything
    if args.uri:
        config["uri"] = args.uri
    if args.user:
        config["user"] = args.user
    if args.password:
        config["password"] = args.password
    if args.database:
        config["database"] = args.database
    
    # Validate required configuration
    if not config.get("password"):
        logger.error("Neo4j password not provided. Set NEO4J_PASSWORD environment variable or use --password")
        sys.exit(1)
    
    # Create setup instance
    setup = Neo4jSetup(
        uri=config.get("uri", "bolt://localhost:7687"),
        user=config.get("user", "neo4j"),
        password=config["password"],
        database=config.get("database", "neo4j")
    )
    
    # Run setup
    success = setup.setup_all(dry_run=args.dry_run)
    
    if success:
        logger.info("Setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
