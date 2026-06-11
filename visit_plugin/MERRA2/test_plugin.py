# VisIt CLI test: open a real MERRA-2 .nc4 with our MERRA2 plugin and read it.
db = "/mnt/c/Users/Justin/visit-isabel-final/merra/MERRA2_400.inst3_3d_asm_Np.20230905.nc4"
print("=== opening with the MERRA2 plugin (forced) ===")
err = OpenDatabase(db, 0, "MERRA2_1.0")
print("OPEN_RESULT", err)

md = GetMetaData(db)
print("NUM_MESHES", md.GetNumMeshes())
if md.GetNumMeshes() > 0:
    print("MESH0", md.GetMeshes(0).name)
print("NUM_SCALARS", md.GetNumScalars())
for i in range(md.GetNumScalars()):
    print("SCALAR", md.GetScalars(i).name)
print("NSTATES", TimeSliderGetNStates())

AddPlot("Pseudocolor", "T")
DrawPlots()
Query("MinMax")
print("T_MINMAX:", GetQueryOutputString().strip())
print("PLUGIN_TEST_OK")
quit()
