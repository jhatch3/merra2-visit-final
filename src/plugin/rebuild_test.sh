#!/usr/bin/env bash
SRC=/mnt/c/Users/Justin/visit-isabel-final/visit_plugin/MERRA2
cp "$SRC/avtMERRA2FileFormat.C" /home/jhatch/merra2_plugin/
cp "$SRC/avtMERRA2FileFormat.h" /home/jhatch/merra2_plugin/
tr -d '\r' < "$SRC/wbuild.sh"      > /tmp/wbuild.sh
tr -d '\r' < "$SRC/test_plugin.sh" > /tmp/test_plugin.sh
tr -d '\r' < "$SRC/test_plugin.py" > /tmp/test_plugin.py
echo "########## BUILD ##########"
bash /tmp/wbuild.sh 2>&1 | tail -5
echo "########## TEST ##########"
bash /tmp/test_plugin.sh 2>&1 | grep -vE "^Running|^$" | tail -18
