# MERRA-2 Atmospheric Visualization — Final Project

Justin Hatch · SCI 410 Scientific Visualization

**Full project (code + all videos): __REPO_URL__**

## What it does

Takes real NASA weather data (MERRA-2) and turns the 3D atmosphere over the
Atlantic during a storm in early September 2023 into temperature, moisture, and
wind videos in VisIt. I get the data into VisIt two ways: a Python **formatter**
that pre-converts the files, and a C++ **VisIt plugin** that reads the raw NASA
files directly. 15 videos total.

MERRA-2 is NASA's global reanalysis — temperature, wind, and humidity on 42
pressure levels (42 layers going up through the atmosphere), every 3 hours. I
used a box over the western Atlantic (10–45 N, 90–40 W) for two days, so 16 time
steps. The catch is the vertical axis comes as pressure, not height, so the
formatter converts pressure to height (`z = 7.5 * ln(1000 / pressure)`) — without
that the atmosphere renders as a flat pancake.

## What each file does

Pipeline (plain Python):

- `download_merra2.py` — downloads the raw MERRA-2 pressure-level files (needs a
  free NASA Earthdata login)
- `build_merra_series.py` — **the formatter.** Pulls one variable over my region,
  stacks the 16 time steps, converts pressure→height, and writes a VTK `.vtr`
  series plus a `.visit` index and a `times.csv` of the real timestamps
- `build_wind_vectors.py` — builds the 3D wind vector field from U, V, and OMEGA
  (vertical pressure velocity)
- `advect_particles.py` — my own Lagrangian particle solver (this VisIt build has
  no streamline plot, so I compute the pathlines myself)
- `_make_test_merra.py` — writes a small synthetic MERRA-shaped file for testing
  the formatter without the 1.2 GB download

VisIt movie scripts (`visit -cli -nowin -s <file>`):

- `make_movies_merra.py` — the six temperature/moisture/wind cross-section movies
  (m1–m6: horizontal slices, vertical slices, and the orbiting 3-slice 3D view)
- `make_flow_merra.py` — the particle flow video
- `make_flow_quad_merra.py` — same particles shown in four panels at once
- `make_particles_merra.py` — wind vector-glyph movies
- `make_volume_merra.py` — the moisture volume render (must run windowed, see below)

Plugin:

- `visit_plugin/MERRA2/` — a C++ database reader (XML descriptor + the
  `avtMERRA2FileFormat` reader) that opens the raw `.nc4` in VisIt and does the
  pressure→height step inside `GetMesh`. It reads the whole global grid
  (~8.7M points) instead of the formatter's Atlantic slice (~144k), about **61×
  more of the map**, with no intermediate files.

## How to run

1. `python download_merra2.py …` to get the data (or `_make_test_merra.py` for a
   quick test file).
2. Format it once per variable, e.g.
   `python build_merra_series.py --var T --lat-min 10 --lat-max 45 --lon-min -90 --lon-max -40 --out ./vtr`
   then again for QV and WS. Run `build_wind_vectors.py` and `advect_particles.py`
   for the flow videos.
3. Render: `visit -cli -nowin -s make_movies_merra.py` (and the other `make_*.py`).
   The volume render has to run **windowed** so it uses the GPU —
   `visit -cli -s make_volume_merra.py` — the headless software renderer is too slow.
4. Encode the PNG frames to mp4 with ffmpeg.

Generate the `.vtr` data with the formatter (step 2) before running the movie scripts.

## Example datasets

- **Real data:** MERRA-2 `M2I3NPASM` (inst3_3d_asm_Np), 5–6 Sep 2023, 10–45 N /
  90–40 W, 16 time steps, from the NASA GES DISC archive (Earthdata login required).
- **Test data:** `_make_test_merra.py` generates a small synthetic file with the
  same shape as a MERRA-2 file, so I could test the formatter and scripts without
  pulling down the full 1.2 GB download.

## Videos

Highlights — the particle simulations and the moisture volume render:

| Preview | Video |
|---|---|
| [![particles following the wind](thumbs/flow.png)](merra_flow_particles.mp4) | **[Particles following the wind](merra_flow_particles.mp4)** — 1,232 particles let loose and tracked as they drift |
| [![four views of the particles](thumbs/quad.png)](merra_flow_quad.mp4) | **[Same particles, four views at once](merra_flow_quad.mp4)** — two side views, a top-down map, and the 3D corner |
| [![moisture volume](thumbs/vol.png)](merra_vol_qv.mp4) | **[Volume render of the moisture](merra_vol_qv.mp4)** — water vapor as a see-through cloud |

**Formatter vs plugin.** The same cross-sections done both ways — "pre" is the
Python formatter, "post" is the plugin doing it inside VisIt. The plugin videos
cover the whole globe; the formatter ones are the Atlantic slice.

| What it shows | Pre (Python formatter) | Post (the plugin) |
|---|---|---|
| Temperature, map | [watch](merra_m1_time.mp4) | [watch](merra_plugin_temp_map.mp4) |
| Temperature, vertical | [watch](merra_m2_vslice.mp4) | [watch](merra_plugin_temp_vert.mp4) |
| Temperature, 3D | [watch](merra_m3_orbit.mp4) | [watch](merra_plugin_temp_3d.mp4) |
| Moisture, map | [watch](merra_m4_qv_time.mp4) | [watch](merra_plugin_humidity_map.mp4) |
| Moisture, vertical | [watch](merra_m5_qv_vert.mp4) | [watch](merra_plugin_humidity_vert.mp4) |
| Wind speed | [watch](merra_m6_ws_time.mp4) | [watch](merra_plugin_wind_map.mp4) |

## Challenges I ran into

- **The volume render crashed the engine.** My formatter writes NaN for missing
  and below-ground values, and VisIt's volume resampler can't handle NaN, so the
  engine just died with no useful error. Fix: a copy of the field with NaNs
  replaced by zero.
- **The volume render was unusably slow.** Headless mode has no GPU, so VisIt
  falls back to a software ray caster — two or three minutes per frame. Running it
  in a real window on the GPU and screen-capturing got it to ~13 s/frame.
- **The volume settings from older examples didn't exist.** VisIt 3.4 has no
  `rendererType`/`numSamples` on the volume, and setting them killed the script
  silently. Had to print the real attribute list to find the right ones.
- **The four-panel labels stacked on top of each other.** VisIt's text annotations
  are global to the whole layout, not per window, so every label showed in every
  panel. I added the four labels afterward with ffmpeg.
- **Everything rendered sideways at first** — altitude ran left-to-right. Had to
  set the camera up-vector to the height axis on every video.
- Smaller stuff: a color table I picked (`ocean`) didn't exist, one vector setting
  was `colorByMagnitude` not `colorByMag`, the `.visit` files need absolute paths,
  and `SaveWindow` appends frames so I clear the folder before each render.

## Time spent

About **36 hours total** — roughly 22 in VisIt (including building and testing the
plugin) and 14 on the Python side (downloading data, the formatter, the wind and
particle code, and writing this up).

Data: NASA GMAO MERRA-2, from the GES DISC archive.
