#!/usr/bin/env python3
"""
make_movies_merra.py  --  Six annotated movies from the MERRA-2 .vtr series
built by build_merra_series.py (variables T, QV, WS).

    visit -cli -nowin -s make_movies_merra.py

Each movie carries a TITLE + SUBTITLE explaining what is shown, plus the real
UTC time. Output PNG sequences in ./frames_merra:

    m1_time     temperature, near-surface horizontal slice, over time
    m2_vslice   temperature, vertical slice swept W->E (atmosphere profile)
    m3_orbit    temperature, 3D warm-air isosurface, camera orbit
    m4_qv_time  specific humidity (moisture), near-surface slice, over time
    m5_qv_vert  specific humidity, vertical slice (how deep the moist layer is)
    m6_ws_time  wind speed (from U,V), mid-level slice, over time
"""

import math
import os
import csv

OUT_DIR = "./frames_merra"
os.makedirs(OUT_DIR, exist_ok=True)


def vpath(var):
    return "./vtr/merra_%s.visit" % var


TIMES = {}
try:
    with open("./vtr/times.csv") as f:
        for row in csv.DictReader(f):
            TIMES[int(row["index"])] = row.get("utc_time", "")
except FileNotFoundError:
    pass

# --- annotation objects (created once) --------------------------------------
_title = _sub = _clock = None


def setup_text():
    global _title, _sub, _clock
    _title = CreateAnnotationObject("Text2D")
    _title.position = (0.02, 0.94)
    _title.height = 0.030
    _title.useForegroundForTextColor = 1
    _sub = CreateAnnotationObject("Text2D")
    _sub.position = (0.02, 0.905)
    _sub.height = 0.017
    _sub.useForegroundForTextColor = 1
    _clock = CreateAnnotationObject("Text2D")
    _clock.position = (0.02, 0.03)
    _clock.height = 0.022
    _clock.useForegroundForTextColor = 1


def banner(title, sub):
    _title.text = title
    _sub.text = sub


def clock(state):
    _clock.text = TIMES.get(state, "") + " UTC"


def clean_annotations():
    a = AnnotationAttributes()
    a.databaseInfoFlag = 0
    a.userInfoFlag = 0
    SetAnnotationAttributes(a)


def save_atts(prefix):
    s = SaveWindowAttributes()
    s.outputToCurrentDirectory = 0
    s.outputDirectory = OUT_DIR
    s.fileName = prefix
    s.format = s.PNG
    s.width = 1280
    s.height = 720
    s.resConstraint = s.NoConstraint   # honor 1280x720 (default forces a square)
    s.family = 1
    SetSaveWindowAttributes(s)


def set_view(vn, vu=(0, 0, 1)):    # altitude (z) is screen-up by default
    v = GetView3D()
    v.viewNormal = vn
    v.viewUp = vu
    SetView3D(v)


# all views keep altitude (z) pointing up, ground (z=0) at the bottom
VIEW_MAP = (0.35, -0.55, 0.55)     # 3/4 view of the upright box (slice sits low)
VIEW_SIDE = (0.94, 0.16, 0.30)     # face the lat-altitude plane, altitude up


def mid_state():
    return int(TimeSliderGetNStates() * 0.5)


def pseudocolor(var, ctable):
    AddPlot("Pseudocolor", var)
    pc = PseudocolorAttributes()
    pc.colorTableName = ctable
    SetPlotOptions(pc)


def horiz_slice(pct):
    AddOperator("Slice")
    sl = SliceAttributes()
    sl.originType = sl.Percent
    sl.originPercent = pct
    sl.axisType = sl.ZAxis
    sl.project2d = 0
    SetOperatorOptions(sl)


