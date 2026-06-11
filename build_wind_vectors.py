#!/usr/bin/env python3
"""
build_wind_vectors.py  --  Format the MERRA-2 wind as a 3D VECTOR field so VisIt
can draw vector glyphs (and so particles can be advected through it).

Reads U, V (horizontal winds, m/s) and OMEGA (vertical pressure velocity, Pa/s),
derives the vertical velocity  w = -OMEGA * R * T / (p * g)  (m/s), and writes
one VTK RectilinearGrid (.vtr) per timestep with:
    point vector "wind"  = (u, v, w)
    point scalar "speed" = sqrt(u^2 + v^2)
plus merra_WIND.visit (time series).

Same region / level-cap / pressure->height conventions as build_merra_series.py.

Usage:
    python build_wind_vectors.py --src ./merra --lat-min 10 --lat-max 45 \
        --lon-min -90 --lon-max -40 --out ./vtr
"""

import argparse
import csv
import glob
import os

import numpy as np
import xarray as xr
import vtk
from vtk.util import numpy_support as nps

H_KM = 7.5
P0 = 1000.0
FILL = 1.0e14
R = 287.0
G = 9.81


def p2z(lev):
    return H_KM * np.log(P0 / np.asarray(lev, "f8"))


def load_var(files, name, args):
    parts = []
    for f in files:
        d = xr.open_dataset(f)
        a = d[name]
        if args.lat_min is not None:
            a = a.sel(lat=slice(args.lat_min, args.lat_max))
        if args.lon_min is not None:
            a = a.sel(lon=slice(args.lon_min, args.lon_max))
        parts.append(a.load())
        d.close()
    return xr.concat(parts, dim="time") if len(parts) > 1 else parts[0]


def write_vtr(path, lon, lat, z, u, v, w):
    """u,v,w shape (nz, ny, nx) -> rectilinear grid with vector 'wind' + 'speed'."""
    g = vtk.vtkRectilinearGrid()
    nx, ny, nz = len(lon), len(lat), len(z)
    g.SetDimensions(nx, ny, nz)
    g.SetXCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(lon, "f4")))
    g.SetYCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(lat, "f4")))
    g.SetZCoordinates(nps.numpy_to_vtk(np.ascontiguousarray(z, "f4")))
    # vector: stack components last, ravel so points are x-fastest
    vec = np.stack([u, v, w], axis=-1).astype("f4").reshape(-1, 3)
    va = nps.numpy_to_vtk(np.ascontiguousarray(vec), deep=1)
    va.SetName("wind")
    g.GetPointData().AddArray(va)
    spd = np.sqrt(u ** 2 + v ** 2).astype("f4").ravel(order="C")
    sa = nps.numpy_to_vtk(spd, deep=1)
    sa.SetName("speed")
    g.GetPointData().SetScalars(sa)
    w_ = vtk.vtkXMLRectilinearGridWriter()
    w_.SetFileName(path)
    w_.SetInputData(g)
    w_.SetCompressorTypeToZLib()
    w_.Write()


def main():
    ap = argparse.ArgumentParser(description="Format MERRA-2 wind as a vector field.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="./vtr")
    ap.add_argument("--lat-min", type=float, default=None)
    ap.add_argument("--lat-max", type=float, default=None)
    ap.add_argument("--lon-min", type=float, default=None)
    ap.add_argument("--lon-max", type=float, default=None)
    ap.add_argument("--min-hpa", type=float, default=100.0)
    ap.add_argument("--name", default="merra")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.nc4"))) or \
        sorted(glob.glob(os.path.join(args.src, "*.nc")))
    if not files:
        raise SystemExit(f"No .nc4/.nc files in {args.src}")

    print(f"Opening {len(files)} file(s) for U, V, OMEGA, T ...")
    U = load_var(files, "U", args)
    V = load_var(files, "V", args)
    OM = load_var(files, "OMEGA", args)
    T = load_var(files, "T", args)

    mask = U["lev"].values >= args.min_hpa
    idx = np.where(mask)[0]

    def filt(a):
        return a.isel(lev=idx).sortby("lev", ascending=False)

    U, V, OM, T = filt(U), filt(V), filt(OM), filt(T)
    lev = U["lev"].values.astype("f8")
    z = p2z(lev)
    lon = U["lon"].values.astype("f8")
    lat = U["lat"].values.astype("f8")
    times = U["time"].values

    uu = U.values.astype("f8")
    vv = V.values.astype("f8")
    oo = OM.values.astype("f8")
    tt = T.values.astype("f8")
    for arr in (uu, vv, oo, tt):
        arr[arr >= FILL] = np.nan
    # vertical velocity from omega (broadcast pressure over time,lev,lat,lon)
    p_pa = (lev * 100.0)[None, :, None, None]
    ww = -oo * R * tt / (p_pa * G)
    uu = np.nan_to_num(uu); vv = np.nan_to_num(vv); ww = np.nan_to_num(ww)

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "times.csv")
    names = []
    with open(csv_path, "w", newline="") as c:
        wcsv = csv.writer(c)
        wcsv.writerow(["index", "utc_time", "filename"])
        for i in range(uu.shape[0]):
            fn = f"{args.name}_WIND_{i:03d}.vtr"
            write_vtr(os.path.join(args.out, fn), lon, lat, z,
                      uu[i], vv[i], ww[i])
            names.append(fn)
            wcsv.writerow([i, str(times[i])[:19], fn])
            print(f"  [{i:02d}] {str(times[i])[:19]}  {fn}")

    visit_path = os.path.join(args.out, f"{args.name}_WIND.visit")
    with open(visit_path, "w") as vf:
        vf.write("!NBLOCKS 1\n")
        for fn in names:
            vf.write(os.path.abspath(os.path.join(args.out, fn)) + "\n")

    print(f"\nWrote {visit_path}  ({len(names)} timesteps)")
    print(f"grid: {len(lon)} x {len(lat)} x {len(z)}  | speed max ~ "
          f"{np.nanmax(np.sqrt(uu**2+vv**2)):.0f} m/s")


if __name__ == "__main__":
    main()
