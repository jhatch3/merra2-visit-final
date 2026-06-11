#!/usr/bin/env python3
"""
build_merra_series.py  --  THE FORMATTER (NASA MERRA-2 edition).

VisIt can open a NetCDF, but raw MERRA-2 3D files are NOT ready for a sensible
3D render:

  * the vertical axis is PRESSURE (hPa), non-uniform (1000, 975, ... 0.1) --
    plotting "level index" squashes the atmosphere; it must be converted to a
    physical pseudo-height;
  * each daily file holds 8 timesteps and you usually want ONE variable over a
    REGION, not the whole global multi-variable cube;
  * the frames must be assembled into a single time-varying database.

This formatter does all of that:

  * opens every MERRA2_*.inst3_3d_asm_Np.*.nc4 in --src (concatenated in time),
  * selects one variable (--var, e.g. T, U, V, OMEGA, QV) over an optional
    lat/lon box,
  * converts pressure levels to pseudo-height  z = H * ln(p0/p)  (H~7.5 km),
  * writes one VTK RectilinearGrid (.vtr) per timestep (rectilinear handles the
    non-uniform vertical correctly), plus
  * merra.visit (the VisIt time series) and times.csv (real UTC timestamps).

Requires xarray, netCDF4, vtk (all standard in a sci-viz python env).

Usage:
    python build_merra_series.py --src ./merra --var T \
        --lat-min 10 --lat-max 45 --lon-min -90 --lon-max -40 --out ./vtr
"""

import argparse
import csv
import glob
import os

import numpy as np
import xarray as xr
import vtk
from vtk.util import numpy_support as nps

H_KM = 7.5          # atmospheric scale height (km) for the pressure->height map
P0 = 1000.0         # reference pressure (hPa)
FILL = 1.0e14       # values >= this are treated as missing


def pressure_to_height(levels_hpa):
    """z = H * ln(p0/p), so the surface (1000 hPa) ~ 0 km and it grows upward."""
    return H_KM * np.log(P0 / np.asarray(levels_hpa, dtype="f8"))


def write_vtr(path, lon, lat, zkm, field):
    """field shape (nlev, nlat, nlon) -> VTK RectilinearGrid (.vtr)."""
    grid = vtk.vtkRectilinearGrid()
    nx, ny, nz = len(lon), len(lat), len(zkm)
    grid.SetDimensions(nx, ny, nz)
    grid.SetXCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(lon, "f4")))
    grid.SetYCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(lat, "f4")))
    grid.SetZCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(zkm, "f4")))
    # VTK point order is x-fastest; field[z,y,x] raveled C-order == x fastest.
    flat = np.ascontiguousarray(field, dtype="f4").ravel(order="C")
    arr = nps.numpy_to_vtk(flat, deep=1)
    arr.SetName(field_name)
    grid.GetPointData().SetScalars(arr)
    w = vtk.vtkXMLRectilinearGridWriter()
    w.SetFileName(path)
    w.SetInputData(grid)
    w.SetCompressorTypeToZLib()
    w.Write()


def main():
    ap = argparse.ArgumentParser(description="Format MERRA-2 3D into a VisIt time series.")
    ap.add_argument("--src", required=True, help="dir of MERRA2 *.nc4 files")
    ap.add_argument("--out", default="./vtr")
    ap.add_argument("--var", default="T", help="variable: T U V OMEGA QV RH H ...")
    ap.add_argument("--lat-min", type=float, default=None)
    ap.add_argument("--lat-max", type=float, default=None)
    ap.add_argument("--lon-min", type=float, default=None)
    ap.add_argument("--lon-max", type=float, default=None)
    ap.add_argument("--name", default="merra")
    ap.add_argument("--min-hpa", type=float, default=100.0,
                    help="drop levels above this (lower pressure); 100 hPa ~ 17 km")
    args = ap.parse_args()

    global field_name
    field_name = args.var

    files = sorted(glob.glob(os.path.join(args.src, "*.nc4"))) or \
        sorted(glob.glob(os.path.join(args.src, "*.nc")))
    if not files:
        raise SystemExit(f"No .nc4/.nc files in {args.src}")

    print(f"Opening {len(files)} file(s)...")

    def load_one(path):
        """Open one daily file, pull just the chosen variable over the chosen
        region, and load that small subset into memory (then the file closes).
        This avoids holding the full ~1 GB global multi-variable cube.
        Special var 'WS' derives wind speed = sqrt(U^2 + V^2)."""
        d = xr.open_dataset(path)

        def pick(name):
            if name not in d:
                raise SystemExit(f"Variable '{name}' not found. "
                                 f"Available: {list(d.data_vars)}")
            a = d[name]
            if args.lat_min is not None:
                a = a.sel(lat=slice(args.lat_min, args.lat_max))
            if args.lon_min is not None:
                a = a.sel(lon=slice(args.lon_min, args.lon_max))
            return a

        if args.var == "WS":                    # derived horizontal wind speed
            a = (pick("U") ** 2 + pick("V") ** 2) ** 0.5
            a = a.rename("WS")
        else:
            a = pick(args.var)
        a = a.load()
        d.close()
        return a

    # open each file and concat in time (per-file region subset keeps memory
    # small; avoids the dask dependency that open_mfdataset requires)
    parts = [load_one(f) for f in files]
    da = xr.concat(parts, dim="time") if len(parts) > 1 else parts[0]

    # keep only levels at/below the chosen top (pressure >= min_hpa: the upper
    # levels are near-empty stratosphere/mesosphere and just stretch the box),
    # then order surface->up so pseudo-height increases monotonically.
    mask = da["lev"].values >= args.min_hpa
    da = da.isel(lev=np.where(mask)[0]).sortby("lev", ascending=False)

    lon = da["lon"].values.astype("f8")
    lat = da["lat"].values.astype("f8")
    lev = da["lev"].values.astype("f8")          # pressure in hPa
    zkm = pressure_to_height(lev)
    times = da["time"].values

    os.makedirs(args.out, exist_ok=True)
    # per-variable .visit so multiple variables can coexist in one folder
    visit_path = os.path.join(args.out, f"{args.name}_{args.var}.visit")
    csv_path = os.path.join(args.out, "times.csv")

    names = []
    with open(csv_path, "w", newline="") as c:
        w = csv.writer(c)
        w.writerow(["index", "utc_time", "filename"])
        for i in range(da.sizes["time"]):
            cube = da.isel(time=i).values.astype("f8")   # (lev, lat, lon)
            cube = np.where(cube >= FILL, np.nan, cube)
            fn = f"{args.name}_{args.var}_{i:03d}.vtr"
            write_vtr(os.path.join(args.out, fn), lon, lat, zkm, cube)
            names.append(fn)
            tstr = str(times[i])[:19]
            w.writerow([i, tstr, fn])
            print(f"  [{i:02d}] {tstr}  {fn}")

    with open(visit_path, "w") as v:
        v.write("!NBLOCKS 1\n")
        for fn in names:
            v.write(os.path.abspath(os.path.join(args.out, fn)) + "\n")

    print(f"\nWrote {visit_path}  ({len(names)} timesteps)")
    print(f"grid: {len(lon)} lon x {len(lat)} lat x {len(lev)} levels"
          f"  | z: {zkm.min():.1f}..{zkm.max():.1f} km")
    print(f"Open in VisIt:  OpenDatabase(\"{visit_path}\")")


if __name__ == "__main__":
    main()
