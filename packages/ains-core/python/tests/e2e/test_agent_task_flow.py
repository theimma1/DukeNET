import time
import threading

def run_sample_agent(client, agent_name, stop_event):
    """Inline agent simulating real agent behavior"""
    # Register
    reg_resp = client.post("/agents", json={"name": agent_name, "capabilities": ["demo"]})
    agent_id = reg_resp.json()["id"]
    
    while not stop_event.is_set():
        # Heartbeat
        client.post(f"/agents/{agent_id}/heartbeat")
        
        # Poll assigned tasks
        tasks_resp = client.get(f"/agents/{agent_id}/tasks")  # Your polling endpoint
        if tasks_resp.status_code == 200:
            tasks = tasks_resp.json()
            for task in tasks:
                tid = task["id"]
                client.post(f"/tasks/{tid}/status", json={"status": "completed", "result": {"processed": True}})
        
        time.sleep(0.2)  # Poll interval

def test_full_e2e_task_routing_completion(client):
    stop_event = threading.Event()
    agent_thread = threading.Thread(target=run_sample_agent, args=(client, "e2e-agent", stop_event), daemon=True)
    agent_thread.start()
    
    try:
        # Create task (should route to active agent)
        payload = {"type": "demo", "client_id": "e2e", "payload": {"msg": "e2e-test"}}
        create_resp = client.post("/tasks", json=payload)
        task_id = create_resp.json()["id"]
        
        # Wait for completion (trust score should update)
        for _ in range(30):  # 6s timeout
            status_resp = client.get(f"/tasks/{task_id}")
            if status_resp.json()["status"] == "completed":
                break
            time.sleep(0.2)
        else:
            pytest.fail("Task not completed by agent")
        
        # All Sprint 8 metrics present
        metrics_resp = client.get("/metrics")
        text = metrics_resp.text
        assert "ains_tasks_completed_total" in text
        assert "ains_agents_active" in text
        assert "ains_agents_trust_score" in text  # Trust updated
        
    finally:
        stop_event.set()
        agent_thread.join(timeout=1)
