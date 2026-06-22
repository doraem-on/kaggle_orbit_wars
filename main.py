"""
Orbit Wars Agent v2 — Pure Heuristic with Mission-Based Planning
================================================================
Single-file, zero external dependencies.
Designed for Kaggle Orbit Wars competition.

Strategy:
  - Aggressive opening: rush neutrals with minimal reserves
  - Mission-based mid/late game: score CAPTURE / DEFEND / SNIPE missions by ROI
  - FFA awareness: focus-fire the weakest opponent to snowball
  - Phase-adaptive reserves: aggressive early, defensive mid, all-in endgame
  - Greedy assignment: fast O(n log n) vs exponential beam search
  - Coordinated attacks: multiple planets can contribute to the same target
"""
import math
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════
BOARD_SIZE = 100.0
CENTER = (50.0, 50.0)
SUN_RADIUS = 10.0
SUN_BUFFER = SUN_RADIUS + 1.0          # Safety margin for launch checks
ROTATION_RADIUS_LIMIT = 50.0           # orbital_radius + planet_radius < 50 → orbits
MAX_TURNS = 500
MAX_FLEET_SPEED = 6.0
DEFAULT_SPEED = 3.0                    # Conservative first-pass speed estimate

# Phase boundaries
PHASE_OPENING  = 0   # step < 25   — rush neutrals
PHASE_EARLY    = 1   # step < 100  — expand + consolidate
PHASE_MID      = 2   # step < 350  — balanced
PHASE_LATE     = 3   # step < 450  — aggressive
PHASE_ENDGAME  = 4   # step >= 450 — all-in

# Min fraction of needed ships to launch an attack (per phase)
MIN_ATTACK_FRAC = [0.85, 0.7, 0.6, 0.4, 0.2]


# ═══════════════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════════════
def _g(obj, key, default=None):
    """Universal getter — handles Kaggle namespace objects AND plain dicts."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    val = getattr(obj, key, None)
    if val is not None:
        return val
    if hasattr(obj, "get"):
        return obj.get(key, default)
    return default


def fleet_speed(n):
    """Fleet speed given ship count. More ships → faster (up to 6.0)."""
    if n <= 1:
        return 1.0
    r = math.log(n) / math.log(1000.0)
    return 1.0 + (MAX_FLEET_SPEED - 1.0) * max(0.0, r) ** 1.5


# ═══════════════════════════════════════════════════════════════════
#  GEOMETRY
# ═══════════════════════════════════════════════════════════════════
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def ang(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def seg_circle(a, b, c, r):
    """Does line segment a→b intersect circle at c with radius r?"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    fx, fy = a[0] - c[0], a[1] - c[1]
    A = dx * dx + dy * dy
    B = fx * dx + fy * dy
    C = fx * fx + fy * fy - r * r
    if A < 1e-12:
        return C <= 0
    t = max(0.0, min(1.0, -B / A))
    return A * t * t + 2.0 * B * t + C <= 0


def pred_pos(x, y, turns, av):
    """Predict orbiting planet position after `turns` steps."""
    if av == 0:
        return (x, y)
    dx, dy = x - CENTER[0], y - CENTER[1]
    a = math.atan2(dy, dx)
    r = math.hypot(dx, dy)
    na = a + av * turns
    return (CENTER[0] + r * math.cos(na), CENTER[1] + r * math.sin(na))


def intercept_orbit(src, spd, tx, ty, av, tr):
    """Launch angle and ETA for an orbiting target. Iterative convergence."""
    if av == 0:
        d = math.hypot(tx - src[0], ty - src[1])
        turns = int(math.ceil(max(0, d - tr) / spd)) if spd > 0 else 9999
        return math.atan2(ty - src[1], tx - src[0]), turns

    dx, dy = tx - CENTER[0], ty - CENTER[1]
    ca = math.atan2(dy, dx)
    orb = math.hypot(dx, dy)
    t = math.hypot(tx - src[0], ty - src[1]) / spd

    for _ in range(15):
        na = ca + av * t
        nx = CENTER[0] + orb * math.cos(na)
        ny = CENTER[1] + orb * math.sin(na)
        tn = max(0, math.hypot(nx - src[0], ny - src[1]) - tr) / spd
        if abs(t - tn) < 0.1:
            t = tn
            break
        t = tn

    turns = max(1, int(math.ceil(t)))
    fa = ca + av * turns
    fx = CENTER[0] + orb * math.cos(fa)
    fy = CENTER[1] + orb * math.sin(fa)
    return math.atan2(fy - src[1], fx - src[0]), turns


