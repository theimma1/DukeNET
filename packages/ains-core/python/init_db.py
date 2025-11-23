"""Initialize the AINS database with all tables"""
import os
import sys

# Make sure we're using the packages path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import engine and Base
from ains.db import Base, engine

def init_database():
    """Create all database tables"""
    print("🔧 Initializing AINS database...")
    
    # Import all models so they register with Base
    print("📦 Loading models...")
    try:
        from ains import db_models
        print("✅ Models loaded from db_models")
    except ImportError:
        try:
            # Try alternative imports
            import ains.api  # This imports models
            print("✅ Models loaded via api import")
        except Exception as e:
            print(f"⚠️  Warning: {e}")
    
    # Drop all tables
    print("⚠️  Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    print("✅ Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialization complete!")
    print(f"\n📊 Tables created ({len(Base.metadata.sorted_tables)}):")
    for table in Base.metadata.sorted_tables:
        print(f"  ✓ {table.name}")

if __name__ == "__main__":
    init_database()
