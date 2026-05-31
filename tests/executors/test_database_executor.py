"""
Tests for DatabaseExecutor implementation.
"""

import sqlite3
import tempfile
import shutil
from pathlib import Path
import pytest

from exoarmur.executors.database_executor import (
    DatabaseExecutor,
    DatabaseRollbackPlan,
    DatabaseRollbackResult
)
from exoarmur.kernel.boundary import (
    ActionIntent,
    ActionClass,
    ValidationResult
)
from exoarmur.kernel.clock import DeterministicClock, set_clock


@pytest.fixture
def temp_db_dir():
    """Create temporary directory for test databases."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_db_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def executor(temp_db_dir):
    """Create DatabaseExecutor instance."""
    return DatabaseExecutor(authorized_db_dir=str(temp_db_dir))


@pytest.fixture
def deterministic_clock():
    """Set up deterministic clock for testing."""
    clock = DeterministicClock()
    set_clock(clock)
    yield clock
    # Reset to SystemClock instead of None
    from exoarmur.kernel.clock import SystemClock
    set_clock(SystemClock())


class TestDatabaseExecutorBasic:
    """Test basic DatabaseExecutor functionality."""
    
    def test_executor_initialization(self, executor, deterministic_clock):
        """Test executor initializes correctly."""
        assert executor.name() == "DatabaseExecutor"
        assert "db_select" in executor.capabilities()["capabilities"]
        assert "db_insert" in executor.capabilities()["capabilities"]
        assert "db_update" in executor.capabilities()["capabilities"]
        assert "db_delete" in executor.capabilities()["capabilities"]
    
    def test_validate_target_authorized_db(self, executor, temp_db_dir, deterministic_clock):
        """Test target validation for authorized database path."""
        db_path = temp_db_dir / "test.db"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={"operation": "select", "table": "test_table"},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        result = executor.validate_target(intent)
        assert result.result == ValidationResult.VALID
        assert result.evidence["is_authorized"] is True
    
    def test_validate_target_unauthorized_extension(self, executor, temp_db_dir, deterministic_clock):
        """Test target validation for unauthorized file extension."""
        txt_path = temp_db_dir / "test.txt"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(txt_path),
            parameters={"operation": "select", "table": "test_table"},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        result = executor.validate_target(intent)
        assert result.result == ValidationResult.VIOLATES_CONSTRAINTS
        assert "must be a .db file" in result.evidence["reason"]
    
    def test_validate_target_outside_authorized_dir(self, executor, deterministic_clock):
        """Test target validation for path outside authorized directory."""
        outside_path = Path("/etc/passwd")
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(outside_path),
            parameters={"operation": "select", "table": "test_table"},
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        result = executor.validate_target(intent)
        assert result.result == ValidationResult.VIOLATES_CONSTRAINTS
        assert "outside authorized directory" in result.evidence["reason"]


class TestDatabaseExecutorOperations:
    """Test database operations."""
    
    def test_create_table(self, executor, temp_db_dir, deterministic_clock):
        """Test CREATE TABLE operation."""
        db_path = temp_db_dir / "test.db"
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "table": "users",
                "payload": {
                    "schema": {
                        "id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "email": "TEXT"
                    }
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["table_created"] == "users"
        
        # Verify table was created
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        conn.close()
    
    def test_insert_row(self, executor, temp_db_dir, deterministic_clock):
        """Test INSERT operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table first
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "insert",
                "table": "users",
                "payload": {
                    "data": {"name": "Alice", "email": "alice@example.com"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["row_id"] > 0
        
        # Verify row was inserted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = 'Alice'")
        row = cursor.fetchone()
        assert row is not None
        conn.close()
    
    def test_select_rows(self, executor, temp_db_dir, deterministic_clock):
        """Test SELECT operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table and insert data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "select",
                "table": "users",
                "payload": {"limit": 10}
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["count"] == 2
        assert len(result.output["result"]["rows"]) == 2
    
    def test_update_row(self, executor, temp_db_dir, deterministic_clock):
        """Test UPDATE operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table and insert data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "update",
                "table": "users",
                "payload": {
                    "data": {"email": "alice_new@example.com"},
                    "where": {"name": "Alice"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["rows_affected"] == 1
        
        # Verify row was updated
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE name = 'Alice'")
        row = cursor.fetchone()
        assert row[0] == "alice_new@example.com"
        conn.close()
    
    def test_delete_row(self, executor, temp_db_dir, deterministic_clock):
        """Test DELETE operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table and insert data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "delete",
                "table": "users",
                "payload": {"where": {"name": "Alice"}}
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["rows_affected"] == 1
        
        # Verify row was deleted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE name = 'Alice'")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()
    
    def test_drop_table(self, executor, temp_db_dir, deterministic_clock):
        """Test DROP TABLE operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "drop_table",
                "table": "users"
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        assert result.output["result"]["table_dropped"] == "users"
        
        # Verify table was dropped
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is None
        conn.close()


class TestDatabaseExecutorRollback:
    """Test rollback functionality."""
    
    def test_update_rollback(self, executor, temp_db_dir, deterministic_clock):
        """Test rollback after UPDATE operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table and insert data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "update",
                "table": "users",
                "payload": {
                    "data": {"email": "alice_new@example.com"},
                    "where": {"name": "Alice"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        # Execute update
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        
        # Get rollback plan
        rollback_plan_id = result.output.get("rollback_plan_id")
        assert rollback_plan_id is not None
        
        rollback_plan = executor._rollback_plans[rollback_plan_id]
        
        # Execute rollback
        rollback_result = executor.rollback(rollback_plan)
        assert rollback_result.success is True
        
        # Verify original state restored
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE name = 'Alice'")
        row = cursor.fetchone()
        assert row[0] == "alice@example.com"  # Original email
        conn.close()
    
    def test_delete_rollback(self, executor, temp_db_dir, deterministic_clock):
        """Test rollback after DELETE operation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table and insert data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        conn.commit()
        conn.close()
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "delete",
                "table": "users",
                "payload": {"where": {"name": "Alice"}}
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        # Execute delete
        result = executor.execute(intent, None, {"final_verdict": "allow"})
        assert result.success is True
        
        # Get rollback plan
        rollback_plan_id = result.output.get("rollback_plan_id")
        assert rollback_plan_id is not None
        
        rollback_plan = executor._rollback_plans[rollback_plan_id]
        
        # Execute rollback
        rollback_result = executor.rollback(rollback_plan)
        assert rollback_result.success is True
        
        # Verify row restored
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = 'Alice'")
        row = cursor.fetchone()
        assert row is not None
        conn.close()
    
    def test_rollback_plan_expiration(self, executor, temp_db_dir):
        """Test expired rollback plan cannot be executed."""
        from exoarmur.kernel.clock import SystemClock, set_clock
        
        # Use system clock for this test to ensure proper time comparison
        set_clock(SystemClock())
        
        db_path = temp_db_dir / "test.db"
        
        # Create the database and table first
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.commit()
        conn.close()
        
        # Create expired rollback plan
        from datetime import datetime, timedelta, timezone
        expiration = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        rollback_plan = DatabaseRollbackPlan(
            action_type="update",
            db_path=str(db_path),
            table="users",
            row_id=1,
            original_state={"name": "Alice", "email": "alice@example.com"},
            expiration_timestamp=expiration
        )
        
        rollback_result = executor.rollback(rollback_plan)
        assert rollback_result.success is False
        assert "expired" in rollback_result.error.lower()


class TestDatabaseExecutorSafetyGate:
    """Test safety gate integration."""
    
    def test_safety_gate_deny_blocks_execution(self, executor, temp_db_dir, deterministic_clock):
        """Test safety gate deny blocks execution."""
        db_path = temp_db_dir / "test.db"
        
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "insert",
                "table": "users",
                "payload": {"data": {"name": "Alice"}}
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "DENY"})
        assert result.success is False
        assert result.error == "SAFETY_GATE_DENY"
        assert "Safety gate denied execution" in result.evidence["reason"]


class TestDatabaseExecutorStateHash:
    """Test state hash computation."""
    
    def test_compute_db_hash(self, executor, temp_db_dir):
        """Test database state hash computation."""
        db_path = temp_db_dir / "test.db"
        
        # Create database with data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO users (name) VALUES ('Alice')")
        cursor.execute("INSERT INTO users (name) VALUES ('Bob')")
        conn.commit()
        conn.close()
        
        hash1 = executor.compute_db_hash(db_path, "users")
        assert hash1 is not None
        
        # Same data should produce same hash
        hash2 = executor.compute_db_hash(db_path, "users")
        assert hash1 == hash2
        
        # Different data should produce different hash
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name) VALUES ('Charlie')")
        conn.commit()
        conn.close()
        
        hash3 = executor.compute_db_hash(db_path, "users")
        assert hash3 != hash1
    
    def test_compute_db_hash_nonexistent_db(self, executor, temp_db_dir):
        """Test hash computation for nonexistent database."""
        db_path = temp_db_dir / "nonexistent.db"
        hash_value = executor.compute_db_hash(db_path, "users")
        assert hash_value is None


class TestDatabaseExecutorSQLInjection:
    """Test SQL injection prevention."""
    
    def test_validate_sql_identifier_valid(self, executor):
        """Test valid SQL identifiers are accepted."""
        # Valid identifiers
        valid_identifiers = ["users", "user_table", "Users", "user123", "_users", "a_b_c"]
        for identifier in valid_identifiers:
            # Should not raise
            DatabaseExecutor._validate_sql_identifier(identifier, "test identifier")
    
    def test_validate_sql_identifier_invalid_characters(self, executor):
        """Test invalid characters in SQL identifiers are rejected."""
        # Test each invalid identifier individually
        with pytest.raises(ValueError, match="Invalid"):
            DatabaseExecutor._validate_sql_identifier("users; DROP TABLE", "test identifier")
        
        with pytest.raises(ValueError, match="Invalid"):
            DatabaseExecutor._validate_sql_identifier("users' OR '1'='1", "test identifier")
        
        with pytest.raises(ValueError, match="Invalid"):
            DatabaseExecutor._validate_sql_identifier("users--comment", "test identifier")
        
        with pytest.raises(ValueError, match="Invalid"):
            DatabaseExecutor._validate_sql_identifier("users/*comment*/", "test identifier")
        
        with pytest.raises(ValueError, match="Invalid"):
            DatabaseExecutor._validate_sql_identifier("users.table", "test identifier")
    
    def test_validate_sql_identifier_starts_with_digit(self, executor):
        """Test identifiers starting with digit are rejected."""
        invalid_identifiers = ["1users", "123table", "9_user"]
        for identifier in invalid_identifiers:
            with pytest.raises(ValueError, match="Invalid"):
                DatabaseExecutor._validate_sql_identifier(identifier, "test identifier")
    
    def test_validate_sql_identifier_empty(self, executor):
        """Test empty identifier is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DatabaseExecutor._validate_sql_identifier("", "test identifier")
    
    def test_execute_rejects_malicious_table_name(self, executor, temp_db_dir, deterministic_clock):
        """Test execution rejects malicious table names."""
        db_path = temp_db_dir / "test.db"
        
        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        # Try to execute with malicious table name
        malicious_tables = [
            "users; DROP TABLE users",
            "users' OR '1'='1",
            "users--",
            "users/*comment*/",
        ]
        
        for malicious_table in malicious_tables:
            intent = ActionIntent.create(
                actor_id="test_actor",
                actor_type="automation",
                action_type="db_operation",
                target=str(db_path),
                parameters={
                    "operation": "insert",
                    "table": malicious_table,
                    "payload": {"data": {"name": "Alice"}}
                },
                safety_context={},
                tenant_id="test_tenant",
                cell_id="test_cell"
            )
            
            result = executor.execute(intent, None, {"final_verdict": "APPROVE"})
            assert result.success is False
            assert "Invalid table name" in result.error
    
    def test_execute_rejects_malicious_column_name(self, executor, temp_db_dir, deterministic_clock):
        """Test execution rejects malicious column names in payload."""
        db_path = temp_db_dir / "test.db"
        
        # Create database with valid table
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        
        # Try to execute with malicious column name
        intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "insert",
                "table": "users",
                "payload": {
                    "data": {
                        "name; DROP TABLE users": "Alice",  # Malicious column name
                        "name": "Alice"
                    }
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        
        result = executor.execute(intent, None, {"final_verdict": "APPROVE"})
        assert result.success is False
        assert "Invalid column name" in result.error
    
    def test_normal_operations_still_work(self, executor, temp_db_dir, deterministic_clock):
        """Test normal CRUD operations still work after validation."""
        db_path = temp_db_dir / "test.db"
        
        # Create table
        create_intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "table": "users",
                "payload": {
                    "schema": {
                        "id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "email": "TEXT"
                    }
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        create_result = executor.execute(create_intent, None, {"final_verdict": "APPROVE"})
        assert create_result.success is True
        
        # Insert data
        insert_intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "insert",
                "table": "users",
                "payload": {
                    "data": {
                        "name": "Alice",
                        "email": "alice@example.com"
                    }
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        insert_result = executor.execute(insert_intent, None, {"final_verdict": "APPROVE"})
        assert insert_result.success is True
        
        # Select data
        select_intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "select",
                "table": "users",
                "payload": {
                    "where": {"name": "Alice"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        select_result = executor.execute(select_intent, None, {"final_verdict": "APPROVE"})
        assert select_result.success is True
        assert len(select_result.output["result"]["rows"]) == 1
        assert select_result.output["result"]["rows"][0]["name"] == "Alice"
        
        # Update data
        update_intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "update",
                "table": "users",
                "payload": {
                    "data": {"email": "alice@newdomain.com"},
                    "where": {"name": "Alice"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        update_result = executor.execute(update_intent, None, {"final_verdict": "APPROVE"})
        assert update_result.success is True
        
        # Delete data
        delete_intent = ActionIntent.create(
            actor_id="test_actor",
            actor_type="automation",
            action_type="db_operation",
            target=str(db_path),
            parameters={
                "operation": "delete",
                "table": "users",
                "payload": {
                    "where": {"name": "Alice"}
                }
            },
            safety_context={},
            tenant_id="test_tenant",
            cell_id="test_cell"
        )
        delete_result = executor.execute(delete_intent, None, {"final_verdict": "APPROVE"})
        assert delete_result.success is True