def intercept_path(src, spd, path, ci, tr):
    """Launch angle and ETA for a comet traveling along a fixed path."""
    remaining = len(path) - ci
    for t in range(remaining):
        p = path[ci + t]
        px, py = (p[0], p[1]) if isinstance(p, (list, tuple)) else (p[0], p[1])
        if max(0, math.hypot(px - src[0], py - src[1]) - tr) <= t * spd:
            return math.atan2(py - src[1], px - src[0]), max(1, t)
    return 0.0, 9999


# ═══════════════════════════════════════════════════════════════════
#  DATA MODEL
# ═══════════════════════════════════════════════════════════════════
class Planet:
    __slots__ = ("id", "owner", "x", "y", "radius", "ships", "production",
                 "is_comet", "av", "comet_path", "comet_pi")

    def __init__(self, pid, owner, x, y, radius, ships, prod, comet, av):
        self.id = pid
        self.owner = owner
        self.x = x
        self.y = y
        self.radius = radius
        self.ships = ships
        self.production = prod
        self.is_comet = comet
        self.av = av
        self.comet_path = None
        self.comet_pi = 0

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def orbiting(self):
        return (not self.is_comet
                and dist(self.pos, CENTER) + self.radius < ROTATION_RADIUS_LIMIT)

    def future(self, t):
        if self.is_comet and self.comet_path:
            i = min(self.comet_pi + t, len(self.comet_path) - 1)
            p = self.comet_path[i]
            return (p[0], p[1])
        if self.orbiting:
            return pred_pos(self.x, self.y, t, self.av)
        return self.pos


class Fleet:
    __slots__ = ("id", "owner", "x", "y", "angle", "ships")

    def __init__(self, fid, owner, x, y, angle, ships):
        self.id = fid
        self.owner = owner
        self.x = x
        self.y = y
        self.angle = angle
        self.ships = ships

    @property
    def pos(self):
        return (self.x, self.y)


class State:
    """Parsed game state from the raw Kaggle observation."""

    def __init__(self, obs, cfg):
        self.step = _g(obs, "step", 0)
        self.pid = _g(obs, "player", 0)
        self.av = _g(obs, "angular_velocity", 0.0)
        self.planets = {}
        self.fleets = []
        self._parse(obs)

    def _parse(self, obs):
        comet_set = set(_g(obs, "comet_planet_ids", []) or [])

        # Build comet path lookup
        cpaths = {}
        for cg in (_g(obs, "comets", []) or []):
            if not isinstance(cg, dict):
                continue
            paths = cg.get("paths", [])
            pi = cg.get("path_index", 0)
            pids = cg.get("planet_ids", [])
            for i, cpid in enumerate(pids):
                if i < len(paths):
                    cpaths[cpid] = (paths[i], pi)

        # Parse planets
        for pd in (_g(obs, "planets", []) or []):
            pid, ow, x, y, r, sh, pr = pd
            p = Planet(pid, ow, x, y, r, sh, pr, pid in comet_set, self.av)
            if p.is_comet and pid in cpaths:
                p.comet_path, p.comet_pi = cpaths[pid]
            self.planets[pid] = p

        # Parse fleets
        for fd in (_g(obs, "fleets", []) or []):
            fid, ow, x, y, a, _fpid, sh = fd
            self.fleets.append(Fleet(fid, ow, x, y, a, sh))

    # Convenience accessors
    def mine(self):
        return [p for p in self.planets.values() if p.owner == self.pid]

    def enemies(self):
        return [p for p in self.planets.values() if p.owner not in (self.pid, -1)]

    def neutrals(self):
        return [p for p in self.planets.values() if p.owner == -1]

    def targets(self):
        return [p for p in self.planets.values() if p.owner != self.pid]


