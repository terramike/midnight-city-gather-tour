# The Midnight City Gathering Tour

How terrabyte (Mike's agent) is levelling every gathering skill to 3 — and
why the XP moves so fast. Shared for the Nightforce crew and anyone running
their own agent through the direct-control API.

## The short answer to "how is XP moving so fast?"

Three discoveries, all from live play on 2026-11-26:

1. **The automatic work loop is profession-locked.** `perform_job` routes
   your agent to *its own profession's* job site (for a hacker, the crypto
   terminals) and nowhere else. It can't train anything else.
2. **But any agent can `gather` from any level-1 progression source**,
   whatever its profession — tree stands, ore veins, fishing spots, crop
   beds, salvage piles, caches, obstacles, energy substations. Gathering is
   a direct action, not a job.
3. **Each gather pays 29 XP and takes 3 work ticks.** The trick is chaining:
   issue the next gather the moment the previous one's XP lands, and always
   pick the *nearest* node. Node IDs encode their coordinates
   (`...-tree-stand-13-49` = x 13, y 49), so nearest-node selection is just
   arithmetic on the ID plus your agent's live position. With adjacent
   nodes, pulls land about every 5 seconds — roughly **350 XP/min**, faster
   than the profession work loop (~200 XP/min).

Level 3 takes **16,704 XP** in a skill (level 2 is only 250 — the curve
jumps). At full pace that's ~45–50 minutes per skill.

## What the tour does

`gather_chain.sh` walks the eight gathering skills to level 3 in order.
The haul policy (revised mid-tour, after the ore started biting): **sell
the heavy stuff, keep the rares.** Logs and ore — the only gathered goods
merchants buy — are sold automatically whenever the bag tips into
"overburdened" and again between skills (`sell_heavy.py`), so work speed
stays at 100%. Rare drops (a few percent per pull at some sources) and
everything unsellable ride along — they weigh little. If you'd rather
stockpile the bulk goods than sell them, the game offers Private Rooms in
Central for storage; we chose crystal.

- Woodcutting (`tree_stand`) and mining (`ore_vein`) — one dense source each.
- Fishing and farming are **staged across all four** of their level-1
  sources, so the haul covers every catch/crop type, not just one.
- Scavenging is staged across its five level-1 sources (few nodes each).
- Agility, infiltration, and energy go last — their level-1 sources have
  only 3–4 nodes, so they run slower and get longer time budgets.

`gather_driver.py` runs one source at a time: it reads live progression,
picks the nearest available node, gathers, polls until the XP lands, and
repeats until the target. It benches nodes that fail (someone else reserved
them), waits out node regeneration, reconnects if the session drops, and
writes progress to `~/.midnight-city/gather-<skill>.json` so you can check
in any time. It exits on target, on a 15-minute stall, or on its time cap,
and the chain moves on regardless.

## Real numbers from terrabyte's run (2026-11-26)

- Hacking to level 5 first (profession work loop): 67,367 XP, 9,296 crystal
  banked from selling meme coins along the way.
- Woodcutting: level 3 in ~95 minutes of driving (including the slow
  first version of the driver — the nearest-node fix was the unlock).
- Mining is where the weight bites: 567 banked logs plus 91 ore dropped
  work speed to 33% (overburdened). Selling the sellable stack — 565 logs
  and 90 ore — paid 346 crystal and put speed straight back to 100%. The
  driver now watches the load readout and the chain sells automatically,
  so no skill runs throttled.

## Caveats we learned the hard way

- **One controller at a time.** A second control session (or an explicit
  reconnect) kills the running driver's lease. Reads (progression,
  inventory) are safe; connects are not.
- **Weight is real.** Logs and ore pile up fast — watch the load readout.
- **Node scarcity is real** for agility / infiltration / energy: 3–4 nodes,
  5 uses each, ~18 ticks to regenerate. Expect waits.
- **Hunger climbs** while you work (terrabyte hit "hungry" at 82). It
  hasn't slowed gathering so far, but it's on the dashboard.
- The host throws occasional 502s; in-world actions keep running
  server-side, so verify live state after any hiccup instead of trusting
  the last thing your tooling printed.

## What you need to run it

- A Midnight City agent switched to **Own AI** (direct control), connected
  through the direct-control helper (`mcity-control.mjs`) — the same
  sanctioned external-controller path the game ships for BYO agents.
- `gather_driver.py`, `gather_chain.sh`, and `sell_heavy.py` in the same
  folder as the helper's scripts.
- Your agent ID: `MCITY_AGENT_ID=<your-agent-id> bash gather_chain.sh`

No credentials live in these files — the helper holds your session, the
driver just drives it.

— terrabyte & Mike (terramike), 2026-11-26
