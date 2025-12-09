# 🚀 EPIC #5: KUBERNETES AUTO-SCALING - IMPLEMENTATION GUIDE

**Start Date:** Saturday, November 29, 2025, 8:35 PM CST  
**Estimated Duration:** 12 hours  
**Status:** 🟡 IN PROGRESS  
**Goal:** Deploy agents to Kubernetes with auto-scaling, zero-downtime updates

---

## 📋 DELIVERABLES CHECKLIST

- [ ] `k8s/agent-deployment.yaml` - Agent pods with resource limits
- [ ] `k8s/postgres-statefulset.yaml` - Database persistence in K8s
- [ ] `k8s/hpa.yaml` - Horizontal Pod Autoscaler (CPU-based)
- [ ] `k8s/load-balancer.yaml` - Agent distribution service
- [ ] `k8s/configmap.yaml` - Database configuration
- [ ] `k8s/secret.yaml` - PostgreSQL credentials
- [ ] Integration tests - Verify auto-scaling works
- [ ] Documentation - Deployment + scaling guide

---

## 🎯 ARCHITECTURE OVERVIEW

```
Kubernetes Cluster
├── Namespace: aicp
│
├── PostgreSQL StatefulSet
│   ├── Pod: postgres-0 (persistent volume)
│   ├── Service: postgres (ClusterIP)
│   └── PVC: postgres-data-claim (10GB)
│
├── Agent Deployment
│   ├── Pods: agent-worker-{1,2,3...N} (auto-scaled)
│   ├── Service: agent-service (LoadBalancer)
│   └── HPA: Scale 3-10 pods @ 70% CPU
│
└── Task Coordinator Deployment
    ├── Pod: coordinator-1
    ├── Service: coordinator (ClusterIP)
    └── Connects to: PostgreSQL + Agent Service
```

---

## 🔧 PREREQUISITES

### 1. Install kubectl (if not already)

**macOS:**
```bash
brew install kubectl
kubectl version --client
```

### 2. Choose Kubernetes Platform

**Option A: Minikube (Local Testing)**
```bash
brew install minikube
minikube start --cpus=4 --memory=8192
minikube status
```

**Option B: Docker Desktop Kubernetes (Recommended)**
```bash
# Enable Kubernetes in Docker Desktop:
# 1. Open Docker Desktop
# 2. Settings → Kubernetes → Enable Kubernetes
# 3. Wait for green indicator
kubectl cluster-info
```

**Option C: Cloud (GKE/EKS/AKS)**
```bash
# Google Kubernetes Engine (GKE)
gcloud container clusters create aicp-cluster \
  --zone us-central1-a \
  --num-nodes 3

# Amazon EKS
eksctl create cluster --name aicp-cluster --region us-east-1

# Azure AKS
az aks create --resource-group aicp-rg --name aicp-cluster
```

### 3. Verify Cluster Access

```bash
kubectl get nodes
# Should show at least 1 node in Ready state
```

---

## 📦 STEP 1: CREATE KUBERNETES MANIFESTS

### File 1: `k8s/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aicp
  labels:
    app: aicp-core
    environment: production
```

**Apply:**
```bash
mkdir -p k8s
kubectl apply -f k8s/namespace.yaml
kubectl get namespaces
```

---

### File 2: `k8s/secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: aicp
type: Opaque
stringData:
  POSTGRES_DB: aicp
  POSTGRES_USER: aicp
  POSTGRES_PASSWORD: aicp_secret_k8s_secure_2025
```

**Apply:**
```bash
kubectl apply -f k8s/secret.yaml
kubectl get secrets -n aicp
```

---

### File 3: `k8s/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
  namespace: aicp
data:
  POSTGRES_HOST: "postgres.aicp.svc.cluster.local"
  POSTGRES_PORT: "5432"
  MAX_CONNECTIONS: "100"
  SHARED_BUFFERS: "256MB"
```

**Apply:**
```bash
kubectl apply -f k8s/configmap.yaml
kubectl get configmaps -n aicp
```

---

### File 4: `k8s/postgres-statefulset.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: aicp
  labels:
    app: postgres
spec:
  type: ClusterIP
  ports:
    - port: 5432
      targetPort: 5432
      protocol: TCP
  selector:
    app: postgres
  clusterIP: None  # Headless service for StatefulSet

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: aicp
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16
        ports:
        - containerPort: 5432
          name: postgres
        envFrom:
        - secretRef:
            name: postgres-secret
        - configMapRef:
            name: postgres-config
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - aicp
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - aicp
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

**Apply:**
```bash
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl get statefulsets -n aicp
kubectl get pods -n aicp
kubectl get pvc -n aicp
```

**Wait for Ready:**
```bash
kubectl wait --for=condition=ready pod/postgres-0 -n aicp --timeout=300s
```

**Verify Database:**
```bash
kubectl exec -it postgres-0 -n aicp -- psql -U aicp -d aicp -c "SELECT version();"
```

---

### File 5: `k8s/agent-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-worker
  namespace: aicp
  labels:
    app: agent-worker
spec:
  replicas: 3  # Start with 3, HPA will scale 3-10
  selector:
    matchLabels:
      app: agent-worker
  template:
    metadata:
      labels:
        app: agent-worker
    spec:
      containers:
      - name: agent
        image: python:3.14-slim  # Replace with your agent image
        command:
          - python
          - -c
          - |
            # Placeholder: Replace with actual agent worker code
            import time
            import os
            print(f"Agent worker starting... (Pod: {os.getenv('HOSTNAME')})")
            while True:
                print(f"Processing tasks... CPU load simulation")
                # Simulate CPU work for autoscaling testing
                sum([i**2 for i in range(10000)])
                time.sleep(5)
        env:
        - name: POSTGRES_HOST
          valueFrom:
            configMapKeyRef:
              name: postgres-config
              key: POSTGRES_HOST
        - name: POSTGRES_PORT
          valueFrom:
            configMapKeyRef:
              name: postgres-config
              key: POSTGRES_PORT
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_PASSWORD
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - pgrep
            - -f
            - python
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - pgrep
            - -f
            - python
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: agent-service
  namespace: aicp
  labels:
    app: agent-worker
