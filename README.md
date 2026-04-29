# IoT Smart Traffic Management System

A Python + Flask simulation of an IoT-powered smart traffic system with real-time congestion detection, dynamic signal control, A* pathfinding, heatmap visualization, and automatic re-routing.

## Features

- Real-time Monitoring across 4 intersections (I-A, I-B, I-C, I-D)
- Congestion Classification — LOW / MEDIUM / HIGH
- Dynamic Signal Control — adjusts green light timing based on vehicle density
- A* Pathfinding Algorithm — finds the least-congested route between intersections
- Auto Re-routing — diverts traffic when congestion is detected
- Traffic Heatmap — visual intensity map of all intersections
- TomTom API Integration — real-time traffic data ingestion (simulated)
- Live Dashboard — fully connected frontend with charts, event log, and controls
- Emergency Vehicle Handling — overrides signals and clears corridor

## Files

```
├── app.py            ← Flask backend (run this first)
├── dashboard.html    ← Frontend dashboard (open in browser)
└── README.md
```

## How to Run

### 1. Install dependencies
```bash
pip install flask flask-cors
```

### 2. Run backend
```bash
python app.py
```

### 3. Open dashboard
Double-click `dashboard.html` in your file explorer to open it in the browser.

> Both `app.py` and `dashboard.html` must be running at the same time.

## Algorithms

### Threshold Classification
```
volume < 50  → LOW    → 30s green signal
volume < 80  → MEDIUM → 45s green signal
volume ≥ 80  → HIGH   → 60s green signal + auto re-routing
```

### Dynamic Signal Timing
Signal duration is demand-based — adjusts automatically based on live vehicle density instead of fixed timers.

### A* Pathfinding
Finds the optimal (least-congested) path between any two intersections. Edge weights increase dynamically based on current traffic volume:
```
edge_weight = base_distance + (volume / 10)
```

### Auto Re-routing
When an intersection hits HIGH congestion, the system identifies all routes not passing through that node and diverts traffic accordingly.

### TomTom API
In production, replace the `tomtom_simulate()` function with a real TomTom Traffic Flow API call:
```python
requests.get(
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
    params={"key": YOUR_API_KEY, "point": f"{lat},{lng}"}
)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | All intersection data, routes, and events |
| GET | `/api/heatmap` | Heatmap node data with intensity values |
| GET | `/api/history` | Time-series volume data for chart |
| POST | `/api/astar` | Run A* between `{start, goal}` |
| POST | `/api/emergency` | Trigger emergency vehicle at `{intersection}` |
| POST | `/api/congestion` | Spike traffic volume at `{intersection}` |
| POST | `/api/pause` | Toggle pause/resume |
| POST | `/api/reset` | Reset simulation to initial state |

## Team

Team 3 — IoT Based Smart Traffic System with Congestion Forecasting
