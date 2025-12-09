# coordinator_service.py Required Changes

## Summary
Your current `coordinator_service.py` is **mostly correct**. Only 2 small tweaks needed to match the App.jsx frontend perfectly.

---

## Change 1: Update TaskCompletion Model

**Location:** Line ~23 (TaskCompletion class)

**Current:**
```python
class TaskCompletion(BaseModel):
    success: bool = True
    result: str = ""
```

**Updated:**
```python
class TaskCompletion(BaseModel):
    success: bool = True
    result: Optional[str] = None
```

**Why:** The `Optional[str]` properly handles when agents don't provide a result (None instead of empty string).

---

## Change 2: Update Result Assignment in complete_task

**Location:** Line ~68 (in complete_task function)

**Current:**
```python
task['result'] = completion.result if completion.result else ""
```

**Updated:**
```python
task['result'] = completion.result if completion.result else ("Success" if completion.success else "Failed")
```

**Why:** Provides better default messaging when no result text is provided by the agent.

---

## Verification Checklist

✅ Endpoint signature: `@app.post("/tasks/{task_id}/complete")` — **Already correct**
✅ Takes JSON body `{ success, result }` — **Already correct**
✅ Updates task status — **Already correct**
✅ Credits agent balance on success — **Already correct**
✅ Returns updated task — **Already correct**

---

## Full Updated Function (Reference)

```python
@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, completion: TaskCompletion):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task['status'] = "completed" if completion.success else "failed"
    task['result'] = completion.result if completion.result else ("Success" if completion.success else "Failed")
    task['completed_at'] = datetime.now().isoformat()
    
    if completion.success:
        for agent in agents_db:
            if agent['name'] == task['agent_name']:
                agent['balance_satoshis'] += task['price_satoshis']
                print(f"✅ Agent {agent['name']} earned {task['price_satoshis']} sat. New balance: {agent['balance_satoshis']}")
                break
    
    return task
```

---

## Testing

After making changes, test with curl:

```bash
# 1. Submit a task
curl -X POST "http://localhost:8000/tasks/submit" \
  -H "Content-Type: application/json" \
  -d '{"description":"Test task","complexity":5,"buyer_id":"buyer-001"}'

# Response will include task_id, copy it

# 2. Complete the task (using the task_id from step 1)
curl -X POST "http://localhost:8000/tasks/{task_id}/complete" \
  -H "Content-Type: application/json" \
  -d '{"success":true,"result":"Task completed by agent"}'

# 3. Verify task and agent balance
curl "http://localhost:8000/tasks/{task_id}"
curl "http://localhost:8000/agents"
```

**Expected Results:**
- Task status changes to `completed`
- Agent balance increases by task price
- Result message displays properly in dashboard