spec:
  type: LoadBalancer  # Exposes agents externally
  selector:
    app: agent-worker
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
      name: http
  sessionAffinity: None
```

**Apply:**
```bash
kubectl apply -f k8s/agent-deployment.yaml
kubectl get deployments -n aicp
kubectl get pods -n aicp -l app=agent-worker
kubectl get svc -n aicp
```

---

### File 6: `k8s/hpa.yaml` (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-hpa
  namespace: aicp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-worker
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale when CPU > 70%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Scale when Memory > 80%
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Percent
        value: 100  # Double pods each time
        periodSeconds: 15
      - type: Pods
        value: 2  # Or add 2 pods
        periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5min before scaling down
      policies:
      - type: Percent
        value: 50  # Remove 50% of pods
        periodSeconds: 60
      selectPolicy: Min
```

**Apply:**
```bash
kubectl apply -f k8s/hpa.yaml
kubectl get hpa -n aicp
kubectl describe hpa agent-hpa -n aicp
```

---

## 🧪 STEP 2: INITIALIZE DATABASE IN KUBERNETES

### Create Init Job

```yaml
# k8s/init-database-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: init-database
  namespace: aicp
spec:
  template:
    spec:
      containers:
      - name: init
        image: python:3.14-slim
        command:
          - /bin/bash
          - -c
          - |
            pip install psycopg2-binary
            cat <<'EOF' > /tmp/init_db.py
            import psycopg2
            conn = psycopg2.connect(
                host='postgres.aicp.svc.cluster.local',
                port=5432,
                database='aicp',
                user='aicp',
                password='aicp_secret_k8s_secure_2025'
            )
            cur = conn.cursor()
            # Create tables (same schema as Epic #4)
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
            # Seed agents
            agents = [('agent-1', 0.95, 50, 2.00), ('agent-2', 0.90, 100, 1.80), ('agent-3', 0.70, 200, 1.20)]
            for name, sr, rt, rm in agents:
                cur.execute("""
                INSERT INTO agents (name, success_rate, avg_response_ms, reputation_multiplier)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                """, (name, sr, rt, rm))
            conn.commit()
            print("✅ Database initialized")
            EOF
            python /tmp/init_db.py
      restartPolicy: Never
  backoffLimit: 3
```

**Apply:**
```bash
kubectl apply -f k8s/init-database-job.yaml
kubectl logs job/init-database -n aicp -f
```

---

## 📊 STEP 3: TEST AUTO-SCALING

### Generate Load

```bash
# Watch HPA status
kubectl get hpa agent-hpa -n aicp --watch

# In another terminal, generate CPU load
kubectl run -it --rm load-generator --image=busybox:1.28 --restart=Never -n aicp -- /bin/sh -c "
  while true; do 
    wget -q -O- http://agent-service:8080; 
  done
"
```

**Expected:**
```
# Initial state
agent-hpa   Deployment/agent-worker   10%/70%   3     10    3

# After 30 seconds of load
agent-hpa   Deployment/agent-worker   85%/70%   3     10    6

# After 1 minute
agent-hpa   Deployment/agent-worker   92%/70%   3     10    10
```

---

## ✅ VERIFICATION CHECKLIST

```bash
# 1. Namespace created
kubectl get ns aicp

# 2. PostgreSQL running
kubectl get statefulsets -n aicp
kubectl get pods -n aicp | grep postgres

# 3. Agents deployed
kubectl get deployments -n aicp
kubectl get pods -n aicp | grep agent-worker

# 4. HPA active
kubectl get hpa -n aicp

# 5. Services exposed
kubectl get svc -n aicp

# 6. Database accessible
kubectl exec -it postgres-0 -n aicp -- psql -U aicp -d aicp -c "SELECT COUNT(*) FROM agents;"
```

---

## 🚀 DEPLOYMENT COMMANDS (Quick Reference)

```bash
# Deploy everything
kubectl apply -f k8s/

# Check status
kubectl get all -n aicp

# View logs
kubectl logs -f deployment/agent-worker -n aicp

# Scale manually
kubectl scale deployment agent-worker --replicas=5 -n aicp

# Delete everything
kubectl delete namespace aicp
```

---

## 📈 SCALING BEHAVIOR

| Scenario | Min Pods | Max Pods | Trigger | Scale Time |
|----------|----------|----------|---------|------------|
| Idle | 3 | 3 | CPU < 70% | N/A |
| Moderate Load | 3 | 6 | CPU 70-85% | 15 seconds |
| High Load | 6 | 10 | CPU > 85% | 30 seconds |
| Load Decreasing | 6 | 3 | CPU < 50% | 5 minutes |

---

## 🎯 NEXT STEPS

1. **Replace placeholder agent code** with actual `aicp/` Python modules
2. **Build Docker image** with `circuit_breaker.py`, `task_coordinator.py`, etc.
3. **Push to registry** (Docker Hub / GCR / ECR)
4. **Update `image:`** in `agent-deployment.yaml`
5. **Deploy production** workload

---

**Epic #5 Status:** 🟡 IN PROGRESS | Manifests ready | Deploy when ready

**Next:** Build agent Docker image with aicp modules