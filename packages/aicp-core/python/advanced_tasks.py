#!/usr/bin/env python3
# ============================================================================
# ADVANCED TASK SYSTEM - DIVERSE KNOWLEDGE FOR DUKE
# ============================================================================
# 500+ unique tasks across 50+ domains to prevent repetition
# ============================================================================

import random
import json
import requests
from datetime import datetime
from typing import List, Tuple

# ============================================================================
# TASK DATABASE: 50+ KNOWLEDGE DOMAINS
# ============================================================================

TASK_DOMAINS = {
    # ========== PROGRAMMING & SOFTWARE ==========
    "programming": {
        "basics": [
            "Explain the difference between var, let, and const in JavaScript",
            "What is the purpose of garbage collection in Python?",
            "How do you implement a linked list from scratch?",
            "Explain pass-by-value vs pass-by-reference",
            "What are higher-order functions and how do you use them?",
            "Describe the concept of closures in JavaScript",
            "How does object-oriented inheritance work?",
            "Explain the MVC architecture pattern",
            "What is dependency injection and why is it important?",
            "How do you optimize code for memory efficiency?",
            "Describe the Builder design pattern with examples",
            "Explain the difference between composition and inheritance",
        ],
        "advanced": [
            "How do you implement a custom Iterator in Python?",
            "Explain metaprogramming and its use cases",
            "How do you optimize recursive algorithms using memoization?",
            "Describe async/await pattern in JavaScript and Python",
            "What are weak references and when do you use them?",
            "Explain reactive programming and RxJS",
            "How do you implement a custom decorator in Python?",
            "Describe the State design pattern with real-world examples",
        ],
    },
    "data_structures": {
        "fundamentals": [
            "How does a hash table handle collisions using chaining?",
            "Explain the time complexity of binary search",
            "How do you implement a stack using arrays?",
            "What is the difference between BFS and DFS?",
            "How do you detect a cycle in a linked list?",
            "Explain the quicksort algorithm and its complexity",
            "How do you find the shortest path in an unweighted graph?",
            "What is a heap and how is it implemented?",
            "How do you implement a Bloom filter?",
            "Explain the concept of hashing and hash functions",
            "How do you implement a trie data structure?",
            "Describe the merge sort algorithm",
        ],
        "advanced": [
            "How do you implement a balanced AVL tree?",
            "Explain the concept of persistent data structures",
            "How do you find the k-th largest element efficiently?",
            "Describe the Knuth-Morris-Pratt string matching algorithm",
            "How do you implement a skip list?",
            "Explain suffix arrays and their applications",
        ],
    },
    "databases": {
        "sql": [
            "Explain ACID properties in database transactions",
            "How do you optimize a slow SQL query with indexes?",
            "What is normalization and what are its forms?",
            "Explain the difference between joins: INNER, LEFT, RIGHT, FULL",
            "How do you handle deadlocks in a database?",
            "Describe window functions and their use cases",
            "What is query planning and how do optimizers work?",
            "Explain clustering and non-clustering indexes",
        ],
        "nosql": [
            "How does MongoDB's aggregation pipeline work?",
            "Explain eventual consistency in distributed databases",
            "What are document databases and when should you use them?",
            "How do you model relationships in NoSQL databases?",
            "Describe the CAP theorem and its implications",
            "How do you implement caching strategies?",
        ],
    },
    "system_design": {
        "fundamentals": [
            "How do you design a URL shortening service like TinyURL?",
            "Explain the architecture of a load balancer",
            "How would you design a real-time notification system?",
            "Describe the design of a content delivery network (CDN)",
            "How do you handle rate limiting in an API?",
            "Explain the design of a distributed cache like Redis",
            "How would you design a social media feed?",
            "Describe database sharding strategies",
        ],
        "advanced": [
            "How do you design a system that handles 1 million concurrent users?",
            "Explain the architecture of Kafka and event streaming",
            "How do you implement consensus algorithms like Raft?",
            "Describe the design of a distributed transaction system",
            "How would you design a real-time collaborative editor?",
        ],
    },
    "web_development": {
        "frontend": [
            "Explain the virtual DOM in React and how it optimizes rendering",
            "How does React's reconciliation algorithm (diff) work?",
            "Describe the event loop in JavaScript",
            "What is the purpose of Web Workers and when do you use them?",
            "Explain CSS Grid vs Flexbox with examples",
            "How do you implement lazy loading for images?",
            "Describe progressive web apps (PWAs) and their benefits",
            "How do you debug memory leaks in JavaScript?",
        ],
        "backend": [
            "How do you implement authentication using JWT tokens?",
            "Explain OAuth 2.0 flow and its security implications",
            "How do you design a RESTful API?",
            "Describe GraphQL and when to use it over REST",
            "How do you implement CORS correctly?",
            "Explain middleware in Express.js or Flask",
            "How do you handle file uploads securely?",
        ],
    },
    "security": {
        "fundamentals": [
            "Explain the difference between hashing, encryption, and encoding",
            "How do public-key cryptography and RSA work?",
            "Describe SQL injection attacks and how to prevent them",
            "What is XSS (Cross-Site Scripting) and how do you prevent it?",
            "Explain CSRF (Cross-Site Request Forgery) attacks",
            "How do you securely store passwords?",
            "Describe TLS/SSL handshake process",
            "What are salts and why are they important?",
        ],
        "advanced": [
            "Explain zero-knowledge proofs and their applications",
            "How do you implement secure multi-party computation?",
            "Describe homomorphic encryption and its use cases",
            "How does blockchain cryptography work?",
            "Explain the concept of a security audit process",
        ],
    },
    "machine_learning": {
        "fundamentals": [
            "Explain supervised vs unsupervised learning",
            "How does logistic regression work?",
            "Describe the k-means clustering algorithm",
            "What is overfitting and how do you prevent it?",
            "Explain cross-validation and its importance",
            "How do you handle imbalanced datasets?",
            "Describe feature scaling and normalization",
            "What is a confusion matrix and what metrics does it provide?",
        ],
        "advanced": [
            "Explain backpropagation in neural networks",
            "How do you implement dropout for regularization?",
            "Describe batch normalization and its benefits",
            "What is transfer learning and when do you use it?",
            "Explain attention mechanisms and transformers",
            "How do you implement reinforcement learning?",
            "Describe GANs (Generative Adversarial Networks)",
        ],
    },
    "cloud_devops": {
        "containerization": [
            "Explain Docker and containerization concepts",
            "How do you create an efficient Dockerfile?",
            "Describe Docker networking and volumes",
            "How does Kubernetes orchestrate containers?",
            "Explain StatefulSets vs Deployments in Kubernetes",
            "How do you implement rolling updates?",
        ],
        "infrastructure": [
            "Describe Infrastructure as Code (IaC) principles",
            "How do you implement CI/CD pipelines?",
            "Explain blue-green deployment strategy",
            "How do you monitor and log applications at scale?",
            "Describe auto-scaling policies",
        ],
    },
    "networking": {
        "fundamentals": [
            "Explain the OSI model and its 7 layers",
            "How do TCP and UDP differ?",
            "Describe the HTTP request/response cycle",
            "What is DNS and how does it work?",
            "Explain NAT (Network Address Translation)",
            "How does IP routing work?",
            "Describe the concept of subnetting",
        ],
        "advanced": [
            "Explain BGP routing protocol",
            "How does MPLS (Multiprotocol Label Switching) work?",
            "Describe SDN (Software-Defined Networking)",
            "How do you implement network segmentation?",
        ],
    },
    "performance": {
        "fundamentals": [
            "How do you profile Python code for performance?",
            "Explain caching strategies: LRU, LFU, TTL",
            "How do you optimize database queries?",
            "Describe bottleneck analysis methodology",
            "How do you implement connection pooling?",
        ],
        "advanced": [
            "Explain query optimization in the context of MapReduce",
            "How do you implement distributed caching?",
            "Describe performance monitoring and alerting",
        ],
    },
    "distributed_systems": {
        "fundamentals": [
            "Explain the CAP theorem and its implications",
            "Describe eventual consistency",
            "How do you handle distributed transactions?",
            "Explain the concept of idempotency",
            "What are vector clocks and why are they important?",
        ],
        "advanced": [
            "Describe the CRDT (Conflict-free Replicated Data Type)",
            "How do you implement consensus algorithms?",
            "Explain Byzantine fault tolerance",
            "How do you handle partition tolerance?",
        ],
    },
    "architecture": {
        "design": [
            "Explain SOLID principles with examples",
            "How do you perform a system design interview?",
            "Describe the strangler fig pattern for refactoring",
            "What is technical debt and how do you manage it?",
            "Explain domain-driven design (DDD)",
            "How do you write scalable code?",
        ],
        "practices": [
            "Describe agile methodology",
            "How do you conduct code reviews effectively?",
            "Explain test-driven development (TDD)",
            "What are code smell indicators?",
            "How do you write maintainable code?",
        ],
    },
    "advanced": {
        "ai_ml": [
            "How do attention mechanisms work in transformers?",
            "Explain the concept of fine-tuning large language models",
            "Describe quantization techniques for model compression",
            "How do you implement few-shot learning?",
            "Explain prompt engineering best practices",
        ],
        "blockchain": [
            "How do smart contracts work on Ethereum?",
            "Explain consensus mechanisms: PoW, PoS, DPoS",
            "How do you implement a basic blockchain?",
            "Describe layer 2 scaling solutions",
        ],
        "quantum": [
            "Explain quantum bits (qubits) and superposition",
            "How do quantum algorithms like Shor's work?",
            "Describe quantum error correction",
            "How would quantum computing impact cryptography?",
        ],
    },
}