# ═══════════════════════════════════════════════════════════════════
#  FLEET INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════
class Intel:
    """Trace every fleet to its destination, build threat/support maps."""

    def __init__(self, state):
        self.st = state
        self.enemy_to = defaultdict(int)    # planet_id → total enemy ships inbound
        self.allied_to = defaultdict(int)    # planet_id → total allied ships inbound
        self.by_owner = defaultdict(lambda: defaultdict(int))

        for f in state.fleets:
            tid = self._trace(f)
            if tid is None:
                continue
            self.by_owner[f.owner][tid] += f.ships
            if f.owner == state.pid:
                self.allied_to[tid] += f.ships
            else:
                self.enemy_to[tid] += f.ships

    def _trace(self, f):
        """Find which planet a fleet's trajectory will hit first."""
        ex = f.x + math.cos(f.angle) * 200
        ey = f.y + math.sin(f.angle) * 200
        best_id, best_d = None, 1e9

        for p in self.st.planets.values():
            if seg_circle(f.pos, (ex, ey), p.pos, p.radius):
                d = dist(f.pos, p.pos)
                if d < best_d:
                    best_d, best_id = d, p.id

        # If sun is closer than any planet hit, fleet is destroyed
        if best_id is not None and seg_circle(f.pos, (ex, ey), CENTER, SUN_RADIUS):
            sun_d = dist(f.pos, CENTER) - SUN_RADIUS
            if sun_d < best_d:
                return None

        return best_id


