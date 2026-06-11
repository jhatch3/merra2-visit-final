#!/usr/bin/env python3
"""
make_flow_merra.py  --  Animate the Lagrangian particle pathlines computed by
advect_particles.py.

    visit -cli -nowin -s make_flow_merra.py

Renders the drifting tracer cloud (colored by wind speed) over time, altitude
up. Output: frames_merra/flow_*  ->  merra_flow_particles.mp4
"""

import csv
import os

DATA = "./vtp/particles.visit"
OUT_DIR = "./frames_merra"
os.makedirs(OUT_DIR, exist_ok=True)

TIMES = {}
try:
    with open("./vtp/times.csv") as f:
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


def main():
    clean_annotations()
    setup_text()
    OpenDatabase(DATA)
    AddPlot("Pseudocolor", "speed")
    pa = PseudocolorAttributes()
    pa.colorTableName = "hot"
    pa.pointType = pa.Point
    pa.pointSizePixels = 5
    pa.minFlag = 1; pa.min = 0.0
    pa.maxFlag = 1; pa.max = 45.0
    SetPlotOptions(pa)
    DrawPlots()

    ResetView()
    v = GetView3D()
    v.viewNormal = (0.35, -0.55, 0.55)
    v.viewUp = (0, 0, 1)             # altitude up, ground at the bottom
    SetView3D(v)

    _title.text = "Air Parcel Trajectories - Lagrangian Tracers"
    _sub.text = ("1,232 massless particles drifting with the wind  |  "
                 "color = speed (m/s)  |  45 h, 5-6 Sep 2023")

    save_atts("flow_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s)
        _clock.text = TIMES.get(s, "") + " UTC"
        SaveWindow()
    print("Done. Encode frames_merra/flow_*.png -> merra_flow_particles.mp4")


main()
