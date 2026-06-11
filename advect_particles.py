#!/usr/bin/env python3
"""
advect_particles.py  --  Lagrangian particle ("flowing tracer") advection
through the MERRA-2 time-varying 3D wind field.

VisIt (this build) has no Streamline plot, so we compute the pathlines here:
seed massless tracers, then integrate their positions through the U/V/W wind
field across the 16 timesteps with RK2, interpolating the wind in space AND
time. Each integration step is written as a VTK point cloud (.vtp) with a
"speed" and "z_km" scalar, and tied together by particles.visit so VisIt
animates the drifting particles.

Wind -> coordinate rates (coords are lon-deg, lat-deg, alt-km):
    dlon/dt = u / (111320 * cos lat)   dlat/dt = v / 110540   dz/dt = w / 1000
Vertical velocity from omega:  w = -OMEGA * R * T / (p * g).

Usage:
    python advect_particles.py --src ./merra --lat-min 10 --lat-max 45 \
        --lon-min -90 --lon-max -40 --out ./vtp
"""

import argparse
import csv
import glob
import os

import numpy as np
import xarray as xr
import vtk
from vtk.util import numpy_support as nps
from scipy.interpolate import RegularGridInterpolator as RGI

H_KM = 7.5
P0 = 1000.0
FILL = 1.0e14
R = 287.0
G = 9.81
M_PER_DEG_LAT = 110540.0


def p2z(lev):
    return H_KM * np.log(P0 / np.asarray(lev, "f8"))


def load_var(files, name, a):
    parts = []
    for f in files:
        d = xr.open_dataset(f)
        x = d[name]
        if a.lat_min is not None:
            x = x.sel(lat=slice(a.lat_min, a.lat_max))
        if a.lon_min is not None:
            x = x.sel(lon=slice(a.lon_min, a.lon_max))
        parts.append(x.load())
        d.close()
    return xr.concat(parts, dim="time") if len(parts) > 1 else parts[0]


def write_vtp(path, pos, speed, zkm):
    pts = vtk.vtkPoints()
    pts.SetData(nps.numpy_to_vtk(np.ascontiguousarray(pos, "f4"), deep=1))
    poly = vtk.vtkPolyData()
    poly.SetPoints(pts)
    n = pos.shape[0]
    # one vertex cell per point so VisIt renders a point cloud
    conn = np.empty(2 * n, dtype=np.int64)
    conn[0::2] = 1
    conn[1::2] = np.arange(n)
    ca = vtk.vtkCellArray()
    ca.SetCells(n, nps.numpy_to_vtkIdTypeArray(conn, deep=1))
    poly.SetVerts(ca)
    sa = nps.numpy_to_vtk(np.ascontiguousarray(speed, "f4"), deep=1)
    sa.SetName("speed")
    poly.GetPointData().AddArray(sa)
    poly.GetPointData().SetScalars(sa)
    za = nps.numpy_to_vtk(np.ascontiguousarray(zkm, "f4"), deep=1)
    za.SetName("z_km")
    poly.GetPointData().AddArray(za)
    w = vtk.vtkXMLPolyDataWriter()
    w.SetFileName(path)
    w.SetInputData(poly)
    w.Write()


