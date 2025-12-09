# 🔄 DASHBOARD AUTO-REFRESH - INSTALLATION GUIDE

Your dashboard now has **auto-refresh functionality!** Here's how to use it:

---

## ✨ NEW DASHBOARD FEATURES

### 1. **Manual Refresh Button**
- Click "🔄 Refresh Now" for instant updates
- No full page reload
- Updates cards & tables smoothly

### 2. **Auto-Refresh Dropdown**
```
Off     → Manual refresh only
5s      → Updates every 5 seconds ⭐ DEFAULT
10s     → Updates every 10 seconds  
15s     → Updates every 15 seconds
30s     → Updates every 30 seconds
```

### 3. **Refresh Indicator**
- 🟢 Green dot = Active
- Shows "Just now", "5s ago", "1m ago"
- Auto-updates every second

---

## 🚀 QUICK START

### Option 1: Replace Your Current File (EASIEST)

```bash
# 1. Stop your current coordinator
# Press CTRL+C in the coordinator terminal

# 2. Rename old file as backup
mv coordinator_api_fixed.py coordinator_api_fixed.py.backup

# 3. Use the new file
mv coordinator_api_with_refresh.py coordinator_api_fixed.py

# 4. Restart
python coordinator_api_fixed.py
```

### Option 2: Copy-Paste the Dashboard Code

```bash
# 1. Open coordinator_api_fixed.py
# 2. Find: @app.get("/dashboard", response_class=HTMLResponse...)
# 3. Replace the entire dashboard function (from @app.get to return HTMLResponse)
# 4. Paste the new code from coordinator_api_with_refresh.py
# 5. Save and restart
```

---

## 📊 WHAT UPDATES AUTOMATICALLY

Every time it refreshes (5s / 10s / 15s / 30s):

✅ **Total Tasks count**
✅ **Completed tasks count**
✅ **Processing tasks count**
✅ **Success rate percentage**
✅ **Duke version number**
✅ **Duke accuracy %**
✅ **Training samples collected**
✅ **Agent performance table**
✅ **Recent tasks table**

---

## 🎯 RECOMMENDED SETTINGS

### For Active Monitoring
```
Auto-refresh: 5s
Why: See updates in real-time while tasks run
Use: When running auto_tasks.py continuous
```

### For Light Monitoring
```
Auto-refresh: 10-15s
Why: Balanced - not too many requests, see timely updates
Use: Background monitoring while working
```

### For Background Only
```
Auto-refresh: 30s or Off
Why: Minimal network requests
Use: Check dashboard occasionally
```

---

## 🔄 HOW IT WORKS

### Manual Refresh Flow:
```
1. User clicks "🔄 Refresh Now"
2. Dot shows spinning animation
3. Fetches updated data from server
4. Updates card values & tables
5. Updates "last refreshed" time
6. Animation stops
```

### Auto-Refresh Flow:
```
Every 5s (or selected interval):
1. Automatically calls manualRefresh()
2. Gets fresh data
3. Updates all metrics
4. Updates "time since last refresh"
5. Continues until interval changed or page closed
```

---

## 📈 LIVE MONITORING EXPERIENCE

### Example: Running `python auto_tasks.py continuous`

```
Dashboard loads → Auto-refresh set to 5s

Time: 21:10:00
- Total Tasks: 0
- Success Rate: 0%
- Training Samples: 0

[auto_tasks submits batch 1 of 5 tasks]

5s later (21:10:05):
- Total Tasks: 5
- Completed: 3 (processing 2)
- Success Rate: 60%
- Training Samples: 3
- Last Refresh: Just now

[tasks complete, auto_tasks waits 60s before batch 2]

1 min later (21:11:00):
- Total Tasks: 5
- Completed: 5
- Success Rate: 100%
- Training Samples: 5
- Last Refresh: 55s ago

[batch 2 submits]

Then repeat until done! 🔄
```

---

## 🎛️ CHANGING REFRESH INTERVAL

### At Runtime (No Restart Needed!)

1. **Open dashboard**: http://localhost:8000/dashboard
2. **Locate dropdown**: Top right corner
3. **Change value**: Select 5s, 10s, 15s, 30s, or Off
4. **Immediate effect**: New interval starts instantly
5. **Switch anytime**: Change between intervals without reloading

### Example:
```
Currently: 5s auto-refresh
Change to: Off (to stop refreshing)
Result: Button click refreshes data, no auto-refresh

Then:
Change to: 30s
Result: Auto-refresh resumes every 30s
```

