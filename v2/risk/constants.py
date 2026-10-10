"""
========================================================================================
        SAJIM RISK — SINGLE SOURCE OF TRUTH FOR EXIT / RATCHET THRESHOLDS
                            (v2/risk/constants.py)
========================================================================================
Every R-multiple threshold used by the position managers lives here so the three
Hummingbird implementations and the two V2 ratchet implementations can no longer drift
apart silently. All R values are measured against the INITIAL risk recorded at entry
(see v2/risk/position_state.py), never against the current (already trailed) stop.
========================================================================================
"""

# ---------------------------------------------------------------------------
# Hummingbird peak harvest (shared M1 evaluator: v2/risk/hummingbird.py)
# ---------------------------------------------------------------------------
HUMMINGBIRD_MIN_R = 1.50            # never harvest below +1.5R
HUMMINGBIRD_DEEP_WICK_R = 1.80      # counter-wick rule needs >= +1.8R
HUMMINGBIRD_STRETCH_R = 1.70        # baseline-envelope stretch rule
HUMMINGBIRD_PEAK_DEFENSE_R = 2.20   # peak-defense stall rule
# Upper bound used by the stand-alone V2 bot (bots/sajim_v2_bot.py): above this the
# take-profit is left to fill naturally. The dual-bot risk manager has no upper bound.
HUMMINGBIRD_V2_BOT_MAX_R = 2.95

# ---------------------------------------------------------------------------
# V1 (bots/sajim_v1_bot.py) management thresholds
# ---------------------------------------------------------------------------
V1_SCRATCH_HEALTH = 0.30            # H(t) below which a minor loser is scratched
V1_SCRATCH_MIN_R = -0.45
V1_SCRATCH_MAX_R = -0.10
V1_SCRATCH_DEEP_HEALTH = 0.25       # H(t) below which a deep loser is scratched
V1_STAGNATION_MINUTES = 45.0
V1_STAGNATION_MIN_R = -0.25
V1_STAGNATION_MAX_R = 0.30
V1_STAGNATION_HEALTH = 0.45
V1_HUMMINGBIRD_MIN_R = HUMMINGBIRD_MIN_R
V1_HUMMINGBIRD_WICK_R = HUMMINGBIRD_DEEP_WICK_R
V1_HUMMINGBIRD_STRETCH_R = 2.00
V1_HARVEST_TRIGGER_R = 1.50         # 50% partial close
V1_BREAKEVEN_TRIGGER_R = 2.00
V1_LOCK_TRIGGER_R = 2.80
V1_LOCK_R = 1.50

# ---------------------------------------------------------------------------
# V2 dual-bot risk manager (v2/risk/ratchet.py)
# ---------------------------------------------------------------------------
V2_BE_SHIELD_TRIGGER_R = 0.35
V2_BE_SHIELD_OFFSET_R = 0.05
V2_EARLY_CUT_R = -0.35
V2_KINETIC_MIN_R = 0.65
V2_STAGE1_TRIGGER_R = 1.50
V2_STAGE1_LOCK_R = 0.30
V2_STAGE2_TRIGGER_R = 2.20
V2_STAGE2_LOCK_R = 1.00

# ---------------------------------------------------------------------------
# Stand-alone V2 bot (bots/sajim_v2_bot.py) two-stage ratchet
# (kept deliberately more conservative at stage 1: BE + 0.15R)
# ---------------------------------------------------------------------------
V2_BOT_STAGE1_TRIGGER_R = V2_STAGE1_TRIGGER_R
V2_BOT_STAGE1_LOCK_R = 0.15
V2_BOT_STAGE2_TRIGGER_R = V2_STAGE2_TRIGGER_R
V2_BOT_STAGE2_LOCK_R = V2_STAGE2_LOCK_R
