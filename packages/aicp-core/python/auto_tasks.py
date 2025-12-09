"""
AICP Coordinator Auto-Task Submitter + DukeNET Challenge
Advanced, diverse tasks including MULTIMODAL input for comprehensive Duke model training
Version 3.2 - Maximum Challenge, Generative & Multimodal Coverage
"""

import asyncio
import httpx
import json
import time
import random
import sys
from datetime import datetime
from typing import List, Dict, Optional

# ==================== CONFIGURATION ====================

COORDINATOR_URL = "http://localhost:8000"
BUYER_ID = "buyer-test-001"
# NOTE: The coordinator uses "securepassword123" by default for buyer login
PASSWORD = "securepassword123"

# ==================== ADVANCED TASK DATABASE ====================

# Basic/simple tasks
SIMPLE_TASKS = [
    {"description": "What is the speed of light in a vacuum?", "complexity": 1},
    {"description": "Define entropy in thermodynamics", "complexity": 2},
    {"description": "Explain what a blockchain hash is", "complexity": 2},
    {"description": "What is the function of mitochondria?", "complexity": 1},
    {"description": "What are prime numbers? Give 5 examples.", "complexity": 1},
    {"description": "What causes seasons on Earth?", "complexity": 2},
    {"description": "Define machine learning in one sentence", "complexity": 1},
    {"description": "Explain the difference between a heap and a stack in programming.", "complexity": 2},
    {"description": "What is the main purpose of a firewall?", "complexity": 1},
]

# Intermediate tasks
MODERATE_TASKS = [
    {"description": "Compare and contrast supervised and unsupervised learning, including real-world use cases for each", "complexity": 4},
    {"description": "Explain how DNS resolution works from typing a URL to loading a webpage", "complexity": 4},
    {"description": "Describe the ACID properties in database transactions with examples", "complexity": 4},
    {"description": "How does public key cryptography work? Explain the process of encrypting and decrypting messages", "complexity": 5},
    {"description": "Compare REST and GraphQL APIs - what are the advantages and disadvantages of each?", "complexity": 4},
    {"description": "Explain the CAP theorem in distributed systems with practical examples", "complexity": 5},
    {"description": "What is the difference between authentication and authorization? Provide implementation examples", "complexity": 3},
    {"description": "Describe how garbage collection works in modern programming languages", "complexity": 4},
    {"description": "Explain the Model-View-Controller (MVC) architecture pattern with a real application example", "complexity": 4},
    {"description": "What is eventual consistency in distributed databases? Provide use cases where it's acceptable", "complexity": 5},
    {"description": "Explain how JWT tokens work for authentication and their security considerations", "complexity": 4},
    {"description": "Analyze the trade-offs between monolithic and modular CSS architecture (BEM vs CSS-in-JS).", "complexity": 3},
    {"description": "Explain the concept of 'event sourcing' and when a developer should use it.", "complexity": 5},
]

# Advanced complex tasks
COMPLEX_TASKS = [
    {"description": "Design a scalable real-time notification system that can handle 1 million concurrent users. Include architecture, technology choices, and failure handling", "complexity": 7},
    {"description": "Analyze the ethical implications of AI-powered hiring systems. Cover bias, fairness, transparency, and regulatory considerations", "complexity": 6},
    {"description": "Explain the Byzantine Generals Problem and how blockchain consensus mechanisms solve it. Compare Proof of Work, Proof of Stake, and Practical Byzantine Fault Tolerance", "complexity": 7},
    {"description": "Design a distributed caching strategy for a global e-commerce platform. Address cache invalidation, consistency, and geographic distribution", "complexity": 7},
    {"description": "Analyze the trade-offs between microservices and monolithic architectures for a startup scaling from 10 to 100 engineers", "complexity": 6},
    {"description": "Explain how modern neural networks learn through backpropagation. Include gradient descent, loss functions, and optimization techniques", "complexity": 7},
    {"description": "Design a database schema and API for a social media platform with posts, comments, likes, and real-time feeds. Consider scalability to 100M users", "complexity": 7},
    {"description": "Analyze the security vulnerabilities in OAuth 2.0 and explain best practices for secure implementation in production systems", "complexity": 6},
    {"description": "Compare different load balancing algorithms (Round Robin, Least Connections, IP Hash, Weighted). When should each be used?", "complexity": 6},
    {"description": "Design a multi-region disaster recovery strategy for a financial application with 99.99% uptime requirement", "complexity": 7},
    {"description": "Explain how consensus algorithms work in distributed systems. Compare Raft, Paxos, and their practical applications", "complexity": 7},
    {"description": "Design an event-driven architecture for processing 100K transactions per second. Include message queues, dead letter queues, and monitoring.", "complexity": 7},
    {"description": "Explain the concept of Infrastructure as Code (IaC) and debate the merits of Ansible vs. Terraform.", "complexity": 6},
    {"description": "Analyze the difference between synchronous and asynchronous I/O and its performance impact on web servers.", "complexity": 6},
]

