import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

// Create axios instance with proper timeout and retry logic
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// Add token to all requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Retry logic for failed requests
// Handle token expiration and other errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Handle 401 Unauthorized (token expired)
    if (error.response?.status === 401) {
      console.error('🔴 Token expired - logging out');
      localStorage.removeItem('token');
      localStorage.removeItem('userType');
      localStorage.removeItem('userId');
      window.location.reload();
    }
    console.error('API Error:', error.message);
    return Promise.reject(error);
  }
);


export default function AICPMarketplace() {
  const [userType, setUserType] = useState(() => {
    const type = localStorage.getItem('userType');
    const token = localStorage.getItem('token');
    if (type && !token) return null;
    return type;
  });
  
  const [userId, setUserId] = useState(() => localStorage.getItem('userId') || '');
  const [isConnected, setIsConnected] = useState(true);

  // Check backend connectivity on mount
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkBackendConnection = async () => {
    try {
      await axios.get(`${API_BASE}/agents`, { timeout: 5000 });
      setIsConnected(true);
    } catch (err) {
      console.warn('⚠️ Backend connection lost');
      setIsConnected(false);
    }
  };

  const handleLogin = (type, id) => {
    setUserType(type);
    setUserId(id);
    localStorage.setItem('userType', type);
    localStorage.setItem('userId', id);
  };

  const handleLogout = () => {
    setUserType(null);
    setUserId('');
    localStorage.removeItem('userType');
    localStorage.removeItem('userId');
    localStorage.removeItem('token');
  };

  if (!userType) {
    return <LoginPage onLogin={handleLogin} isConnected={isConnected} />;
  }

  return userType === 'buyer' ? (
    <BuyerDashboard buyerId={userId} onLogout={handleLogout} isConnected={isConnected} />
  ) : (
    <AgentDashboard agentName={userId} onLogout={handleLogout} isConnected={isConnected} />
  );
}

