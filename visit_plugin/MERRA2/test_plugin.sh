#!/usr/bin/env bash
PREFIX=/home/jhatch/visit-dev/visit3.4.0/build/_CPack_Packages/Linux/TGZ/visit3_4_0.linux-x86_64
VAH="$PREFIX/3.4.0/linux-x86_64"
NCLIB=/home/jhatch/ncloc/root/usr/lib/x86_64-linux-gnu

echo "=== where the build put the plugin libs ==="
ls -1 "$VAH/bin/plugins/databases/"*MERRA2* 2>&1

# copy them into the private plugin dir where VisIt always looks
PRIV="$HOME/.visit/3.4.0/linux-x86_64/plugins/databases"
mkdir -p "$PRIV"
cp "$VAH/bin/plugins/databases/"*MERRA2Database*.so "$PRIV/"
echo "=== copied into $PRIV ==="; ls -1 "$PRIV"

# also point VisIt at the build output dir, and make netcdf deps loadable
export VISITPLUGINDIR="$VAH/bin/plugins"
export LD_LIBRARY_PATH="$NCLIB:$VAH/lib:$LD_LIBRARY_PATH"

echo "=== visit -cli open test (timeout 150s) ==="
timeout 150 "$PREFIX/bin/visit" -cli -nowin -nosplash -s /tmp/test_plugin.py 2>&1 | grep -vE "^Running|^$" | tail -45
echo "exit=$?"
