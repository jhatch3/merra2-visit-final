# Render the scalar videos straight from the raw NASA .nc4 via the MERRA2 plugin.
# Runs in WSL VisIt 3.4.0. Frames are written to the Windows side for encoding.
import math

DB = "/mnt/c/Users/Justin/visit-isabel-final/merra/MERRA2_400.inst3_3d_asm_Np.20230905.nc4"
OUT = "/mnt/c/Users/Justin/visit-isabel-final/frames_plugin"

_title = _sub = None


def clean_ann():
    a = AnnotationAttributes()
    a.databaseInfoFlag = 0
    a.userInfoFlag = 0
    SetAnnotationAttributes(a)


def banner(t, s):
    global _title, _sub
    if _title is None:
        _title = CreateAnnotationObject("Text2D")
        _title.position = (0.02, 0.94); _title.height = 0.030
        _title.useForegroundForTextColor = 1
        _sub = CreateAnnotationObject("Text2D")
        _sub.position = (0.02, 0.905); _sub.height = 0.017
        _sub.useForegroundForTextColor = 1
    _title.text = t
    _sub.text = s


def save_atts(prefix):
    sw = SaveWindowAttributes()
    sw.outputToCurrentDirectory = 0
    sw.outputDirectory = OUT
    sw.fileName = prefix
    sw.format = sw.PNG
    sw.width = 1100
    sw.height = 700
    sw.family = 1
    SetSaveWindowAttributes(sw)


def setview(vn, vu=(0, 0, 1)):
    v = GetView3D()
    v.viewNormal = vn
    v.viewUp = vu
    SetView3D(v)


def openplugin():
    OpenDatabase(DB, 0, "MERRA2_1.0")


VIEW_MAP = (0.30, -0.55, 0.62)     # angled look down at a global map, altitude up
VIEW_SIDE = (0.92, 0.16, 0.32)     # face a vertical (lon-constant) slice


def horiz(prefix, var, ctable, pct, title, sub):
    openplugin()
    AddPlot("Pseudocolor", var)
    pc = PseudocolorAttributes(); pc.colorTableName = ctable
    pc.lightingFlag = 0; SetPlotOptions(pc)
    AddOperator("Slice")
    sl = SliceAttributes(); sl.originType = sl.Percent; sl.originPercent = pct
    sl.axisType = sl.ZAxis; sl.project2d = 0; SetOperatorOptions(sl)
    DrawPlots(); ResetView(); setview(VIEW_MAP)
    banner(title, sub)
    save_atts(prefix)
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(DB)


def vsweep(prefix, var, ctable, title, sub, nframes=16):
    openplugin()
    AddPlot("Pseudocolor", var)
    pc = PseudocolorAttributes(); pc.colorTableName = ctable
    pc.lightingFlag = 0; SetPlotOptions(pc)
    AddOperator("Slice")
    DrawPlots(); SetTimeSliderState(0); ResetView(); setview(VIEW_SIDE)
    banner(title, sub)
    save_atts(prefix)
    for i in range(nframes):
        sl = SliceAttributes(); sl.originType = sl.Percent
        sl.originPercent = 100.0 * i / (nframes - 1)
        sl.axisType = sl.XAxis; sl.project2d = 0; SetOperatorOptions(sl)
        SaveWindow()
    DeleteAllPlots(); CloseDatabase(DB)


def main():
    clean_ann()
    # wind speed as a VisIt expression from the plugin's U and V
    openplugin()
    DefineScalarExpression("WS", "sqrt(U*U + V*V)")
    CloseDatabase(DB)

    # 1-3: temperature
    horiz("ptemp_map_", "T", "hot_desaturated", 8,
          "Global Air Temperature (plugin-read)",
          "near-surface slice  |  read straight from the NASA .nc4 by the MERRA2 VisIt plugin")
    vsweep("ptemp_vert_", "T", "hot_desaturated",
           "Vertical Temperature Structure (plugin-read)",
           "slice swept across longitude  |  warm surface to cold tropopause", 16)
    # 3D three-slice orbit (temperature)
    openplugin()
    AddPlot("Pseudocolor", "T")
    pc = PseudocolorAttributes(); pc.colorTableName = "hot_desaturated"
    pc.lightingFlag = 0; SetPlotOptions(pc)
    AddOperator("ThreeSlice")
    DrawPlots(); SetTimeSliderState(0); ResetView()
    banner("3D Temperature, Orthogonal Slices (plugin-read)",
           "three planes through the global atmosphere  |  slow orbit")
    save_atts("ptemp_3d_")
    for i in range(36):
        rad = 2 * math.pi * i / 36
        setview((0.6 * math.cos(rad), 0.6 * math.sin(rad), 0.45))
        SaveWindow()
    DeleteAllPlots(); CloseDatabase(DB)

    # 4-5: humidity
    horiz("phum_map_", "QV", "viridis", 6,
          "Global Moisture, Specific Humidity (plugin-read)",
          "near-surface slice  |  water vapor read by the plugin")
    vsweep("phum_vert_", "QV", "viridis",
           "Moisture Depth (plugin-read)",
           "vertical slice swept across longitude  |  how high the humid layer reaches", 16)

    # 6: wind speed (from the expression)
    horiz("pwind_map_", "WS", "hot", 30,
          "Global Wind Speed (plugin-read)",
          "mid-level slice  |  wind speed = sqrt(U^2+V^2), an expression on the plugin's U and V")

    # 7: moisture volume render (last, in case the software volume renderer is slow)
    openplugin()
    AddPlot("Volume", "QV")
    va = VolumeAttributes(); va.opacityAttenuation = 0.5; va.lightingFlag = 0
    SetPlotOptions(va)
    DrawPlots(); SetTimeSliderState(0); ResetView(); setview(VIEW_MAP)
    banner("3D Moisture Volume (plugin-read)",
           "volume render of water vapor, read straight from the NASA file")
    save_atts("pvol_")
    for s in range(TimeSliderGetNStates()):
        SetTimeSliderState(s); SaveWindow()
    DeleteAllPlots(); CloseDatabase(DB)

    print("PLUGIN_MOVIES_DONE")
    quit()


main()
