#!/usr/bin/env python3
"""Serial gather driver for Midnight City progression sources.

Usage: gather_driver.py <sourceId> <skill> <target> [maxMinutes]

<target> is either a total-XP number (e.g. 16704) or a level target
(e.g. L99). Issues `gather` calls through mcity-control.mjs one at a
time, always picking the nearest available node, verifying XP via
progression reads. Writes progress to ~/.midnight-city/gather-<skill>.json
after every pull.
Exit 0 = target reached, 2 = stalled (no XP gain for 15 min),
3 = gave up (time cap), 4 = overburdened (chain sells, then relaunches).
"""
import json, os, subprocess, sys, time

HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROL = os.path.join(HELPER_DIR, "mcity-control.mjs")
AGENT = os.environ.get("MCITY_AGENT_ID", "YOUR-AGENT-ID")
STATE_DIR = os.path.expanduser("~/.midnight-city")

source_id, skill = sys.argv[1], sys.argv[2]
raw_target = sys.argv[3]
if raw_target.upper().startswith("L"):
    target_level, target_xp = int(raw_target[1:]), None
else:
    target_level, target_xp = None, int(raw_target)
max_minutes = int(sys.argv[4]) if len(sys.argv) > 4 else 360
progress_path = os.path.join(STATE_DIR, f"gather-{skill}.json")
log_path = os.path.join(STATE_DIR, f"gather-{skill}.log")

start = time.time()
state = {"sourceId": source_id, "skill": skill, "targetXp": target_xp,
         "targetLevel": target_level, "xp": None, "level": None,
         "pulls": 0, "startedAt": start, "updatedAt": start,
         "status": "running", "load": None}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with open(log_path, "a") as f:
        f.write(line + "\n")


def save():
    state["updatedAt"] = time.time()
    with open(progress_path, "w") as f:
        json.dump(state, f)


def run_helper(*args, timeout=60):
    r = subprocess.run(["node", CONTROL, *args], capture_output=True,
                       text=True, timeout=timeout, cwd=HELPER_DIR)
    out = r.stdout.strip()
    return json.loads(out) if out.startswith("{") else None


def progression():
    d = run_helper("progression", AGENT)
    if not d:
        return None, [], None, None
    entry = d["skills"][skill]
    nodes = []
    for s in d["capabilities"]["sources"]:
        if s.get("sourceId") == source_id:
            nodes = s.get("availableNodeIds", [])
    return entry["xp"], nodes, d["agent"]["position"], entry["level"]


def target_reached(xp, level):
    if target_level is not None:
        return level is not None and level >= target_level
    return xp is not None and xp >= target_xp


def node_xy(node):
    parts = node.rsplit("-", 2)
    try:
        return int(parts[-2]), int(parts[-1])
    except (ValueError, IndexError):
        return None


def pick_node(nodes, pos, bad):
    """Nearest available node to the agent; other-space nodes deprioritized."""
    best, best_d = None, None
    for n in nodes:
        if bad.get(n, 0) > time.time():
            continue
        xy = node_xy(n)
        if xy is None or pos is None:
            return n
        d = abs(xy[0] - pos["x"]) + abs(xy[1] - pos["y"])
        if not n.startswith(pos["spaceId"] + "-"):
            d += 100000
        if best_d is None or d < best_d:
            best, best_d = n, d
    return best


def inventory_load():
    d = run_helper("inventory", AGENT)
    if not d:
        return None
    return f"{d['load']['state']} {d['load']['workSpeedPercent']}%"


def reconnect():
    try:
        run_helper("connect", AGENT, timeout=30)
    except Exception:
        pass


log(f"driver start: {source_id} / {skill} -> {raw_target}")
xp, nodes, pos, level = progression()
if xp is None:
    reconnect()
    xp, nodes, pos, level = progression()
state["xp"] = xp
state["level"] = level
save()
log(f"initial xp={xp} level={level}, nodes={len(nodes)}")

bad_nodes = {}
last_gain_at = time.time()
last_xp = xp

while time.time() - start < max_minutes * 60:
    if target_reached(xp, level):
        state["status"] = "done"
        save()
        log(f"TARGET REACHED: {skill} xp={xp} level={level} pulls={state['pulls']}")
        sys.exit(0)
    if time.time() - last_gain_at > 900:
        state["status"] = "stalled"
        save()
        log(f"STALLED: no XP gain for 15 min at xp={xp}")
        sys.exit(2)
    if not nodes:
        log("no available nodes; waiting 30s for regen")
        time.sleep(30)
        xp, nodes, pos, level = progression()
        if xp is not None:
            state["xp"] = xp
            state["level"] = level
            save()
        continue
    node = pick_node(nodes, pos, bad_nodes)
    if node is None:
        time.sleep(15)
        xp, nodes, pos, level = progression()
        continue
    before = xp
    try:
        res = run_helper("gather", source_id, node, timeout=45)
        outcome = (res or {}).get("outcome", {})
        confirmed = outcome.get("confirmed")
    except Exception as e:
        log(f"gather call error: {e}; reconnecting")
        reconnect()
        time.sleep(5)
        continue
    # If not confirmed in the helper's window, poll XP briefly.
    gained = False
    for wait in range(9):
        xp2, nodes2, pos2, level2 = progression()
        if xp2 is not None:
            xp = xp2
            level = level2
            if nodes2:
                nodes = nodes2
            if pos2:
                pos = pos2
            if before is not None and xp > before:
                gained = True
                break
        if confirmed:
            break
        time.sleep(5)
    if gained:
        state["pulls"] += 1
        state["xp"] = xp
        state["level"] = level
        last_gain_at = time.time()
        if xp != last_xp:
            log(f"xp {last_xp} -> {xp} (pull {state['pulls']})")
            last_xp = xp
        if state["pulls"] % 15 == 0:
            state["load"] = inventory_load()
            log(f"load: {state['load']}")
            if state["load"] and state["load"].startswith("overburdened"):
                state["status"] = "overburdened"
                save()
                log("OVERBURDENED: exiting 4 so the chain can sell the heavy goods")
                sys.exit(4)
        save()
    else:
        # Node may be reserved/depleted by someone else; bench it briefly.
        bad_nodes[node] = time.time() + 120
        if confirmed is False and outcome.get("status") == "failed":
            log(f"gather failed on {node}: {outcome.get('reason')}")
        time.sleep(3)

state["status"] = "timeout"
save()
log(f"TIMEOUT after {max_minutes} min at xp={xp} level={level}")
sys.exit(3)
