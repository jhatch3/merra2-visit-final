#!/usr/bin/env python3
"""
make_flow_quad_merra.py  --  4-panel (2x2) view of the Lagrangian particle flow.

    visit -cli -nowin -s make_flow_quad_merra.py

Four synchronized views of the same drifting particles, saved tiled:
    top-left   : looking down X  (latitude vs height)
    top-right  : looking down Y  (longitude vs height)
    bottom-left: looking down Z  (top-down map)
    bottom-right: 3D corner view (like the single flow movie)

Panels are rendered clean; the labels are drawn on afterward with ffmpeg
(VisIt's text annotations are global to the window layout, so they'd overlap).

Output: frames_merra/flowquad_*.png  ->  merra_flow_quad.mp4
"""

import os

DATA = "./vtp/particles.visit"
OUT_DIR = "./frames_merra"
os.makedirs(OUT_DIR, exist_ok=True)

VIEWS = {
    1: ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),     # down X: lat vs height
    2: ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),     # down Y: lon vs height
    3: ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),     # down Z: map
    4: ((0.35, -0.55, 0.55), (0.0, 0.0, 1.0)),  # corner
}


def main():
    SetWindowLayout(4)
    for w in (1, 2, 3, 4):
        SetActiveWindow(w)
        a = AnnotationAttributes()
        a.databaseInfoFlag = 0
        a.userInfoFlag = 0
        a.axes3D.visible = 0
        a.axes3D.triadFlag = 0
        a.axes3D.bboxFlag = 0
        SetAnnotationAttributes(a)
        OpenDatabase(DATA)
        AddPlot("Pseudocolor", "speed")
        pa = PseudocolorAttributes()
        pa.colorTableName = "hot"
        pa.pointType = pa.Point
        pa.pointSizePixels = 4
        pa.minFlag = 1; pa.min = 0.0
        pa.maxFlag = 1; pa.max = 45.0
        pa.legendFlag = 0
        SetPlotOptions(pa)
        DrawPlots()
        ResetView()
        vn, vu = VIEWS[w]
        v = GetView3D()
        v.viewNormal = vn
        v.viewUp = vu
        if w != 4:
            v.perspective = 0                  # straight-on orthographic
        SetView3D(v)

    s = SaveWindowAttributes()
    s.outputToCurrentDirectory = 0
    s.outputDirectory = OUT_DIR
    s.fileName = "flowquad_"
    s.format = s.PNG
    s.family = 1
    s.saveTiled = 1
    s.width = 1400
    s.height = 1000
    SetSaveWindowAttributes(s)

    SetActiveWindow(1)
    ns = TimeSliderGetNStates()
    for state in range(ns):
        for w in (1, 2, 3, 4):
            SetActiveWindow(w)
            SetTimeSliderState(state)
        SaveWindow()
    print("QUAD_DONE")


main()
