#!/bin/bash

echo "🔧 Configuring Grafana Data Source..."

curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://localhost:9090",
    "access": "proxy",
    "isDefault": true
  }'

echo ""
echo "✅ Prometheus data source configured!"
echo ""
echo "📊 Now creating dashboards..."

curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @- << 'DASHBOARD1'
{
  "dashboard": {
    "title": "AINS - HTTP & Core Metrics",
    "tags": ["ains", "http"],
    "timezone": "browser",
    "refresh": "10s",
    "panels": [
      {
        "id": 1,
        "title": "HTTP Requests (Total)",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
        "targets": [{
          "expr": "sum(ains_http_requests_total)",
          "refId": "A"
        }]
      },
      {
        "id": 2,
        "title": "Requests In Progress",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
        "targets": [{
          "expr": "ains_http_requests_in_progress",
          "refId": "A"
        }]
      },
      {
        "id": 3,
        "title": "Active Agents",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
        "targets": [{
          "expr": "ains_agents_active",
          "refId": "A"
        }]
      },
      {
        "id": 4,
        "title": "Total Agents",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
        "targets": [{
          "expr": "ains_agents_total",
          "refId": "A"
        }]
      }
    ]
  },
  "overwrite": true
}
DASHBOARD1

echo ""
echo "✅ Dashboard 1 created!"

curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @- << 'DASHBOARD2'
{
  "dashboard": {
    "title": "AINS - Tasks & Agents",
    "tags": ["ains", "tasks"],
    "timezone": "browser",
    "refresh": "10s",
    "panels": [
      {
        "id": 1,
        "title": "Tasks Created",
        "type": "stat",
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
        "targets": [{
          "expr": "ains_tasks_created_total",
          "refId": "A"
        }]
      },
      {
        "id": 2,
        "title": "Tasks Completed",
        "type": "stat",
        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
        "targets": [{
          "expr": "ains_tasks_completed_total",
          "refId": "A"
        }]
      },
      {
        "id": 3,
        "title": "Tasks Failed",
        "type": "stat",
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
        "targets": [{
          "expr": "ains_tasks_failed_total",
          "refId": "A"
        }]
      },
      {
        "id": 4,
        "title": "Tasks in Queue",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [{
          "expr": "ains_tasks_in_queue",
          "refId": "A"
        }]
      },
      {
        "id": 5,
        "title": "Active Chains",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [{
          "expr": "ains_chains_active",
          "refId": "A"
        }]
      }
    ]
  },
  "overwrite": true
}
DASHBOARD2

echo ""
echo "✅ Dashboard 2 created!"
echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Access your dashboards at:"
echo "  http://localhost:3000"
echo ""
echo "Login: admin / admin"
