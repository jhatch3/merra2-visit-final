#!/usr/bin/env python3
"""
download_merra2.py  --  Download MERRA-2 3D pressure-level files (product
M2I3NPASM, "inst3_3d_asm_Np": 3-hourly, 42 pressure levels) from NASA GES DISC.

NASA Earthdata Login is REQUIRED. One-time setup:

  1. Make a free account:           https://urs.earthdata.nasa.gov/users/new
  2. Approve the GES DISC app:      log in, Applications -> Authorized Apps ->
                                    approve "NASA GESDISC DATA ARCHIVE"
  3. Create a ~/.netrc (Windows: C:\\Users\\<you>\\.netrc or _netrc) with:

         machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASS

     (chmod 600 on Unix; on Windows just keep it private.)

Then:
    python download_merra2.py --start 2023-09-05 --days 2 --out ./merra
    python download_merra2.py --start 2023-09-05 --days 2 --list   # preview only

Each daily file is ~1.2 GB and contains 8 timesteps (00,03,...,21 UTC), so even
1-2 days gives a usable time series. Files land in --out; feed them to
build_merra_series.py next.
"""

import argparse
import datetime as dt
import http.cookiejar
import os
import re
import urllib.request

PRODUCT = "M2I3NPASM.5.12.4"
ROOT = "https://goldsmr5.gesdisc.eosdis.nasa.gov/data/MERRA2/" + PRODUCT
FILE_RE_TMPL = r'MERRA2_\d+\.inst3_3d_asm_Np\.{date}\.nc4'


def make_opener():
    """Cookie-aware opener that authenticates via ~/.netrc against URS."""
    cj = http.cookiejar.CookieJar()
    # HTTPBasicAuth with netrc; urllib handles the URS redirect + cookie dance
    pwmgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    try:
        import netrc
        auth = netrc.netrc()
        user, _, pw = auth.authenticators("urs.earthdata.nasa.gov")
    except Exception:
        raise SystemExit("Could not read ~/.netrc entry for urs.earthdata.nasa.gov. "
                         "See the setup notes at the top of this script.")
    pwmgr.add_password(None, "https://urs.earthdata.nasa.gov", user, pw)
    opener = urllib.request.build_opener(
        urllib.request.HTTPBasicAuthHandler(pwmgr),
        urllib.request.HTTPCookieProcessor(cj),
    )
    return opener


def dir_url(day):
    return f"{ROOT}/{day:%Y}/{day:%m}/"


def find_file(opener, day):
    """Scrape the month directory listing for the file matching this date."""
    html = opener.open(dir_url(day), timeout=60).read().decode("utf-8", "replace")
    m = re.search(FILE_RE_TMPL.format(date=day.strftime("%Y%m%d")), html)
    return m.group(0) if m else None


def head_size(opener, url):
    req = urllib.request.Request(url, method="HEAD")
    with opener.open(req, timeout=60) as r:
        return int(r.headers.get("Content-Length", 0))


def download(opener, url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  skip (have)  {os.path.basename(dest)}")
        return
    tmp = dest + ".part"
    with opener.open(url, timeout=300) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {os.path.basename(dest)}  {done>>20}/{total>>20} MB"
                      f" ({100*done/total:4.1f}%)", end="", flush=True)
    os.replace(tmp, dest)
    print()


def main():
    ap = argparse.ArgumentParser(description="Download MERRA-2 3D daily files.")
    ap.add_argument("--start", required=True, help="start date YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=2, help="number of consecutive days")
    ap.add_argument("--out", default="./merra")
    ap.add_argument("--list", action="store_true", help="preview only, no download")
    args = ap.parse_args()

    start = dt.datetime.strptime(args.start, "%Y-%m-%d").date()
    days = [start + dt.timedelta(days=i) for i in range(args.days)]
    opener = make_opener()

    os.makedirs(args.out, exist_ok=True)
    total = 0
    for day in days:
        fn = find_file(opener, day)
        if not fn:
            print(f"  {day}: no file found (data may not exist for this date)")
            continue
        url = dir_url(day) + fn
        if args.list:
            sz = head_size(opener, url)
            total += sz
            print(f"  {fn}  {sz>>20} MB")
        else:
            download(opener, url, os.path.join(args.out, fn))

    if args.list:
        print(f"\nTotal: {total>>20} MB ({total/1e9:.2f} GB) across {len(days)} day(s)")
    else:
        print(f"\nDone. Next:  python build_merra_series.py --src {args.out} --var T "
              f"--lat-min 10 --lat-max 45 --lon-min -90 --lon-max -40")


if __name__ == "__main__":
    main()
