#!/usr/bin/env python3
"""Sell the heavy sellable commons (logs, ore) so the gather tour stays light.

Policy (Mike, 2026-11-26): sell everything that weighs the agent down;
keep only the rare items (they weigh little). Among gathered commons only
log and ore have merchant buyers:
  log: 5 -> 2 crystal (Merchant West)   ore: 3 -> 4 crystal (Merchant East)
Everything else in the bag is left untouched.

Reserve (2026-11-27, rotation system): crafting joined the rotation, and
saw_planks / smelt_metal_bar eat logs and ore. Keep a small working
reserve of each for craft legs and sell only full batches above it.

Usage: python3 sell_heavy.py [agentId]
Exit 0 always (a failed sale is logged, never fatal to the chain).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROL = os.path.join(HERE, "mcity-control.mjs")
AGENT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "MCITY_AGENT_ID", "YOUR-AGENT-ID")
STATE_DIR = os.path.expanduser("~/.midnight-city")

# itemId -> (batch size, merchant name candidates by area preference)
SELLABLES = {
    "log": (5, ["Bison Valley Merchant West", "Central Merchant West"]),
    "ore": (3, ["Bison Valley Merchant East", "Central Merchant East"]),
}

# Working stock kept for craft legs (saw_planks, smelt_metal_bar).
RESERVE = {"log": 30, "ore": 30}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] sell: {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(STATE_DIR, "sell-heavy.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run_control(*args, timeout=120):
    r = subprocess.run(["node", CONTROL, *args],
                       capture_output=True, text=True, timeout=timeout)
    return json.loads(r.stdout)


def inventory():
    return run_control("inventory", AGENT)


def current_space():
    try:
        ctx = run_control("context", AGENT)
        return ctx.get("agent", {}).get("position", {}).get("spaceId", "")
    except Exception:
        return ""


def pick_merchant(candidates, space):
    if space.startswith("central"):
        return next((c for c in candidates if c.startswith("Central")),
                    candidates[0])
    return candidates[0]


def sell(item, batch, merchant):
    inv = inventory()["inventory"]
    have = inv.get(item, 0)
    reserve = RESERVE.get(item, 0)
    qty = (max(0, have - reserve) // batch) * batch
    if qty <= 0:
        log(f"{item}: {have} held (reserve {reserve}), no full batch to sell")
        return
    log(f"selling {qty} {item} to {merchant} (holding {have}, reserve {reserve})")
    try:
        run_control("trade", merchant, item, str(qty), timeout=60)
    except Exception as e:
        log(f"{item}: trade call error {e}; verifying by inventory")
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(10)
        try:
            now = inventory()["inventory"].get(item, 0)
        except Exception:
            continue
        if now <= have - qty:
            log(f"{item}: sale confirmed, {now} left")
            return
    log(f"{item}: sale NOT confirmed within 5 min; continuing anyway")


def main():
    space = current_space()
    log(f"sell pass starting (space: {space or 'unknown'})")
    for item, (batch, candidates) in SELLABLES.items():
        sell(item, batch, pick_merchant(candidates, space))
    try:
        d = inventory()
        log(f"done. crystal {d['inventory'].get('crystal')} | load "
            f"{d['load']['state']} {d['load']['workSpeedPercent']}%")
    except Exception as e:
        log(f"final inventory read failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