def main():
    ap = argparse.ArgumentParser(description="Advect tracer particles through MERRA-2 wind.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="./vtp")
    ap.add_argument("--lat-min", type=float, default=None)
    ap.add_argument("--lat-max", type=float, default=None)
    ap.add_argument("--lon-min", type=float, default=None)
    ap.add_argument("--lon-max", type=float, default=None)
    ap.add_argument("--min-hpa", type=float, default=150.0)
    ap.add_argument("--dt", type=float, default=1800.0, help="integration step (s)")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.nc4"))) or \
        sorted(glob.glob(os.path.join(args.src, "*.nc")))
    if not files:
        raise SystemExit(f"No .nc4/.nc files in {args.src}")

    print("Loading U, V, OMEGA, T ...")
    U = load_var(files, "U", args)
    V = load_var(files, "V", args)
    OM = load_var(files, "OMEGA", args)
    T = load_var(files, "T", args)

    idx = np.where(U["lev"].values >= args.min_hpa)[0]

    def filt(x):
        return x.isel(lev=idx).sortby("lev", ascending=False)

    U, V, OM, T = filt(U), filt(V), filt(OM), filt(T)
    lev = U["lev"].values.astype("f8")
    zc = p2z(lev)                                   # ascending km
    latc = U["lat"].values.astype("f8")
    lonc = U["lon"].values.astype("f8")
    times = U["time"].values
    nt = len(times)
    tc = np.arange(nt, dtype="f8") * 10800.0        # 3-hourly -> seconds

    uu = np.nan_to_num(U.values.astype("f8"))
    vv = np.nan_to_num(V.values.astype("f8"))
    oo = np.nan_to_num(OM.values.astype("f8"))
    tt = np.nan_to_num(T.values.astype("f8"), nan=250.0)
    p_pa = (lev * 100.0)[None, :, None, None]
    ww = -oo * R * tt / (p_pa * G)

    grid = (tc, zc, latc, lonc)
    ui = RGI(grid, uu, bounds_error=False, fill_value=0.0)
    vi = RGI(grid, vv, bounds_error=False, fill_value=0.0)
    wi = RGI(grid, ww, bounds_error=False, fill_value=0.0)

    # seed a grid of particles at two low/mid altitudes, inset from the edges
    lo, la = np.meshgrid(
        np.linspace(lonc.min() + 3, lonc.max() - 3, 28),
        np.linspace(latc.min() + 3, latc.max() - 3, 22),
    )
    seeds = []
    for z0 in (1.5, 5.0):
        seeds.append(np.column_stack([lo.ravel(), la.ravel(),
                                      np.full(lo.size, z0)]))
    pos = np.vstack(seeds)                           # (N,3): lon,lat,z
    N = pos.shape[0]
    print(f"{N} particles seeded; integrating {nt} snapshots ...")

    lon_lo, lon_hi = lonc.min(), lonc.max()
    lat_lo, lat_hi = latc.min(), latc.max()
    z_lo, z_hi = zc.min(), zc.max()

    def vel(t, p):
        tq = min(t, tc[-1])
        q = np.column_stack([np.full(N, tq), p[:, 2], p[:, 1], p[:, 0]])
        u = ui(q); v = vi(q); w = wi(q)
        dlon = u / (111320.0 * np.cos(np.radians(p[:, 1])))
        dlat = v / M_PER_DEG_LAT
        dz = w / 1000.0
        return np.column_stack([dlon, dlat, dz]), np.sqrt(u * u + v * v)

    os.makedirs(args.out, exist_ok=True)
    dt = args.dt
    nsteps = int(tc[-1] / dt)
    names, rows = [], []
    base = times[0]
    for k in range(nsteps + 1):
        t = k * dt
        _, spd = vel(t, pos)
        fn = f"particles_{k:03d}.vtp"
        write_vtp(os.path.join(args.out, fn), pos, spd, pos[:, 2].copy())
        names.append(fn)
        stamp = str(base + np.timedelta64(int(t), "s"))[:19]
        rows.append((k, stamp, fn))
        # RK2 step
        k1, _ = vel(t, pos)
        k2, _ = vel(t + dt, pos + dt * k1)
        pos = pos + 0.5 * dt * (k1 + k2)
        np.clip(pos[:, 0], lon_lo, lon_hi, out=pos[:, 0])
        np.clip(pos[:, 1], lat_lo, lat_hi, out=pos[:, 1])
        np.clip(pos[:, 2], z_lo, z_hi, out=pos[:, 2])
        if k % 10 == 0:
            print(f"  step {k:03d}/{nsteps}  {stamp}")

    with open(os.path.join(args.out, "particles.visit"), "w") as vf:
        vf.write("!NBLOCKS 1\n")
        for fn in names:
            vf.write(os.path.abspath(os.path.join(args.out, fn)) + "\n")
    with open(os.path.join(args.out, "times.csv"), "w", newline="") as c:
        wc = csv.writer(c)
        wc.writerow(["index", "utc_time", "filename"])
        wc.writerows(rows)

    print(f"\nWrote {len(names)} particle frames to {args.out}")
    print(f"Open in VisIt: OpenDatabase(\"{os.path.join(args.out, 'particles.visit')}\")")


if __name__ == "__main__":
    main()
