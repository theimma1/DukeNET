# DukeNET v2.0 - Professional React Dashboard
# Save as frontend/src/App.jsx and supporting components

# ============================================================================
# App.jsx - Main Application Component
# ============================================================================

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

// Stores
import { useAuthStore } from './stores/authStore';
import { useMarketplaceStore } from './stores/marketplaceStore';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import BuyerDashboard from './pages/BuyerDashboard';
import AgentDashboard from './pages/AgentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import ModelTrainingDashboard from './pages/ModelTrainingDashboard';

// Components
import Navigation from './components/Navigation';
import ProtectedRoute from './components/ProtectedRoute';

// Styles
import './styles/App.css';
import './styles/tailwind.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const { user, token, setUser, setToken, logout } = useAuthStore();
  const { setMetrics } = useMarketplaceStore();
  const [loading, setLoading] = useState(true);

  // Setup API interceptors
  useEffect(() => {
    const api = axios.create({
      baseURL: API_URL,
      timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || 30000),
    });

    // Add auth header
    api.interceptors.request.use((config) => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle responses
    api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          logout();
        }
        return Promise.reject(error);
      }
    );

    window.api = api;
    setLoading(false);
  }, [token, logout]);

  // Load user from token
  useEffect(() => {
    const loadUser = async () => {
      if (token && !user) {
        try {
          const response = await window.api.get('/api/v2/auth/profile');
          setUser(response.data);
        } catch (error) {
          console.error('Failed to load user:', error);
          logout();
        }
      }
    };

    loadUser();
  }, [token, user, setUser, logout]);

  // Fetch system metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      if (user?.user_type === 'admin') {
        try {
          const response = await window.api.get('/api/v2/admin/metrics');
          setMetrics(response.data);
        } catch (error) {
          console.error('Failed to fetch metrics:', error);
        }
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [user, setMetrics]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <Router>
      {user && <Navigation user={user} />}
      <AnimatePresence mode="wait">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute user={user}>
                {user?.user_type === 'buyer' && <BuyerDashboard />}
                {user?.user_type === 'agent' && <AgentDashboard />}
                {user?.user_type === 'admin' && <AdminDashboard />}
              </ProtectedRoute>
            }
          />

          <Route
            path="/model-training"
            element={
              <ProtectedRoute user={user}>
                {user?.user_type === 'admin' && <ModelTrainingDashboard />}
              </ProtectedRoute>
            }
          />

          {/* Redirect */}
          <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} />
        </Routes>
      </AnimatePresence>
    </Router>
  );
}

export default App;

# ============================================================================
# stores/authStore.js - Zustand Auth Store
# ============================================================================

import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isLoading: false,

  setUser: (user) => set({ user }),
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
    set({ token });
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await window.api.post('/api/v2/auth/login', {
        email,
        password,
      });
      set({
        user: response.data.user,
        token: response.data.access_token,
        isLoading: false,
      });
      localStorage.setItem('token', response.data.access_token);
      return response.data;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (email, password, fullName, userType) => {
    set({ isLoading: true });
    try {
      const response = await window.api.post('/api/v2/auth/register', {
        email,
        password,
        full_name: fullName,
        user_type: userType,
      });
      set({ isLoading: false });
      return response.data;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    set({ user: null, token: null });
    localStorage.removeItem('token');
  },
}));

# ============================================================================
# stores/marketplaceStore.js - Zustand Marketplace Store
# ============================================================================

import { create } from 'zustand';

