"""
config/parameters.py

Central place for every constant used in Phase 1.

Nothing in here is "magic" -- every number is explained below.  When you
move to later phases (PID, adaptive, predictive) you will keep importing
from this file so that every controller is tested against the *same*
physical plant and the *same* disturbance schedule (Section 11 / 19 of
the project brief: fair comparison requires identical conditions).

-----------------------------------------------------------------------
SIMULATION-SCALE ASSUMPTION (read this first)
-----------------------------------------------------------------------
A real industrial cold room has a thermal time constant of several
hours, because it contains a large, well-insulated volume of air,
metal shelving and stored product. If we modelled that faithfully,
a single door-opening experiment would need to run for many
simulated hours before anything interesting happened on a plot.

For a mini-project we deliberately choose a *smaller virtual chamber*
(think: a lab-scale insulated box, not a warehouse) so that:
    - the whole pull-down + disturbance + recovery cycle fits in a
      simulation window of a few hours of *simulated* time,
    - the door-opening effect is clearly visible on a graph,
    - the underlying physics (first-order thermal system) is
      identical in form to the real industrial case -- only the
      numeric values of C and UA are scaled down.

This is explicitly an assumption, not a claim about a real industrial
chamber. It is safe to change these numbers later once you calibrate
against a real or literature-reported cold room.
"""

# ---------------------------------------------------------------------
# 1. TEMPERATURES  (all in degrees Celsius, deg C)
# ---------------------------------------------------------------------

T_INITIAL_DEGC = 25.0
# The chamber starts at ambient temperature, i.e. the compressor has
# just been switched on for the first time ("cold start" / pull-down).

T_SETPOINT_DEGC = -18.0
# Standard target temperature for frozen cold storage.

T_AMBIENT_DEGC = 25.0
# Temperature of the room/outside air surrounding the chamber and the
# air that rushes in whenever the door is opened.

# ---------------------------------------------------------------------
# 2. THERMAL MODEL PARAMETERS
# ---------------------------------------------------------------------
#
# Governing equation (Phase 1, no controller yet):
#
#     C * dT/dt = Q_leak(t) + Q_door(t) - Q_cooling
#
# where
#     T          chamber air temperature                [degC]
#     C          effective thermal capacitance           [J/K]
#     Q_leak     heat leaking in through walls/insulation [W]
#     Q_door     EXTRA heat entering because the door is open [W]
#     Q_cooling  heat removed by the refrigeration unit   [W]
#
# Heat leak and door heat are both modelled with simple linear
# (Newton's-law-of-cooling) conductances:
#
#     Q_leak = UA_LEAK * (T_ambient - T)
#     Q_door = UA_DOOR_EXTRA * (T_ambient - T)      (only while door open)
#
# This is the same "resistance x temperature-difference" idea used for
# heat leakage through walls in Unit 1 mathematical-modelling problems.

C_THERMAL_J_PER_K = 20_000.0
# Effective thermal capacitance of the chamber (air + walls + a modest
# amount of stored product, lumped together -- a single "capacitor" in
# the electrical-thermal analogy). ASSUMPTION for a small virtual
# chamber; a real industrial room would be 100-1000x larger.

UA_LEAK_W_PER_K = 8.0
# Overall heat-leak conductance through the insulated walls while the
# door is CLOSED. Larger UA = worse insulation = faster heat leaks in.

UA_DOOR_EXTRA_W_PER_K = 40.0
# ADDITIONAL conductance that appears only while the door is OPEN,
# representing direct air exchange + convection with the warm room air.
# It is intentionally much larger than UA_LEAK_W_PER_K because an open
# doorway is a far worse thermal barrier than an insulated wall.

# ---------------------------------------------------------------------
# 3. COOLING CAPACITY  (Phase 1 placeholder -- NOT a controller yet)
# ---------------------------------------------------------------------
#
# Phase 1 has no PID / ON-OFF controller. To still get a *meaningful*
# physics demonstration (pull-down to setpoint, and self-recovery after
# a disturbance) we give the compressor a FIXED cooling power, sized so
# that the natural steady state with the door closed equals the
# setpoint:
#
#     0 = UA_LEAK * (T_ambient - T_setpoint) - Q_cooling_max
#     => Q_cooling_max = UA_LEAK * (T_ambient - T_setpoint)
#
# Real controllers (Phase 4 onward) will instead compute Q_cooling
# dynamically from a compressor command in [0, 100]%. For now this
# constant lets us test and trust the plant model in isolation, which
# is the whole point of Phase 1.

Q_COOLING_MAX_W = UA_LEAK_W_PER_K * (T_AMBIENT_DEGC - T_SETPOINT_DEGC)
# = 8.0 * (25 - (-18)) = 8.0 * 43 = 344.0 W

# ---------------------------------------------------------------------
# 4. TIME / SIMULATION SETTINGS
# ---------------------------------------------------------------------

DT_SECONDS = 1.0
# Integration time step for the explicit Euler method. Small enough
# for this first-order system to be numerically stable and accurate.

SIM_DURATION_SECONDS = 12_000.0
# Total simulated time (12,000 s = 200 minutes = ~3.33 hours). Long
# enough to (a) see the pull-down from ambient to setpoint, (b) apply
# a door-opening disturbance, and (c) see the chamber recover.

# ---------------------------------------------------------------------
# 5. DOOR-OPENING DISTURBANCE SCHEDULE (Phase 1 demo event)
# ---------------------------------------------------------------------

DOOR_OPEN_AT_SECONDS = 8_000.0
# When the door opens during this demonstration run. Chosen so the
# chamber has already settled close to the setpoint (see README for
# the settling-time estimate) before the disturbance hits.

DOOR_OPEN_DURATION_SECONDS = 90.0
# How long the door stays open (a fairly long "worker carrying boxes
# through the doorway" event) before it is closed again.

# ---------------------------------------------------------------------
# 6. INTELLIGENT DOOR HEAT-EXCHANGE & SEVERITY PARAMETERS (SPECIAL FEATURE)
# ---------------------------------------------------------------------

# Configurable Safety Limits and Thresholds
MAX_COOLING_POWER_W = Q_COOLING_MAX_W

# Estimated Heat Load Thresholds [W]
WARNING_HEAT_LOAD_W = 250.0
CRITICAL_HEAT_LOAD_W = 750.0

# Temperature Deviation Thresholds [degC]
WARNING_TEMPERATURE_DEVIATION_DEGC = 2.0
CRITICAL_TEMPERATURE_DEVIATION_DEGC = 5.0

# Temperature Rate Thresholds [degC/s]
WARNING_TEMP_RATE_DEGC_PER_S = 0.05
CRITICAL_TEMP_RATE_DEGC_PER_S = 0.15

# Thermal Severity Score Thresholds (0 to 100)
SEVERITY_SCORE_WARNING_THRESHOLD = 30.0
SEVERITY_SCORE_CRITICAL_THRESHOLD = 70.0

# Feedforward Compensation Ramp Rate (% per second limit to prevent instant jumps)
COMPENSATION_RAMP_RATE_PCT_PER_S = 10.0

