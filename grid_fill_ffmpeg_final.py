import os, shutil, subprocess, sys

# ---- controls ----
INPUT  = os.path.expanduser("~/Desktop/video.mp4")
OUTPUT = os.path.expanduser("~/Desktop/collage_fill.mp4")
ROWS, COLS = 4, 4            # grid size
FILL_DURATION = 4.0          # seconds until all squares are on

# ---- ffmpeg binary ----
CANDIDATES = [
    os.path.expanduser("~/ai-env/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"),
    shutil.which("ffmpeg")
]
FFMPEG = next((p for p in CANDIDATES if p and os.path.exists(p)), None)
if not FFMPEG:
    sys.exit("FFmpeg not found (try: brew install ffmpeg)")
if not os.path.isfile(INPUT):
    sys.exit(f"Input not found: {INPUT}")

N = ROWS * COLS
step = FILL_DURATION / N

# 0) bg: make a black stream the SAME size as the input
# use the input to carry size through format->geq (black)
fc = ["[0:v]format=rgba,geq=r=0:g=0:b=0[bg]"]

# 1) split source
fc.append(f"[0:v]split={N}" + "".join(f"[s{i}]" for i in range(N)))

# 2) crop tiles
idx = 0
for r in range(ROWS):
    for c in range(COLS):
        fc.append(
            f"[s{idx}]crop=w=iw/{COLS}:h=ih/{ROWS}:x={c}*iw/{COLS}:y={r}*ih/{ROWS}[t{idx}]"
        )
        idx += 1

# 3) overlay tiles onto bg with proper quoting around enable=
prev = "[bg]"
idx = 0
for r in range(ROWS):
    for c in range(COLS):
        delay = idx * step
        x = f"{c}*main_w/{COLS}"
        y = f"{r}*main_h/{ROWS}"
        out = f"[v{idx+1}]" if idx < N - 1 else "[vfinal]"
        # NOTE: quote the expression so the comma doesn't break parsing
        fc.append(f"{prev}[t{idx}]overlay=x={x}:y={y}:enable='gte(t\\,{delay})'{out}")
        prev = out
        idx += 1

filter_complex = ";".join(fc)

cmd = [
    FFMPEG, "-y",
    "-i", INPUT,
    "-filter_complex", filter_complex,
    "-map", "[vfinal]",
    "-map", "0:a?",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-movflags", "+faststart",
    OUTPUT,
]

print("Running FFmpeg…")
subprocess.run(cmd, check=True)
print(f"Done! Saved to: {OUTPUT}")

