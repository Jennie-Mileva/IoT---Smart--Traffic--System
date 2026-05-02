"""
IoT Smart Traffic Management System — Upgraded Backend
Team 3 | Review 2

Upgrades over original:
- Flask REST API (frontend can poll this)
- A* Algorithm for shortest path / rerouting
- TomTom-style API simulation (would be real API key in production)
- Heatmap data endpoint
- Emergency vehicle handling
- Full event log
"""

from flask import Flask, jsonify, request, send_file
import os
from flask_cors import CORS
import random
import time
import math
from datetime import datetime
from collections import defaultdict
import heapq
import threading

app = Flask(__name__)
CORS(app)  # Allow frontend to call this API

# ─────────────────────────────────────────────────────
# GRAPH — 4 Intersections as nodes, roads as edges
# Used by A* Algorithm for rerouting
# ─────────────────────────────────────────────────────
# Each intersection has (x, y) coordinates (for heuristic)
NODES = {
    'I-A': {'x': 0, 'y': 1, 'label': 'North'},
    'I-B': {'x': 1, 'y': 2, 'label': 'East'},
    'I-C': {'x': 0, 'y': 0, 'label': 'West'},
    'I-D': {'x': 1, 'y': 1, 'label': 'South'},
}

# Adjacency list: node → [(neighbor, base_weight)]
BASE_GRAPH = {
    'I-A': [('I-B', 5), ('I-C', 4)],
    'I-B': [('I-A', 5), ('I-D', 6)],
    'I-C': [('I-A', 4), ('I-D', 5)],
    'I-D': [('I-B', 6), ('I-C', 5)],
}

ROUTES = {
    'Route 1': ('I-A', 'I-B'),
    'Route 2': ('I-A', 'I-C'),
    'Route 3': ('I-C', 'I-D'),
    'Route 4': ('I-B', 'I-D'),
}

# ─────────────────────────────────────────────────────
# THRESHOLDS (same as original, your professor knows these)
# ─────────────────────────────────────────────────────
THRESHOLD_LOW    = 50   # < 50 = LOW
THRESHOLD_HIGH   = 80   # > 80 = HIGH → triggers rerouting
SIGNAL_LOW       = 30   # seconds
SIGNAL_MEDIUM    = 45
SIGNAL_HIGH      = 60

# ─────────────────────────────────────────────────────
# SHARED STATE (thread-safe via lock)
# ─────────────────────────────────────────────────────
lock = threading.Lock()

state = {
    'tick': 0,
    'running': True,
    'emergency': False,
    'emergency_intersection': None,
    'reroute_count': 0,
    'event_log': [],
    'history': {k: [] for k in NODES},  # volume history per intersection
    'volumes': {
        'I-A': 38.0,
        'I-B': 52.0,
        'I-C': 29.0,
        'I-D': 44.0,
    },
    'congestion_flags': {},
    'active_routes': {
        'Route 1': {'path': ('I-A', 'I-B'), 'status': 'normal'},
        'Route 2': {'path': ('I-A', 'I-C'), 'status': 'normal'},
        'Route 3': {'path': ('I-C', 'I-D'), 'status': 'normal'},
        'Route 4': {'path': ('I-B', 'I-D'), 'status': 'normal'},
    },
    'astar_result': None,   # last A* computed path
}

# ─────────────────────────────────────────────────────
# CORE ALGORITHMS
# ─────────────────────────────────────────────────────

def classify_congestion(vol):
    """Algorithm 1: Threshold Classification"""
    if vol < THRESHOLD_LOW:
        return 'LOW'
    elif vol < THRESHOLD_HIGH:
        return 'MEDIUM'
    else:
        return 'HIGH'

def adjust_signal(vol):
    """Algorithm 2: Dynamic Signal Timing"""
    if vol >= THRESHOLD_HIGH:
        return SIGNAL_HIGH
    elif vol >= THRESHOLD_LOW:
        return SIGNAL_MEDIUM
    else:
        return SIGNAL_LOW

def reroute(congested_intersection):
    """Algorithm 3: Simple Re-routing (original logic kept)"""
    return [
        f"{name}: {src} → {dst}"
        for name, (src, dst) in ROUTES.items()
        if congested_intersection not in (src, dst)
    ]

def heuristic(node, goal):
    """Euclidean distance heuristic for A*"""
    nx, ny = NODES[node]['x'], NODES[node]['y']
    gx, gy = NODES[goal]['x'], NODES[goal]['y']
    return math.sqrt((nx - gx) ** 2 + (ny - gy) ** 2)

