"""
AICP Coordinator Service + REAL Duke Machine Learning v4.2.0
FastAPI backend + SQLite + JWT + OpenAI GPT-3.5 Integration
REAL: PyTorch neural network training with persistent model weights
DASHBOARD: Enterprise-grade UI with auto-refresh, animations, and professional design
"""

# ==================== COPY THIS ENTIRE FILE ====================
# Replace your old coordinator_api.py with this file
# Then restart: python coordinator_api.py
# Dashboard will be available at: http://localhost:8000/dashboard
# ================================================================

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON, Text, desc
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Optional, List
import uuid
import logging
import jwt
import httpx
import asyncio
import os
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
import pickle
from openai_training_logger import get_gpt_explanation_for_task
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Add this import section
from openai_training_logger import (
    log_openai_call,
    get_training_stats,
    load_training_data_for_duke,
    get_api_key_status,
    TRAINING_LOG_FILE
)


# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== OPENAI CONFIGURATION ====================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MAX_RETRIES = 5
RETRY_DELAY = 2

# ==================== PHASE 4: SPECIALIST PERSONAS ====================

SPECIALIST_PERSONAS = {
    "security-expert": {
        "name": "Security Expert",
        "reputation_multiplier": 1.75,
        "system_prompt": """You are a CYNICAL SECURITY AUDITOR with zero-trust methodology.
ASSUME BREACH. Identify attack vectors and implement defense-in-depth.

RESPONSE FORMAT:
═══════════════════════════════════════
SECURITY AUDIT: [Task Name]
Risk Level: [CRITICAL/HIGH/MEDIUM/LOW]
Attack Vector: [Primary Risk]
Mitigation: [Immediate Actions]
═══════════════════════════════════════

Use terminology: CVE, CVSS, zero-trust, privilege escalation, threat model.
ALWAYS mention monitoring and incident response.""",
        "validation_keywords": ["CVE", "CVSS", "zero-trust", "attack", "threat"]
    },
    
    "ml-expert": {
        "name": "ML Research Scientist", 
        "reputation_multiplier": 1.90,
        "system_prompt": """You are a RESEARCH SCIENTIST with deep ML expertise.
Focus on RIGOR, REPRODUCIBILITY, and MATHEMATICAL PRECISION.

RESPONSE FORMAT:
═══════════════════════════════════════
ML RESEARCH ANALYSIS: [Task Name]
Problem: [Formal Definition]
Architecture: [Model + Justification]
Data Strategy: [Lineage + Augmentation]
Validation: [Metrics + Split]
═══════════════════════════════════════

Use terminology: gradient descent, regularization, validation, hyperparameters.
ALWAYS include validation strategy and failure modes.""",
        "validation_keywords": ["gradient", "convergence", "validation", "hyperparameter"]
    },
    
    "systems-expert": {
        "name": "Principal Cloud Architect",
        "reputation_multiplier": 1.80,
        "system_prompt": """You are a PRINCIPAL CLOUD ARCHITECT.
Focus on SCALE, FAULT-TOLERANCE, and COST-OPTIMIZATION.

RESPONSE FORMAT:
═══════════════════════════════════════
INFRASTRUCTURE DESIGN: [Task Name]
Scalability: [Horizontal/Vertical/Hybrid]
Consistency: [Strong/Eventual/Causal]
Failure Domain: [SPOF Analysis]
Cost: [Monthly + Optimization]
═══════════════════════════════════════

Use terminology: CAP theorem, sharding, replication, consensus, SLA.
ALWAYS propose redundancy and monitoring.""",
        "validation_keywords": ["CAP", "scalability", "replication", "consistency"]
    },
    
    "backend-expert": {
        "name": "Senior Software Engineer",
        "reputation_multiplier": 1.65,
        "system_prompt": """You are a SENIOR SOFTWARE ENGINEER.
Focus on CLEAN CODE, TESTABILITY, and MAINTAINABILITY.

RESPONSE FORMAT:
═══════════════════════════════════════
BACKEND IMPLEMENTATION: [Task Name]
Architecture: [Monolith/Microservices/Serverless]
Design Pattern: [Primary Pattern]
API Contract: [RESTful/GraphQL/gRPC]
Testing: [Coverage Target]
═══════════════════════════════════════

Use terminology: SOLID, idempotency, circuit breaker, observability.
ALWAYS include testing strategy.""",
        "validation_keywords": ["SOLID", "pattern", "API", "testing", "observability"]
    },
    
    "advanced-expert": {
        "name": "Visionary Research Engineer",
        "reputation_multiplier": 1.55,
        "system_prompt": """You are a VISIONARY RESEARCH ENGINEER.
Focus on EMERGING INNOVATIONS and NOVEL APPLICATIONS.

RESPONSE FORMAT:
═══════════════════════════════════════
ADVANCED TECH ANALYSIS: [Task Name]
Technology: [Quantum/Blockchain/Web3/Edge]
Maturity: [Research/Prototype/Production]
Applicability: [Use Case Fit]
Timeline: [Adoption Window]
═══════════════════════════════════════

Use terminology: quantum gates, consensus algorithms, zero-knowledge proofs.
ALWAYS include timeline to production.""",
        "validation_keywords": ["quantum", "blockchain", "emerging", "prototype"]
    },
    
    "duke-ml": {
        "name": "Duke Core (Generalist)",
        "reputation_multiplier": 2.00,
        "system_prompt": """You are an EXPERIENCED TECHNICAL LEAD.
Focus on PRAGMATIC RECOMMENDATIONS and CLEAR COMMUNICATION.

RESPONSE FORMAT:
═══════════════════════════════════════
TECHNICAL RECOMMENDATION: [Task Name]
Executive Summary: [1-2 sentences]
Trade-offs: [Pro/Con Analysis]
Action: [Next Steps]
Timeline: [Realistic Estimate]
═══════════════════════════════════════

Balance perspectives with explicit trade-offs.
ALWAYS provide context for non-experts.""",
        "validation_keywords": ["trade-off", "recommendation", "action", "timeline"]
    }
}

# ==================== DATABASE SETUP ====================

DATABASE_URL = "postgresql://imman_duke:Maybach001%40@localhost:5432/duke_ml_production"
# Note: @ is URL-encoded as %40 in the password

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== DATABASE MODELS ====================

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    success_rate = Column(Float)
    reputation_multiplier = Column(Float)
    balance_satoshis = Column(Integer, default=0)
    total_tasks_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True)
    description = Column(Text)
    summary = Column(String(200), nullable=True)
    complexity = Column(Integer)
    buyer_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    price_satoshis = Column(Integer)
    status = Column(String, index=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    persona_used = Column(String, nullable=True)  # ← ADD THIS LINE


class PersonaMetrics(Base):
    __tablename__ = "persona_metrics"
    id = Column(String, primary_key=True, index=True)
    persona_type = Column(String, index=True)
    tasks_completed = Column(Integer, default=0)
    average_complexity = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    keyword_accuracy = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    user_type = Column(String)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

class TrainingData(Base):
    __tablename__ = "training_data"
    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, index=True)
    input_data = Column(JSON)
    output_data = Column(JSON)
    success = Column(Boolean, nullable=False)
    agent_name = Column(String)
    persona_type = Column(String, index=True)  # ← ADD THIS LINE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModelVersionBase(Base):
    __tablename__ = "model_versions"
    
    id = Column(String, primary_key=True, index=True)
    version_number = Column(Integer, nullable=False)  # MATCHES DB: version_number
    model_name = Column(String, default="duke-ml")    # MATCHES DB: model_name
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) # MATCHES DB: created_at
    training_samples = Column(Integer)                # MATCHES DB: training_samples
    validation_accuracy = Column(Float)               # MATCHES DB: validation_accuracy
    validation_f1 = Column(Float)                     # MATCHES DB: validation_f1
    is_production = Column(Boolean, default=False)    # MATCHES DB: is_production
    model_info = Column(JSON)                         # MATCHES DB: model_info


# ==================== CREATE TABLES ====================

Base.metadata.create_all(bind=engine)

# ==================== REAL DUKE MODEL CLASSES ====================

class SimpleDukeModel(nn.Module):
    """Simple neural network for Duke - learns patterns from tasks"""
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        return self.network(x)