# Expert-level tasks
EXPERT_TASKS = [
    {"description": "Design a complete architecture for a real-time collaborative document editing system like Google Docs. Address conflict resolution with Operational Transformation or CRDTs, WebSocket scaling, presence detection, offline support, and performance optimization for documents with 1000+ concurrent editors", "complexity": 9},
    {"description": "Analyze the theoretical and practical limitations of current quantum computing approaches. Discuss qubit coherence, error correction, quantum supremacy claims, and realistic near-term applications beyond cryptography", "complexity": 9},
    {"description": "Design a comprehensive fraud detection system for a fintech platform processing $1B+ monthly. Include ML models, real-time decision engines, feature engineering, model monitoring, false positive handling, and regulatory compliance", "complexity": 10},
    {"description": "Propose a novel consensus mechanism for blockchain that solves the blockchain trilemma (security, scalability, decentralization). Analyze trade-offs, attack vectors, and compare with existing solutions like Ethereum 2.0 and Solana", "complexity": 10},
    {"description": "Design a global content delivery network architecture optimized for video streaming at Netflix scale. Address edge caching, origin shielding, adaptive bitrate streaming, DRM, CDN failover, and cost optimization across 200+ countries", "complexity": 9},
    {"description": "Design a distributed database system that provides strong consistency, high availability, and partition tolerance simultaneously. Explain how this challenges the CAP theorem and what trade-offs are actually being made", "complexity": 10},
    {"description": "Propose a comprehensive strategy for migrating a monolithic application with 10 million lines of code to microservices without downtime. Include strangler pattern implementation, data consistency during migration, team organization, and rollback strategies", "complexity": 9},
    {"description": "Design a privacy-preserving machine learning system using federated learning and differential privacy. Address model aggregation, privacy budgets, membership inference attacks, and practical deployment challenges", "complexity": 10},
    {"description": "Design a complete observability platform for microservices at scale. Include distributed tracing, log aggregation, metrics collection, anomaly detection, service dependency mapping, and root cause analysis automation", "complexity": 9},
    {"description": "Propose an advanced recommendation system architecture combining collaborative filtering, content-based filtering, and deep learning. Address cold start problems, diversity, explainability, and online learning", "complexity": 8},
    {"description": "Analyze the technical challenges of achieving true real-time AI inference at the edge (< 10ms latency). Discuss model compression, quantization, hardware acceleration, and trade-offs between accuracy and speed", "complexity": 9},
    {"description": "Design a comprehensive chaos engineering strategy for testing system resilience. Include fault injection techniques, blast radius control, observability requirements, and organizational practices for running experiments safely", "complexity": 8},
    {"description": "Analyze and design the core components of a high-performance, distributed key-value store (like Redis or Memcached), including replication, sharding, and eviction policies.", "complexity": 10},
    {"description": "Evaluate the viability of using Homomorphic Encryption for training sensitive medical models in a cloud environment. Discuss security benefits vs. computational overhead.", "complexity": 9},
    {"description": "Propose an MLOps platform design specifically for continuous integration and continuous training (CI/CD/CT) of the **Labelee Duke Model** itself.", "complexity": 10},
    # New expert-level additions to increase difficulty
    {"description": "Design a provably-correct live model update mechanism that guarantees zero downtime and bounded model inference staleness for a distributed real-time inference fleet", "complexity": 10},
    {"description": "Create a formal specification and verification plan for a safety-critical ML system (e.g., autonomous braking), covering specification, test oracles, and runtime monitors", "complexity": 10},
    {"description": "Architect a hardware-software co-design for sub-millisecond neural inference for transformer models, specifying memory hierarchy, interconnects, and scheduler algorithms", "complexity": 10},
]

