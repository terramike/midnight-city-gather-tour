#!/usr/bin/env python3
"""Craft-leg driver for Midnight City's rotation system.

Usage: craft_driver.py <skill> <target> [maxMinutes]

Trains one craft skill (crafting, smithing, cooking, chemistry,
engineering) by repeatedly crafting the best recipe that trains it:
highest required level the agent has unlocked, with inputs in the bag
(craftableBatches > 0 and no failureReason in live progression).
<target> is a total-XP number, a level target like L99, or "next"
(current level + 1, resolved at start) for rotation legs.

Progress goes to ~/.midnight-city/gather-<skill>.json (same schema as
the gather driver, so the watcher treats every skill uniformly).
Exit 0 = target reached, 2 = stalled (no XP gain for 15 min),
3 = time cap, 4 = overburdened, 5 = hungry/starving,
6 = already level 99 (target "next" only),
7 = nothing craftable (no unlocked recipe with inputs in the bag);
the rotation chain treats 7 as a skipped leg, not a failure.
"""
import json, os, subprocess, sys, time

HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROL = os.path.join(HELPER_DIR, "mcity-control.mjs")
AGENT = os.environ.get("MCITY_AGENT_ID", "YOUR-AGENT-ID")
STATE_DIR = os.path.expanduser("~/.midnight-city")

skill = sys.argv[1]
raw_target = sys.argv[2]
leg_mode = raw_target.lower() == "next"
if leg_mode:
    target_level, target_xp = None, None
elif raw_target.upper().startswith("L"):
    target_level, target_xp = int(raw_target[1:]), None
else:
    target_level, target_xp = None, int(raw_target)
max_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 360
progress_path = os.path.join(STATE_DIR, f"gather-{skill}.json")
log_path = os.path.join(STATE_DIR, f"gather-{skill}.log")

start = time.time()
state = {"sourceId": None, "tier": None, "skill": skill,
         "targetXp": target_xp, "targetLevel": target_level,
         "xp": None, "level": None, "pulls": 0, "startedAt": start,
         "updatedAt": start, "status": "running", "load": None}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] craft: {msg}"
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


_def_skill_cache = {}


def recipe_skill(row):
    """Which skill a recipe trains: from the progression row when it
    carries one, else from the recipe definition (cached)."""
    s = row.get("skill") or row.get("skillId")
    if s:
        return s
    rid = row.get("recipeId") or row.get("id")
    if rid in _def_skill_cache:
        return _def_skill_cache[rid]
    found = None
    d = run_helper("definition", "recipe", rid)
    if isinstance(d, dict):
        defn = d.get("definition", d)
        if isinstance(defn, dict):
            found = defn.get("skill") or defn.get("skillId")
    _def_skill_cache[rid] = found
    return found


def progression():
    """Return (xp, level, recipes) for this skill."""
    d = run_helper("progression", AGENT)
    if not d:
        return None, None, []
    entry = d["skills"][skill]
    recipes = d.get("capabilities", {}).get("recipes", [])
    return entry["xp"], entry["level"], recipes


def pick_recipe(recipes, current_id):
    """Best craftable recipe training this skill: highest required
    level unlocked, then most craftable batches. Stick with the
    current recipe while it stays craftable."""
    cands = []
    for row in recipes:
        if recipe_skill(row) != skill:
            continue
        if row.get("failureReason"):
            continue
        batches = row.get("craftableBatches") or 0
        if batches <= 0:
            continue
        rid = row.get("recipeId") or row.get("id")
        cands.append((row.get("requiredLevel") or 1, batches, rid, row))
    if not cands:
        return None
    for c in cands:
        if c[2] == current_id:
            return c
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return cands[0]


def target_reached(xp, level):
    if target_level is not None:
        return level is not None and level >= target_level
    return xp is not None and xp >= target_xp


def inventory_load():
    d = run_helper("inventory", AGENT)
    if not d:
        return None
    return f"{d['load']['state']} {d['load']['workSpeedPercent']}%"


def hunger_state():
    d = run_helper("needs", AGENT)
    if not d:
        return None
    return d["hunger"]["state"]


def reconnect():
    try:
        run_helper("connect", AGENT, timeout=30)
    except Exception:
        pass


log(f"driver start: {skill} -> {raw_target} (craft)")
xp, level, recipes = progression()
if xp is None:
    reconnect()
    xp, level, recipes = progression()
state["xp"] = xp
state["level"] = level
if leg_mode:
    if level is not None and level >= 99:
        state["status"] = "done"
        state["targetLevel"] = 99
        save()
        log(f"ALREADY 99: {skill} is level 99; leg skipped")
        sys.exit(6)
    if level is not None:
        target_level = level + 1
        state["targetLevel"] = target_level
        log(f"leg target resolved: {skill} L{level} -> L{target_level}")
save()
log(f"initial xp={xp} level={level}")

last_gain_at = time.time()
last_xp = xp
craft_calls = 0

while time.time() - start < max_minutes * 60:
    if target_reached(xp, level):
        state["status"] = "done"
        save()
        log(f"TARGET REACHED: {skill} xp={xp} level={level} batches={state['pulls']}")
        sys.exit(0)
    if time.time() - last_gain_at > 900:
        state["status"] = "stalled"
        save()
        log(f"STALLED: no XP gain for 15 min at xp={xp}")
        sys.exit(2)
    pick = pick_recipe(recipes, state["sourceId"])
    if pick is None:
        state["status"] = "no-inputs"
        save()
        log(f"NO CRAFTABLE RECIPE for {skill} at xp={xp} level={level}: "
            f"leg skipped (exit 7)")
        sys.exit(7)
    req_level, batches_avail, rid, _row = pick
    if rid != state["sourceId"]:
        log(f"RECIPE: {rid} (req {req_level}, {batches_avail} batches craftable)")
        state["sourceId"] = rid
        state["tier"] = req_level
        save()
    n = min(batches_avail, 10)
    before = xp
    try:
        run_helper("craft", rid, str(n), timeout=240)
    except Exception as e:
        log(f"craft call error: {e}; reconnecting")
        reconnect()
        time.sleep(5)
        continue
    craft_calls += 1
    gained = False
    for _wait in range(12):
        xp2, level2, recipes2 = progression()
        if xp2 is not None:
            xp, level = xp2, level2
            if recipes2:
                recipes = recipes2
            if before is not None and xp > before:
                gained = True
                break
        time.sleep(5)
    if gained:
        state["pulls"] += n
        state["xp"] = xp
        state["level"] = level
        last_gain_at = time.time()
        if xp != last_xp:
            log(f"xp {last_xp} -> {xp} (+{xp - last_xp}, batches {state['pulls']})")
            last_xp = xp
        if craft_calls % 5 == 0:
            state["load"] = inventory_load()
            log(f"load: {state['load']}")
            if state["load"] and state["load"].startswith("overburdened"):
                state["status"] = "overburdened"
                save()
                log("OVERBURDENED: exiting 4 so the chain can sell")
                sys.exit(4)
            hunger = hunger_state()
            if hunger in ("hungry", "starving"):
                state["status"] = "hungry"
                save()
                log(f"HUNGRY ({hunger}): exiting 5 so the chain can feed")
                sys.exit(5)
        save()
    else:
        log(f"craft of {rid} x{n} produced no XP gain; re-checking recipes")
        time.sleep(5)
        xp, level, recipes = progression()

state["status"] = "timeout"
save()
log(f"TIMEOUT after {max_minutes} min at xp={xp} level={level}")
sys.exit(3)
