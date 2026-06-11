#!/usr/bin/env bash
PREFIX=/home/jhatch/visit-dev/visit3.4.0/build/_CPack_Packages/Linux/TGZ/visit3_4_0.linux-x86_64
VAH="$PREFIX/3.4.0/linux-x86_64"
NCLIB=/home/jhatch/ncloc/root/usr/lib/x86_64-linux-gnu
export VISITPLUGINDIR="$VAH/bin/plugins"
export LD_LIBRARY_PATH="$NCLIB:$VAH/lib:$LD_LIBRARY_PATH"
FRAMES=/mnt/c/Users/Justin/visit-isabel-final/frames_plugin
mkdir -p "$FRAMES"
rm -f "$FRAMES"/*.png
tr -d '\r' < /mnt/c/Users/Justin/visit-isabel-final/visit_plugin/MERRA2/make_plugin_movies.py > /tmp/make_plugin_movies.py
echo "=== rendering plugin movies (software mode, be patient) ==="
timeout 2400 "$PREFIX/bin/visit" -cli -nowin -nosplash -s /tmp/make_plugin_movies.py 2>&1 \
  | grep -iE "error|exception|abnormal|PLUGIN_MOVIES_DONE" | tail -25
echo "visit exit=$?"
echo "=== frames rendered per movie ==="
ls "$FRAMES"/ 2>/dev/null | sed 's/_[0-9]*\.png$//' | sort | uniq -c