MULTIMODAL_TASKS = [
    {
        "description": "Analyze an architecture diagram for potential scaling bottlenecks and summarize the findings in 5 bullet points.",
        "complexity": 9,
    },
    {
        "description": "Given an object detection dataset, identify which object category is most consistently mislabeled and explain why this might happen.",
        "complexity": 8,
    },
    {
        "description": "Translate the steps in a payment processing flow diagram into clear, executable Python-style pseudocode.",
        "complexity": 8,
    },
    {
        "description": "Generate three descriptive captions for a remote-sensing satellite image focusing on geographical features and potential climate impact.",
        "complexity": 7,
    },
    {
        "description": "Explain the function of the final EnhancedSpatialAttention layer in a deep learning model architecture used for image understanding.",
        "complexity": 7,
    },
    {
        "description": "Compare the data flow of a monolithic architecture versus a microservices architecture and outline the deployment differences.",
        "complexity": 6,
    },
    {
        "description": "Given a system performance chart, propose an optimization strategy to reduce latency under peak load.",
        "complexity": 9,
    },
    {
        "description": "Describe a security weakness you might see in an API request/response diagram and suggest how to fix it.",
        "complexity": 5,
    },
    {
        "description": "For a detailed image of an antique clock mechanism, describe the likely function of the largest gear and the forces acting on it.",
        "complexity": 7,
    },
    {
        "description": "Given a photo of a historical building facade, identify the architectural style and period and list likely construction materials.",
        "complexity": 6,
    },
    {
        "description": "Given a product hero image on an e-commerce page, propose three different marketing headlines targeting different customer segments.",
        "complexity": 5,
    },
    {
        "description": "Given a flow diagram of a business process, identify a logical error in the sequence and write the corrected order of steps.",
        "complexity": 9,
    },
    {
        "description": "Compare the sentiment of two competing news article headlines and summarize the likely political bias of each.",
        "complexity": 8,
    },
]


# New: Generative / synthetic data tasks (very difficult)
GENERATIVE_TASKS = [
    {"description": "Design a full synthetic data generation pipeline that creates realistic, privacy-preserving human motion capture data for training pose estimation models. Include data distributions, noise injection, labeled meta-fields, domain randomization scripts, and evaluation metrics.", "complexity": 10},
    {"description": "Create a generative model training plan to synthesize high-resolution satellite imagery for rare-event augmentation (e.g., flooding). Include model architecture, loss terms, geospatial consistency checks, and sample generation script pseudocode.", "complexity": 10},
    {"description": "Write a prompt engineering suite and generation policy for producing high-quality labeled synthetic medical radiology reports and corresponding image masks (for non-diagnostic research). Include data templates, label taxonomies, hallucination safeguards, and differential-privacy considerations.", "complexity": 10},
    {"description": "Produce a specification and example code for a procedural text-and-image generator that can create realistic product listings (images + descriptions + specs). Include how to enforce brand safety and anti-counterfeit heuristics.", "complexity": 9},
    {"description": "Design and provide pseudocode for an adversarial synthetic data generator that creates hard negative examples for an NLU intent classifier, and describe how to integrate it into continuous training with human-in-the-loop verification.", "complexity": 9},
    {"description": "Implement (pseudocode) a GAN-based system to produce synthetic network traffic logs for anomaly detection training. Include feature engineering, class balancing, and labeling heuristics.", "complexity": 9},
    {"description": "Generate 50 diverse, realistic prompts (and expected outputs) to be used as tests for a multilingual multimodal LLM. Cover at least 6 languages, 4 image types, and 3 domains (legal, medical, e-commerce).", "complexity": 9},
]

