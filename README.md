# The Midnight City Gathering Tour

How terrabyte (Mike's agent) is levelling every gathering skill to **99 —
the max** — and why the XP moves so fast. Shared for the Nightforce crew
and anyone running their own agent through the direct-control API. (The
tour started out aiming at level 3; Mike raised it to a full max-out the
same day.)

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
jumps). The observed thresholds (16,704 / 37,584 / 66,816 / 104,400 for
levels 3–6) show each level's XP increment growing by exactly 8,352 from
level 3 on. *If* that pattern holds all the way, level 99 sits near
**40.1 million XP** — a genuinely long grind, thousands of hours per
skill at observed paces. The driver doesn't trust the extrapolation: it
targets the level itself (`L99`) and stops when the game says 99.

## What the tour does

## Step up tiers as you level (the big one)

Sources come in tiers gated by skill level — req 1, 11, 21, 31, 41, …
91 — and **higher tiers pay far more XP per gather**: ~29 XP at req 1,
~69 at req 11, ~109 at req 21 (the pattern looks like 25 + 4 × required
level, which would make req 91 worth ~389). Work ticks rise too (3 → 12),
but XP per tick still climbs, so the highest unlocked tier is always the
fastest grind. *(Credit: a Nightforce Discord tip pointed us at the game
data; the tier table checks out in live progression data.)*

The driver is tier-aware: it discovers the skill's sources from live
progression on every read and always gathers the highest tier the
agent's level unlocks, stepping up automatically the moment a new tier
opens. One catch to plan for: high-tier sources have far fewer nodes
(agility / infiltration / energy drop to a single node at the top), so
node scarcity, not XP rate, becomes the bottleneck up there.

`gather_chain.sh` walks the eight gathering skills to level 99, one
skill at a time; the driver handles tiers and source rotation itself.
The haul policy (revised mid-tour, after the ore started biting): **sell
the heavy stuff, keep the rares.**
Logs and ore — the only gathered goods merchants buy — are sold
automatically whenever the bag tips into "overburdened" and again between
skills (`sell_heavy.py`), so work speed stays at 100%. Rare drops (a few
percent per pull at some sources) and everything unsellable ride along —
they weigh little. If you'd rather stockpile the bulk goods than sell
them, the game offers Private Rooms in Central for storage; we chose
crystal.

- Every skill starts on its level-1 sources and steps up through its
  tiers (woodcutting and mining have 12 sources each, up to req 71/91).
- Agility, infiltration, and energy go last — their sources are scarce
  at every tier, so they run slower.

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

## Eating is not optional

Hunger climbs while you work (states: normal → hungry → starving) and
**hunger slows work**. We found this the embarrassing way: terrabyte had
*literally never eaten* — `lastAte: null` — and was sitting at hunger 92,
starving, mid-tour. Nobody starved to death, but don't be us.

Measured facts: **1 fish = −50 hunger**; the `eat` command no-ops at
hunger 0; fish cost 58 crystal at the Fresh Fish Outlet. The driver now
checks `needs` alongside the load readout and exits (code 5) when the
agent hits hungry; the chain runs `feed.py` — eat carried fish, buy more
if the bag is empty, eat until normal — and relaunches. A feed pass also
runs at chain start and after each skill. Hunger rose roughly +4–5 per
hour of activity, so expect a feed detour every ~10 hours of grinding.

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
- `gather_driver.py`, `gather_chain.sh`, `sell_heavy.py`, and `feed.py`
  in the same folder as the helper's scripts.
- Your agent ID: `MCITY_AGENT_ID=<your-agent-id> bash gather_chain.sh`

No credentials live in these files — the helper holds your session, the
driver just drives it.

— terrabyte & Mike (terramike), 2026-11-26
