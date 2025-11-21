"""AINS Database Models"""

from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, DECIMAL, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

# Database connection - use SQLite for tests, PostgreSQL for production
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test_ains_temp.db"  # SQLite for local development/testing
)

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Agent(Base):
    """Agent registry table"""
    __tablename__ = "agents"
    
    agent_id = Column(String(64), primary_key=True)
    public_key = Column(Text, nullable=False, unique=True)
    display_name = Column(String(255))
    description = Column(Text)
    endpoint_url = Column(String(255))
    status = Column(String(20), default='ACTIVE')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    owner_address = Column(String(42))
    avatar_url = Column(String(255))
    trust_score = Column(DECIMAL(5,2), default=50.0)
    version = Column(String(20))
    
    # Relationships
    tags = relationship("AgentTag", back_populates="agent")
    capabilities = relationship("Capability", back_populates="agent")
    trust_record = relationship("TrustRecord", back_populates="agent", uselist=False)


class AgentTag(Base):
    """Agent tags for categorization"""
    __tablename__ = "agent_tags"
    
    agent_id = Column(String(64), ForeignKey("agents.agent_id"), primary_key=True)
    tag = Column(String(100), primary_key=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tags")


class Capability(Base):
    """Agent capabilities"""
    __tablename__ = "agent_capabilities"
    
    capability_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), ForeignKey("agents.agent_id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(20))
    
    # Schemas as JSON
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=False)
    
    # Pricing
    pricing_model = Column(String(20))
    price = Column(DECIMAL(10,4))
    currency = Column(String(10), default='USD')
    
    # SLO
    latency_p99_ms = Column(Integer)
    availability_percent = Column(DECIMAL(5,2))
    
    deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="capabilities")


class TrustRecord(Base):
    """Trust scores and reputation tracking"""
    __tablename__ = "trust_records"
    
    record_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), ForeignKey("agents.agent_id"), unique=True)
    
    # Scores
    trust_score = Column(DECIMAL(5,2), default=50.0)
    reputation_score = Column(DECIMAL(5,2), default=50.0)
    rating = Column(DECIMAL(3,2), default=0.0)
    total_ratings = Column(Integer, default=0)
    
    # Transactions
    successful_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    
    # Uptime
    uptime_30d = Column(DECIMAL(5,2), default=100.0)
    uptime_90d = Column(DECIMAL(5,2), default=100.0)
    uptime_all_time = Column(DECIMAL(5,2), default=100.0)
    
    # Performance
    avg_latency_ms = Column(Integer, default=0)
    p99_latency_ms = Column(Integer, default=0)
    success_rate = Column(DECIMAL(5,2), default=100.0)
    
    # Security
    verified_signer = Column(Boolean, default=False)
    rate_limited = Column(Boolean, default=False)
    fraud_flags = Column(Integer, default=0)
    last_audit = Column(DateTime)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="trust_record")


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
