"""
Database Migration Tests

Tests that all 19 migrations run successfully and can be rolled back.
"""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text, inspect
import os


@pytest.mark.integration
class TestDatabaseMigrations:
    """Test database migrations."""
    
    def test_migrations_run_successfully(self, engine):
        """
        Test that all migrations run without errors.
        """
        # Get alembic config
        alembic_ini = os.path.join(os.path.dirname(__file__), "../../../alembic.ini")
        alembic_cfg = Config(alembic_ini)
        
        # Set database URL
        db_url = str(engine.url)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        
        # Verify we're at latest revision
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT version_num FROM alembic_version
            """))
            version = result.scalar()
            assert version is not None
    
    def test_all_expected_tables_exist(self, engine):
        """
        Test that all expected tables from migrations exist.
        """
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "alembic_version",
            "api_keys",
            "agent_models",
            "specialists",
            "projects",
            "tasks",
            "gates",
            "prompts",
            "prompt_versions",
            "prompt_ab_tests",
            "collaboration_requests",
            "collaboration_responses",
            "collaboration_loops",
            "knowledge_staging",
            "token_usage",
            "llm_pricing"
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
    
    def test_critical_indexes_exist(self, engine):
        """
        Test that critical indexes exist for performance.
        """
        inspector = inspect(engine)
        
        # Check gates indexes
        gates_indexes = inspector.get_indexes("gates")
        index_names = [idx["name"] for idx in gates_indexes]
        assert "idx_gates_status" in index_names
        assert "idx_gates_project" in index_names
        
        # Check knowledge_staging indexes
        knowledge_indexes = inspector.get_indexes("knowledge_staging")
        index_names = [idx["name"] for idx in knowledge_indexes]
        assert "idx_knowledge_staging_embedded" in index_names
        assert "idx_knowledge_staging_type" in index_names
    
    def test_foreign_key_constraints(self, engine):
        """
        Test that foreign key relationships are properly defined.
        """
        inspector = inspect(engine)
        
        # Check collaboration_responses has FK to collaboration_requests
        fks = inspector.get_foreign_keys("collaboration_responses")
        fk_tables = [fk["referred_table"] for fk in fks]
        assert "collaboration_requests" in fk_tables
        
        # Check prompt_versions has FK to prompts
        fks = inspector.get_foreign_keys("prompt_versions")
        fk_tables = [fk["referred_table"] for fk in fks]
        assert "prompts" in fk_tables
    
    def test_migration_rollback(self, engine):
        """
        Test that migrations can be rolled back (downgrade).
        """
        alembic_ini = os.path.join(os.path.dirname(__file__), "../../../alembic.ini")
        alembic_cfg = Config(alembic_ini)
        
        db_url = str(engine.url)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Get current version
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
        
        # Downgrade one step
        command.downgrade(alembic_cfg, "-1")
        
        # Verify version changed
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            new_version = result.scalar()
            assert new_version != current_version
        
        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")
        
        # Verify we're back at latest
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            final_version = result.scalar()
            assert final_version == current_version


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
