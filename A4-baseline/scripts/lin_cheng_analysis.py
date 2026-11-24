#!/usr/bin/env python3
"""Analytical model of Lin & Cheng, IEEE IoT-J 10(24), 2023, eqs. (1)-(16).

Multiframe multichannel slotted-ALOHA with one-shot arrival of M UEs at slot 1,
uniform backoff [0, W_BO-1] (time-slots) and transmission bound N_PTmax.

Implementation notes (see A4-baseline/study-note.md, "Interpretation choices"):
* alpha[i, j] (eq. 12) is evaluated numerically as sum_k g[i,k] h[k,j]
  (eqs. 10-11) by pushing collided mass forward, which is the same quantity.
* The RA-frame layout is given by explicit frame offsets inside one RO
  repetition period, so pattern (iv), which starts with interval T2, is covered
  (paper Sec. II-C says "the same technique can be applied").
* First attempt: UEs are ready at slot 1 and pick uniformly among the J RA
  slots of the first RA frame (the same rule as eq. 11, Region <2>). For J = 1
  this is exactly M_1[1] = M as written in the paper.
* P_S is reported as successes / M. Eq. (13) as typeset divides by sum_i M_i
  (all transmissions); that variant is also returned as ps_per_tx.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DELTA_MS = 0.125 / 6.0  # Table I: RO time unit, 120 kHz slot / P^T = 6


@dataclass(frozen=True)
class Pattern:
    name: str
    R: int
    J: int
    T: int
    frame_offsets: tuple[int, ...]  # first slot of each RA frame, 0-based within T
    T1: int
    T2: int  # used only by eq. (1)

    @property
    def C(self) -> int:
        return len(self.frame_offsets)


# Table I with N^RA = 56.  Pattern (iv) frame layout (slots 1, 5, 63, 121, ...)
# follows Fig. 5(d).
PATTERNS = {
    "i": Pattern("i", 28, 6, 60, (0,), 60, 60),
    "ii": Pattern("ii", 112, 6, 60, (0,), 60, 60),
    "iii": Pattern("iii", 224, 1, 60, (0, 2, 4), 2, 56),
    "iv": Pattern("iv", 448, 1, 120, (0, 4, 62), 58, 4),
}


def i_max(p: Pattern, npt_max: int, w_bo: int) -> int:
    """Eq. (1). For C = 1 there is no T2 interval, so T1 is used for both."""
    t2 = p.T2 if p.C > 1 else p.T1
    return p.J + (npt_max - 1) * (w_bo + max(p.T1 - p.J, t2 - p.J) + p.J)


def ra_window(p: Pattern, k: int) -> tuple[int, int]:
    """RA slots a UE ready at slot k (1-based) chooses from uniformly.

    Region <2> of eq. (11): k inside an RA frame -> slots k..end of frame.
    Region <1>: k outside -> all J slots of the next RA frame.
    """
    pos = (k - 1) % p.T
    base = k - pos  # slot index of position 0 in this period
    for off in p.frame_offsets:
        if off <= pos < off + p.J:
            return k, base + off + p.J - 1
    for off in p.frame_offsets:
        if base + off > k:
            return base + off, base + off + p.J - 1
    start = base + p.T + p.frame_offsets[0]
    return start, start + p.J - 1


def is_ra(p: Pattern, s: int) -> bool:
    pos = (s - 1) % p.T
    return any(off <= pos < off + p.J for off in p.frame_offsets)


def analyse(p: Pattern, m: float, npt_max: int, w_bo: int) -> dict:
    horizon = i_max(p, npt_max, w_bo)
    size = horizon + 2 * (w_bo + p.T + p.J) + 2
    contend = [[0.0] * (npt_max + 1) for _ in range(size)]  # M_i[n]
    success = [[0.0] * (npt_max + 1) for _ in range(size)]  # M_{i,S}[n]

    first, last = ra_window(p, 1)
    for s in range(first, last + 1):
        contend[s][1] += m / (last - first + 1)

    total_tx = 0.0
    for i in range(1, size):
        mi = sum(contend[i])  # eq. (2)
        if mi == 0.0:
            continue
        assert is_ra(p, i), f"mass on non-RA slot {i}"
        total_tx += mi
        ps = math.exp(-mi / p.R)
        for n in range(1, npt_max + 1):
            mn = contend[i][n]
            if mn == 0.0:
                continue
            success[i][n] = mn * ps  # eq. (5)
            collided = mn * (1.0 - ps)  # eq. (6)
            if n == npt_max:
                continue
            # eqs. (7), (10)-(12): backoff k uniform in [i+1, i+W_BO]
            share = collided / w_bo
            for k in range(i + 1, i + w_bo + 1):
                a, b = ra_window(p, k)
                w = share / (b - a + 1)
                for s in range(a, b + 1):
                    contend[s][n + 1] += w

    last_used = max((i for i in range(size) if any(contend[i])), default=0)
    assert last_used <= horizon, f"activity at slot {last_used} beyond I_max={horizon}"

    succ_total = sum(sum(row) for row in success)
    by_attempt = [sum(success[i][n] for i in range(size)) for n in range(npt_max + 1)]
    by_slot = [sum(success[i]) for i in range(size)]
    delay = (
        sum(by_slot[i] * i for i in range(size)) * DELTA_MS / succ_total
        if succ_total > 0
        else float("nan")
    )
    return {
        "ps": succ_total / m,  # 3GPP TR 37.868 definition, matches Fig. 4(a)
        "ps_per_tx": succ_total / total_tx,  # eq. (13) as typeset
        "da_ms": delay,  # eq. (14)
        "i_max": horizon,
        "success_by_slot": by_slot,  # numerator of eq. (15)
        "success_by_attempt": by_attempt,  # numerator of eq. (16)
        "success_total": succ_total,
    }


def cdf_delay(result: dict, u_ms: list[float]) -> list[float]:
    """Eq. (15) evaluated at u*Delta = u_ms."""
    by_slot, tot = result["success_by_slot"], result["success_total"]
    out = []
    for t in u_ms:
        u = math.floor(t / DELTA_MS + 1e-9)
        out.append(sum(by_slot[: u + 1]) / tot)
    return out


def cdf_attempts(result: dict, npt_max: int) -> list[float]:
    """Eq. (16) for m = 1..N_PTmax."""
    by_n, tot = result["success_by_attempt"], result["success_total"]
    acc, out = 0.0, []
    for n in range(1, npt_max + 1):
        acc += by_n[n]
        out.append(acc / tot)
    return out


if __name__ == "__main__":
    for name in ("ii", "iii", "iv"):
        pat = PATTERNS[name]
        for m in (100, 500, 1000, 2000):
            r = analyse(pat, m, 5, 120)
            print(
                f"({name}) M={m:5d} Ps={r['ps']:.4f} Ps_tx={r['ps_per_tx']:.4f} "
                f"Da={r['da_ms']:.3f} ms Imax={r['i_max']}"
            )
        r = analyse(pat, 1000, 5, 120)
        print("   F[m] @1000:", [round(v, 3) for v in cdf_attempts(r, 5)])
        print("   G[u] @1000:", [round(v, 3) for v in cdf_delay(r, list(range(13)))])