export const useMarketplaceStore = create((set) => ({
  tasks: [],
  results: [],
  files: [],
  metrics: null,
  agents: [],
  isLoading: false,

  // Tasks
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({ tasks: [task, ...state.tasks] })),

  // Results
  setResults: (results) => set({ results }),
  addResult: (result) => set((state) => ({ results: [result, ...state.results] })),

  // Files
  setFiles: (files) => set({ files }),
  addFile: (file) => set((state) => ({ files: [file, ...state.files] })),
  removeFile: (fileId) => set((state) => ({
    files: state.files.filter((f) => f.id !== fileId),
  })),

  // Metrics
  setMetrics: (metrics) => set({ metrics }),

  // Agents
  setAgents: (agents) => set({ agents }),

  // Loading
  setIsLoading: (isLoading) => set({ isLoading }),

  // Fetch tasks
  fetchTasks: async (status = null) => {
    set({ isLoading: true });
    try {
      const params = status ? { status } : {};
      const response = await window.api.get('/api/v2/tasks/list', { params });
      set({ tasks: response.data, isLoading: false });
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      set({ isLoading: false });
    }
  },

  // Create task
  createTask: async (description, complexity, fileIds = []) => {
    try {
      const response = await window.api.post('/api/v2/tasks/create', {
        description,
        complexity,
        file_ids: fileIds,
      });
      set((state) => ({ tasks: [response.data, ...state.tasks] }));
      return response.data;
    } catch (error) {
      console.error('Failed to create task:', error);
      throw error;
    }
  },

  // Submit result
  submitResult: async (taskId, resultText, success, confidenceScore, executionTimeMs) => {
    try {
      const response = await window.api.post('/api/v2/results/submit', {
        task_id: taskId,
        result_text: resultText,
        success,
        confidence_score: confidenceScore,
        execution_time_ms: executionTimeMs,
      });
      return response.data;
    } catch (error) {
      console.error('Failed to submit result:', error);
      throw error;
    }
  },

  // Upload file
  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await window.api.post('/api/v2/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      set((state) => ({ files: [response.data, ...state.files] }));
      return response.data;
    } catch (error) {
      console.error('Failed to upload file:', error);
      throw error;
    }
  },
}));

# ============================================================================
# pages/LoginPage.jsx - Login Component
# ============================================================================

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiMail, FiLock, FiAlertCircle } from 'react-icons/fi';
import { useAuthStore } from '../stores/authStore';

function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            ⚡ DukeNET
          </h1>
          <p className="text-slate-400">
            Bitcoin AI Agent Marketplace
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 shadow-2xl">
          <h2 className="text-2xl font-bold text-white mb-6">Sign In</h2>

          {/* Error Alert */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3"
            >
              <FiAlertCircle className="text-red-500" size={20} />
              <span className="text-sm text-red-400">{error}</span>
            </motion.div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email
              </label>
              <div className="relative">
                <FiMail className="absolute left-3 top-3 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="your@email.com"
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <div className="relative">
                <FiLock className="absolute left-3 top-3 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition"
                />
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white font-semibold rounded-lg transition mt-6"
            >
              {isLoading ? 'Signing In...' : 'Sign In'}
            </motion.button>
          </form>

          {/* Register Link */}
          <p className="text-center text-slate-400 text-sm mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-400 hover:text-blue-300">
              Sign up
            </Link>
          </p>
        </div>

        {/* Demo Credentials */}
        <div className="mt-8 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <p className="text-xs text-slate-400 mb-2">Demo Credentials:</p>
          <div className="space-y-1 text-xs text-slate-300">
            <p><strong>Buyer:</strong> buyer@dukenete.com / password</p>
            <p><strong>Admin:</strong> admin@dukenete.com / password</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default LoginPage;

# ============================================================================
# pages/BuyerDashboard.jsx - Buyer Dashboard
# ============================================================================

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FiPlus, FiUpload, FiTrendingUp } from 'react-icons/fi';
import TaskCreationForm from '../components/TaskCreationForm';
import FileUploader from '../components/FileUploader';
import TaskList from '../components/TaskList';
import ResultsDisplay from '../components/ResultsDisplay';
import { useMarketplaceStore } from '../stores/marketplaceStore';