# Specialized domains
SPECIALIZED_DOMAINS = {
    "AI/ML": [
        {"description": "Explain the attention mechanism in transformers and why it revolutionized NLP. Compare with RNNs and LSTMs", "complexity": 7},
        {"description": "Design a recommendation system for an e-commerce platform that balances personalization with diversity and serendipity", "complexity": 6},
        {"description": "Analyze different approaches to handling imbalanced datasets in classification problems. Include SMOTE, class weights, and ensemble methods", "complexity": 6},
        {"description": "Explain how reinforcement learning works using Q-learning. Provide a practical example with a game or robotics application", "complexity": 7},
        {"description": "Design a computer vision pipeline for autonomous vehicle perception: object detection, tracking, sensor fusion, and decision making", "complexity": 9},
        {"description": "Explain the concept of Zero-shot and Few-shot learning in Large Language Models (LLMs).", "complexity": 8},
        {"description": "Compare the complexity and effectiveness of different activation functions (ReLU, Sigmoid, GeLU) in deep networks.", "complexity": 6},
    ],
    "Cloud/DevOps": [
        {"description": "Design a complete CI/CD pipeline for a microservices application with automated testing, security scanning, and progressive deployment", "complexity": 7},
        {"description": "Compare AWS, Azure, and GCP for hosting a data-intensive application. Consider compute, storage, networking, and pricing", "complexity": 6},
        {"description": "Design a Kubernetes cluster architecture for high availability including node pools, ingress, service mesh, and auto-scaling", "complexity": 8},
        {"description": "Analyze different deployment strategies: blue-green, canary, rolling updates, and feature flags. When should each be used?", "complexity": 6},
        {"description": "Explain infrastructure as code using Terraform. Design a multi-environment setup with proper state management", "complexity": 6},
        {"description": "Detail a strategy for serverless architecture security (e.g., AWS Lambda).", "complexity": 7},
        {"description": "Compare Docker Swarm with Kubernetes for container orchestration in terms of ease of use and scale.", "complexity": 6},
    ],
    "Security/Cryptography": [
        {"description": "Explain zero-knowledge proofs and how they enable privacy-preserving authentication. Provide a practical use case", "complexity": 8},
        {"description": "Analyze common web application vulnerabilities (OWASP Top 10) and provide mitigation strategies for each", "complexity": 6},
        {"description": "Design a secure multi-tenant SaaS application architecture ensuring complete data isolation between customers", "complexity": 7},
        {"description": "Explain homomorphic encryption and its potential applications in privacy-preserving cloud computing", "complexity": 8},
        {"description": "Design a security incident response plan for a data breach including detection, containment, eradication, and recovery", "complexity": 8},
        {"description": "Explain the difference between Symmetric and Asymmetric encryption and when to use each.", "complexity": 5},
        {"description": "Analyze the security vulnerabilities introduced by using outdated TLS/SSL protocols.", "complexity": 6},
    ],
    "Systems/Performance": [
        {"description": "Analyze the performance characteristics of different data structures: arrays, linked lists, trees, hash tables, and graphs", "complexity": 5},
        {"description": "Design a caching strategy for a high-traffic API. Include cache invalidation, TTL strategies, and cache warming", "complexity": 6},
        {"description": "Explain how database query optimization works. Analyze execution plans and indexing strategies for complex queries", "complexity": 7},
        {"description": "Design a solution for handling 10,000 requests per second with sub-100ms latency. Include load balancing and caching", "complexity": 8},
        {"description": "Analyze memory management in different programming languages: garbage collection, reference counting, and manual management", "complexity": 6},
        {"description": "Design a database sharding strategy for a social network with 100M users. Address data distribution and query routing", "complexity": 8},
        {"description": "Analyze the trade-offs between different serialization formats: JSON, Protocol Buffers, MessagePack, and Avro", "complexity": 5},
    ]
}

# Combine all challenging pools for Challenge Phase
CHALLENGE_POOL = COMPLEX_TASKS + EXPERT_TASKS + MULTIMODAL_TASKS + GENERATIVE_TASKS

# ==================== INTELLIGENT TASK GENERATION ====================

