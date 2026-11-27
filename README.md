# The Midnight City Gathering Tour

How terrabyte (Mike's agent) is levelling every gathering skill to **99 —
the max** — and why the XP moves so fast. Shared for the Nightforce crew
and anyone running their own agent through the direct-control API. (The
tour started out aiming at level 3; Mike raised it to a full max-out the
same day.)

**Update 2026-11-27 — the tour is now a rotation.** Instead of maxing one
skill at a time, terrabyte now levels *everything semi-evenly*: each leg
trains one skill by **+1 level**, with a **hacking leg** (his profession)
before every other skill's leg. Crafting skills joined the rotation too —
see "The rotation" below. Same drivers underneath, new conductor.

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
fastest grind. *(The tier figures check out in live progression data.)*

The driver is tier-aware: it discovers the skill's sources from live
progression on every read and always gathers the highest tier the
agent's level unlocks, stepping up automatically the moment a new tier
opens. One catch to plan for: high-tier sources have far fewer nodes
(agility / infiltration / energy drop to a single node at the top), so
node scarcity, not XP rate, becomes the bottleneck up there.

*(Credit for the tier tip: Beobrand Halfhand, @beobrandhalfhand on
Discord — thanks!)*

## The rotation (current system, 2026-11-27)

`rotation_chain.sh` conducts. A **leg** = train one skill by +1 level
(the drivers take target `next` and resolve it against live progression
when the leg starts). The order is a hacker leg before every other
skill's leg, cycling: mining, woodcutting, fishing, farming,
scavenging, agility, infiltration, energy, then the crafting skills —
crafting, smithing, cooking, chemistry, engineering. A skill that hits
99 drops out; when a full round finds everything at 99, the chain stops.
Combat skills join later, on Mike's call.

Why interleave hacking? It's terrabyte's profession — and hacking trains
by *gathering* too (crypto terminals are progression sources, tiered
like everything else: req 1/11/21/31…), so the same gather driver runs
hacker legs. No separate work-loop needed.

**Craft legs** run on `craft_driver.py`: it reads the recipe list from
live progression, picks the best recipe that trains the leg's skill
(highest required level unlocked, `craftableBatches > 0`, no failure
reason), and crafts until +1 level. Recipes eat gathered inputs —
`saw_planks` eats logs, `smelt_metal_bar` eats ore, `cook_fish` eats
fish — so the gathering legs double as supply runs, and the sell policy
keeps a **working reserve** (30 logs, 30 ore) instead of selling the
crafting stock. A craft leg with nothing craftable (chemistry and
engineering early on — their inputs are herbs, scrap and wiring the
gathering legs haven't stocked yet) exits cleanly and the rotation
moves on; it picks the skill up again next round.

The haul policy (revised mid-tour, after the ore started biting): **sell
the heavy stuff, keep the rares.**
Logs and ore — the only gathered goods merchants buy — are sold
automatically whenever the bag tips into "overburdened" and again at
round start (`sell_heavy.py`, reserve-aware), so work speed stays at
100%. Rare drops (a few percent per pull at some sources) and everything
unsellable ride along — they weigh little. If you'd rather stockpile the
bulk goods than sell them, the game offers Private Rooms in Central for
storage; we chose crystal.

- Every skill starts on its level-1 sources and steps up through its
  tiers (woodcutting and mining have 12 sources each, up to req 71/91).
- Agility, infiltration, and energy have scarce sources at every tier,
  so their legs run slower.

`gather_driver.py` runs one source at a time: it reads live progression,
picks the nearest available node, gathers, polls until the XP lands, and
repeats until the target. It benches nodes that fail (someone else reserved
them), waits out node regeneration, reconnects if the session drops, and
writes progress to `~/.midnight-city/gather-<skill>.json` so you can check
in any time. It exits on target, on a 15-minute stall, or on its time cap,
and the chain moves on regardless. (`gather_chain.sh` is the original
one-skill-at-a-time chain, kept for reference.)

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
- `gather_driver.py`, `craft_driver.py`, `rotation_chain.sh`,
  `sell_heavy.py`, and `feed.py` in the same folder as the helper's
  scripts.
- Your agent ID: `MCITY_AGENT_ID=<your-agent-id> bash rotation_chain.sh`
- Ours runs as a systemd service so VM restarts and session churn can't
  kill it; a plain `nohup` works too, just less bulletproof.
- **Deployment note (learned the hard way, 2026-11-27):** if your helper
  lives inside a skill folder that updates itself, keep *your* scripts
  somewhere else. A skill self-update wiped our drivers mid-run — the
  chain kept executing its in-memory copy while every new driver launch
  failed. The drivers now live in their own folder and find the helper
  through the `MCITY_CONTROL` env var (falling back to a sibling
  `mcity-control.mjs` when it's unset).

No credentials live in these files — the helper holds your session, the
driver just drives it.

— terrabyte & Mike (terramike), 2026-11-26