# ═══════════════════════════════════════════════════════════════════
#  STRATEGIC PLANNER
# ═══════════════════════════════════════════════════════════════════
class Planner:
    """
    Mission-based planner with greedy assignment.

    Missions are scored and sorted. Ships are allocated greedily
    from highest-score to lowest, ensuring no planet over-commits.
    """

    def __init__(self, state, intel):
        self.st = state
        self.intel = intel
        self.turns_left = max(1, MAX_TURNS - state.step)

        # ── Phase ──
        s = state.step
        if   s < 25:  self.phase = PHASE_OPENING
        elif s < 100: self.phase = PHASE_EARLY
        elif s < 350: self.phase = PHASE_MID
        elif s < 450: self.phase = PHASE_LATE
        else:         self.phase = PHASE_ENDGAME

        # ── Opponent profiling ──
        self.opp = defaultdict(lambda: [0, 0, 0])  # [ships, production, planets]
        for p in state.planets.values():
            if p.owner not in (-1, state.pid):
                self.opp[p.owner][0] += p.ships
                self.opp[p.owner][1] += p.production
                self.opp[p.owner][2] += 1
        for f in state.fleets:
            if f.owner not in (-1, state.pid):
                self.opp[f.owner][0] += f.ships

        self.ffa = len(self.opp) > 1
        self.weakest = (min(self.opp,
                            key=lambda o: self.opp[o][0] + self.opp[o][1] * 20)
                        if self.opp else None)

    # ── Reserves ──
    def _reserve(self, planet):
        """Minimum ships to hold back for defense on this planet."""
        threat = self.intel.enemy_to.get(planet.id, 0)
        if self.phase == PHASE_ENDGAME:
            return 0
        if self.phase == PHASE_OPENING:
            return max(1, int(threat * 0.5))
        if self.phase == PHASE_LATE:
            return max(1, int(threat * 0.6))
        return max(3, int(threat * 0.7))

    # ── Intercept helper ──
    def _intercept(self, src_pos, tgt, spd):
        """Unified intercept: returns (launch_angle, travel_turns)."""
        if tgt.is_comet and tgt.comet_path:
            return intercept_path(src_pos, spd, tgt.comet_path, tgt.comet_pi, tgt.radius)
        if tgt.orbiting:
            return intercept_orbit(src_pos, spd, tgt.x, tgt.y, tgt.av, tgt.radius)
        d = dist(src_pos, tgt.pos)
        dt = max(0, d - tgt.radius)
        turns = int(math.ceil(dt / spd)) if spd > 0 else 9999
        return ang(src_pos, tgt.pos), turns

    # ── Sun check ──
    def _sun_blocked(self, src, angle):
        lx = src.x + math.cos(angle) * (src.radius + 0.2)
        ly = src.y + math.sin(angle) * (src.radius + 0.2)
        fx = lx + math.cos(angle) * 200
        fy = ly + math.sin(angle) * 200
        return seg_circle((lx, ly), (fx, fy), CENTER, SUN_BUFFER)

    # ── Main planning routine ──
    def plan(self):
        my = self.st.mine()
        if not my:
            return []

        missions = []

        # ═════════════════════════════════════════════════════════
        #  1. DEFENSE MISSIONS — protect threatened planets
        # ═════════════════════════════════════════════════════════
        for p in my:
            threat = self.intel.enemy_to.get(p.id, 0)
            if threat <= 0:
                continue

            # Can the planet handle it alone (with ~15 turns of production)?
            self_defense = p.ships + p.production * 15
            allied_incoming = self.intel.allied_to.get(p.id, 0)
            gap = threat - self_defense - allied_incoming
            if gap <= 0:
                continue

            # Need reinforcements from other planets
            for src in my:
                if src.id == p.id:
                    continue
                a, t = self._intercept(src.pos, p, DEFAULT_SPEED)
                if t > 80 or self._sun_blocked(src, a):
                    continue

                missions.append({
                    "type": "D",
                    "src": src.id,
                    "tgt": p.id,
                    "angle": a,
                    "need": max(1, gap + 3),
                    "score": 3000 + p.production * 25 - t,
                })

        # ═════════════════════════════════════════════════════════
        #  2. CAPTURE MISSIONS — take neutrals and enemy planets
        # ═════════════════════════════════════════════════════════
        all_targets = self.st.targets()

        for src in my:
            for tgt in all_targets:
                if tgt.id == src.id:
                    continue

                # Skip worthless neutrals (no production)
                if tgt.production == 0 and tgt.owner == -1:
                    continue

                # ── Pass 1: rough estimate ──
                a1, t1 = self._intercept(src.pos, tgt, DEFAULT_SPEED)
                if t1 > 200 or t1 < 0:
                    continue
                if self._sun_blocked(src, a1):
                    continue

                # Comet lifetime check
                if tgt.is_comet and tgt.comet_path:
                    life = len(tgt.comet_path) - tgt.comet_pi
                    if life < t1 + 5:
                        continue  # Comet expires before or right after arrival

                # ── Garrison estimate at arrival ──
                neutral = (tgt.owner == -1)
                garrison = tgt.ships
                if not neutral:
                    garrison += tgt.production * t1
                    # Same-owner reinforcements heading there
                    garrison += self.intel.by_owner.get(tgt.owner, {}).get(tgt.id, 0)

                # Subtract our fleets already committed
                garrison -= self.intel.allied_to.get(tgt.id, 0)
                garrison = max(0, garrison)

                buf = 3 + (tgt.production * 2 if not neutral else 0)
                need = garrison + buf

                # ── Pass 2: refine with actual speed ──
                spd = fleet_speed(max(1, need))
                a2, t2 = self._intercept(src.pos, tgt, spd)
                if t2 > 200 or self._sun_blocked(src, a2):
                    continue

                # Recalculate garrison with refined travel time
                if not neutral:
                    garrison = tgt.ships + tgt.production * t2
                    garrison += self.intel.by_owner.get(tgt.owner, {}).get(tgt.id, 0)
                    garrison -= self.intel.allied_to.get(tgt.id, 0)
                    garrison = max(0, garrison)
                    need = garrison + buf

                need = max(1, int(need))

                # ── Score ──
                if tgt.is_comet and tgt.comet_path:
                    effective_life = max(1, min(
                        len(tgt.comet_path) - tgt.comet_pi - t2,
                        self.turns_left - t2))
                else:
                    effective_life = max(1, min(self.turns_left - t2, 150))

                roi = tgt.production * effective_life / max(need, 1)
                score = roi

                # Neutral bonus (cheap, no retaliation)
                if neutral:
                    score *= 1.8

                # FFA: bonus for targeting weakest opponent
                if self.ffa and tgt.owner == self.weakest:
                    score *= 1.4

                # Snipe bonus: very low garrison → likely just captured
                if tgt.ships <= 5 and tgt.production >= 2:
                    score += 300

                # Opening bonus: grab neutrals FAST
                if self.phase == PHASE_OPENING and neutral:
                    score += 150

                # Late-game aggression multiplier
                if self.phase >= PHASE_LATE:
                    score *= 1.3

                # Distance penalty
                score -= t2 * 0.3

                missions.append({
                    "type": "C",
                    "src": src.id,
                    "tgt": tgt.id,
                    "angle": a2,
                    "need": need,
                    "score": score,
                })

        # ═════════════════════════════════════════════════════════
        #  3. GREEDY ASSIGNMENT
        # ═════════════════════════════════════════════════════════
        missions.sort(key=lambda m: m["score"], reverse=True)

        avail = {p.id: p.ships for p in my}
        committed = defaultdict(int)   # tgt_id → ships already assigned
        moves = []

        for m in missions:
            sid, tid = m["src"], m["tgt"]

            # How many more ships does this target still need?
            remaining = max(0, m["need"] - committed[tid])
            if remaining <= 0:
                continue

            res = self._reserve(self.st.planets[sid])
            can = avail[sid] - res
            if can <= 0:
                continue

            send = min(remaining, can)
            if send <= 0:
                continue

            # Don't send futile partial attacks
            if m["type"] == "C" and committed[tid] == 0:
                min_frac = MIN_ATTACK_FRAC[self.phase]
                if send < m["need"] * min_frac and m["need"] > 5:
                    continue

            moves.append((sid, m["angle"], int(send)))
            avail[sid] -= send
            committed[tid] += send

        # ═════════════════════════════════════════════════════════
        #  4. LATE-GAME FALLBACK — never sit idle
        # ═════════════════════════════════════════════════════════
        if not moves and self.phase >= PHASE_LATE:
            enemy_planets = self.st.enemies()
            for src in my:
                if avail.get(src.id, 0) <= 1:
                    continue
                # Attack nearest enemy
                best_tgt, best_d = None, 1e9
                for ep in enemy_planets:
                    d = dist(src.pos, ep.pos)
                    if d < best_d:
                        best_d, best_tgt = d, ep
                if best_tgt is None:
                    # No enemy planets — try neutrals
                    for np_ in self.st.neutrals():
                        d = dist(src.pos, np_.pos)
                        if d < best_d:
                            best_d, best_tgt = d, np_
                if best_tgt is not None:
                    spd = fleet_speed(max(1, avail[src.id]))
                    a, t = self._intercept(src.pos, best_tgt, spd)
                    if not self._sun_blocked(src, a):
                        send = max(1, avail[src.id] - 1)
                        moves.append((src.id, a, send))
                        avail[src.id] -= send

        return moves


