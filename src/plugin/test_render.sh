#!/usr/bin/env bash
PREFIX=/home/jhatch/visit-dev/visit3.4.0/build/_CPack_Packages/Linux/TGZ/visit3_4_0.linux-x86_64
VAH="$PREFIX/3.4.0/linux-x86_64"
NCLIB=/home/jhatch/ncloc/root/usr/lib/x86_64-linux-gnu
export VISITPLUGINDIR="$VAH/bin/plugins"
export LD_LIBRARY_PATH="$NCLIB:$VAH/lib:$LD_LIBRARY_PATH"
rm -f /tmp/plugin_render_test_*.png
echo "=== render test (timeout 150s) ==="
timeout 150 "$PREFIX/bin/visit" -cli -nowin -nosplash -s /tmp/test_render.py 2>&1 | grep -ivE "^Running|^$" | tail -25
echo "visit exit=$?"
echo "=== output png? ==="
ls -la /tmp/plugin_render_test_*.png 2>&1