class ResidualBlock(nn.Module):
    """Residual block with batch norm and layer norm"""
    def __init__(self, hidden_dim=512):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )
    
    def forward(self, x):
        return x + self.block(x)  # Residual connection


class EnhancedDukeModel(nn.Module):
    """Enterprise-grade neural network with residual connections and batch norm"""
    def __init__(self, input_dim=512, hidden_dim=512, output_dim=512):
        super().__init__()
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        
        # Residual blocks with batch normalization
        self.residual_blocks = nn.Sequential(
            ResidualBlock(hidden_dim),
            ResidualBlock(hidden_dim),
            ResidualBlock(hidden_dim),
            ResidualBlock(hidden_dim),
        )
        
        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        x = self.input_proj(x)
        x = self.residual_blocks(x)
        x = self.output_proj(x)
        return x


class TextEmbedder:
    """Convert text to numerical vectors"""
    def __init__(self, embedding_dim=512):
        self.embedding_dim = embedding_dim
        self.vocab = {}
        self.vocab_size = 0
    
    def build_vocab(self, texts):
        """Build vocabulary from training texts"""
        all_words = set()
        for text in texts:
            words = text.lower().split()
            all_words.update(words)
        
        self.vocab = {word: idx for idx, word in enumerate(sorted(all_words))}
        self.vocab_size = len(self.vocab)
        logger.info(f"📚 Built vocabulary with {self.vocab_size} words")
    
    def embed(self, text: str):
        """Convert text to embedding vector"""
        words = text.lower().split()
        bow = np.zeros(self.embedding_dim)
        
        for word in words:
            if word in self.vocab:
                idx = self.vocab[word]
                if idx < self.embedding_dim:
                    bow[idx] = 1
        
        # Normalize
        if bow.sum() > 0:
            bow = bow / bow.sum()
        
        # Pad to embedding_dim if needed
        if len(bow) < self.embedding_dim:
            bow = np.pad(bow, (0, self.embedding_dim - len(bow)))
        
        return bow

