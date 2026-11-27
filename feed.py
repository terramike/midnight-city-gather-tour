#!/usr/bin/env python3
"""Feed the agent: eat fish until hunger state is "normal".

Facts measured live (2026-11-26): 1 fish = -50 hunger; the eat command
no-ops when hunger is already 0; hunger states run normal -> hungry ->
starving, and hunger slows work. Fish are bought at the Bison Valley
Fresh Fish Outlet (58 crystal each) when none are carried.

Usage: python3 feed.py [agentId]
Exit 0 always (failures are logged, never fatal to the chain).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROL = os.environ.get("MCITY_CONTROL", os.path.join(HERE, "mcity-control.mjs"))
AGENT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "MCITY_AGENT_ID", "YOUR-AGENT-ID")
STATE_DIR = os.path.expanduser("~/.midnight-city")
OUTLET = "Bison Valley Fresh Fish Outlet"
FISH_PRICE = 58
BUY_COUNT = 5


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] feed: {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(STATE_DIR, "feed.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run_control(*args, timeout=120):
    r = subprocess.run(["node", CONTROL, *args],
                       capture_output=True, text=True, timeout=timeout)
    return json.loads(r.stdout)


def hunger():
    return run_control("needs", AGENT)["hunger"]


def fish_count():
    return run_control("inventory", AGENT)["inventory"].get("fish", 0)


def buy_fish():
    cost = FISH_PRICE * BUY_COUNT
    log(f"buying {BUY_COUNT} fish for {cost} crystal at {OUTLET}")
    try:
        run_control("trade", OUTLET, "crystal", str(cost), timeout=60)
    except Exception as e:
        log(f"trade call error {e}; verifying by inventory")
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(10)
        try:
            if fish_count() > 0:
                log(f"fish arrived: {fish_count()} carried")
                return True
        except Exception:
            continue
    log("fish purchase NOT confirmed within 5 min")
    return False


def main():
    try:
        h = hunger()
    except Exception as e:
        log(f"needs read failed: {e}")
        return 0
    log(f"hunger check: value={h['value']} state={h['state']}")
    cycles = 0
    while h["state"] != "normal" and cycles < 8:
        cycles += 1
        if fish_count() <= 0 and not buy_fish():
            break
        try:
            run_control("eat", AGENT, timeout=60)
        except Exception as e:
            log(f"eat call error {e}")
        time.sleep(8)
        try:
            h = hunger()
        except Exception as e:
            log(f"needs re-read failed: {e}")
            break
        log(f"after eat {cycles}: value={h['value']} state={h['state']}")
    log(f"done. hunger value={h['value']} state={h['state']}, "
        f"fish carried={fish_count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
