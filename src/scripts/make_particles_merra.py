#!/usr/bin/env python3
"""
make_particles_merra.py  --  Vector-glyph ("particle"/flow) movies from the
MERRA-2 wind vector field built by build_wind_vectors.py.

    visit -cli -nowin -s make_particles_merra.py

This VisIt build has no Streamline/IntegralCurve plot, so we use the Vector
plot: thousands of little arrows sampled through the 3D wind field, colored by
speed, showing the storm's circulation. Altitude (z) is up.

Outputs in ./frames_merra:
    p1_windvec_*   3D wind arrows over the whole volume, swept over time
    p2_windmap_*   wind arrows on a near-surface slice (clean circulation map)
"""

import csv
import os

DATA = "./vtr/merra_WIND.visit"
OUT_DIR = "./frames_merra"
os.makedirs(OUT_DIR, exist_ok=True)

TIMES = {}
try:
    with open("./vtr/times.csv") as f:
        for row in csv.DictReader(f):
            TIMES[int(row["index"])] = row.get("utc_time", "")
except FileNotFoundError:
    pass

_title = _sub = _clock = None


def setup_text():
    global _title, _sub, _clock
    _title = CreateAnnotationObject("Text2D")
    _title.position = (0.02, 0.94); _title.height = 0.030
    _title.useForegroundForTextColor = 1
    _sub = CreateAnnotationObject("Text2D")
    _sub.position = (0.02, 0.905); _sub.height = 0.017
    _sub.useForegroundForTextColor = 1
    _clock = CreateAnnotationObject("Text2D")
    _clock.position = (0.02, 0.03); _clock.height = 0.022
    _clock.useForegroundForTextColor = 1


def banner(t, s):
    _title.text = t; _sub.text = s


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
    s.width = 1280; s.height = 720; s.family = 1
    SetSaveWindowAttributes(s)


def set_view(vn, vu=(0, 0, 1)):
    v = GetView3D(); v.viewNormal = vn; v.viewUp = vu; SetView3D(v)


def vector_atts(n):
    va = VectorAttributes()
    va.useStride = 0
    va.nVectors = n
    va.scaleByMagnitude = 1
    va.autoScale = 1
    va.colorByMagnitude = 1
    va.colorTableName = "hot"
    SetPlotOptions(va)


def p1_windvec():
    OpenDatabase(DATA)
    AddPlot("Vector", "wind")
    vector_atts(4000)
    DrawPlots(); ResetView(); set_view((0.35, -0.55, 0.55))
    banner("Wind Vectors - 3D Atmospheric Flow",
           "Arrows sampled through the wind field  |  color = speed (m/s)  |  altitude up, ground at bottom")
    save_atts("p1_windvec_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); clock(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(DATA)


def p2_windmap():
    OpenDatabase(DATA)
    AddPlot("Vector", "wind")
    AddOperator("Slice")
    sl = SliceAttributes()
    sl.originType = sl.Percent
    sl.originPercent = 18
    sl.axisType = sl.ZAxis
    sl.project2d = 0
    SetOperatorOptions(sl)
    vector_atts(2500)
    DrawPlots(); ResetView(); set_view((0.30, -0.45, 0.70))
    banner("Wind Circulation Map - Lower Troposphere",
           "Wind arrows on a near-surface slice  |  color = speed (m/s)  |  follow the cyclonic swirl over time")
    save_atts("p2_windmap_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); clock(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(DATA)


def main():
    clean_annotations()
    setup_text()
    p1_windvec()
    p2_windmap()
    print("Done. Encode p1/p2 with ffmpeg.")


main()
