"""
Prepare Test Database

Sets up test database and runs migrations before testing.
"""
import os
import subprocess
import sys
from sqlalchemy import create_engine, text


def main():
    """Prepare test database for testing."""
    print("🔧 Preparing test database...")
    
    # Database URLs
    postgres_url = "postgresql://postgres:postgres@localhost:55432/postgres"
    test_db_url = "postgresql://postgres:postgres@localhost:55432/theappapp_test"
    
    # 1. Connect to postgres and create test database if needed
    print("\n📦 Creating test database...")
    try:
        engine = create_engine(postgres_url)
        with engine.connect() as conn:
            # Must be outside transaction for CREATE DATABASE
            conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # Drop existing test database
            try:
                conn.execute(text("DROP DATABASE IF EXISTS theappapp_test"))
                print("   Dropped existing test database")
            except Exception as e:
                print(f"   Warning: {e}")
            
            # Create fresh test database
            conn.execute(text("CREATE DATABASE theappapp_test"))
            print("   ✅ Created theappapp_test database")
        
        engine.dispose()
    except Exception as e:
        print(f"   ❌ Error creating database: {e}")
        return False
    
    # 2. Run Alembic migrations
    print("\n📊 Running Alembic migrations...")
    try:
        # Set environment variable for alembic
        os.environ["DATABASE_URL"] = test_db_url
        
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("   ✅ Migrations completed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout}")
        else:
            print(f"   ❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error running migrations: {e}")
        return False
    
    # 3. Verify tables exist
    print("\n🔍 Verifying database schema...")
    try:
        engine = create_engine(test_db_url.replace("postgresql://", "postgresql+psycopg://"))
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            print(f"   Found {table_count} tables")
            
            # Check for critical tables
            critical_tables = ["gates", "knowledge_staging", "specialists", "prompts"]
            for table in critical_tables:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """))
                exists = result.scalar()
                status = "✅" if exists else "❌"
                print(f"   {status} Table: {table}")
        
        engine.dispose()
        
    except Exception as e:
        print(f"   ❌ Error verifying schema: {e}")
        return False
    
    print("\n🎉 Test database ready!")
    print(f"   URL: {test_db_url}")
    print("\n💡 Run tests with: pytest backend/tests/ -v")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