function LoginPage({ onLogin, isConnected }) {
  const [inputValue, setInputValue] = useState('');
  const [userType, setUserType] = useState('buyer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!inputValue.trim()) {
      setError('Please enter an ID');
      return;
    }

    if (!isConnected) {
      setError('❌ Backend is not connected. Please check if http://localhost:8000 is running');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const endpoint = userType === 'buyer' ? '/auth/buyer/login' : '/auth/agent/login';
      const response = await axios.post(`${API_BASE}${endpoint}`, {
        [userType === 'buyer' ? 'buyer_id' : 'agent_id']: inputValue,
        password: userType === 'buyer' ? 'securepassword123' : 'agentpassword123',
      });

      localStorage.setItem('token', response.data.access_token);
      console.log('✅ Token stored:', response.data.access_token.substring(0, 30) + '...');
      onLogin(userType, inputValue);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      setError(`Login failed: ${errorMsg}`);
      console.error('❌ Login error:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.loginContainer}>
      <div style={styles.loginBox}>
        <div style={styles.logo}>🎯</div>
        <h1 style={styles.title}>AICP Marketplace</h1>
        <p style={styles.subtitle}>Autonomous Agent Marketplace</p>
        
        {!isConnected && (
          <div style={{...styles.errorBox, marginBottom: '20px'}}>
            ⚠️ Backend connection lost. Make sure http://localhost:8000 is running.
          </div>
        )}

        {error && (
          <div style={{...styles.errorBox, marginBottom: '20px'}}>
            {error}
          </div>
        )}

        <div style={styles.typeSelector}>
          <button
            onClick={() => setUserType('buyer')}
            style={{
              ...styles.typeBtn,
              ...(userType === 'buyer' ? styles.typeBtnActive : {}),
            }}
          >
            👤 Buyer
          </button>
          <button
            onClick={() => setUserType('agent')}
            style={{
              ...styles.typeBtn,
              ...(userType === 'agent' ? styles.typeBtnActive : {}),
            }}
          >
            🤖 Agent
          </button>
        </div>
        <input
          type="text"
          placeholder={userType === 'buyer' ? 'buyer-1' : 'agent-1'}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
          style={styles.input}
        />
        <button 
          onClick={handleLogin} 
          disabled={loading || !isConnected} 
          style={styles.loginBtn}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
        <div style={styles.links}>
          <a href="http://localhost:8000/dashboard" target="_blank" rel="noopener noreferrer">
            📊 Backend Dashboard
          </a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
            📚 API Docs
          </a>
        </div>
      </div>
    </div>
  );
}

function BuyerDashboard({ buyerId, onLogout, isConnected }) {
  const [description, setDescription] = useState('');
  const [complexity, setComplexity] = useState(1);
  const [tasks, setTasks] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (!isConnected) {
      setError('⚠️ Backend disconnected. Trying to reconnect...');
      return;
    }

    fetchAgents();
    fetchTasks();
    const interval = setInterval(() => {
      fetchTasks();
      fetchAgents();
    }, 2000);
    return () => clearInterval(interval);
  }, [buyerId, isConnected]);

  const fetchAgents = async () => {
    try {
      const res = await apiClient.get('/agents');
      setAgents(res.data.agents || []);
      console.log('✅ Agents fetched:', res.data.agents.length);
    } catch (err) {
      console.error('❌ Error fetching agents:', err.message);
    }
  };

  const fetchTasks = async () => {
    try {
      setSyncing(true);
      const res = await apiClient.get('/tasks');
      const tasksArray = res.data.tasks || [];
      setTasks(tasksArray);
      console.log(`✅ Found ${tasksArray.length} total tasks`);
      setError('');
    } catch (err) {
      console.error('❌ Error fetching tasks:', err.message);
      setError(`Tasks sync error: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleSubmitTask = async () => {
    if (!description.trim()) {
      alert('Please enter a task description');
      return;
    }

    if (!isConnected) {
      alert('❌ Backend is not connected. Cannot submit task.');
      return;
    }

    setLoading(true);
    try {
      console.log(`📤 Submitting task for buyer: ${buyerId}`);
      const res = await apiClient.post('/tasks/submit', {
        description,
        complexity: parseInt(complexity),
        buyer_id: buyerId,
      });
      
      console.log('✅ Task created:', res.data.task_id);
      setDescription('');
      setComplexity(1);
      
      // Fetch updated tasks immediately
      await fetchTasks();
      alert(`✅ Task created successfully: ${res.data.task_id}`);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      console.error('❌ Error submitting task:', errorMsg);
      alert(`Error: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const estimatedPrice = (complexity * 100000 * 2).toLocaleString();

  return (
    <div style={styles.dashboard}>
      <Header title={`Buyer - ${buyerId}`} onLogout={onLogout} isConnected={isConnected} syncing={syncing} />
      {error && <div style={{...styles.errorBox, margin: '16px'}}>{error}</div>}
      
      <div style={styles.container}>
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>📝 Submit Task</h2>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What do you need done?"
            style={styles.textarea}
            disabled={!isConnected}
          />
          <div style={{ marginTop: '12px' }}>Complexity: {complexity}/10</div>
          <input
            type="range"
            min="1"
            max="10"
            value={complexity}
            onChange={(e) => setComplexity(e.target.value)}
            style={{ width: '100%' }}
            disabled={!isConnected}
          />
          <div
            style={{
              marginTop: '12px',
              padding: '12px',
              background: 'rgba(59, 130, 246, 0.1)',
              borderRadius: '8px',
            }}
          >
            Price: <strong>{estimatedPrice} sat</strong>
          </div>
          <button 
            onClick={handleSubmitTask} 
            disabled={loading || !isConnected} 
            style={styles.submitBtn}
          >
            {loading ? 'Submitting...' : 'Submit Task'}
          </button>
        </div>

        <div style={styles.card}>
          <h2 style={styles.cardTitle}>🤖 Available Agents ({agents.length})</h2>
          {agents.length === 0 ? (
            <p>No agents available</p>
          ) : (
            agents.map((a) => (
              <div key={a.name} style={{ marginBottom: '12px', padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
                <strong>{a.name}</strong>
                <br />
                Success: {(a.success_rate * 100).toFixed(0)}% | Reputation: {a.reputation_multiplier.toFixed(2)}x
              </div>
            ))
          )}
        </div>

        <div style={styles.card}>
          <h2 style={styles.cardTitle}>⚡ All Tasks ({tasks.length}) {syncing && '🔄'}</h2>
          {tasks.length === 0 ? (
            <p>No tasks yet. Create one to get started!</p>
          ) : (
            tasks.map((t) => (
              <div
                key={t.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: '#0f172a',
                  borderRadius: '8px',
                  border: t.buyer_id === buyerId ? '2px solid #3b82f6' : '1px solid #334155',
                  opacity: syncing ? 0.7 : 1,
                }}
              >
                <strong>#{t.id}</strong> {t.buyer_id === buyerId && '(YOUR TASK ⭐)'} - {t.description}
                <br />
                <small>Buyer: {t.buyer_id} | Agent: {t.agent_name || 'Unassigned'} | {t.price_satoshis.toLocaleString()} sat</small>
                <br />
                <span style={{
                  color: t.status === 'completed' ? '#10b981' : t.status === 'failed' ? '#ef4444' : '#f59e0b',
                  fontWeight: 'bold'
                }}>
                  {t.status.toUpperCase()}
                </span>
                {t.status === 'completed' && t.result && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #10b981',
                    fontSize: '12px',
                    color: '#cbd5f5',
                  }}>
                    <strong>✅ Result:</strong> {t.result}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function AgentDashboard({ agentName, onLogout, isConnected }) {
  const [agentData, setAgentData] = useState(null);
  const [allTasks, setAllTasks] = useState([]);
  const [activeTasks, setActiveTasks] = useState([]);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (!isConnected) {
      console.warn('⚠️ Not connected to backend');
      return;
    }

    fetchAgentData();
    fetchAllTasks();
    const interval = setInterval(() => {
      fetchAllTasks();
      fetchAgentData();
    }, 2000);
    return () => clearInterval(interval);
  }, [agentName, isConnected]);

  const fetchAgentData = async () => {
    try {
      const res = await apiClient.get('/agents');
      const agent = res.data.agents.find((x) => x.name === agentName);
      setAgentData(agent);
      console.log('✅ Agent data updated:', agentName);
    } catch (err) {
      console.error('❌ Error fetching agent data:', err.message);
    }
  };

  const fetchAllTasks = async () => {
    try {
      setSyncing(true);
      const res = await apiClient.get('/tasks');
      const tasksArray = res.data.tasks || [];
      
      const assigned = tasksArray.filter((t) => t.status === 'assigned');
      const active = tasksArray.filter((t) => t.agent_name === agentName);
      
      setAllTasks(assigned);
      setActiveTasks(active);
      console.log(`✅ Tasks synced - Available: ${assigned.length}, Active: ${active.length}`);
    } catch (err) {
      console.error('❌ Error fetching tasks:', err.message);
    } finally {
      setSyncing(false);
    }
  };

  const completeTask = async (taskId, success = true) => {
    if (!isConnected) {
      alert('❌ Backend is not connected');
      return;
    }

    try {
      const result = success
        ? 'Task completed successfully by agent.'
        : 'Task failed.';

      console.log(`📤 Completing task ${taskId}:`, { success, result });

      const response = await apiClient.post(`/tasks/${taskId}/complete`, {
        success,
        result,
      });

      console.log(`✅ Task completed:`, response.data);
      await fetchAgentData();
      await fetchAllTasks();
      alert(`✅ Task ${success ? 'completed' : 'marked as failed'}`);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      console.error('❌ Error completing task:', errorMsg);
      alert(`Error: ${errorMsg}`);
    }
  };

  if (!agentData) {
    return (
      <div style={styles.dashboard}>
        <Header title={`Agent - Loading...`} onLogout={onLogout} isConnected={isConnected} />
        <div style={styles.container}>
          <p>🔄 Loading agent data...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.dashboard}>
      <Header title={`Agent - ${agentName}`} onLogout={onLogout} isConnected={isConnected} syncing={syncing} />
      <div style={styles.container}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '16px',
          marginBottom: '24px',
        }}>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Reputation</div>
            <div style={styles.statValue}>{agentData.reputation_multiplier.toFixed(2)}x</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Success</div>
            <div style={styles.statValue}>{(agentData.success_rate * 100).toFixed(0)}%</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Earnings</div>
            <div style={styles.statValue}>{agentData.balance_satoshis.toLocaleString()} sat</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Status</div>
            <div style={{ ...styles.statValue, color: '#10b981' }}>🟢 Online</div>
          </div>
        </div>

        <div style={styles.card}>
          <h2 style={styles.cardTitle}>📋 Available Tasks ({allTasks.length}) {syncing && '🔄'}</h2>
          {allTasks.length === 0 ? (
            <p>No tasks available</p>
          ) : (
            allTasks.map((t) => (
              <div
                key={t.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: 'rgba(16, 185, 129, 0.05)',
                  borderRadius: '8px',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  opacity: syncing ? 0.7 : 1,
                }}
              >
                <strong>#{t.id}</strong> - {t.description}
                <br />
                <strong>{t.price_satoshis.toLocaleString()} sat</strong>
              </div>
            ))
          )}
        </div>

        <div style={styles.card}>
          <h2 style={styles.cardTitle}>⚡ Active Tasks ({activeTasks.length}) {syncing && '🔄'}</h2>
          {activeTasks.length === 0 ? (
            <p>No active tasks</p>
          ) : (
            activeTasks.map((t) => (
              <div
                key={t.id}
                style={{
                  marginBottom: '12px',
                  padding: '12px',
                  background: 'rgba(59, 130, 246, 0.05)',
                  borderRadius: '8px',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  opacity: syncing ? 0.7 : 1,
                }}
              >
                <strong>#{t.id}</strong> - {t.description}
                <br />
                <strong>{t.price_satoshis.toLocaleString()} sat</strong>
                {t.status === 'completed' && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #10b981',
                    fontSize: '12px',
                    color: '#cbd5f5',
                  }}>
                    <strong>✅ Completed</strong>
                  </div>
                )}
                {t.status === 'assigned' && (
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => completeTask(t.id, true)}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                      }}
                    >
                      ✅ Complete
                    </button>
                    <button
                      onClick={() => completeTask(t.id, false)}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: '#ef4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                      }}
                    >
                      ❌ Failed
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function Header({ title, onLogout, isConnected, syncing }) {
  return (
    <div style={styles.header}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <h1 style={styles.headerTitle}>🎯 {title}</h1>
        <div style={{
          fontSize: '12px',
          color: isConnected ? '#10b981' : '#ef4444',
          fontWeight: 'bold',
        }}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
        {syncing && <span>🔄</span>}
      </div>
      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <a
          href="http://localhost:8000/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          style={styles.headerLink}
        >
          📊 Backend Dashboard
        </a>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          style={styles.headerLink}
        >
          📚 API Docs
        </a>
        <button onClick={onLogout} style={styles.logoutBtn}>
          🚪 Logout
        </button>
      </div>
    </div>
  );
}

const styles = {
  loginContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    padding: '20px',
  },
  loginBox: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '16px',
    padding: '40px',
    maxWidth: '400px',
    width: '100%',
    textAlign: 'center',
  },
  errorBox: {
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    padding: '12px',
    borderRadius: '8px',
    fontSize: '14px',
  },
  logo: { fontSize: '64px', marginBottom: '20px' },
  title: { fontSize: '28px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' },
  subtitle: { color: '#94a3b8', marginBottom: '30px' },
  typeSelector: { display: 'flex', gap: '12px', marginBottom: '20px' },
  typeBtn: {
    flex: 1,
    padding: '10px 16px',
    border: '1px solid #334155',
    background: 'transparent',
    color: '#94a3b8',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '600',
  },
  typeBtnActive: { background: '#3b82f6', color: 'white', borderColor: '#3b82f6' },
  input: {
    width: '100%',
    padding: '12px 16px',
    border: '1px solid #334155',
    background: '#0f172a',
    color: '#f1f5f9',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  loginBtn: {
    width: '100%',
    padding: '12px 16px',
    background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '700',
    cursor: 'pointer',
    marginBottom: '20px',
  },
  links: { marginTop: '20px', display: 'flex', gap: '16px', justifyContent: 'center' },
  dashboard: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    color: '#f1f5f9',
  },
  header: {
    background: '#1e293b',
    borderBottom: '1px solid #334155',
    padding: '20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: { fontSize: '24px', fontWeight: '700', margin: 0 },
  headerLink: { color: '#3b82f6', textDecoration: 'none', fontSize: '14px' },
  logoutBtn: {
    padding: '8px 12px',
    background: '#ef4444',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '600',
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '20px',
  },
  card: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
  },
  cardTitle: { fontSize: '18px', fontWeight: '700', marginBottom: '20px', margin: 0 },
  textarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #334155',
    background: '#0f172a',
    color: '#f1f5f9',
    borderRadius: '8px',
    fontSize: '14px',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
    minHeight: '100px',
  },
  submitBtn: {
    width: '100%',
    padding: '12px 16px',
    background: 'linear-gradient(135deg, #10b981, #059669)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '700',
    cursor: 'pointer',
    marginTop: '12px',
  },
  statCard: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '20px',
    textAlign: 'center',
  },
  statLabel: { fontSize: '12px', color: '#94a3b8', marginBottom: '8px' },
  statValue: { fontSize: '28px', fontWeight: '700' },
};