def build_dynamic_graph(volumes):
    """
    A* ALGORITHM SUPPORT:
    Builds a cost-weighted graph based on current traffic volumes.
    Higher volume = higher edge weight = A* avoids it.
    Weight formula: base_weight + (volume / 10)
    """
    graph = {}
    for node, neighbors in BASE_GRAPH.items():
        graph[node] = []
        for (neighbor, base_w) in neighbors:
            # Volume at the neighbor increases its cost
            congestion_cost = volumes.get(neighbor, 0) / 10
            dynamic_weight = base_w + congestion_cost
            graph[node].append((neighbor, dynamic_weight))
    return graph

def astar(start, goal, volumes):
    """
    Algorithm 4: A* Pathfinding
    Finds the least-congested path from start to goal.

    Priority queue: (f_cost, node, path)
    f_cost = g_cost (actual) + h_cost (heuristic)
    """
    graph = build_dynamic_graph(volumes)
    
    # (f_cost, g_cost, current_node, path_so_far)
    open_set = [(0 + heuristic(start, goal), 0, start, [start])]
    visited = set()

    while open_set:
        f, g, current, path = heapq.heappop(open_set)

        if current in visited:
            continue
        visited.add(current)

        if current == goal:
            return path, round(g, 2)  # path + total cost

        for (neighbor, weight) in graph.get(current, []):
            if neighbor not in visited:
                new_g = g + weight
                new_f = new_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (new_f, new_g, neighbor, path + [neighbor]))

    return None, float('inf')  # No path found

def tomtom_simulate(intersection, tick):
    """
    TomTom API Simulation
    In production: replace with real TomTom Traffic Flow API call.
    GET https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json
        ?key=YOUR_API_KEY&point=lat,lng

    Here we simulate the response with realistic random walk + peak hour.
    """
    base = state['volumes'][intersection]
    noise = random.uniform(-8, 8)
    
    # Simulate peak hour buildup at I-A during ticks 10-20
    if 10 <= tick <= 20 and intersection == 'I-A':
        noise += 14

    # Gradual recovery after peak
    if tick > 20 and intersection == 'I-A':
        noise -= 5

    new_vol = max(10, min(100, base + noise))
    return round(new_vol, 1)

def log_event(message, level='INFO'):
    entry = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': message
    }
    state['event_log'].append(entry)
    # Keep last 50 events
    if len(state['event_log']) > 50:
        state['event_log'].pop(0)

def simulation_tick():
    """One tick of the simulation — called every second by background thread"""
    with lock:
        if not state['running']:
            return

        state['tick'] += 1
        tick = state['tick']

        # Step 1: Ingest sensor data (TomTom simulation)
        for inter in NODES:
            state['volumes'][inter] = tomtom_simulate(inter, tick)
            # Store history (last 30 ticks for chart)
            state['history'][inter].append(state['volumes'][inter])
            if len(state['history'][inter]) > 30:
                state['history'][inter].pop(0)

        # Step 2: Process each intersection
        for inter in NODES:
            vol = state['volumes'][inter]
            level = classify_congestion(vol)

            if level == 'HIGH' and not state['congestion_flags'].get(inter):
                state['reroute_count'] += 1
                state['congestion_flags'][inter] = True
                alts = reroute(inter)
                log_event(f"CONGESTION at {inter} ({vol:.0f} veh/min). Re-routing!", 'ALERT')
                log_event(f"Alternate routes: {' | '.join(alts)}", 'INFO')

                # Mark re-routed routes in active_routes
                for rname, rdata in state['active_routes'].items():
                    src, dst = rdata['path']
                    if inter in (src, dst):
                        state['active_routes'][rname]['status'] = 'rerouted'
                    else:
                        state['active_routes'][rname]['status'] = 'active'

                # Run A* to find best alternate path
                # Find a node that isn't the congested one
                alts_nodes = [n for n in NODES if n != inter]
                if len(alts_nodes) >= 2:
                    path, cost = astar(alts_nodes[0], alts_nodes[-1], state['volumes'])
                    state['astar_result'] = {
                        'path': path,
                        'cost': cost,
                        'avoiding': inter
                    }
                    log_event(f"A* path: {' → '.join(path)} (cost: {cost})", 'INFO')

            if level != 'HIGH' and state['congestion_flags'].get(inter):
                state['congestion_flags'][inter] = False
                log_event(f"{inter} congestion cleared.", 'SUCCESS')
                for rname, rdata in state['active_routes'].items():
                    state['active_routes'][rname]['status'] = 'normal'

        # Step 3: Emergency vehicle (if triggered via API)
        if state['emergency']:
            inter = state['emergency_intersection']
            log_event(f"EMERGENCY VEHICLE at {inter}! All signals → GREEN 90s", 'ALERT')
            alt = reroute(inter)
            log_event(f"Cross traffic diverted: {', '.join(alt)}", 'INFO')
            state['emergency'] = False

