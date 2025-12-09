cat > GRAFANA_SETUP_GUIDE.md << 'EOF'

# 📊 DukeNet AINS - Grafana Monitoring Setup

## Quick Start

### 1. Start Monitoring Stack

docker-compose up -d

### 2. Verify Services Running

docker-compose ps

Expected output:
NAME IMAGE STATUS
ains-grafana grafana/grafana:latest Up
ains-prometheus prom/prometheus:latest Up

### 3. Access Dashboards

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
- **Prometheus**: http://localhost:9090

### 4. Check Metrics Collection

Visit: http://localhost:8000/metrics

Should show Prometheus metrics from your API.

---

## Dashboards

### Dashboard 1: HTTP & Core Metrics

**Location:** Dashboards → AINS - HTTP & Core Metrics

**Panels:**

- Request Rate (req/sec)
- Request Latency (p95, p99)
- Error Rate (4xx, 5xx)
- Active Requests

### Dashboard 2: Tasks & Agents

**Location:** Dashboards → AINS - Tasks & Agents

**Panels:**

- Task Throughput
- Task Queue Depth
- Agent Heartbeats
- Agent Status Distribution
- Task Completion Rate
- Task Failure Rate

---

## Troubleshooting

### Services won't start

docker-compose down
docker-compose up -d
docker-compose logs

### Can't access Grafana

docker-compose logs grafana

Check: http://localhost:3000/api/health

### Prometheus not scraping

curl http://localhost:9090/api/v1/targets

Check if `ains-api` target is UP.

### No metrics showing

1. Verify API is running: `curl http://localhost:8000/health`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Verify Prometheus config: `cat prometheus.yml`

---

## Commands Reference

### Start services

docker-compose up -d

### Stop services

docker-compose down

### View logs

docker-compose logs -f
docker-compose logs grafana
docker-compose logs prometheus

### Restart services

docker-compose restart

### Remove everything (including data)

docker-compose down -v

---

## Configuration Files

- `docker-compose.yml` - Service definitions
- `prometheus.yml` - Prometheus scraping config
- `grafana-provisioning/` - Auto-provisioned dashboards

---

## Default Ports

- **3000** - Grafana UI
- **9090** - Prometheus UI
- **8000** - AINS API (metrics at /metrics)

---

## Next Steps

1. ✅ Start monitoring stack
2. ✅ Access Grafana at http://localhost:3000
3. ✅ View pre-configured dashboards
4. ✅ Generate load on API to see metrics
5. ✅ Customize dashboards as needed

---

**Created:** November 28, 2025, 12:39 PM CST  
**Sprint:** 9 - Part 3  
**Status:** ✅ Complete
