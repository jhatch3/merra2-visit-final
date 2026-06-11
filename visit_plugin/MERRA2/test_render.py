# Can WSL VisIt render an image headless, reading via the MERRA2 plugin?
db = "/mnt/c/Users/Justin/visit-isabel-final/merra/MERRA2_400.inst3_3d_asm_Np.20230905.nc4"
OpenDatabase(db, 0, "MERRA2_1.0")
AddPlot("Pseudocolor", "T")
AddOperator("Slice")
s = SliceAttributes()
s.axisType = s.ZAxis
s.originType = s.Percent
s.originPercent = 10
s.project2d = 0
SetOperatorOptions(s)
DrawPlots()

sw = SaveWindowAttributes()
sw.outputToCurrentDirectory = 0
sw.outputDirectory = "/tmp"
sw.fileName = "plugin_render_test_"
sw.format = sw.PNG
sw.width = 900
sw.height = 600
sw.family = 0
SetSaveWindowAttributes(sw)
name = SaveWindow()
print("SAVED_FILE:", name)
print("RENDER_TEST_DONE")
quit()