# ─────────────────────────────────────────────────────
# BACKGROUND SIMULATION THREAD
# ─────────────────────────────────────────────────────
def simulation_loop():
    while True:
        simulation_tick()
        time.sleep(1)

thread = threading.Thread(target=simulation_loop, daemon=True)
thread.start()

# ─────────────────────────────────────────────────────
# REST API ENDPOINTS
# ─────────────────────────────────────────────────────

@app.route('/api/status')
def get_status():
    """Main status endpoint — frontend polls this every second"""
    with lock:
        volumes = state['volumes']
        result = {}
        for inter in NODES:
            vol = volumes[inter]
            level = classify_congestion(vol)
            signal = adjust_signal(vol)
            result[inter] = {
                'volume': vol,
                'level': level,
                'signal': signal,
                'label': NODES[inter]['label'],
            }
        return jsonify({
            'tick': state['tick'],
            'intersections': result,
            'reroute_count': state['reroute_count'],
            'active_routes': state['active_routes'],
            'astar_result': state['astar_result'],
            'event_log': state['event_log'][-10:],
        })

@app.route('/api/heatmap')
def get_heatmap():
    """
    Heatmap data endpoint
    Returns volume at each node + coordinates for frontend to render
    """
    with lock:
        data = []
        for inter, coords in NODES.items():
            vol = state['volumes'][inter]
            level = classify_congestion(vol)
            data.append({
                'id': inter,
                'x': coords['x'],
                'y': coords['y'],
                'label': coords['label'],
                'volume': vol,
                'level': level,
                'intensity': min(vol / 100, 1.0),  # normalized 0–1 for heatmap color
            })
        return jsonify(data)

@app.route('/api/history')
def get_history():
    """Returns time-series data for chart"""
    with lock:
        return jsonify({
            'ticks': list(range(1, len(state['history']['I-A']) + 1)),
            'data': state['history'],
            'threshold_high': THRESHOLD_HIGH,
            'threshold_low': THRESHOLD_LOW,
        })

@app.route('/api/astar', methods=['POST'])
def run_astar():
    """
    Manually trigger A* from frontend
    POST body: { "start": "I-A", "goal": "I-D" }
    """
    body = request.json
    start = body.get('start', 'I-A')
    goal = body.get('goal', 'I-D')
    with lock:
        path, cost = astar(start, goal, state['volumes'])
        result = {
            'start': start,
            'goal': goal,
            'path': path,
            'cost': cost,
            'volumes_used': {k: state['volumes'][k] for k in NODES}
        }
        state['astar_result'] = result
        log_event(f"Manual A* from {start}→{goal}: {' → '.join(path or [])} (cost {cost})", 'INFO')
    return jsonify(result)

@app.route('/api/emergency', methods=['POST'])
def trigger_emergency():
    """Trigger emergency vehicle at a given intersection"""
    body = request.json
    inter = body.get('intersection', 'I-A')
    with lock:
        state['emergency'] = True
        state['emergency_intersection'] = inter
    return jsonify({'status': 'Emergency triggered', 'intersection': inter})

@app.route('/api/congestion', methods=['POST'])
def trigger_congestion():
    """Manually spike congestion at an intersection (for demo)"""
    body = request.json
    inter = body.get('intersection', 'I-A')
    with lock:
        state['volumes'][inter] = 90.0
    return jsonify({'status': 'Congestion simulated', 'intersection': inter})

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset simulation state"""
    with lock:
        state['tick'] = 0
        state['reroute_count'] = 0
        state['event_log'] = []
        state['congestion_flags'] = {}
        state['astar_result'] = None
        state['history'] = {k: [] for k in NODES}
        state['volumes'] = {'I-A': 38.0, 'I-B': 52.0, 'I-C': 29.0, 'I-D': 44.0}
        for r in state['active_routes']:
            state['active_routes'][r]['status'] = 'normal'
        log_event('System reset.', 'SUCCESS')
    return jsonify({'status': 'Reset complete'})

@app.route('/api/pause', methods=['POST'])
def toggle_pause():
    with lock:
        state['running'] = not state['running']
        status = 'running' if state['running'] else 'paused'
        log_event(f'Simulation {status}.', 'INFO')
    return jsonify({'status': status})

# Serve dashboard.html from root URL
@app.route('/')
def index():
    # Look for dashboard.html next to app.py
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')
    if os.path.exists(html_path):
        return send_file(html_path)
    return '<h2>dashboard.html not found — place it in the same folder as app.py</h2>', 404

if __name__ == '__main__':
    thread = threading.Thread(target=simulation_loop, daemon=True)
    thread.start()
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*55)
    print("  IoT Smart Traffic System")
    print(f"  Open http://localhost:{port} in your browser")
    print("="*55 + "\n")
    app.run(debug=False, host='0.0.0.0', port=port)