---

## 💡 TIPS & TRICKS

### 1. **Smooth Updates**
- Only updates changed values
- No page flicker
- Scroll position preserved
- Feels native

### 2. **Network Efficient**
- Each refresh = 1 lightweight request
- Not heavy on server
- Safe to run continuously

### 3. **Browser Performance**
- JavaScript runs smoothly
- Minimal CPU usage
- Works on all modern browsers
- Mobile-friendly

### 4. **Task Details Still Work**
- Click any task row to see full details
- Refreshes don't interfere
- Works with any refresh interval

---

## 🔧 CUSTOMIZING REFRESH INTERVALS

### Edit the dropdown options in coordinator_api_fixed.py:

```html
<select id="refreshInterval" onchange="changeRefreshInterval()">
  <option value="0">Off</option>
  <option value="5" selected>5s</option>
  <option value="10">10s</option>
  <option value="15">15s</option>
  <option value="30">30s</option>
  <!-- ADD MORE HERE -->
  <option value="60">60s</option>
  <option value="120">2m</option>
</select>
```

### Change default (currently 5s):

```html
<!-- From: -->
<option value="5" selected>5s</option>

<!-- To: -->
<option value="5">5s</option>
<option value="10" selected>10s</option>  <!-- Now default -->
```

---

## ❌ TROUBLESHOOTING

### Dashboard not refreshing?

```bash
# 1. Check file replacement
python coordinator_api_fixed.py  # Should show "Auto-Refresh: ✅ Enabled"

# 2. Open browser console
# Right-click → Inspect → Console tab
# Look for errors

# 3. Try manual refresh first
# Click "🔄 Refresh Now" button

# 4. Check dropdown
# Make sure value is set to 5s (not Off)
```

### Updates look frozen?

```bash
# 1. Click "🔄 Refresh Now" to verify updates work
# 2. Check auto_tasks.py is still running
# 3. Verify OpenAI API is responding
# 4. Try changing refresh interval

curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### Too many requests?

```bash
# If server seems slow, increase interval:
Change from: 5s → 10s or 15s
Or: 30s or Off (manual refresh only)
```

---

## 📊 MONITORING YOUR SYSTEM

### Best Practices:

```bash
# Terminal 1: Start coordinator
python coordinator_api_fixed.py

# Terminal 2: Start auto-tasks
python auto_tasks.py continuous

# Terminal 3: Open dashboard with 5s refresh
open http://localhost:8000/dashboard
# Keep dashboard open & watch metrics update in real-time

# Recommended: 
# - Refresh every 5s while monitoring
# - Change to 30s when backgrounding
# - Manual refresh when checking status
```

---

## 🎯 EXPECTED BEHAVIOR

### On Page Load:
```
✅ Dropdown shows "5s" (default selected)
✅ Green dot appears (pulsing)
✅ "Last Refresh: Just now" displays
✅ Auto-refresh starts automatically
```

### After 5 seconds:
```
✅ All values update smoothly
✅ "Last Refresh: 5s ago" updates
✅ Continues every 5 seconds
```

### Click Dropdown → Select "Off":
```
✅ Auto-refresh stops immediately
✅ Button still works for manual refresh
✅ Change back to 5s → resumes auto-refresh
```

### Click "🔄 Refresh Now":
```
✅ Dot spins during update
✅ All values refresh immediately
✅ "Last Refresh: Just now" resets
```

---

## ✅ INSTALLATION CHECKLIST

- [ ] Downloaded `coordinator_api_with_refresh.py`
- [ ] Stopped old coordinator (CTRL+C)
- [ ] Replaced file (or copy-pasted code)
- [ ] Restarted: `python coordinator_api_fixed.py`
- [ ] Opened dashboard: `http://localhost:8000/dashboard`
- [ ] Dropdown visible (top right)
- [ ] Default set to "5s"
- [ ] Clicked "🔄 Refresh Now" → values update
- [ ] Waited 5 seconds → auto-updated
- [ ] Changed dropdown to "10s" → interval changed
- [ ] System working! ✨

---

## 🚀 YOU'RE READY!

Your dashboard now has professional auto-refresh built-in. 

**Enjoy live monitoring of your system!** 🎉

---

**Questions?**

Check logs:
```bash
tail -f coordinator_api.log | grep -i refresh
```

Check dashboard functionality:
```bash
curl http://localhost:8000/health
```

Both should show ✅ status.

---

**Your dashboard is now fully interactive with real-time updates! 🔄✨**
