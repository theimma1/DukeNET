"""Test AINS Database Models"""

import pytest
from ains.db import Agent, AgentTag, TrustRecord, Base, engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime


@pytest.fixture
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_agent_creation(db_session):
    """Test creating an agent"""
    agent = Agent(
        agent_id="test_agent_123",
        public_key="test_public_key",
        display_name="Test Agent",
        endpoint_url="http://localhost:8000"
    )
    db_session.add(agent)
    db_session.commit()
    
    retrieved = db_session.query(Agent).filter(Agent.agent_id == "test_agent_123").first()
    assert retrieved is not None
    assert retrieved.display_name == "Test Agent"
    assert retrieved.trust_score == 50.0


def test_agent_tag_relationship(db_session):
    """Test agent tags"""
    agent = Agent(
        agent_id="test_agent_456",
        public_key="test_key",
        display_name="Tagged Agent",
        endpoint_url="http://localhost:8000"
    )
    db_session.add(agent)
    
    tag1 = AgentTag(agent_id="test_agent_456", tag="python")
    tag2 = AgentTag(agent_id="test_agent_456", tag="ml")
    db_session.add(tag1)
    db_session.add(tag2)
    db_session.commit()
    
    tags = db_session.query(AgentTag).filter(AgentTag.agent_id == "test_agent_456").all()
    assert len(tags) == 2
    assert {tag.tag for tag in tags} == {"python", "ml"}


def test_trust_record_creation(db_session):
    """Test creating trust record"""
    agent = Agent(
        agent_id="test_agent_789",
        public_key="test_key",
        display_name="Trust Agent",
        endpoint_url="http://localhost:8000"
    )
    db_session.add(agent)
    
    trust = TrustRecord(
        agent_id="test_agent_789",
        trust_score=75.5,
        successful_transactions=10,
        failed_transactions=2
    )
    db_session.add(trust)
    db_session.commit()
    
    retrieved = db_session.query(TrustRecord).filter(TrustRecord.agent_id == "test_agent_789").first()
    assert retrieved is not None
    assert float(retrieved.trust_score) == 75.5
    assert retrieved.successful_transactions == 10
