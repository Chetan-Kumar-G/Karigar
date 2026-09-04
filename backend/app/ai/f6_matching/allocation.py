"""F6 — AI B2B Matching + Cluster Order Pooling.

**Mode: REAL.**  Two mechanisms run live, both from spec §8:

1. **Allocation** — a MILP solved with Google OR-Tools CP-SAT (spec §8.I)::

       minimize  Σ (unit_cost_i + logistics_i)·x_i  −  λ·Σ (quality_i + reliability_i)·x_i
       s.t.  Σ x_i ≥ D·fulfillment_min
             x_i ≤ capacity_i·y_i         ∀i
             x_i ≥ min_lot·y_i            ∀i (only if selected)
             Σ y_i ≤ max_artisans_per_order

   If total eligible capacity < demand, the model switches objective to
   *maximise fill* and reports the shortfall honestly (spec §8 failure case).

2. **Fair payment split** — the exact **Shapley value** over the coalition of
   selected artisans (spec §8.I.5).  The characteristic function ``v(S)`` is the
   coalition's achievable surplus (fill cheapest-surplus-first up to demand and
   capacity) — computed exactly for every one of the ``2^|N|`` sub-coalitions,
   which is tractable at the |N| ≤ ~8 sizes a pooled order actually reaches.
   Shares are normalised to the buyer's total payment.  A proportional-by-units
   split is returned alongside so the divergence is visible (spec §8, §15).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from math import factorial

from app.ai.base import REAL, AiResult, timed
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("f6.allocation")

# Above this coalition size the exact 2^N Shapley is replaced by Monte-Carlo
# permutation sampling (spec §8 — scalable path for large N).
SHAPLEY_EXACT_MAX = 8
SHAPLEY_SAMPLES = 4000


@dataclass
class EligibleArtisan:
    artisan_id: str
    name: str
    capacity_units: int
    unit_cost_inr: float
    quality_score: float
    reliability_score: float
    logistics_cost_inr_per_unit: float
    craft_match: bool = True
    # trust & verification (spec add-on) — advisory unless SUSPENDED/REJECTED
    verified: bool = True
    verification_status: str = "VERIFIED"
    reliability_pct: float = 80.0


@dataclass
class BuyerOrder:
    quantity: int
    unit_price_min: float
    unit_price_max: float
    required_craft_id: str | None = None
    required_material: str | None = None
    fulfillment_min: float = 1.0
    lambda_weight: float | None = None


# ── eligibility (craft-compatibility + price band + capacity) ─────────────
def _filter_eligible(order: BuyerOrder, pool: list[EligibleArtisan]):
    kept, rejected = [], []
    for a in pool:
        reason = None
        if a.verification_status in ("SUSPENDED", "REJECTED"):
            # trust gate: a suspended / rejected account loses B2B privileges
            reason = "verification_" + a.verification_status.lower()
        elif not a.craft_match:
            reason = "craft_mismatch"
        elif a.capacity_units <= 0:
            reason = "no_capacity"
        elif a.unit_cost_inr > order.unit_price_max:
            reason = "above_price_ceiling"
        (rejected if reason else kept).append(
            {"artisan_id": a.artisan_id, "reason": reason} if reason else a
        )
    return kept, rejected


# ── characteristic function for Shapley: coalition surplus ───────────────
def _coalition_value(members: tuple[EligibleArtisan, ...], demand: int, buyer_unit_price: float) -> float:
    """Max surplus S can produce: fill highest-surplus artisans first up to
    demand and their capacity.  Exact for this relaxed sub-problem (linear
    objective, only capacity + total-demand constraints)."""
    if not members:
        return 0.0
    ranked = sorted(
        members,
        key=lambda a: (buyer_unit_price - a.unit_cost_inr - a.logistics_cost_inr_per_unit),
        reverse=True,
    )
    remaining = demand
    surplus = 0.0
    for a in ranked:
        if remaining <= 0:
            break
        take = min(a.capacity_units, remaining)
        per_unit = buyer_unit_price - a.unit_cost_inr - a.logistics_cost_inr_per_unit
        if per_unit <= 0:
            continue
        surplus += take * per_unit
        remaining -= take
    return surplus


def _shapley_exact(members: list[EligibleArtisan], demand: int, buyer_unit_price: float) -> dict[str, float]:
    n = len(members)
    idx = list(range(n))
    vcache: dict[frozenset, float] = {}
    for r in range(n + 1):
        for combo in combinations(idx, r):
            key = frozenset(combo)
            vcache[key] = _coalition_value(tuple(members[i] for i in combo), demand, buyer_unit_price)

    phi = {members[i].artisan_id: 0.0 for i in idx}
    for i in idx:
        others = [j for j in idx if j != i]
        for r in range(len(others) + 1):
            w = factorial(r) * factorial(n - r - 1) / factorial(n)
            for combo in combinations(others, r):
                s = frozenset(combo)
                phi[members[i].artisan_id] += w * (vcache[s | {i}] - vcache[s])
    return phi


def _shapley_montecarlo(members: list[EligibleArtisan], demand: int, buyer_unit_price: float,
                        samples: int = SHAPLEY_SAMPLES) -> dict[str, float]:
    """Unbiased Shapley estimate via random marginal contributions over
    permutations. Scales linearly in ``samples`` regardless of |N|."""
    n = len(members)
    rng = random.Random(42)  # fixed seed → reproducible for a live demo
    phi = {a.artisan_id: 0.0 for a in members}
    order = list(range(n))
    for _ in range(samples):
        rng.shuffle(order)
        coalition: list[EligibleArtisan] = []
        prev = 0.0
        for j in order:
            coalition.append(members[j])
            cur = _coalition_value(tuple(coalition), demand, buyer_unit_price)
            phi[members[j].artisan_id] += cur - prev
            prev = cur
    return {k: v / samples for k, v in phi.items()}


def _shapley(members: list[EligibleArtisan], demand: int, buyer_unit_price: float) -> tuple[dict[str, float], str]:
    n = len(members)
    if n == 0:
        return {}, "none"
    if n == 1:
        return ({members[0].artisan_id: _coalition_value(tuple(members), demand, buyer_unit_price)},
                "exact")
    if n <= SHAPLEY_EXACT_MAX:
        return _shapley_exact(members, demand, buyer_unit_price), "exact"
    return _shapley_montecarlo(members, demand, buyer_unit_price), f"montecarlo_{SHAPLEY_SAMPLES}"


# ── MILP allocation via OR-Tools CP-SAT ─────────────────────────────────
def _solve_cpsat(order: BuyerOrder, elig: list[EligibleArtisan], lam: float):
    from ortools.sat.python import cp_model

    total_cap = sum(a.capacity_units for a in elig)
    target = int(round(order.quantity * order.fulfillment_min))
    feasible_full = total_cap >= target

    model = cp_model.CpModel()
    x = [model.new_int_var(0, a.capacity_units, f"x{i}") for i, a in enumerate(elig)]
    y = [model.new_bool_var(f"y{i}") for i in range(len(elig))]
    min_lot = min(settings.f6_min_lot_size, max(1, order.quantity // max(len(elig), 1)))

    for i, a in enumerate(elig):
        # per-artisan floor — never larger than the artisan's own capacity, so a
        # small-capacity artisan is not silently forced out by the lot rule.
        lot_i = min(min_lot, a.capacity_units)
        model.add(x[i] <= a.capacity_units * y[i])
        model.add(x[i] >= lot_i * y[i])
        model.add(x[i] >= 1).only_enforce_if(y[i])
        model.add(x[i] == 0).only_enforce_if(y[i].Not())
    model.add(sum(y) <= settings.f6_max_artisans_per_order)
    model.add(sum(x) <= order.quantity)

    # objective coefficients, integer-scaled
    cost_c = [int(round((a.unit_cost_inr + a.logistics_cost_inr_per_unit) * 100)) for a in elig]
    merit_c = [int(round(lam * (a.quality_score + a.reliability_score) * 100)) for a in elig]
    obj = sum(cost_c[i] * x[i] - merit_c[i] * x[i] for i in range(len(elig)))

    if feasible_full:
        model.add(sum(x) >= target)
        model.minimize(obj)
    else:
        # can't meet demand — maximise fill first (lexicographic via big weight)
        big = max(cost_c) + max(merit_c) + 1
        model.maximize(sum(x) * big * 1000 - obj)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    # Reproducible output for a live demo: single worker + fixed seed on the
    # small instances a pooled order actually reaches; parallel only if large.
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 1 if len(elig) <= 16 else 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    alloc = []
    for i, a in enumerate(elig):
        units = int(solver.value(x[i]))
        units = max(0, min(units, a.capacity_units))  # capacity guard (defense in depth)
        if units > 0:
            alloc.append((a, units))
    return {
        "alloc": alloc,
        "solve_time_ms": solver.wall_time * 1000.0,
        "status": "fully_allocated" if feasible_full else "partially_allocated",
        "objective_value": solver.objective_value / 100.0,
        "feasible_full": feasible_full,
        "solver": "cp_sat",
        "optimality": "optimal" if status == cp_model.OPTIMAL else "feasible",
    }


def _greedy_allocation(order: BuyerOrder, elig: list[EligibleArtisan]) -> dict:
    """Deterministic fallback used only if CP-SAT is unavailable or errors, so a
    live demo never dead-ends on a 500. Respects capacity and the max-artisans
    cap; assigns best landed-cost-minus-merit first."""
    lam = order.lambda_weight if order.lambda_weight is not None else settings.f6_lambda
    ranked = sorted(
        elig,
        key=lambda a: (a.unit_cost_inr + a.logistics_cost_inr_per_unit)
        - lam * (a.quality_score + a.reliability_score),
    )[: settings.f6_max_artisans_per_order]
    remaining = order.quantity
    alloc: list[tuple[EligibleArtisan, int]] = []
    for a in ranked:
        if remaining <= 0:
            break
        take = max(0, min(a.capacity_units, remaining))
        if take > 0:
            alloc.append((a, take))
            remaining -= take
    total = sum(u for _a, u in alloc)
    feasible_full = total >= int(round(order.quantity * order.fulfillment_min))
    return {
        "alloc": alloc,
        "solve_time_ms": 0.0,
        "status": "fully_allocated" if feasible_full else "partially_allocated",
        "objective_value": sum(
            (a.unit_cost_inr + a.logistics_cost_inr_per_unit) * u for a, u in alloc
        ),
        "feasible_full": feasible_full,
        "solver": "greedy_fallback",
        "optimality": "heuristic",
    }


def allocate(order: BuyerOrder, pool: list[EligibleArtisan]) -> AiResult:
    lam = order.lambda_weight if order.lambda_weight is not None else settings.f6_lambda
    with timed() as t:
        kept, rejected = _filter_eligible(order, pool)
        elig: list[EligibleArtisan] = [a for a in kept if isinstance(a, EligibleArtisan)]

        if not elig:
            return AiResult(
                data={"status": "no_eligible_artisans", "allocations": [], "rejected": rejected,
                      "total_allocated": 0, "fulfillment_pct": 0.0},
                feature="F6", model="OR-Tools CP-SAT + Shapley value", mode=REAL,
                inputs={"quantity": order.quantity, "pool": len(pool)}, latency_ms=t["ms"],
            )

        try:
            result = _solve_cpsat(order, elig, lam)
        except Exception as exc:  # OR-Tools missing / solver crash — keep the demo alive
            log.warning("CP-SAT unavailable (%s) — using deterministic greedy fallback", exc)
            result = None
        used_fallback = False
        if result is None:
            result = _greedy_allocation(order, elig)
            used_fallback = True
            if not result["alloc"]:
                return AiResult(
                    data={"status": "infeasible", "allocations": [], "rejected": rejected,
                          "total_allocated": 0, "fulfillment_pct": 0.0,
                          "solver": "greedy_fallback"},
                    feature="F6", model="OR-Tools CP-SAT + Shapley value", mode=REAL,
                    inputs={"quantity": order.quantity, "pool": len(pool)}, latency_ms=t["ms"],
                )

        alloc = result["alloc"]
        members = [a for a, _u in alloc]
        units_by_id = {a.artisan_id: u for a, u in alloc}
        total_allocated = sum(units_by_id.values())

        avg_cost = sum((a.unit_cost_inr + a.logistics_cost_inr_per_unit) * u
                       for a, u in alloc) / max(total_allocated, 1)
        max_landed = max((a.unit_cost_inr + a.logistics_cost_inr_per_unit) for a, _u in alloc)
        # The buyer's blended B2B unit price. It must (a) sit in the buyer's band,
        # (b) clear the *most expensive allocated* maker's landed cost with a small
        # margin — otherwise the optimiser would assign an artisan the payment
        # model then values at zero surplus, which is neither fair nor defensible.
        buyer_unit_price = max(order.unit_price_min, avg_cost * 1.18, max_landed * 1.08)
        buyer_unit_price = float(min(order.unit_price_max, buyer_unit_price))
        total_buyer_payment = buyer_unit_price * total_allocated
        total_cost = sum(a.unit_cost_inr * u for a, u in alloc) + \
            sum(a.logistics_cost_inr_per_unit * u for a, u in alloc)

        # Shapley split, normalised to the buyer's total payment
        phi, shapley_method = _shapley(members, total_allocated, buyer_unit_price)
        phi_sum = sum(v for v in phi.values() if v > 0) or 1.0
        shapley_share = {k: max(v, 0) / phi_sum * total_buyer_payment for k, v in phi.items()}
        prop_share = {a.artisan_id: units_by_id[a.artisan_id] / total_allocated * total_buyer_payment
                      for a in members}

        landed = {a.artisan_id: a.unit_cost_inr + a.logistics_cost_inr_per_unit for a in members}
        cheapest_landed = min(landed.values()) if landed else 0.0
        allocations = []
        for a in sorted(members, key=lambda m: units_by_id[m.artisan_id], reverse=True):
            units = units_by_id[a.artisan_id]
            pay = round(shapley_share[a.artisan_id])
            prop = round(prop_share[a.artisan_id])
            cap_frac = units / max(a.capacity_units, 1)
            allocations.append({
                "artisan_id": a.artisan_id,
                "artisan_name": a.name,
                "allocated_units": units,
                "unit_cost_inr": round(a.unit_cost_inr, 2),
                "unit_price_inr": round(buyer_unit_price, 2),
                "payment_share_inr": pay,
                "proportional_share_inr": prop,
                "shapley_marginal_inr": round(phi[a.artisan_id]),
                "quality_score": a.quality_score,
                "reliability_score": a.reliability_score,
                "reliability_pct": a.reliability_pct,
                "verified": a.verified,
                "verification_status": a.verification_status,
                "capacity_units": a.capacity_units,
                "capacity_used_pct": round(100 * cap_frac, 1),
                "match_reasons": _match_reasons(order, a),
                "allocation_rationale": (
                    f"Landed cost ₹{landed[a.artisan_id]:.0f}/unit"
                    + ("" if landed[a.artisan_id] <= cheapest_landed + 1e-6
                       else f" (₹{landed[a.artisan_id] - cheapest_landed:.0f} above the cheapest)")
                    + f", quality {a.quality_score:.2f}, reliability {a.reliability_score:.2f}"
                    + f" → assigned {units} units ({round(100 * cap_frac)}% of capacity)."
                ),
                "payment_rationale": (
                    f"Shapley share ₹{pay:,} vs a units-only split of ₹{prop:,} "
                    + (
                        "— matches the units split (contribution is proportional)."
                        if abs(pay - prop) <= max(2, 0.01 * max(prop, 1))
                        else f"— {'+' if pay > prop else ''}{round(100 * (pay - prop) / max(prop, 1))}% "
                             f"because this artisan's "
                             f"{'low cost / high reliability made their capacity pivotal' if pay > prop else 'higher cost reduced their marginal surplus'}."
                    )
                ),
            })

        fulfillment_pct = round(100 * total_allocated / order.quantity, 1)
        cap_util = round(100 * total_allocated / sum(a.capacity_units for a in members), 1)

        # ── invariants worth asserting for a live demo ───────────────────
        over_capacity = [a.artisan_id for a, u in alloc if u > a.capacity_units]
        share_sum = round(sum(v["payment_share_inr"] for v in allocations))
        fairness_check = {
            "no_artisan_over_capacity": not over_capacity,
            "over_capacity_ids": over_capacity,
            "payment_shares_sum_to_total": abs(share_sum - round(total_buyer_payment)) <= len(members) + 1,
            "payment_share_sum_inr": share_sum,
            "all_shares_non_negative": all(v["payment_share_inr"] >= 0 for v in allocations),
            "shapley_method": shapley_method,
        }

        # greedy baseline for the "why MILP" comparison (spec §8 evaluation)
        greedy = _greedy_baseline(order, elig)

        # eligibility funnel (spec add-on: filter before the optimiser)
        eligibility_trace = {
            "pool": len(pool),
            "craft_compatible": sum(1 for a in pool if a.craft_match),
            "capacity_available": sum(1 for a in pool if a.capacity_units > 0),
            "verification_ok": sum(
                1 for a in pool if a.verification_status not in ("SUSPENDED", "REJECTED")
            ),
            "within_price_band": sum(1 for a in pool if a.unit_cost_inr <= order.unit_price_max),
            "eligible": len(elig),
            "excluded": rejected,
            "note": "Verification status and reliability filter the pool before the "
                    "CP-SAT optimiser runs. Reliability also feeds the objective's merit term.",
        }

        data = {
            "status": result["status"] if total_allocated >= order.quantity else "partially_allocated",
            "allocations": allocations,
            "rejected": rejected,
            "total_allocated": total_allocated,
            "total_requested": order.quantity,
            "fulfillment_pct": fulfillment_pct,
            "capacity_utilization_pct": cap_util,
            "shortfall_units": max(0, order.quantity - total_allocated),
            "total_cost_inr": round(total_cost),
            "total_buyer_payment_inr": round(total_buyer_payment),
            "buyer_unit_price_inr": round(buyer_unit_price, 2),
            "objective_value": round(result["objective_value"], 2),
            "solve_time_ms": round(result["solve_time_ms"], 1),
            "solver": result.get("solver", "cp_sat"),
            "solver_optimality": result.get("optimality", "optimal"),
            "used_fallback": used_fallback,
            "lambda": lam,
            "revenue_allocation_method": "shapley_value",
            "shapley_method": shapley_method,
            "shapley_note": (
                f"Exact Shapley over 2^N sub-coalitions (N={len(members)} ≤ {SHAPLEY_EXACT_MAX})."
                if shapley_method == "exact" else
                f"Monte-Carlo Shapley — {SHAPLEY_SAMPLES} random permutations (N={len(members)} > "
                f"{SHAPLEY_EXACT_MAX}; exact 2^N is intractable)."
            ),
            "fairness_check": fairness_check,
            "baseline_greedy": greedy,
            "eligibility_trace": eligibility_trace,
        }

    return AiResult(
        data=data,
        feature="F6",
        model="OR-Tools CP-SAT MILP (allocation) + exact Shapley value (payment split)",
        mode=REAL,
        inputs={"quantity": order.quantity, "eligible": len(elig), "lambda": lam,
                "fulfillment_min": order.fulfillment_min},
        latency_ms=t["ms"],
    )


def _match_reasons(order: BuyerOrder, a: EligibleArtisan) -> dict[str, bool]:
    return {
        "craft": a.craft_match,
        "material": order.required_material is None,
        "price": a.unit_cost_inr <= order.unit_price_max,
        "capacity": a.capacity_units > 0,
        "delivery": a.reliability_score >= 0.75,
        "quality": a.quality_score >= 0.75,
    }


def _greedy_baseline(order: BuyerOrder, elig: list[EligibleArtisan]) -> dict:
    ranked = sorted(elig, key=lambda a: a.unit_cost_inr + a.logistics_cost_inr_per_unit)
    remaining, cost, used = order.quantity, 0.0, 0
    for a in ranked:
        if remaining <= 0:
            break
        take = min(a.capacity_units, remaining)
        cost += take * (a.unit_cost_inr + a.logistics_cost_inr_per_unit)
        remaining -= take
        used += 1
    filled = order.quantity - remaining
    return {
        "strategy": "cheapest-artisan-first (ignores quality / reliability / balance)",
        "filled_units": filled,
        "artisans_used": used,
        "total_cost_inr": round(cost),
        "fulfillment_pct": round(100 * filled / order.quantity, 1),
    }
