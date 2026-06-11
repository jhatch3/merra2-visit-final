#!/usr/bin/env python3
"""
make_volume_merra.py  --  TRUE VOLUME RENDER of the moisture field.

Must run in WINDOWED mode (uses the GPU; the headless software volume renderer
is unusably slow and the engine crashes on NaN):

    visit -cli -s make_volume_merra.py      # NOTE: no -nowin

A VisIt window appears and screen-capture grabs the GPU-rendered frames, so
keep the window on top while it runs. Input is the NaN-free QV volume series
(merra_QVvol.visit). Output: frames_merra/vol_qv_*  ->  merra_vol_qv.mp4
"""

import csv
import os

DATA = "./vtr/merra_QVvol.visit"
OUT_DIR = "./frames_merra"
os.makedirs(OUT_DIR, exist_ok=True)

TIMES = {}
try:
    with open("./vtr/times.csv") as f:
        for row in csv.DictReader(f):
            TIMES[int(row["index"])] = row.get("utc_time", "")
except FileNotFoundError:
    pass


def main():
    a = AnnotationAttributes()
    a.databaseInfoFlag = 0
    a.userInfoFlag = 0
    SetAnnotationAttributes(a)

    title = CreateAnnotationObject("Text2D")
    title.position = (0.02, 0.94); title.height = 0.030
    title.useForegroundForTextColor = 1
    sub = CreateAnnotationObject("Text2D")
    sub.position = (0.02, 0.905); sub.height = 0.017
    sub.useForegroundForTextColor = 1
    clock = CreateAnnotationObject("Text2D")
    clock.position = (0.02, 0.03); clock.height = 0.022
    clock.useForegroundForTextColor = 1
    title.text = "3D Moisture Volume Render"
    sub.text = ("Volume rendering of water vapor (QV)  |  translucent = humid air"
                "  |  full 3D, altitude up")

    OpenDatabase(DATA)
    AddPlot("Volume", "QV")
    va = VolumeAttributes()
    va.opacityAttenuation = 0.55
    va.opacityMode = va.FreeformMode
    va.lightingFlag = 0
    SetPlotOptions(va)
    DrawPlots()

    ResizeWindow(1, 1920, 1280)         # high-res GPU render (fits a 2560x1440 screen)
    SetTimeSliderState(0)
    v = GetView3D()
    v.viewNormal = (0.35, -0.55, 0.55)
    v.viewUp = (0, 0, 1)             # altitude up, ground at bottom
    SetView3D(v)

    s = SaveWindowAttributes()
    s.outputToCurrentDirectory = 0
    s.outputDirectory = OUT_DIR
    s.fileName = "vol_qv_"
    s.format = s.PNG
    s.screenCapture = 1             # capture the GPU-rendered window
    s.family = 1
    SetSaveWindowAttributes(s)

    for state in range(TimeSliderGetNStates()):
        SetTimeSliderState(state)
        clock.text = TIMES.get(state, "") + " UTC"
        SaveWindow()
    print("VOLUME_MOVIE_DONE")
    quit()


main()
