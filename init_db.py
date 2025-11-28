"""Initialize the AINS database with all tables"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ains.db import Base, engine
from ains.models import (
    Agent, Task, Capability, AgentCapability,
    TrustRecord, Webhook, TaskChain, ScheduledTask, TaskTemplate
)

def init_database():
    """Create all database tables"""
    print("🔧 Initializing AINS database...")
    
    # Drop all tables (careful in production!)
    print("⚠️  Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    print("✅ Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialization complete!")
    print("\nTables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")

if __name__ == "__main__":
    init_database()