# ----------------------------------------------------------------------
def m1_temp_time():
    db = vpath("T"); OpenDatabase(db)
    pseudocolor("T", "hot_desaturated")
    horiz_slice(12)
    DrawPlots(); ResetView(); set_view(VIEW_MAP)
    banner("Atlantic Air Temperature - Lower Troposphere",
           "Horizontal slice ~2 km  |  color = temperature (K)  |  MERRA-2 reanalysis, 5-6 Sep 2023")
    save_atts("m1_time_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); clock(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def m2_temp_vslice():
    db = vpath("T"); OpenDatabase(db)
    pseudocolor("T", "hot_desaturated")
    AddOperator("Slice")
    DrawPlots(); SetTimeSliderState(mid_state())
    ResetView(); set_view(VIEW_SIDE); clock(mid_state())
    banner("Vertical Temperature Structure",
           "West-East slice swept through the volume  |  0-17 km  |  warm surface to cold tropopause")
    save_atts("m2_vslice_")
    for i in range(60):
        sl = SliceAttributes()
        sl.originType = sl.Percent
        sl.originPercent = 100.0 * i / 59
        sl.axisType = sl.XAxis
        sl.project2d = 0
        SetOperatorOptions(sl); SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def _sweep(lo, hi, frac, phase, cycles=2.0, inset=0.06):
    """Ping-pong a slice plane between lo..hi as frac goes 0->1.

    inset keeps the plane off the exact faces so it never falls outside the
    volume and vanish; phase offsets each axis so the planes glide
    independently (like sliders being dragged at once).
    """
    span = hi - lo
    lo += span * inset
    hi -= span * inset
    # cosine ping-pong: smooth, starts/ends mid-travel, never snaps
    t = 0.5 * (1.0 - math.cos(2 * math.pi * (cycles * frac + phase)))
    return lo + (hi - lo) * t


def m3_wind_orbit():
    db = vpath("T"); OpenDatabase(db)
    # two VERTICAL slice planes (no horizontal/altitude plane): one at constant
    # longitude (X) and one at constant latitude (Y). Each is its own plot+Slice,
    # since one plot can't carry two independent planes.
    for k in range(2):
        AddPlot("Pseudocolor", "T")
        pc = PseudocolorAttributes()
        pc.colorTableName = "hot_desaturated"
        pc.lightingFlag = 0                  # flat colors so edge-on slices don't go black
        pc.legendFlag = 1 if k == 0 else 0   # single shared legend
        SetPlotOptions(pc)
        AddOperator("Slice")
    DrawPlots(); SetTimeSliderState(0); ResetView()
    banner("3D Temperature - Vertical Slices",
           "Two vertical planes glide through the volume  |  slow orbit while time advances  |  5-6 Sep 2023")
    save_atts("m3_orbit_")

    def vslice(axis, pct):                   # set the active plot's slice plane
        sl = SliceAttributes()
        sl.originType = sl.Percent
        sl.originPercent = pct
        sl.axisType = axis
        sl.project2d = 0
        SetOperatorOptions(sl)

    N = 160                                  # many frames -> slow orbit
    ns = TimeSliderGetNStates()
    sa = SliceAttributes()                   # for the axis enums
    for i in range(N):
        frac = i / float(N)
        state = min(ns - 1, int(frac * ns))  # sweep through all 16 timesteps
        SetTimeSliderState(state)
        clock(state)
        # slide the two vertical planes (the "x/y sliders"), each on its own phase
        SetActivePlots(0); vslice(sa.XAxis, _sweep(0.0, 100.0, frac, phase=0.00))
        SetActivePlots(1); vslice(sa.YAxis, _sweep(0.0, 100.0, frac, phase=0.50))
        rad = 2 * math.pi * frac             # one slow revolution over the run
        set_view((0.6 * math.cos(rad), 0.6 * math.sin(rad), 0.45))
        SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def m4_qv_time():
    db = vpath("QV"); OpenDatabase(db)
    pseudocolor("QV", "viridis")
    horiz_slice(8)
    DrawPlots(); ResetView(); set_view(VIEW_MAP)
    banner("Atmospheric Moisture - Specific Humidity",
           "Near-surface slice  |  color = water vapor (kg/kg)  |  bright = humid tropical air")
    save_atts("m4_qv_time_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); clock(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def m5_qv_vslice():
    db = vpath("QV"); OpenDatabase(db)
    pseudocolor("QV", "viridis")
    AddOperator("Slice")
    DrawPlots(); SetTimeSliderState(mid_state())
    ResetView(); set_view(VIEW_SIDE); clock(mid_state())
    banner("Moisture Depth - Vertical Slice",
           "West-East slice  |  how high the humid layer reaches before the dry upper troposphere")
    save_atts("m5_qv_vert_")
    for i in range(60):
        sl = SliceAttributes()
        sl.originType = sl.Percent
        sl.originPercent = 100.0 * i / 59
        sl.axisType = sl.XAxis
        sl.project2d = 0
        SetOperatorOptions(sl); SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def m6_ws_time():
    db = vpath("WS"); OpenDatabase(db)
    pseudocolor("WS", "hot")
    horiz_slice(30)
    DrawPlots(); ResetView(); set_view(VIEW_MAP)
    banner("Wind Speed & Circulation",
           "Slice ~5 km altitude  |  color = horizontal wind speed (m/s)  |  derived from U, V")
    save_atts("m6_ws_time_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); clock(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(db)


def main():
    clean_annotations()
    setup_text()
    m1_temp_time()
    m2_temp_vslice()
    m3_wind_orbit()
    m4_qv_time()
    m5_qv_vslice()
    m6_ws_time()
    print("Done. Encode the 6 movies with ffmpeg (see README).")


main()
