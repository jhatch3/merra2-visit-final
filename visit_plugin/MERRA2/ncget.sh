#!/usr/bin/env bash
# Get NetCDF dev locally without sudo: download the .deb(s) and unpack into ~/ncloc/root
mkdir -p ~/ncloc/debs ~/ncloc/root
cd ~/ncloc/debs || exit 1

echo "=== deps of libnetcdf-dev ==="
apt-cache depends libnetcdf-dev 2>/dev/null | grep -i "depends"

echo "=== download libnetcdf-dev (no sudo) ==="
apt-get download libnetcdf-dev 2>&1 | tail -3

LIBPKG=$(apt-cache depends libnetcdf-dev 2>/dev/null | grep -oE 'libnetcdf[0-9]+' | head -1)
echo "runtime lib package: $LIBPKG"
[ -n "$LIBPKG" ] && apt-get download "$LIBPKG" 2>&1 | tail -3

echo "=== debs downloaded ==="; ls -la *.deb 2>&1

echo "=== unpack into ~/ncloc/root ==="
for d in *.deb; do dpkg-deb -x "$d" ~/ncloc/root 2>&1; done
echo "header:"; find ~/ncloc/root -name netcdf.h 2>/dev/null
echo "lib:";    find ~/ncloc/root -name "libnetcdf.so*" 2>/dev/null

echo "=== system hdf5 present (runtime dep)? ==="
ls /usr/lib/x86_64-linux-gnu/libhdf5*.so* 2>/dev/null | head -2 || echo "no system hdf5"