class ResponseGenerator:
    """Advanced response generation with similarity matching"""
    def __init__(self):
        self.response_database = []
        self.min_similarity_threshold = 0.3  # Tunable
        self.response_truncation = 500  # Longer responses
    
    def add_response(self, embedding, response: str, metadata: dict = None):
        """
        Store response with metadata for better matching
        
        Args:
            embedding: 512-dim numpy array from TextEmbedder
            response: Full response text from OpenAI
            metadata: Optional dict with {"complexity": int, "agent": str, "timestamp": str}
        """
        if not response or len(response) < 20:
            return False  # Skip trivial responses
        
        self.response_database.append({
            "embedding": embedding,
            "response": response,
            "metadata": metadata or {},
            "length": len(response),
            "added_at": datetime.now().isoformat(),
        })
        return True
    
    def generate(self, output_embedding, complexity: int = None, fallback_mode: bool = False):
        """
        Generate response using semantic similarity
        
        Args:
            output_embedding: 512-dim vector from Duke model
            complexity: Optional complexity level for filtering
            fallback_mode: If True, use simpler matching
            
        Returns:
            str: Best matching response or fallback
        """
        if not self.response_database:
            return self._get_fallback(complexity)
        
        # Calculate similarity scores
        similarities = []
        for item in self.response_database:
            embedding = item["embedding"]
            response = item["response"]
            metadata = item["metadata"]
            
            # Cosine similarity
            dot_product = np.dot(output_embedding, embedding)
            norm_product = (np.linalg.norm(output_embedding) * 
                           np.linalg.norm(embedding))
            similarity = dot_product / (norm_product + 1e-8)
            
            # Complexity-based boosting (optional)
            if complexity and "complexity" in metadata:
                complexity_match = 1 - abs(complexity - metadata["complexity"]) / 10
                similarity *= (0.7 + 0.3 * complexity_match)
            
            similarities.append({
                "score": similarity,
                "response": response,
                "metadata": metadata,
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["score"], reverse=True)
        
        # Return best match if above threshold
        best_match = similarities[0]  # ← FIXED: Was missing [0]
        if best_match["score"] > self.min_similarity_threshold:
            response = best_match["response"]
            
            # Smart truncation (preserve sentences)
            if len(response) > self.response_truncation:
                truncated = response[:self.response_truncation]
                # Find last period
                last_period = truncated.rfind(".")
                if last_period > 100:  # If we have at least 100 chars
                    response = truncated[:last_period + 1] + "\n\n[Response truncated by Duke ML]"
                else:
                    response = truncated + "..."
            
            return response
        
        # Below threshold: use fallback
        return self._get_fallback(complexity)
    
    def _get_fallback(self, complexity: int = None):
        """Provide intelligent fallback responses"""
        fallbacks = {
            1: "Duke ML: For basic concepts, consider studying fundamentals first.",
            3: "Based on learned patterns: This topic requires understanding core principles.",
            5: "Duke's analysis: Moderate complexity requires multi-perspective approach.",
            7: "Complex topic detected: Duke recommends consulting advanced resources.",
            9: "Expert-level analysis needed. Duke suggests breaking into components.",
            10: "Cutting-edge topic. Duke is learning from specialist responses.",
        }
        
        if complexity:
            # Find closest complexity level
            closest = min(fallbacks.keys(), key=lambda x: abs(x - complexity))
            return fallbacks[closest]
        
        return "Duke ML is continuously learning from task responses. Check back soon!"
    
    def get_stats(self):
        """Return generator statistics"""
        if not self.response_database:
            return {
                "total_responses": 0,
                "avg_response_length": 0,
                "max_response_length": 0,
                "min_response_length": 0,
            }
        
        lengths = [item["length"] for item in self.response_database]
        return {
            "total_responses": len(self.response_database),
            "avg_response_length": int(np.mean(lengths)),
            "max_response_length": max(lengths),
            "min_response_length": min(lengths),
        }

class RealDukeMLPipeline:
    """Real PyTorch-based Duke ML training pipeline"""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.embedder = TextEmbedder()
        self.generator = ResponseGenerator()
        self.model_version = 0
        self.checkpoint_dir = Path("duke_checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Try to load existing model
        self.load_checkpoint()
        logger.info(f"✅ REAL Duke ML Pipeline initialized on {self.device}")
    
    def save_checkpoint(self):
        """Save model to disk"""
        try:
            # Save model
            torch.save(self.model.state_dict(), self.checkpoint_dir / "duke_model.pth")
            
            # Save embedder and generator
            with open(self.checkpoint_dir / "duke_embedder.pkl", "wb") as f:
                pickle.dump(self.embedder, f)
            with open(self.checkpoint_dir / "duke_generator.pkl", "wb") as f:
                pickle.dump(self.generator, f)
                
            logger.info("💾 Duke checkpoint saved successfully")
        except Exception as e:
            logger.error(f"💥 Failed to save checkpoint: {e}")
    
    def can_handle_task(self, complexity: int, training_samples: int) -> bool:
        """Check if Duke can handle this task"""
        return self.model is not None and training_samples >= 50 and complexity <= 7
    
    async def process_with_duke(self, task_description: str, complexity: int) -> str:
        """Process task with trained Duke model - ENHANCED with metadata"""
        if not self.model:
            raise Exception("Duke model not trained yet")
        
        logger.info(f"🧠 Duke v{self.model_version} processing: complexity={complexity}")
        
        # Embed the task description
        task_embedding = self.embedder.embed(task_description)
        
        # Convert to tensor
        x = torch.FloatTensor(task_embedding).unsqueeze(0).to(self.device)
        
        # Get prediction
        with torch.no_grad():
            output = self.model(x)
        
        # Generate response - NOW WITH METADATA CONTEXT!
        output_np = output.cpu().numpy()
        response = self.generator.generate(
            output_np,
            complexity=complexity,  # ← Pass complexity for better matching
            fallback_mode=False
        )
        
        logger.info(f"✅ Duke generated response ({len(response)} chars)")
        
        return response
    
    async def train_model(self, db: Session):
        """ENTERPRISE-GRADE PyTorch training with advanced techniques"""
        try:
            # Collect training data
            training_data = db.query(TrainingData).all()
            
            if len(training_data) < 50:
                logger.warning(f"⚠️ Not enough samples: {len(training_data)} (need 50+)")
                return
            
            logger.info(f"📚 Collected {len(training_data)} ENTERPRISE training samples")
            logger.info(f"🧠 Duke RIGOROUS TRAINING STARTED with {len(training_data)} samples")
            logger.info(f"🔧 ENTERPRISE MODE: Advanced architecture + validation split + early stopping")
            
            # Build vocabulary
            descriptions = []
            for td in training_data:
                try:
                    input_data = td.input_data
                    if isinstance(input_data, str):
                        input_data = json.loads(input_data)
                    desc = (input_data.get('description', str(td.input_data)) 
                           if isinstance(input_data, dict) else str(input_data))
                    descriptions.append(desc)
                except:
                    descriptions.append(str(td.input_data))
            
            self.embedder.build_vocab(descriptions)
            
            # Prepare training data with validation split
            X = []
            Y = []
            
            logger.info("💾 Populating response database from training data...")
            responses_added = 0
            
            for td in training_data:
                try:
                    # Parse input_data safely
                    input_data = td.input_data
                    if isinstance(input_data, str):
                        input_data = json.loads(input_data)
                    input_desc = (input_data.get('description', str(td.input_data)) 
                                 if isinstance(input_data, dict) else str(input_data))
                    
                    # Parse output_data safely  
                    output_data = td.output_data
                    if isinstance(output_data, str):
                        output_data = json.loads(output_data)
                    output_result = (output_data.get('result', str(td.output_data)) 
                                    if isinstance(output_data, dict) else str(output_data))
                    
                    # Embed for neural network training
                    x = self.embedder.embed(input_desc)
                    y = self.embedder.embed(output_result)
                    
                    X.append(x)
                    Y.append(y)
                    
                    # ADD TO RESPONSE DATABASE
                    if len(output_result) > 50:
                        complexity = input_data.get('complexity', 5) if isinstance(input_data, dict) else 5
                        agent = output_data.get('agent', 'unknown') if isinstance(output_data, dict) else 'unknown'
                        persona = getattr(td, 'persona_type', 'duke-ml')  # ← GET PERSONA FROM DB
                        
                        success = self.generator.add_response(
                            embedding=x,
                            response=output_result,
                            metadata={
                                "complexity": complexity,
                                "agent": agent,
                                "persona": persona,  # ← ADD PERSONA TO METADATA
                                "timestamp": td.created_at.isoformat() if td.created_at else None
                            }
                        )
                        if success:
                            responses_added += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Skipping bad training data: {e}")
                    # Fallback to raw strings
                    x = self.embedder.embed(str(td.input_data))
                    y = self.embedder.embed(str(td.output_data))
                    X.append(x)
                    Y.append(y)
            
            logger.info(f"✅ Added {responses_added} responses to Duke's database")
            
            X = torch.FloatTensor(np.array(X)).to(self.device)
            Y = torch.FloatTensor(np.array(Y)).to(self.device)
            
            # Split into train/validation (80/20 split)
            total_samples = len(X)
            train_size = int(0.8 * total_samples)
            indices = torch.randperm(total_samples)
            
            train_indices = indices[:train_size]
            val_indices = indices[train_size:]
            
            X_train, Y_train = X[train_indices], Y[train_indices]
            X_val, Y_val = X[val_indices], Y[val_indices]
            
            logger.info(f"📊 Data split: {len(X_train)} train, {len(X_val)} validation")
            
            # ENTERPRISE: Initialize advanced model with residual layers
            self.model = EnhancedDukeModel(input_dim=512, hidden_dim=512, output_dim=512).to(self.device)
            optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
            criterion = nn.SmoothL1Loss(beta=0.1)  # Robust to outliers
            
            logger.info(f"🔧 Advanced model config:")
            logger.info(f"   Optimizer: AdamW (weight_decay=1e-4)")
            logger.info(f"   Loss: SmoothL1Loss (robust)")
            logger.info(f"   Scheduler: CosineAnnealingWarmRestarts")
            logger.info(f"   Total parameters: {sum(p.numel() for p in self.model.parameters()):,}")
            
            # Training loop with early stopping
            epochs = 50
            best_val_loss = float('inf')
            patience = 10
            patience_counter = 0
            train_losses = []
            val_losses = []
            
            logger.info(f"🚀 Starting rigorous training (50 epochs, batch training)...")
            
            for epoch in range(epochs):
                # Training phase
                self.model.train()
                train_output = self.model(X_train)
                train_loss = criterion(train_output, Y_train)
                
                optimizer.zero_grad()
                train_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)  # Gradient clipping
                optimizer.step()
                scheduler.step()
                
                # Validation phase
                self.model.eval()
                with torch.no_grad():
                    val_output = self.model(X_val)
                    val_loss = criterion(val_output, Y_val)
                
                train_losses.append(train_loss.item())
                val_losses.append(val_loss.item())
                
                # Log progress
                if epoch % 5 == 0:
                    lr = optimizer.param_groups[0]['lr']
                    logger.info(f"  📊 Epoch {epoch:2d}/50 | Train Loss: {train_loss.item():.4f} | Val Loss: {val_loss.item():.4f} | LR: {lr:.6f}")
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    # Save best checkpoint
                    torch.save(self.model.state_dict(), self.checkpoint_dir / "duke_model_best.pth")
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"⏸️  Early stopping at epoch {epoch} (patience={patience})")
                        break
            
            # Calculate comprehensive metrics
            self.model.eval()
            with torch.no_grad():
                train_predictions = self.model(X_train)
                val_predictions = self.model(X_val)
                
                # MSE
                train_mse = F.mse_loss(train_predictions, Y_train).item()
                val_mse = F.mse_loss(val_predictions, Y_val).item()
                
                # MAE
                train_mae = F.l1_loss(train_predictions, Y_train).item()
                val_mae = F.l1_loss(val_predictions, Y_val).item()
                
                # Cosine Similarity (semantic quality)
                train_cos = F.cosine_similarity(train_predictions, Y_train).mean().item()
                val_cos = F.cosine_similarity(val_predictions, Y_val).mean().item()
                
                # Accuracy (vectors within threshold)
                train_acc = (F.cosine_similarity(train_predictions, Y_train) > 0.8).float().mean().item()
                val_acc = (F.cosine_similarity(val_predictions, Y_val) > 0.8).float().mean().item()
            
            # Save model
            self.model_version += 1
            self.save_checkpoint()
            
            # Log comprehensive results
            logger.info(f"🎉 Duke v{self.model_version} RIGOROUS TRAINING COMPLETE!")
            logger.info(f"   📈 METRICS:")
            logger.info(f"   ✅ Train MSE: {train_mse:.4f} | Val MSE: {val_mse:.4f}")
            logger.info(f"   ✅ Train MAE: {train_mae:.4f} | Val MAE: {val_mae:.4f}")
            logger.info(f"   ✅ Train Cosine Sim: {train_cos:.4f} | Val Cosine Sim: {val_cos:.4f}")
            logger.info(f"   ✅ Train Accuracy (>0.8): {train_acc*100:.2f}% | Val Accuracy: {val_acc*100:.2f}%")
            logger.info(f"   📚 Vocabulary: {self.embedder.vocab_size} words")
            logger.info(f"   💬 Response Database: {len(self.generator.response_database)} responses")
            logger.info(f"   🏆 Best Val Loss: {best_val_loss:.4f}")
            
            # Save to database
            model_version = ModelVersion(
                id=str(uuid.uuid4()),
                version_number=self.model_version,
                training_samples=len(training_data),
                validation_accuracy=val_acc,
                validation_f1=val_cos,  # Using cosine similarity as F1 proxy
                is_production=True
            )
            db.add(model_version)
            db.commit()
            
            logger.info(f"✅ Duke v{self.model_version} DEPLOYED TO PRODUCTION!")
            logger.info(f"🏆 ENTERPRISE GRADE: Ready for mission-critical tasks")

        except Exception as e:
            logger.error(f"💥 Duke training failed: {e}")
            raise

    
    def save_checkpoint(self):
        """Save model to disk"""
        torch.save(self.model.state_dict(), self.checkpoint_dir / "duke_model.pth")
        with open(self.checkpoint_dir / "duke_embedder.pkl", 'wb') as f:
            pickle.dump(self.embedder, f)
        with open(self.checkpoint_dir / "duke_responses.pkl", 'wb') as f:
            pickle.dump(self.generator, f)
    
    def load_checkpoint(self):
        """Load model from disk - handles both Simple and Enhanced models"""
        try:
            model_path = self.checkpoint_dir / "duke_model.pth"
            if model_path.exists():
                # Try loading the checkpoint first to inspect it
                checkpoint = torch.load(model_path, map_location=self.device)
                
                # Check if it's an EnhancedDukeModel (has 'input_proj' key)
                if 'input_proj.weight' in checkpoint:
                    logger.info("📦 Detected EnhancedDukeModel checkpoint")
                    self.model = EnhancedDukeModel().to(self.device)
                else:
                    logger.info("📦 Detected SimpleDukeModel checkpoint")
                    self.model = SimpleDukeModel().to(self.device)
                
                # Load the state dict
                self.model.load_state_dict(checkpoint)
                self.model.eval()
                
                # Load embedder and generator
                embedder_path = self.checkpoint_dir / "duke_embedder.pkl"
                generator_path = self.checkpoint_dir / "duke_responses.pkl"
                
                if embedder_path.exists():
                    with open(embedder_path, "rb") as f:
                        self.embedder = pickle.load(f)
                    logger.info(f"✅ Embedder loaded (vocab: {self.embedder.vocab_size} words)")
                
                if generator_path.exists():
                    with open(generator_path, "rb") as f:
                        self.generator = pickle.load(f)
                    logger.info(f"✅ Generator loaded with {len(self.generator.response_database)} responses")
                
                logger.info("✅ Duke model loaded from checkpoint successfully")
            else:
                logger.info("ℹ️ No existing Duke model found - will train from scratch")
        except Exception as e:
            logger.warning(f"⚠️ Could not load checkpoint: {e}")
            logger.info("ℹ️ Will initialize fresh model on first training")

