# aicp/database.py - PostgreSQL Production Database
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aicp',
    'user': 'aicp',
    'password': 'aicp_secret'
}

@contextmanager
def get_connection():
    """Context manager for PostgreSQL connections"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Create all tables and indexes"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Agents table (reputation tracking)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            success_rate DECIMAL(5,2) DEFAULT 0.95,
            avg_response_ms INTEGER DEFAULT 100,
            reputation_multiplier DECIMAL(4,2) DEFAULT 1.0,
            balance_satoshis BIGINT DEFAULT 0,
            total_tasks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """)
        
        # Tasks table (coordination + scheduling)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
            task_type VARCHAR(50) NOT NULL,
            complexity VARCHAR(20) NOT NULL CHECK (complexity IN ('LOW', 'MEDIUM', 'HIGH')),
            base_price_satoshis BIGINT NOT NULL,
            final_price_satoshis BIGINT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'running', 'completed', 'failed')),
            result JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
        """)
        
        # Payments table (escrow + settlement)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id VARCHAR(8) PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
            task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
            amount_satoshis BIGINT NOT NULL,
            status VARCHAR(20) DEFAULT 'escrow' CHECK (status IN ('escrow', 'released', 'refunded')),
            created_at TIMESTAMP DEFAULT NOW(),
            released_at TIMESTAMP,
            refunded_at TIMESTAMP
        );
        """)
        
        # Indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agents_reputation ON agents(reputation_multiplier DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_agent ON payments(agent_id);")
        
        conn.commit()
        cur.close()
        print("✅ Database initialized: agents, tasks, payments tables created")

def seed_initial_agents():
    """Load agent-1, agent-2, agent-3 from test data"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        agents = [
            ('agent-1', 0.95, 50, 2.00),
            ('agent-2', 0.90, 100, 1.80),
            ('agent-3', 0.70, 200, 1.20)
        ]
        
        for name, success_rate, avg_response, multiplier in agents:
            cur.execute("""
            INSERT INTO agents (name, success_rate, avg_response_ms, reputation_multiplier)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                success_rate = EXCLUDED.success_rate,
                avg_response_ms = EXCLUDED.avg_response_ms,
                reputation_multiplier = EXCLUDED.reputation_multiplier
            """, (name, success_rate, avg_response, multiplier))
        
        conn.commit()
        cur.close()
        print("✅ Seeded 3 test agents")

def get_agent_by_name(name: str):
    """Get agent details by name"""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM agents WHERE name = %s", (name,))
        agent = cur.fetchone()
        cur.close()
        return dict(agent) if agent else None

def update_agent_balance(name: str, amount_satoshis: int):
    """Add to agent's balance"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE agents 
            SET balance_satoshis = balance_satoshis + %s,
                updated_at = NOW()
            WHERE name = %s
        """, (amount_satoshis, name))
        conn.commit()
        cur.close()

def create_payment(payment_id: str, agent_name: str, amount_satoshis: int, task_id: int = None):
    """Create payment in escrow"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get agent_id
        cur.execute("SELECT id FROM agents WHERE name = %s", (agent_name,))
        result = cur.fetchone()
        agent_id = result[0] if result else None
        
        # Insert payment
        cur.execute("""
            INSERT INTO payments (id, agent_id, task_id, amount_satoshis, status)
            VALUES (%s, %s, %s, %s, 'escrow')
        """, (payment_id, agent_id, task_id, amount_satoshis))
        
        conn.commit()
        cur.close()

def release_payment(payment_id: str):
    """Release payment from escrow to agent"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get payment details
        cur.execute("""
            SELECT p.amount_satoshis, a.name 
            FROM payments p
            JOIN agents a ON p.agent_id = a.id
            WHERE p.id = %s AND p.status = 'escrow'
        """, (payment_id,))
        
        result = cur.fetchone()
        if not result:
            cur.close()
            return False
        
        amount_satoshis, agent_name = result
        
        # Update payment status
        cur.execute("""
            UPDATE payments 
            SET status = 'released', released_at = NOW()
            WHERE id = %s
        """, (payment_id,))
        
        # Update agent balance
        cur.execute("""
            UPDATE agents 
            SET balance_satoshis = balance_satoshis + %s,
                updated_at = NOW()
            WHERE name = %s
        """, (amount_satoshis, agent_name))
        
        conn.commit()
        cur.close()
        return True

if __name__ == "__main__":
    init_database()
    seed_initial_agents()
    print("\n✅ Database ready! Test with:")
    print('docker exec -it aicp-db psql -U aicp -d aicp -c "SELECT * FROM agents;"')