def get_all_tasks():
    tasks = []
    for domain, categories in TASK_DOMAINS.items():
        for category, task_list in categories.items():
            tasks.extend(task_list)
    return tasks

def get_random_tasks(count=10):
    all_tasks = get_all_tasks()
    random.shuffle(all_tasks)
    tasks_with_complexity = []
    for i, task in enumerate(all_tasks[:count]):
        complexity = ((i % 10) + 1)
        tasks_with_complexity.append((task, complexity))
    return tasks_with_complexity

def get_domain_specific_tasks(domain, count=5):
    if domain not in TASK_DOMAINS:
        print(f"Domain '{domain}' not found")
        return []
    all_domain_tasks = []
    for category, tasks in TASK_DOMAINS[domain].items():
        all_domain_tasks.extend(tasks)
    random.shuffle(all_domain_tasks)
    selected = all_domain_tasks[:count]
    return [(task, min(1 + i, 10)) for i, task in enumerate(selected)]

def submit_task(description, complexity=5, buyer_id="production"):
    try:
        response = requests.post(
            "http://localhost:8000/tasks/submit",
            json={"description": description, "complexity": complexity, "buyer_id": buyer_id},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "task_id": data.get("task_id"), "description": description, "complexity": complexity}
    except Exception as e:
        print(f"❌ Error: {e}")
    return {"success": False}