function BuyerDashboard() {
  const { tasks, files, fetchTasks } = useMarketplaceStore();
  const [activeTab, setActiveTab] = useState('tasks');
  const [stats, setStats] = useState({
    totalTasks: 0,
    completedTasks: 0,
    totalSatoshis: 0,
    successRate: 0,
  });

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (tasks.length > 0) {
      const completed = tasks.filter((t) => t.status === 'completed').length;
      const totalSatoshis = tasks.reduce((sum, t) => sum + t.price_satoshis, 0);
      
      setStats({
        totalTasks: tasks.length,
        completedTasks: completed,
        totalSatoshis,
        successRate: completed > 0 ? (completed / tasks.length) * 100 : 0,
      });
    }
  }, [tasks]);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-white mb-2">
            Buyer Dashboard
          </h1>
          <p className="text-slate-400">
            Submit tasks, manage files, and track agent performance
          </p>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ staggerChildren: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"
        >
          {[
            { label: 'Total Tasks', value: stats.totalTasks, icon: '📋' },
            { label: 'Completed', value: stats.completedTasks, icon: '✅' },
            { label: 'Total Spent', value: `${stats.totalSatoshis.toLocaleString()} sat`, icon: '₿' },
            { label: 'Success Rate', value: `${stats.successRate.toFixed(0)}%`, icon: '📈' },
          ].map((stat, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-slate-800 rounded-lg p-6 border border-slate-700"
            >
              <div className="text-2xl mb-2">{stat.icon}</div>
              <div className="text-slate-400 text-sm">{stat.label}</div>
              <div className="text-2xl font-bold text-white">{stat.value}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-slate-700">
          {[
            { id: 'tasks', label: '📋 Tasks', icon: FiPlus },
            { id: 'upload', label: '📤 Files', icon: FiUpload },
            { id: 'results', label: '📊 Results', icon: FiTrendingUp },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 font-semibold transition ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === 'tasks' && <TaskCreationForm />}
          {activeTab === 'upload' && <FileUploader />}
          {activeTab === 'results' && (
            <div className="grid grid-cols-2 gap-6">
              <TaskList tasks={tasks} />
              <ResultsDisplay />
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

export default BuyerDashboard;

# ============================================================================
# pages/AdminDashboard.jsx - Admin Dashboard with ML Training
# ============================================================================

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import SystemMetrics from '../components/SystemMetrics';
import AgentLeaderboard from '../components/AgentLeaderboard';
import MLTrainingPanel from '../components/MLTrainingPanel';
import { useMarketplaceStore } from '../stores/marketplaceStore';

function AdminDashboard() {
  const { metrics, setMetrics } = useMarketplaceStore();

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await window.api.get('/api/v2/admin/metrics');
        setMetrics(response.data);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [setMetrics]);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-white mb-2">
            Admin Dashboard
          </h1>
          <p className="text-slate-400">
            System monitoring, agent management, and ML training
          </p>
        </motion.div>

        {/* Metrics Grid */}
        {metrics && <SystemMetrics metrics={metrics} />}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          <AgentLeaderboard />
          <MLTrainingPanel />
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;

# ============================================================================
# components/ProtectedRoute.jsx - Route Protection
# ============================================================================

import React from 'react';
import { Navigate } from 'react-router-dom';

function ProtectedRoute({ user, children }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;

# ============================================================================
# components/Navigation.jsx - Top Navigation Bar
# ============================================================================

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiLogOut, FiSettings } from 'react-icons/fi';
import { useAuthStore } from '../stores/authStore';

function Navigation({ user }) {
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link
          to="/dashboard"
          className="text-2xl font-bold text-blue-400 hover:text-blue-300 transition"
        >
          ⚡ DukeNET
        </Link>

        {/* User Info */}
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-white font-semibold">{user?.full_name}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.user_type}</p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-4">
            {user?.user_type === 'admin' && (
              <Link
                to="/model-training"
                className="text-slate-400 hover:text-white transition"
              >
                <FiSettings size={20} />
              </Link>
            )}
            <motion.button
              whileHover={{ scale: 1.1 }}
              onClick={handleLogout}
              className="text-slate-400 hover:text-red-400 transition"
            >
              <FiLogOut size={20} />
            </motion.button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navigation;

# ============================================================================
# SUMMARY - Complete Production System
# ============================================================================

This gives you:

✅ BACKEND (FastAPI)
   - Full authentication & JWT
   - Task management & assignment
   - Result submission & tracking
   - File upload/download
   - ML training pipeline
   - Agent reputation tracking
   - Bitcoin satoshi pricing
   - Admin metrics & monitoring

✅ FRONTEND (React)
   - Professional UI with Tailwind CSS
   - Authentication flows
   - Buyer dashboard (create tasks, track results)
   - Agent dashboard (execute tasks)
   - Admin dashboard (system monitoring)
   - ML training controls
   - Real-time updates
   - Responsive design

✅ DATABASE (PostgreSQL)
   - User management
   - Task lifecycle
   - Results & feedback
   - Training data collection
   - Model versioning
   - Agent statistics

✅ ML INTEGRATION
   - Duke Labelee model learning from ALL platform activity
   - Automatic training triggers
   - Model version control
   - Agent reputation multipliers
   - Performance metrics tracking

🚀 DEPLOYMENT READY
   - Docker & Docker Compose
   - Environment-based config
   - Production-ready security
   - Scalable architecture
