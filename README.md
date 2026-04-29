# IoT Smart Traffic Management System — Team 3 (Upgraded)

## What's New (Review 2 Upgrades)

| Feature | Original | Upgraded |
|---------|----------|---------|
| Backend | Print-only simulation | Flask REST API |
| Routing Algorithm | Simple filter | **A* Pathfinding** |
| Data Source | Random only | **TomTom API simulation** (real API-ready) |
| Frontend connection | None (independent) | **Fully connected via polling** |
| Heatmap | ❌ | **✅ Canvas heatmap** |
| Re-routing UI | Terminal only | **Live route status badges** |
| A* UI | ❌ | **✅ Interactive A* tool** |

---

## How to Run

### 1. Install dependencies
```bash
pip3 install flask flask-cors
```

### 2. Start the backend
```bash
python3 app.py
```
You'll see: `API running at: http://localhost:5000`

### 3. Open the dashboard
Open `dashboard.html` in your browser (double-click it).

> **Note:** Both must run at the same time. The dashboard polls the backend every 1 second.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | All intersection data + routes + events |
| GET | `/api/heatmap` | Heatmap node data with intensity values |
| GET | `/api/history` | Time-series volume data for chart |
| POST | `/api/astar` | Run A* from `{start, goal}` |
| POST | `/api/emergency` | Trigger emergency vehicle at `{intersection}` |
| POST | `/api/congestion` | Spike volume at `{intersection}` |
| POST | `/api/pause` | Toggle pause |
| POST | `/api/reset` | Reset simulation |

---

## Algorithms

### Algorithm 1: Threshold Classification
```
volume < 50  → LOW    (30s green)
volume < 80  → MEDIUM (45s green)
volume ≥ 80  → HIGH   (60s green + rerouting)
```

### Algorithm 2: Dynamic Signal Timing
Signal duration is demand-based, not fixed-timer.

### Algorithm 3: Simple Re-routing
Finds all routes NOT passing through the congested node.

### Algorithm 4: A* Pathfinding
- Builds a dynamic cost graph where congested nodes have higher edge weights
- `weight = base_distance + (volume / 10)`
- Uses Euclidean distance as heuristic
- Always finds the least-congested path

### TomTom API (Simulated)
In production, replace `tomtom_simulate()` with:
```python
import requests
res = requests.get(
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
    params={"key": YOUR_KEY, "point": f"{lat},{lng}"}
)
volume = res.json()['flowSegmentData']['currentSpeed']
```

---

## Files

```
smart_traffic/
├── app.py           ← Flask backend (run this)
├── dashboard.html   ← Frontend (open this in browser)
└── README.md
```