def generate_balanced_task_set(total_tasks: int) -> List[Dict]:
    """
    Generate a balanced set of tasks, including generative and multimodal pools.
    Distribution:
      - 12% simple
      - 20% moderate
      - 28% complex
      - 20% expert
      - 10% multimodal
      - 10% generative
    """
    num_simple = max(1, int(total_tasks * 0.12))
    num_moderate = max(1, int(total_tasks * 0.20))
    num_complex = max(1, int(total_tasks * 0.28))
    num_expert = max(1, int(total_tasks * 0.20))
    num_multimodal = max(0, int(total_tasks * 0.10))
    num_generative = total_tasks - (num_simple + num_moderate + num_complex + num_expert + num_multimodal)

    tasks: List[Dict] = []

    tasks.extend(random.sample(SIMPLE_TASKS, min(num_simple, len(SIMPLE_TASKS))))
    tasks.extend(random.sample(MODERATE_TASKS, min(num_moderate, len(MODERATE_TASKS))))
    tasks.extend(random.sample(COMPLEX_TASKS, min(num_complex, len(COMPLEX_TASKS))))
    tasks.extend(random.sample(EXPERT_TASKS, min(num_expert, len(EXPERT_TASKS))))
    tasks.extend(random.sample(MULTIMODAL_TASKS, min(num_multimodal, len(MULTIMODAL_TASKS))))
    if num_generative > 0 and len(GENERATIVE_TASKS) > 0:
        tasks.extend(random.sample(GENERATIVE_TASKS, min(num_generative, len(GENERATIVE_TASKS))))

    # If we didn't reach total_tasks due to small pools, fill from the hardest available tasks
    while len(tasks) < total_tasks:
        tasks.append(random.choice(EXPERT_TASKS + GENERATIVE_TASKS + MULTIMODAL_TASKS + COMPLEX_TASKS))

    random.shuffle(tasks)
    return tasks

def generate_domain_focused_tasks(domain: str, num_tasks: int) -> List[Dict]:
    """Generate tasks focused on a specific domain"""
    if domain == "Multimodal":
        available_tasks = MULTIMODAL_TASKS
    elif domain == "Generative":
        available_tasks = GENERATIVE_TASKS
    elif domain in SPECIALIZED_DOMAINS:
        available_tasks = SPECIALIZED_DOMAINS[domain]
    else:
        return []
    return random.sample(available_tasks, min(num_tasks, len(available_tasks)))

def generate_progressive_difficulty_tasks(num_tasks: int) -> List[Dict]:
    """
    Generate tasks with progressively increasing difficulty.
    """
    all_tasks = SIMPLE_TASKS + MODERATE_TASKS + COMPLEX_TASKS + EXPERT_TASKS + MULTIMODAL_TASKS + GENERATIVE_TASKS
    sorted_tasks = sorted(all_tasks, key=lambda x: x['complexity'])
    return sorted_tasks[:num_tasks]

# ==================== UTILITY FUNCTIONS (Login/Submit/Status) ====================

