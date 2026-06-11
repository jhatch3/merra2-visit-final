#!/usr/bin/env bash
# Pull netcdf's runtime dependency chain (hdf5, etc.) locally, no sudo.
cd ~/ncloc/debs || exit 1
PKGS=$(apt-cache depends --recurse --no-recommends --no-suggests \
         --no-conflicts --no-breaks --no-replaces --no-enhances libnetcdf19t64 2>/dev/null \
       | grep "^\w" | grep -vE "^(libc6|libgcc|libstdc|gcc)" | sort -u)
echo "=== packages to fetch ==="; echo $PKGS
apt-get download $PKGS 2>&1 | tail -4
echo "=== unpack all into ~/ncloc/root ==="
find . -maxdepth 1 -name '*.deb' -exec dpkg-deb -x {} /home/jhatch/ncloc/root \;
echo "=== hdf5 present now? ==="
find /home/jhatch/ncloc/root -name "libhdf5_serial.so*" -o -name "libhdf5_serial_hl.so*" 2>/dev/null | head
echo "=== curl/xml present? ==="
find /home/jhatch/ncloc/root -name "libcurl-gnutls.so*" -o -name "libxml2.so*" 2>/dev/null | head
