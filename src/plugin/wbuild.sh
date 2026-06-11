#!/usr/bin/env bash
# Build the MERRA2 VisIt plugin in WSL against the local VisIt 3.4.0 dev install
# and the locally-unpacked NetCDF (no sudo).
VAH=/home/jhatch/visit-dev/visit3.4.0/build/_CPack_Packages/Linux/TGZ/visit3_4_0.linux-x86_64/3.4.0/linux-x86_64
CMAKE=/home/jhatch/visit-dev/cmake-3.24.3/bin/cmake
NCROOT=/home/jhatch/ncloc/root/usr
export VISITARCHHOME="$VAH"
export VISITPLUGININSTPRI="$HOME/.visit/3.4.0/linux-x86_64"
export VISITPLUGININSTPUB="$VAH/plugins"
export LD_LIBRARY_PATH="$VAH/lib:$NCROOT/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
mkdir -p "$VISITPLUGININSTPRI/plugins/databases"
cd /home/jhatch/merra2_plugin || { echo "no plugin dir"; exit 1; }

echo "===== xml2cmake ====="
"$VAH/bin/xml2cmake" -clobber MERRA2.xml > /dev/null 2>&1
echo "CMakeLists lines=$(wc -l < CMakeLists.txt)"

echo "===== cmake (local netcdf) ====="
rm -f CMakeCache.txt
"$CMAKE" -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_CXX_FLAGS="-I$NCROOT/include" \
         -DNETCDF_INCLUDE_DIR="$NCROOT/include" \
         -DNETCDF_LIBRARY="$NCROOT/lib/x86_64-linux-gnu/libnetcdf.so" . > cmake.log 2>&1
echo "cmake exit=$?"; tail -4 cmake.log

echo "===== make ====="
make > make.log 2>&1
echo "make exit=$?"
echo "--- last 50 lines of make.log ---"
tail -50 make.log