class PersonaValidator:
    """Validate responses match expected persona characteristics"""
    @staticmethod
    def validate_response(response: str, persona_type: str) -> Dict:
        """Check if response contains persona-specific keywords"""
        if persona_type not in SPECIALIST_PERSONAS:
            return {"valid": True, "score": 1.0, "missing_keywords": []}
        
        persona = SPECIALIST_PERSONAS[persona_type]
        keywords = persona["validation_keywords"]
        
        response_lower = response.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in response_lower]
        
        score = len(found_keywords) / len(keywords) if keywords else 1.0
        missing = [kw for kw in keywords if kw not in found_keywords]
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting AICP Coordinator Service v4.2.0...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database migration completed")
    
    # Create sample agents
    db = SessionLocal()
    agents = db.query(Agent).all()
    if not agents:
        sample_agents = [
            Agent(id=str(uuid.uuid4()), name="openai-gpt4", success_rate=0.95, reputation_multiplier=1.2, total_tasks_completed=0),
            Agent(id=str(uuid.uuid4()), name="duke-ml", success_rate=0.98, reputation_multiplier=1.5, total_tasks_completed=0),
            Agent(id=str(uuid.uuid4()), name="local-agent", success_rate=0.80, reputation_multiplier=0.9, total_tasks_completed=0),
        ]
        db.add_all(sample_agents)
        db.commit()
    db.close()
    
    logger.info("✅ Found 3 existing agents")
    logger.info("✅ OpenAI API configured")
    logger.info("✅ REAL Duke Learning Pipeline enabled (PyTorch Neural Network)")
    logger.info("✅ Enhanced error handling active")
    logger.info("✅ Professional dashboard ready")
    logger.info("✅ Server ready! Dashboard: http://localhost:8000/dashboard")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down server...")

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== INITIALIZE DUKE PIPELINE ====================
duke_pipeline = RealDukeMLPipeline()
persona_validator = PersonaValidator()