# ═══════════════════════════════════════════════════════════════════
#  AGENT ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def agent(observation, configuration=None):
    """
    Kaggle entry point.  Returns list of [planet_id, angle, ships].
    Wrapped in try/except so no crash ever causes a forfeit.
    """
    try:
        st = State(observation, configuration)
        intel = Intel(st)
        planner = Planner(st, intel)
        raw = planner.plan()

        # ── Safety filter ──
        actions = []
        used = defaultdict(int)

        for pid, angle, ships in raw:
            if pid not in st.planets:
                continue
            p = st.planets[pid]
            if p.owner != st.pid:
                continue

            left = p.ships - used[pid]
            ships = min(ships, max(0, left - 1))   # Always keep ≥1 ship
            if ships <= 0:
                continue

            # Final sun-collision check on the actual launch trajectory
            lx = p.x + math.cos(angle) * (p.radius + 0.1)
            ly = p.y + math.sin(angle) * (p.radius + 0.1)
            fx = lx + math.cos(angle) * 200
            fy = ly + math.sin(angle) * 200
            if seg_circle((lx, ly), (fx, fy), CENTER, SUN_BUFFER):
                continue

            actions.append([pid, angle, int(ships)])
            used[pid] += ships

        return actions

    except Exception:
        # NEVER crash — return empty actions instead of forfeiting
        return []
