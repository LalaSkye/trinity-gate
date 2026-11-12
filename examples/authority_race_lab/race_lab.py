"""Synthetic deterministic authority-at-effect schedule explorer."""
from dataclasses import dataclass
from itertools import permutations
import json

EVENTS = ("A.check", "A.commit", "B.check", "B.commit", "revoke")

@dataclass(frozen=True)
class Outcome:
    schedule: tuple[str, ...]
    accepted: tuple[str, ...]
    stale_effects: tuple[str, ...]

def explore(schedule, mode="unsafe_cache"):
    if mode not in ("unsafe_cache", "effect_recheck"):
        raise ValueError("invalid mode")
    if len(schedule) != 5 or set(schedule) != set(EVENTS):
        raise ValueError("schedule must contain each event exactly once")
    if schedule.index("A.check") > schedule.index("A.commit") or schedule.index("B.check") > schedule.index("B.commit"):
        raise ValueError("check must precede commit")
    revoked = False
    checks = {}
    accepted, stale = [], []
    for event in schedule:
        if event == "revoke":
            revoked = True
        elif event.endswith(".check"):
            checks[event[0]] = not revoked
        else:
            actor = event[0]
            allowed = checks[actor] if mode == "unsafe_cache" else (checks[actor] and not revoked)
            if allowed:
                accepted.append(actor)
                if revoked:
                    stale.append(actor)
    return Outcome(tuple(schedule), tuple(accepted), tuple(stale))

def schedules():
    for schedule in permutations(EVENTS):
        if schedule.index("A.check") < schedule.index("A.commit") and schedule.index("B.check") < schedule.index("B.commit"):
            yield schedule

def report():
    options = list(schedules())
    unsafe = [explore(s) for s in options]
    guarded = [explore(s, "effect_recheck") for s in options]
    return {
        "schema": "trinity-authority-race-lab/0.1",
        "schedules": len(options),
        "unsafe_stale_schedules": sum(bool(x.stale_effects) for x in unsafe),
        "guarded_stale_schedules": sum(bool(x.stale_effects) for x in guarded),
        "counterexample": list(next(x.schedule for x in unsafe if x.stale_effects)),
        "model_limits": "Single-process sequential events; instantaneous revocation; no network, clocks, leases, escrow or consensus",
        "claim": "Effect-time recheck blocks stale effects in this synthetic model only."
    }

if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
