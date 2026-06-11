import numpy as np, netCDF4 as nc, os
os.makedirs("merra", exist_ok=True)
# MERRA-2-like structure: time, lev(pressure hPa), lat, lon
nt, nlev, nlat, nlon = 4, 12, 60, 90
levs = np.array([1000,925,850,700,600,500,400,300,250,200,150,100],"f4")[:nlev]
lat = np.linspace(10,45,nlat).astype("f4")
lon = np.linspace(-90,-40,nlon).astype("f4")
f = nc.Dataset("merra/MERRA2_400.inst3_3d_asm_Np.20230906.nc4","w")
f.createDimension("time",nt); f.createDimension("lev",nlev)
f.createDimension("lat",nlat); f.createDimension("lon",nlon)
vt=f.createVariable("time","f8",("time",)); vt.units="minutes since 2023-09-06 00:00:00"; vt[:]=np.arange(nt)*180
vl=f.createVariable("lev","f4",("lev",)); vl.units="hPa"; vl[:]=levs
va=f.createVariable("lat","f4",("lat",)); va[:]=lat
vo=f.createVariable("lon","f4",("lon",)); vo[:]=lon
T=f.createVariable("T","f4",("time","lev","lat","lon",)); T.units="K"
LO,LA=np.meshgrid(lon,lat)
for t in range(nt):
    cx=-75+5*t; cy=20+3*t   # a warm-core "storm" drifting NE over time
    for k,p in enumerate(levs):
        base=288-0.05*(7.5*np.log(1000/p))*10   # cooler aloft
        warm=8*np.exp(-((LO-cx)**2+(LA-cy)**2)/12)*np.exp(-7.5*np.log(1000/p)/8)
        T[t,k]=base+warm
f.close(); print("wrote synthetic MERRA-2 file: merra/MERRA2_400.inst3_3d_asm_Np.20230906.nc4")