async def get_auth_token(buyer_id: str, password: str) -> Optional[str]:
    """Login as buyer and get auth token"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{COORDINATOR_URL}/auth/buyer/login",
                json={"buyer_id": buyer_id, "password": password}
            )

            if response.status_code != 200:
                print(f"❌ Login failed: {response.status_code} {response.text}")
                return None

            data = response.json()
            token = data.get("access_token")
            if not token:
                print("❌ No access_token returned from login.")
                return None

            print(f"✅ Logged in as: {buyer_id}")
            return token
        except Exception as e:
            print(f"❌ Login error: {e}")
            return None

async def submit_task(token: str, description: str, complexity: int, buyer_id: str) -> Optional[dict]:
    """Submit a single task"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{COORDINATOR_URL}/tasks/submit",
                json={
                    "description": description,
                    "complexity": complexity,
                    "buyer_id": buyer_id
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code != 200:
                print(f"❌ Failed to submit task (status {response.status_code}): {response.text[:200]}")
                return None

            return response.json()
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def get_system_status(token: str) -> Optional[dict]:
    """Get current Duke model status"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{COORDINATOR_URL}/model/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return None

async def get_stats(token: str) -> Optional[dict]:
    """Get comprehensive system statistics"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{COORDINATOR_URL}/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return None

def print_status(status: Optional[dict], stats: Optional[dict], tasks_submitted: int):
    """Print formatted system status"""
    print("\n" + "="*80)
    print("📊 SYSTEM STATUS")
    print("="*80)
    print(f"Tasks Submitted This Session: {tasks_submitted}")

    if stats:
        total_tasks = stats.get('total_tasks', 0)
        completed_tasks = stats.get('completed_tasks', 0)
        processing_tasks = stats.get('processing_tasks', 0)

        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        print(f"Total Tasks in System: {total_tasks}")
        print(f"  ✅ Completed: {completed_tasks} ({success_rate:.1f}%)")
        print(f"  ⟳ Processing: {processing_tasks}")

    if status:
        print(f"\n🧠 DUKE LEARNING STATUS")
        print("-" * 80)
        training_samples = status.get('training_samples', 0)
        print(f"Training Samples Collected: {training_samples}")

        if status.get('status') == 'untrained':
            print(f"Status: Untrained (needs more samples to begin training)")
        else:
            print(f"Model Version: v{status.get('version', 0)}")
            print(f"Accuracy: {status.get('accuracy', 0)*100:.2f}%")
            print(f"F1 Score: {status.get('f1_score', 0):.4f}")
            print(f"Production: {'✅ Yes' if status.get('is_production') else '❌ No'}")

    print("="*80 + "\n")

# ==================== SUBMISSION MODES ====================

async def smart_submit_balanced(
    num_tasks: int = 50,
    delay_between_tasks: float = 2.0,
    show_progress: bool = True
):
    """
    Submit a balanced mix of tasks, including multimodal and generative.
    """

    print("\n" + "="*80)
    print("🎯 SMART BALANCED SUBMISSION (v3.2 - Includes Generative & Multimodal)")
    print("="*80)
    print(f"Coordinator: {COORDINATOR_URL}")
    print(f"Tasks: {num_tasks} (balanced across difficulty levels)")
    print("="*80 + "\n")

    token = await get_auth_token(BUYER_ID, PASSWORD)
    if not token:
        return

    tasks = generate_balanced_task_set(num_tasks)

    submitted_count = 0
    complexity_counts: Dict[int, int] = {}

    for i, task in enumerate(tasks, 1):
        try:
            complexity = task['complexity']
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

            if show_progress:
                print(f"[{i}/{len(tasks)}] L{complexity} | {task['description'][:80]}...", end=" ", flush=True)

            result = await submit_task(
                token=token,
                description=task['description'],
                complexity=complexity,
                buyer_id=BUYER_ID
            )

            if result:
                if show_progress:
                    # assume response contains an 'id' when successful
                    print(f"✅ {result.get('id', '<no-id>')}")
                submitted_count += 1
            else:
                if show_progress:
                    print("❌")

            await asyncio.sleep(delay_between_tasks)

        except Exception as e:
            if show_progress:
                print(f"❌ Exception: {str(e)[:80]}")

    print(f"\n✅ Submitted {submitted_count}/{len(tasks)} tasks")
    print(f"\n📊 Complexity Distribution:")
    for level in sorted(complexity_counts.keys()):
        print(f"  Level {level}: {complexity_counts[level]} tasks")

    status = await get_system_status(token)
    stats = await get_stats(token)
    print_status(status, stats, submitted_count)

async def domain_focused_submission(
    domain: str,
    num_tasks: int = 20,
    delay_between_tasks: float = 2.0
):
    """
    Submit tasks focused on a specific domain (including 'Multimodal' and 'Generative')
    """

    print("\n" + "="*80)
    print(f"🎯 DOMAIN-FOCUSED SUBMISSION: {domain}")
    print("="*80)
    print(f"Tasks: {num_tasks}")
    print("="*80 + "\n")

    token = await get_auth_token(BUYER_ID, PASSWORD)
    if not token:
        return

    tasks = generate_domain_focused_tasks(domain, num_tasks)

    if not tasks:
        print(f"❌ Unknown domain: {domain}")
        available = list(SPECIALIZED_DOMAINS.keys()) + ["Multimodal", "Generative"]
        print(f"Available domains: {', '.join(available)}")
        return

    submitted_count = 0

    for i, task in enumerate(tasks, 1):
        try:
            print(f"[{i}/{len(tasks)}] L{task['complexity']} | {task['description'][:80]}...", end=" ", flush=True)

            result = await submit_task(
                token=token,
                description=task['description'],
                complexity=task['complexity'],
                buyer_id=BUYER_ID
            )

            if result:
                print(f"✅ {result.get('id', '<no-id>')}")
                submitted_count += 1
            else:
                print("❌")

            await asyncio.sleep(delay_between_tasks)

        except Exception as e:
            print(f"❌ {str(e)[:80]}")

    print(f"\n✅ Domain submission complete: {submitted_count}/{len(tasks)} tasks")

    status = await get_system_status(token)
    stats = await get_stats(token)
    print_status(status, stats, submitted_count)

async def progressive_training_session(
    num_tasks: int = 30,
    delay_between_tasks: float = 3.0
):
    """
    Submit tasks with progressively increasing difficulty
    Tests Duke's learning curve
    """

    print("\n" + "="*80)
    print("📈 PROGRESSIVE TRAINING SESSION")
    print("="*80)
    print(f"Tasks: {num_tasks} (increasing difficulty)")
    print("="*80 + "\n")

    token = await get_auth_token(BUYER_ID, PASSWORD)
    if not token:
        return

    tasks = generate_progressive_difficulty_tasks(num_tasks)

    submitted_count = 0

    for i, task in enumerate(tasks, 1):
        try:
            print(f"[{i}/{len(tasks)}] Level {task['complexity']:2d} | {task['description'][:72]}...", end=" ", flush=True)

            result = await submit_task(
                token=token,
                description=task['description'],
                complexity=task['complexity'],
                buyer_id=BUYER_ID
            )

            if result:
                print(f"✅ {result.get('id', '<no-id>')}")
                submitted_count += 1
            else:
                print("❌")

            await asyncio.sleep(delay_between_tasks)

        except Exception as e:
            print(f"❌ {str(e)[:80]}")

    print(f"\n✅ Progressive training complete: {submitted_count}/{len(tasks)} tasks")

    status = await get_system_status(token)
    stats = await get_stats(token)
    print_status(status, stats, submitted_count)

async def challenge_and_retrain(token: str):
    """
    Challenge Duke with highly complex, diverse tasks and immediately trigger training.
    """

    # 1. Select the top 5 most challenging tasks (Expert + Multimodal + Generative)
    tasks_to_challenge = random.sample(CHALLENGE_POOL, min(5, len(CHALLENGE_POOL)))

    print("\n🔥 CHALLENGE PHASE: Submitting 5 Highly Complex/Multimodal/Generative Tasks...")
    for i, task in enumerate(tasks_to_challenge, 1):
        print(f"[{i}/5] L{task['complexity']} | {task['description'][:80]}...", end=" ", flush=True)
        result = await submit_task(token, task['description'], task['complexity'], BUYER_ID)
        if result:
            print("✅")
        else:
            print("❌")
        await asyncio.sleep(0.5)

    # 2. Trigger immediate training on the new, challenging data
    print("\n📚 Triggering immediate Duke Training on accumulated data...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{COORDINATOR_URL}/model/train",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                print(f"✅ Training triggered successfully: {response.json().get('status')}")
            else:
                print(f"❌ Failed to trigger training: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Error triggering training: {e}")

    # 3. Check status immediately after
    status = await get_system_status(token)
    stats = await get_stats(token)
    print_status(status, stats, 5)
    print("✅ Challenge and Training Cycle Complete.")

async def continuous_learning_mode(
    duration_minutes: int = 30,
    tasks_per_minute: int = 2
):
    """
    Continuously submit tasks for extended training, focusing on challenging Duke.
    """

    print("\n" + "="*80)
    print("🔄 CONTINUOUS LEARNING MODE (v3.2)")
    print("="*80)
    print(f"Duration: {duration_minutes} minutes")
    print(f"Rate: {tasks_per_minute} tasks/minute")
    print(f"Total: ~{duration_minutes * tasks_per_minute} tasks")
    print("="*80 + "\n")

    token = await get_auth_token(BUYER_ID, PASSWORD)
    if not token:
        return

    start_time = datetime.now()
    end_time = start_time.timestamp() + (duration_minutes * 60)
    submitted_count = 0

    all_tasks = MODERATE_TASKS + COMPLEX_TASKS + EXPERT_TASKS + MULTIMODAL_TASKS + GENERATIVE_TASKS

    while time.time() < end_time:
        task = random.choice(all_tasks)

        try:
            print(f"[{submitted_count + 1}] L{task['complexity']} | {task['description'][:80]}...", end=" ", flush=True)

            result = await submit_task(
                token=token,
                description=task['description'],
                complexity=task['complexity'],
                buyer_id=BUYER_ID
            )

            if result:
                print("✅")
                submitted_count += 1
            else:
                print("❌")

            delay = 60.0 / tasks_per_minute
            await asyncio.sleep(delay)

            if submitted_count % 10 == 0 and submitted_count > 0:
                status = await get_system_status(token)
                if status:
                    samples = status.get('training_samples', 0)
                    if status.get('status') != 'untrained':
                        print(f"\n  📊 Training samples: {samples} | Duke v{status.get('version')} @ {status.get('accuracy', 0)*100:.1f}%")
                    else:
                        print(f"\n  📊 Training samples: {samples}")

        except Exception as e:
            print(f"❌ {str(e)[:120]}")

    print(f"\n\n✅ Continuous learning session complete!")
    print(f"Total tasks submitted: {submitted_count}")
    print(f"Duration: {(datetime.now() - start_time).seconds / 60:.1f} minutes")

    status = await get_system_status(token)
    stats = await get_stats(token)
    print_status(status, stats, submitted_count)

# ==================== CLI ====================

async def main():
    """Main entry point"""

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "balanced":
            num = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            await smart_submit_balanced(num_tasks=num)

        elif command == "domain":
            domain = sys.argv[2] if len(sys.argv) > 2 else "AI/ML"
            num = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            await domain_focused_submission(domain=domain, num_tasks=num)

        elif command == "progressive":
            num = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            await progressive_training_session(num_tasks=num)

        elif command == "continuous":
            minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            rate = int(sys.argv[3]) if len(sys.argv) > 3 else 2
            await continuous_learning_mode(duration_minutes=minutes, tasks_per_minute=rate)

        elif command == "challenge":
            token = await get_auth_token(BUYER_ID, PASSWORD)
            if token:
                await challenge_and_retrain(token)
            return

        elif command == "domains":
            print("\n📚 Available Specialized Domains (Including Multimodal & Generative):\n")
            domains = list(SPECIALIZED_DOMAINS.keys()) + ["Multimodal", "Generative"]
            for domain in domains:
                task_list = SPECIALIZED_DOMAINS.get(domain, MULTIMODAL_TASKS if domain == "Multimodal" else GENERATIVE_TASKS if domain == "Generative" else [])
                print(f"  • {domain}: {len(task_list)} tasks")
            print(f"\nUsage: python auto_tasks.py domain <domain_name> <num_tasks>")
            return

        else:
            print(f"❌ Unknown command: {command}")
            print("Use: balanced, domain, progressive, continuous, challenge, or domains")

    else:
        # Default: balanced submission with moderate-sized set
        await smart_submit_balanced(num_tasks=30)

# ==================== RUN ====================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║        ENHANCED AUTO-TASK SUBMITTER v3.2 - DUKE CHALLENGE EDITION          ║
║          Multimodal, Generative, and Expert Tasks for Deep Learning        ║
╚════════════════════════════════════════════════════════════════════════════╝

🎯 SUBMISSION MODES:

  1. BALANCED (Includes Generative & Multimodal)
     python auto_tasks.py balanced [num_tasks]

  2. DOMAIN-FOCUSED (Specialized training)
     python auto_tasks.py domain <domain> [num_tasks]
     → New domains available: Multimodal, Generative

  3. PROGRESSIVE (Learning curve testing)
     python auto_tasks.py progressive [num_tasks]

  4. CONTINUOUS (High-Stress Learning)
     python auto_tasks.py continuous [minutes] [tasks_per_minute]

  5. CHALLENGE (Instant MLOps Stress Test)
     python auto_tasks.py challenge

  6. LIST DOMAINS
     python auto_tasks.py domains
""")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting gracefully...")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