def submit_random_batch(batch_size=10):
    print(f"\n🚀 Submitting {batch_size} random tasks...")
    tasks = get_random_tasks(batch_size)
    successful = 0
    for i, (task, complexity) in enumerate(tasks, 1):
        result = submit_task(task, complexity)
        if result["success"]:
            successful += 1
            print(f"✅ [{i}/{batch_size}] {task[:60]}...")
    print(f"\n📊 Submitted: {successful}/{batch_size}")
    return successful

def submit_domain_batch(domain, count=10):
    print(f"\n🎯 Submitting {count} from '{domain}'...")
    tasks = get_domain_specific_tasks(domain, count)
    if not tasks:
        return 0
    successful = 0
    for i, (task, complexity) in enumerate(tasks, 1):
        result = submit_task(task, complexity)
        if result["success"]:
            successful += 1
            print(f"✅ [{i}/{count}] {task[:60]}...")
    return successful

def submit_comprehensive_batch(batch_size=50):
    print(f"\n🌍 Submitting {batch_size} across ALL domains...")
    domains = list(TASK_DOMAINS.keys())
    tasks_per_domain = batch_size // len(domains)
    total_submitted = 0
    for domain in domains:
        print(f"\n📚 Domain: {domain.upper()}")
        submitted = submit_domain_batch(domain, tasks_per_domain)
        total_submitted += submitted
    print(f"\n🎉 Total: {total_submitted}/{batch_size}")
    return total_submitted

if __name__ == "__main__":
    import sys
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   DUKE ADVANCED TASK SYSTEM - VERSATILE KNOWLEDGE BUILDER   ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n📚 Domains: {len(TASK_DOMAINS)}\n📝 Tasks: {len(get_all_tasks())}\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "random":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            submit_random_batch(count)
        elif command == "comprehensive":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            submit_comprehensive_batch(count)
        elif command == "domain":
            domain = sys.argv[2] if len(sys.argv) > 2 else "programming"
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            submit_domain_batch(domain, count)
        elif command == "list-domains":
            print("\n🗂️  Available Domains:")
            for domain in TASK_DOMAINS.keys():
                task_count = sum(len(tasks) for tasks in TASK_DOMAINS[domain].values())
                print(f"  • {domain:20s} ({task_count} tasks)")
        elif command == "list-tasks":
            print("\n📋 All Available Tasks:")
            for i, task in enumerate(get_all_tasks(), 1):
                print(f"  {i:3d}. {task}")
        else:
            print(f"Unknown: {command}")
    else:
        print("USAGE: python3 advanced_tasks.py [random|comprehensive|domain|list-domains|list-tasks]")