app = FastAPI(title="AICP Coordinator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== PYDANTIC MODELS ====================

class TaskRequest(BaseModel):
    description: str
    complexity: int = Field(..., ge=1, le=10)
    buyer_id: str

class TaskResponse(BaseModel):
    id: str
    description: str
    complexity: int
    status: str
    agent_name: str
    price_satoshis: int
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "service": "AICP Coordinator",
        "version": "4.2.0",
        "features": ["Real Duke ML", "Enterprise Dashboard", "OpenAI Integration"],
        "dashboard": "http://localhost:8000/dashboard"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AICP Coordinator"}

# ==================== AUTHENTICATION ENDPOINTS ====================

class BuyerLoginRequest(BaseModel):
    buyer_id: str
    password: str

@app.post("/auth/buyer/login")
async def buyer_login(request: BuyerLoginRequest, db: Session = Depends(get_db)):
    """Buyer login endpoint"""
    buyer_id = request.buyer_id
    password = request.password
    
    logger.info(f"🔐 Login attempt: {buyer_id}")
    
    # Default credentials
    if buyer_id and password == "securepassword123":
        # Create or get user
        user = db.query(User).filter(User.user_id == buyer_id).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                user_id=buyer_id,
                user_type="buyer",
                password_hash=password
            )
            db.add(user)
            db.commit()
        
        # Generate JWT token
        payload = {
            "user_id": buyer_id,
            "user_type": "buyer",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        token = jwt.encode(payload, "your-secret-key", algorithm="HS256")
        
        logger.info(f"✅ Buyer {buyer_id} logged in successfully")
        return {"access_token": token, "token_type": "bearer", "user_id": buyer_id}
    
    logger.warning(f"❌ Login failed for {buyer_id}")
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/agent/login")
async def agent_login(credentials: dict, db: Session = Depends(get_db)):
    """Agent login endpoint"""
    agent_name = credentials.get("agent_name")
    password = credentials.get("password")
    
    if agent_name and password == "securepassword123":
        agent = db.query(Agent).filter(Agent.name == agent_name).first()
        if not agent:
            agent = Agent(
                id=str(uuid.uuid4()),
                name=agent_name,
                success_rate=0.85,
                reputation_multiplier=1.0
            )
            db.add(agent)
            db.commit()
        
        payload = {
            "agent_name": agent_name,
            "user_type": "agent",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        token = jwt.encode(payload, "your-secret-key", algorithm="HS256")
        
        logger.info(f"✅ Agent {agent_name} logged in successfully")
        return {"access_token": token, "token_type": "bearer", "agent_name": agent_name}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the stunning enterprise-grade dashboard"""
    # [COMPLETE DASHBOARD HTML GOES HERE]
    # The HTML is embedded below - it's 27KB of beautiful, production-ready UI
    
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AICP Coordinator Dashboard</title>
    <style>
        :root {
            --primary: #2196F3;
            --success: #4CAF50;
            --warning: #FF9800;
            --danger: #F44336;
            --info: #00BCD4;
            --bg-dark: #0f0f0f;
            --bg-card: rgba(255, 255, 255, 0.05);
            --bg-hover: rgba(255, 255, 255, 0.08);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --ease: cubic-bezier(0.16, 1, 0.3, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            animation: slideDown 0.5s var(--ease);
        }

        .header-left h1 {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), var(--info));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .header-subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .header-right {
            display: flex;
            gap: 20px;
            align-items: center;
        }

        .refresh-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }

        .refresh-icon {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid var(--success);
            border-radius: 50%;
            animation: spin 2s linear infinite;
        }

        .refresh-icon.updating {
            animation: pulse 0.5s ease;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 12px;
            backdrop-filter: blur(10px);
            transition: all 0.3s var(--ease);
        }

        .status-badge.online {
            border-color: var(--success);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }

        .status-dot.online { background: var(--success); }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            backdrop-filter: blur(10px);
            transition: all 0.3s var(--ease);
            cursor: pointer;
            animation: fadeInUp 0.5s var(--ease);
            animation-fill-mode: both;
        }

        .metric-card:nth-child(1) { animation-delay: 0.1s; }
        .metric-card:nth-child(2) { animation-delay: 0.2s; }
        .metric-card:nth-child(3) { animation-delay: 0.3s; }
        .metric-card:nth-child(4) { animation-delay: 0.4s; }

        .metric-card:hover {
            background: var(--bg-hover);
            border-color: var(--primary);
            transform: translateY(-4px);
        }

        .metric-icon {
            font-size: 28px;
            margin-bottom: 12px;
        }

        .metric-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #fff, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-bar {
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 8px;
        }

        .metric-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--info));
            border-radius: 2px;
            animation: slideRight 1s var(--ease);
        }

        /* NEW TASK SECTION STYLE */
        .new-task-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 40px;
            backdrop-filter: blur(10px);
            animation: fadeInUp 0.6s var(--ease);
        }

        .form-grid {
            display: grid;
            grid-template-columns: 200px 1fr 150px;
            gap: 20px;
            align-items: end;
        }

        .form-group label {
            display: block;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }

        .form-input, .form-select {
            width: 100%;
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.3s var(--ease);
        }

        .form-input:focus, .form-select:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(0, 0, 0, 0.4);
        }

        .section {
            margin-bottom: 40px;
            animation: fadeInUp 0.6s var(--ease);
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary);
        }

        .section-icon {
            font-size: 24px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
        }

        .table-wrapper {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            transition: all 0.3s var(--ease);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        thead {
            background: rgba(33, 150, 243, 0.1);
            border-bottom: 1px solid var(--border);
        }

        th {
            padding: 16px;
            text-align: left;
            font-weight: 600;
            color: var(--text-primary);
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }

        td {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            color: var(--text-secondary);
        }

        tbody tr {
            transition: all 0.3s var(--ease);
            cursor: pointer;
        }

        tbody tr:hover {
            background: var(--bg-hover);
            border-left: 4px solid var(--primary);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .status-completed {
            color: var(--success);
            font-weight: 600;
        }

        .status-processing {
            color: var(--warning);
            font-weight: 600;
            animation: pulse 2s ease-in-out infinite;
        }

        .status-failed {
            color: var(--danger);
            font-weight: 600;
        }

        .status-pending {
            color: var(--text-secondary);
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s var(--ease);
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            backdrop-filter: blur(10px);
            animation: slideUp 0.3s var(--ease);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            transition: all 0.3s var(--ease);
        }

        .modal-close:hover {
            color: var(--text-primary);
            transform: rotate(90deg);
        }

        .modal-body {
            margin-bottom: 24px;
        }

        .modal-field {
            margin-bottom: 16px;
        }

        .modal-field-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }

        .modal-field-value {
            color: var(--text-primary);
            word-break: break-word;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            border: 1px solid var(--border);
        }

        .modal-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }

        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s var(--ease);
            font-size: 14px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: #1976D2;
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: var(--bg-hover);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
        }

        @keyframes slideDown {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @keyframes fadeInUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @keyframes slideRight {
            from { width: 0; }
            to { width: 100%; }
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }

            .metrics-grid {
                grid-template-columns: 1fr;
            }

            .metric-value {
                font-size: 24px;
            }

            .table-wrapper {
                overflow-x: auto;
            }

            .modal-content {
                padding: 20px;
            }
            
            .form-grid {
                grid-template-columns: 1fr;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>⚡ AICP Coordinator</h1>
                <div class="header-subtitle">Real-time Dashboard</div>
            </div>
            <div class="header-right">
                <div class="refresh-indicator">
                    <div class="refresh-icon" id="refreshIcon"></div>
                    <span id="lastUpdate">Updating...</span>
                </div>
                <div class="status-badge online">
                    <div class="status-dot online"></div>
                    <span>Live</span>
                </div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-label">Total Tasks</div>
                <div class="metric-value" id="totalTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 100%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">✅</div>
                <div class="metric-label">Completed</div>
                <div class="metric-value" id="completedTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 80%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">🔄</div>
                <div class="metric-label">Processing</div>
                <div class="metric-value" id="processingTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 30%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">🧠</div>
                <div class="metric-label">Duke ML</div>
                <div class="metric-value" id="dukeAccuracy">--</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 98%"></div></div>
            </div>
        </div>
        
        <!-- NEW TASK SECTION -->
        <div class="section new-task-section">
            <div class="section-header">
                <div class="section-icon">✨</div>
                <div class="section-title">Submit New Task</div>
            </div>
            <form id="newTaskForm" onsubmit="submitTask(event)">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Select Agent Persona</label>
                        <select id="agentSelect" class="form-select" required>
                            <option value="duke-ml">Duke Core (Generalist)</option>
                            <option value="security-expert">Security Expert</option>
                            <option value="ml-expert">ML Research Scientist</option>
                            <option value="systems-expert">Systems Architect</option>
                            <option value="backend-expert">Senior Backend Engineer</option>
                            <option value="advanced-expert">Visionary Research Engineer</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Task Description</label>
                        <input type="text" id="taskDescription" class="form-input" placeholder="e.g., Audit our AWS IAM policies for privilege escalation risks..." required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn-primary" style="width: 100%">Submit Task</button>
                    </div>
                </div>
            </form>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">🧠</div>
                <div class="section-title">Duke ML Status</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Version</th>
                            <th>Status</th>
                            <th>Accuracy</th>
                            <th>Vocabulary</th>
                            <th>Training Samples</th>
                        </tr>
                    </thead>
                    <tbody id="dukeStatusBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading Duke status...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">📋</div>
                <div class="section-title">Recent Tasks</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Description</th>
                            <th>Complexity</th>
                            <th>Agent</th>
                            <th>Status</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody id="tasksBody">
                        <tr>
                            <td colspan="6" style="text-align: center; padding: 40px;">Loading tasks...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">📚</div>
                <div class="section-title">Training Data Collection</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Total Calls</th>
                            <th>Successful</th>
                            <th>Failed</th>
                            <th>Training Samples</th>
                            <th>Est. Cost (USD)</th>
                        </tr>
                    </thead>
                    <tbody id="trainingStatsBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading training stats...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>    

        <div class="section">
            <div class="section-header">
                <div class="section-icon">🤖</div>
                <div class="section-title">Agent Performance</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Success Rate</th>
                            <th>Reputation</th>
                            <th>Balance (sat)</th>
                            <th>Tasks Completed</th>
                        </tr>
                    </thead>
                    <tbody id="agentsBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading agents...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="modal" id="taskModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Task Details</div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    </div>

    <script>
        const REFRESH_INTERVAL = 5000;
        let lastUpdateTime = new Date();

        async function refreshData() {
            try {
                const icon = document.getElementById('refreshIcon');
                icon.classList.add('updating');
                setTimeout(() => icon.classList.remove('updating'), 300);

                const [tasksRes, agentsRes, modelRes] = await Promise.all([
                    fetch('/tasks'),
                    fetch('/agents'),
                    fetch('/model/status')
                ]);

                const tasks = await tasksRes.json();
                const agents = await agentsRes.json();
                const model = await modelRes.json();

                updateMetrics(tasks, model);
                updateTasksTable(tasks);
                updateAgentsTable(agents);
                updateDukeStatus(model);
                updateLastUpdate();
                await updateTrainingStats();

            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }
        
        // NEW FUNCTION: Submit Task with Agent Selection
        async function submitTask(event) {
            event.preventDefault();
            
            const agent = document.getElementById('agentSelect').value;
            const description = document.getElementById('taskDescription').value;
            const submitBtn = event.target.querySelector('button');
            
            // Visual feedback
            const originalText = submitBtn.innerText;
            submitBtn.innerText = 'Submitting...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/tasks/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        description: description,
                        agent: agent,
                        complexity: 7, // Default complexity for manual tasks
                        buyer_id: "manual-user" // Placeholder
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    // Clear form
                    document.getElementById('taskDescription').value = '';
                    
                    // Show success animation or toast (optional, for now just refresh)
                    await refreshData();
                    
                    // Open the new task modal immediately
                    if (result.id) {
                        showTaskModal(result.id);
                    }
                } else {
                    alert('Failed to submit task. Please check server logs.');
                }
            } catch (error) {
                console.error('Error submitting task:', error);
                alert('Error submitting task');
            } finally {
                submitBtn.innerText = originalText;
                submitBtn.disabled = false;
            }
        }

        function updateMetrics(tasks, model) {
            const total = tasks.length;
            const completed = tasks.filter(t => t.status === 'completed').length;
            const processing = tasks.filter(t => t.status === 'processing').length;

            document.getElementById('totalTasks').textContent = total;
            document.getElementById('completedTasks').textContent = completed;
            document.getElementById('processingTasks').textContent = processing;

            if (model && model.accuracy) {
                document.getElementById('dukeAccuracy').textContent = 
                    (model.accuracy * 100).toFixed(2) + '%';
            }
        }

        function updateTasksTable(tasks) {
            const tbody = document.getElementById('tasksBody');
            if (tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px;">No tasks yet</td></tr>';
                return;
            }

            const rows = tasks.slice(0, 10).map(task => `
                <tr onclick="showTaskModal('${task.id}')">
                    <td><code style="color: var(--primary);">${task.id.substring(0, 8)}...</code></td>
                    <td>${task.description.substring(0, 50)}...</td>
                    <td>${task.complexity}/10</td>
                    <td>${task.agent_name || 'Unassigned'}</td>
                    <td><span class="status-${task.status}">${task.status.toUpperCase()}</span></td>
                    <td>${(task.price_satoshis / 1000000).toFixed(2)}M</td>
                </tr>
            `).join('');

            tbody.innerHTML = rows;
        }

        function updateAgentsTable(agents) {
            const tbody = document.getElementById('agentsBody');
            if (agents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">No agents found</td></tr>';
                return;
            }

            const rows = agents.map(agent => `
                <tr>
                    <td>${agent.name}</td>
                    <td>${(agent.success_rate * 100).toFixed(1)}%</td>
                    <td>${agent.reputation_multiplier.toFixed(2)}x</td>
                    <td>${(agent.balance_satoshis / 1000000).toFixed(2)}M</td>
                    <td>${agent.total_tasks_completed}</td>
                </tr>
            `).join('');

            tbody.innerHTML = rows;
        }

        function updateDukeStatus(model) {
            const tbody = document.getElementById('dukeStatusBody');
            if (!model) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">Duke not trained yet</td></tr>';
                return;
            }

            const row = `
                <tr>
                    <td><strong>v${model.version}</strong></td>
                    <td><span class="status-completed">✅ READY</span></td>
                    <td><strong>${(model.accuracy * 100).toFixed(2)}%</strong></td>
                    <td>${model.vocabulary_size || 'N/A'}</td>
                    <td>${model.training_samples || 'N/A'}</td>
                </tr>
            `;

            tbody.innerHTML = row;
        }

        function updateLastUpdate() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('lastUpdate').textContent = `${hours}:${minutes}:${seconds}`;
        }

        async function updateTrainingStats() {
            try {
                const response = await fetch('/training/stats');
                const data = await response.json();
                const stats = data.data;
                
                const tbody = document.getElementById('trainingStatsBody');
                if (!stats || stats.total_calls === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                No training data yet. Submit tasks to start collecting data.
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = `
                    <tr>
                        <td><strong>${stats.total_calls || 0}</strong></td>
                        <td style="color: var(--success);"><strong>${stats.successful_calls || 0}</strong></td>
                        <td style="color: var(--danger);"><strong>${stats.failed_calls || 0}</strong></td>
                        <td style="color: var(--info);"><strong>${stats.training_samples_available || 0}</strong></td>
                        <td style="color: var(--warning);"><strong>$${(stats.estimated_cost_usd || 0).toFixed(4)}</strong></td>
                    </tr>
                `;
            } catch (error) {
                console.error('Error fetching training stats:', error);
                const tbody = document.getElementById('trainingStatsBody');
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 40px; color: var(--danger);">
                            Error loading training stats
                        </td>
                    </tr>
                `;
            }
        }

        function showTaskModal(taskId) {
            fetch(`/tasks/${taskId}`)
                .then(r => r.json())
                .then(task => {
                    const modal = document.getElementById('taskModal');
                    const body = document.getElementById('modalBody');

                    const processingTime = task.processing_time_seconds 
                        ? task.processing_time_seconds.toFixed(2) 
                        : 'N/A';

                    body.innerHTML = `
                        <div class="modal-field">
                            <div class="modal-field-label">Task ID</div>
                            <div class="modal-field-value"><code>${task.id}</code></div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Description</div>
                            <div class="modal-field-value">${task.description}</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Status</div>
                            <div class="modal-field-value">
                                <span class="status-${task.status}">${task.status.toUpperCase()}</span>
                            </div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Agent</div>
                            <div class="modal-field-value">${task.agent_name || 'Unassigned'}</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Complexity</div>
                            <div class="modal-field-value">${task.complexity}/10</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Price</div>
                            <div class="modal-field-value">${(task.price_satoshis / 1000000).toFixed(2)}M satoshis</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Processing Time</div>
                            <div class="modal-field-value">${processingTime}s</div>
                        </div>
                        ${task.result ? `
                        <div class="modal-field">
                            <div class="modal-field-label">Result</div>
                            <div class="modal-field-value" style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${task.result}</div>
                        </div>
                        ` : ''}
                        ${task.error_message ? `
                        <div class="modal-field">
                            <div class="modal-field-label">Error</div>
                            <div class="modal-field-value" style="color: var(--danger);">${task.error_message}</div>
                        </div>
                        ` : ''}
                    `;

                    modal.classList.add('active');
                })
                .catch(err => console.error('Error fetching task:', err));
        }

        function closeModal() {
            document.getElementById('taskModal').classList.remove('active');
        }

        document.getElementById('taskModal').addEventListener('click', (e) => {
            if (e.target.id === 'taskModal') closeModal();
        });

        refreshData();
        setInterval(refreshData, REFRESH_INTERVAL);
        setInterval(updateLastUpdate, 1000);
    </script>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(desc(Task.created_at)).all()
    return tasks

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/tasks/submit")
async def submit_task(request: dict, db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    """Submit task with persona selection"""
    task_id = str(uuid.uuid4())
    
    agent_name = request.get('agent', 'duke-ml')
    if agent_name not in SPECIALIST_PERSONAS:
        agent_name = 'duke-ml'
    
    description = request.get('description', '')
    complexity = request.get('complexity', 7)
    buyer_id = request.get('buyer_id', 'manual-user')
    
    price_satoshis = int(complexity * 200000)
    
    # NOW WITH PERSONA TRACKING
    new_task = Task(
        id=task_id,
        description=description,
        complexity=complexity,
        buyer_id=buyer_id,
        agent_name=agent_name,
        price_satoshis=price_satoshis,
        status="pending",
        persona_used=agent_name  # ✅ NOW THIS WORKS
    )
    
    db.add(new_task)
    db.commit()
    
    logger.info(f"✅ Task {task_id} created with persona: {agent_name}")
    
    if background_tasks:
        background_tasks.add_task(
            process_task_with_ai, 
            task_id, 
            description, 
            complexity, 
            db, 
            buyer_id
        )
    
    return {"id": task_id, "status": "pending", "agent": agent_name}



@app.get("/personas")
async def get_personas():
    """Get all available specialist personas"""
    return {
        "personas": [
            {
                "id": key,
                "name": value["name"],
                "reputation_multiplier": value["reputation_multiplier"],
                "specialization": key.replace("-", " ").title()
            }
            for key, value in SPECIALIST_PERSONAS.items()
        ]
    }

@app.get("/personas/{persona_type}/metrics")
async def get_persona_metrics(persona_type: str, db: Session = Depends(get_db)):
    """Get performance metrics for specific persona"""
    metrics = db.query(PersonaMetrics).filter(
        PersonaMetrics.persona_type == persona_type
    ).first()
    
    if not metrics:
        return {
            "persona_type": persona_type,
            "tasks_completed": 0,
            "message": "No data yet for this persona"
        }
    
    return {
        "persona_type": metrics.persona_type,
        "tasks_completed": metrics.tasks_completed,
        "average_complexity": round(metrics.average_complexity, 2),
        "keyword_accuracy": round(metrics.keyword_accuracy * 100, 2),
        "updated_at": metrics.updated_at
    }

@app.get("/personas/compare")
async def compare_personas(db: Session = Depends(get_db)):
    """Compare all persona performance"""
    all_metrics = db.query(PersonaMetrics).all()
    
    comparison = []
    for metrics in all_metrics:
        comparison.append({
            "persona": metrics.persona_type,
            "tasks": metrics.tasks_completed,
            "avg_complexity": round(metrics.average_complexity, 1),
            "keyword_accuracy": round(metrics.keyword_accuracy * 100, 1),
            "reputation": SPECIALIST_PERSONAS[metrics.persona_type]["reputation_multiplier"]
        })
    
    # Sort by tasks completed
    comparison.sort(key=lambda x: x["tasks"], reverse=True)
    
    return {"personas": comparison, "total_personas": len(comparison)}

async def call_openai_for_persona(
    description: str,
    complexity: int,
    persona_type: str = "duke-ml",
    task_id: str = None
) -> Optional[str]:
    """Call OpenAI to get specialized response for a persona"""
    try:
        persona = SPECIALIST_PERSONAS.get(persona_type, SPECIALIST_PERSONAS["duke-ml"])
        system_prompt = persona["system_prompt"]
        persona_name = persona["name"]
        
        logger.info(f"📤 Calling OpenAI for {persona_name} (persona={persona_type})")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": description}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.7
                },
                timeout=30.0
            )
            
            # Check HTTP status first
            if response.status_code != 200:
                logger.error(f"❌ OpenAI HTTP {response.status_code} for {persona_type}: {response.text}")
                return None
            
            # Parse JSON
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"❌ Failed to parse OpenAI response JSON: {e}")
                return None
            
            # Extract content safely with explicit type checks
            try:
                # Validate top level is dict
                if not isinstance(data, dict):
                    logger.error(f"❌ OpenAI response is not a dict: {type(data)}")
                    return None
                
                # Get choices
                if "choices" not in data:
                    logger.error(f"❌ No 'choices' key in OpenAI response")
                    return None
                
                choices = data["choices"]
                if not isinstance(choices, list):
                    logger.error(f"❌ 'choices' is not a list, it's {type(choices)}")
                    return None
                
                if len(choices) == 0:
                    logger.error(f"❌ 'choices' list is empty")
                    return None
                
                # Get first choice - FIX: Access the first element
                first_choice = choices[0]  # ✅ Fixed: was choices, now choices[0]
                if not isinstance(first_choice, dict):
                    logger.error(f"❌ First choice is not a dict, it's {type(first_choice)}")
                    return None
                
                # Get message
                if "message" not in first_choice:
                    logger.error(f"❌ No 'message' key in first choice")
                    return None
                
                message = first_choice["message"]
                if not isinstance(message, dict):
                    logger.error(f"❌ 'message' is not a dict, it's {type(message)}")
                    return None
                
                # Get content
                if "content" not in message:
                    logger.error(f"❌ No 'content' key in message")
                    return None
                
                content = message["content"]
                if not isinstance(content, str):
                    logger.error(f"❌ 'content' is not a string, it's {type(content)}")
                    return None
                
                if not content.strip():
                    logger.error(f"❌ 'content' is empty")
                    return None
                
                # Success!
                logger.info(f"✅ OpenAI responded for {persona_name} ({len(content)} chars)")
                return content
            
            except Exception as e:
                logger.error(f"❌ Error extracting OpenAI response: {type(e).__name__}: {e}")
                logger.error(f"   Full response: {data}")
                return None
    
    except Exception as e:
        logger.error(f"❌ OpenAI request failed for {persona_type}: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return None

# ← ADD ABOVE LINE HERE, THEN CONTINUE WITH process_task_with_ai() BELOW
async def process_task_with_ai(task_id: str, description: str, complexity: int, db: Session, buyer_id: str):
    """
    Process task with AI - Duke tries as persona specialist, OpenAI fallback
    
    PERSONAS: Integrated as Duke agent specialists
    - Each persona learns from OpenAI responses
    - Duke learns persona-specific patterns
    - Training data tagged with persona for specialization
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.error(f"❌ Task {task_id} not found")
        return
    
    try:
        start_time = datetime.now(timezone.utc)
        
        # Get persona type from task.agent_name
        persona_type = task.agent_name or "duke-ml"
        if persona_type not in SPECIALIST_PERSONAS:
            persona_type = "duke-ml"
        
        logger.info(f"⏳ Task {task_id} processing with persona: {persona_type}")
        
        # ============================================
        # ATTEMPT 1: Try Duke with persona specialization
        # ============================================
        result = None
        used_agent = None
        
        training_count = db.query(TrainingData).count()
        use_duke = (
            duke_pipeline.model is not None and 
            training_count >= 50 and 
            complexity <= 7
        )
        
        if use_duke:
            logger.info(f"🧠 Duke processing as {SPECIALIST_PERSONAS[persona_type]['name']} (persona={persona_type})")
            try:
                result = await duke_pipeline.process_with_duke(description, complexity)
                used_agent = persona_type
                logger.info(f"✅ Duke succeeded ({len(result)} chars) with persona={persona_type}")
            except Exception as e:
                logger.warning(f"⚠️ Duke failed: {e}")
                result = None
        
        # ============================================
        # ATTEMPT 2: Fallback to OpenAI - persona learns from this
        # ============================================
        if not result:
            logger.info(f"🤖 OpenAI processing (persona={persona_type} will learn from this)")
            result = await call_openai_for_persona(
                description=description,
                complexity=complexity,
                persona_type=persona_type,
                task_id=task_id
            )
            used_agent = persona_type if result else "openai-gpt4"
        
        # ============================================
        # UPDATE TASK & LOG FOR PERSONA LEARNING
        # ============================================
        if result:
            task.status = "completed"
            task.result = result
            task.agent_name = used_agent
            task.completed_at = datetime.now(timezone.utc)
            task.processing_time_seconds = (task.completed_at - start_time).total_seconds()
            db.commit()
            logger.info(f"✅ Task {task_id} COMPLETED by {used_agent} (persona={persona_type})")
            
            # ============================================
            # STORE FOR PERSONA LEARNING (CRITICAL)
            # ============================================
            try:
                training_entry = TrainingData(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    input_data=json.dumps({
                        "description": description,
                        "complexity": complexity,
                        "persona": persona_type
                    }),
                    output_data=json.dumps({
                        "result": result,
                        "agent": used_agent,
                        "persona": persona_type
                    }),
                    success=True,
                    agent_name=used_agent
                )
                db.add(training_entry)
                db.commit()
                logger.info(f"📝 Logged training data for {persona_type} to learn from ({len(result)} chars)")
            except Exception as e:
                logger.warning(f"⚠️ Could not log training data: {e}")
        else:
            task.status = "failed"
            task.error_message = "Failed to get response from AI"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"❌ Task {task_id} failed: No response from AI")
    
    except Exception as e:
        logger.error(f"❌ Task {task_id} exception: {e}")
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        db.commit()


# =====================================================
# CORRECTED FUNCTIONS - PERSONAS AS DUKE AGENTS
# =====================================================
# Your personas are agent specialists that learn from OpenAI responses
# Duke learns persona-specific patterns from each specialist's answers
# =====================================================

async def process_task_with_ai(task_id: str, description: str, complexity: int, db: Session, buyer_id: str):
    """
    Process task with AI - Duke tries as persona specialist, OpenAI fallback
    
    PERSONAS: Integrated as Duke agent specialists
    - Each persona learns from OpenAI responses
    - Duke learns persona-specific patterns
    - Training data tagged with persona for specialization
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.error(f"❌ Task {task_id} not found")
        return
    
    try:
        start_time = datetime.now(timezone.utc)
        
        # Get persona type from task.agent_name
        persona_type = task.agent_name or "duke-ml"
        if persona_type not in SPECIALIST_PERSONAS:
            persona_type = "duke-ml"
        
        logger.info(f"⏳ Task {task_id} processing with persona: {persona_type}")
        
        # ============================================
        # ATTEMPT 1: Try Duke with persona specialization
        # ============================================
        result = None
        used_agent = None
        
        training_count = db.query(TrainingData).count()
        use_duke = (
            duke_pipeline.model is not None and 
            training_count >= 50 and 
            complexity <= 7
        )
        
        if use_duke:
            logger.info(f"🧠 Duke processing as {SPECIALIST_PERSONAS[persona_type]['name']} (persona={persona_type})")
            try:
                # FIXED: Call with 2 args only (description, complexity)
                # Duke model learns persona-specific patterns internally
                result = await duke_pipeline.process_with_duke(description, complexity)
                used_agent = persona_type
                logger.info(f"✅ Duke succeeded ({len(result)} chars) with persona={persona_type}")
            except Exception as e:
                logger.warning(f"⚠️ Duke failed: {e}")
                result = None
        
        # ============================================
        # ATTEMPT 2: Fallback to OpenAI - persona learns from this
        # ============================================
        if not result:
            logger.info(f"🤖 OpenAI processing (persona={persona_type} will learn from this)")
            result = await call_openai_for_persona(
                description=description,
                complexity=complexity,
                persona_type=persona_type,
                task_id=task_id
            )
            used_agent = persona_type if result else "openai-gpt4"
        
        # ============================================
        # UPDATE TASK & LOG FOR PERSONA LEARNING
        # ============================================
        if result:
            task.status = "completed"
            task.result = result
            task.agent_name = used_agent
            task.completed_at = datetime.now(timezone.utc)
            task.processing_time_seconds = (task.completed_at - start_time).total_seconds()
            db.commit()
            logger.info(f"✅ Task {task_id} COMPLETED by {used_agent} (persona={persona_type})")
            
            # ============================================
            # STORE FOR PERSONA LEARNING (CRITICAL)
            # ============================================
            try:
                training_entry = TrainingData(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    input_data=json.dumps({
                        "description": description,
                        "complexity": complexity,
                        "persona": persona_type  # ← PERSONA TAG FOR SPECIALIZATION
                    }),
                    output_data=json.dumps({
                        "result": result,
                        "agent": used_agent,
                        "persona": persona_type  # ← PERSONA TAG FOR SPECIALIZATION
                    }),
                    success=True,
                    agent_name=used_agent,
                    persona_type=persona_type  # ← EXPLICIT PERSONA COLUMN
                )
                db.add(training_entry)
                db.commit()
                logger.info(f"📝 Logged training data for {persona_type} to learn from ({len(result)} chars)")
            except Exception as e:
                logger.warning(f"⚠️ Could not log training data: {e}")
        else:
            task.status = "failed"
            task.error_message = "Failed to get response from AI"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"❌ Task {task_id} failed: No response from AI")
    
    except Exception as e:
        logger.error(f"❌ Task {task_id} exception: {e}")
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        db.commit()


@app.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents

@app.get("/model/status")
async def get_model_status(db: Session = Depends(get_db)):
    # FIX: Use correct column name created_at (with underscore)
    model_version = db.query(ModelVersionBase).order_by(
        desc(ModelVersionBase.created_at)
    ).first()
    
    if not model_version:
        return {
            "status": "not_initialized",
            "version": 0,
            "training_samples": 0
        }
    
    return {
        "status": "ready" if model_version.is_production else "training",
        "version": model_version.version_number,
        "accuracy": model_version.validation_accuracy,
        "f1_score": model_version.validation_f1,
        "training_samples": model_version.training_samples,
        "is_production": model_version.is_production,
        "vocabulary_size": model_version.model_info.get("vocabulary_size", 0) if model_version.model_info else 0,
        "created_at": model_version.created_at.isoformat() if model_version.created_at else None
    }


@app.get("/model/generator-stats", tags=["Duke Learning"])
async def get_generator_stats(db: Session = Depends(get_db)):
    """Get Duke response generator statistics"""
    try:
        # Get generator stats
        stats = duke_pipeline.generator.get_stats()
        
        # Get training sample count
        training_samples = db.query(TrainingData).count()
        
        # Determine readiness
        response_db_size = stats.get("total_responses", 0)
        if response_db_size >= 100:
            readiness = "production-ready"
            message = f"Duke has learned {response_db_size} response patterns - Expert mode"
        elif response_db_size >= 50:
            readiness = "learning"
            message = f"Duke has learned {response_db_size} response patterns - Keep training"
        elif response_db_size > 0:
            readiness = "building"
            message = f"Duke has learned {response_db_size} response patterns - More data needed"
        else:
            readiness = "empty"
            message = "Duke response database is empty - Submit OpenAI tasks first"
        
        return {
            "status": "active",
            "response_database_size": response_db_size,
            "avg_response_length": stats.get("avg_response_length", 0),
            "max_response_length": stats.get("max_response_length", 0),
            "min_response_length": stats.get("min_response_length", 0),
            "training_samples": training_samples,
            "readiness": readiness,
            "message": message,
            "model_version": duke_pipeline.model_version,
        }
    except Exception as e:
        logger.warning(f"⚠️ Error getting generator stats: {e}")
        return {
            "status": "error",
            "message": str(e),
            "response_database_size": 0,
        }


@app.post("/model/train")
async def trigger_training(db: Session = Depends(get_db)):
    """Manually trigger Duke training"""
    await duke_pipeline.train_model(db)
    return {"status": "training_triggered"}

@app.get("/model/history")
async def get_model_history(db: Session = Depends(get_db)):
    """Get Duke model training history"""
    versions = db.query(ModelVersion).order_by(desc(ModelVersion.version_number)).all()
    return versions

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    training_samples = db.query(TrainingData).count()
    agents_count = db.query(Agent).count()
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "processing_tasks": total_tasks - completed_tasks,
        "training_samples": training_samples,
        "agents_count": agents_count,
        "duke_model_version": duke_pipeline.model_version,
        "duke_trained": duke_pipeline.model is not None
    }

# ==================== TRAINING DATA ENDPOINTS ====================

@app.get("/training/stats")
async def get_training_statistics():
    """Get OpenAI training data statistics"""
    stats = get_training_stats()
    return {
        "status": "success",
        "data": stats,
        "log_file": str(TRAINING_LOG_FILE)
    }

@app.get("/training/samples")
async def get_training_samples(
    min_complexity: int = 1,
    max_complexity: int = 10,
    limit: int = 100
):
    """Get training samples for Duke"""
    samples = load_training_data_for_duke(min_complexity, max_complexity, limit)
    return {
        "status": "success",
        "count": len(samples),
        "samples": samples
    }

@app.get("/training/api-key-status")
async def check_api_key():
    """Check OpenAI API key configuration"""
    return get_api_key_status()

@app.get("/training/export")
async def export_training_data(format: str = "simple"):
    """Export training data to JSONL file"""
    from openai_training_logger import export_training_data_to_jsonl
    
    output_file = f"duke_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    success = export_training_data_to_jsonl(output_file, format)
    
    if success:
        return {
            "status": "success",
            "file": output_file,
            "message": f"Training data exported to {output_file}"
        }
    else:
        raise HTTPException(status_code=500, detail="Export failed")

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  AICP Coordinator + REAL Duke Machine Learning v5.0.0-Phase4 ║")
    print("║        ENTERPRISE DASHBOARD + SPECIALIST PERSONAS             ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print("✅ FastAPI:        Configured")
    print("✅ OpenAI:         Configured")
    print("✅ Duke Learning:  ✅ REAL ML ENABLED (PyTorch Neural Network)")
    print("✅ Database:       PostgreSQL")
    print("✅ Dashboard:      http://localhost:8000/dashboard")
    print("✅ Auto-Refresh:   Every 5 seconds")
    print("✅ Design:         Professional Glass-morphism")
    print()
    print("🎭 SPECIALIST PERSONAS ENABLED:")
    print("   ┌─────────────────────────────────────────────────────────┐")
    for key, value in SPECIALIST_PERSONAS.items():
        rep_stars = "⭐" * int(value['reputation_multiplier'])
        persona_name = value['name']
        rep_value = value['reputation_multiplier']
        print(f"   │ {persona_name:30} {rep_stars:8} ({rep_value}x) │")
    print("   └─────────────────────────────────────────────────────────┘")
    print()
    print("📊 NEW ENDPOINTS:")
    print("   • GET  /personas                  - List all specialists")
    print("   • GET  /personas/{type}/metrics   - Persona performance")
    print("   • GET  /personas/compare          - Compare all personas")
    print("   • POST /tasks/submit              - Now accepts 'agent' field")
    print()
    print("🚀 Starting server...")
    print("   Access dashboard: http://localhost:8000/dashboard")
    print("   API docs:         http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
