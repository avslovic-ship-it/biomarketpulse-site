"""BioMarket Pulse audio briefing + site bundle builder.

Usage:
  python3 pulse_audio.py --script script.txt --page pulse.html --date 2026-10-30 \
      --edition 41 --summary "One-line episode summary" --out site/ [--models DIR]

Produces in --out:
  index.html                     the dashboard with a "Listen" player added
  pulse-YYYY-MM-DD.mp3           today's episode (Kokoro, voice am_michael)
  feed.xml                       podcast RSS feed (existing feed read from the
                                 public GitHub repo, newest 30 episodes kept)
"""
import argparse, os, re, subprocess, urllib.request, html, datetime
from email.utils import format_datetime

SITE = "https://biomarketpulse.com"
RAW_FEED = "https://raw.githubusercontent.com/avslovic-ship-it/biomarketpulse-site/main/feed.xml"
VOICE, SPEED, GAP = "am_michael", 1.15, 0.35
KEEP = 30

ap = argparse.ArgumentParser()
for a in ["script", "page", "date", "edition", "summary", "out"]:
    ap.add_argument("--" + a, required=True)
ap.add_argument("--models", default=os.path.expanduser("~/kokoro"))
o = ap.parse_args()
os.makedirs(o.out, exist_ok=True)
d = datetime.date.fromisoformat(o.date)
mp3_name = f"pulse-{o.date}.mp3"
mp3_path = os.path.join(o.out, mp3_name)

# 1. Speech
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro(os.path.join(o.models, "kokoro-v1.0.onnx"), os.path.join(o.models, "voices-v1.0.bin"))
paras = [p.strip() for p in open(o.script, encoding="utf8").read().split("\n\n") if p.strip()]
chunks, sr = [], 24000
for p in paras:
    audio, sr = k.create(p, voice=VOICE, speed=SPEED, lang="en-us")
    chunks += [audio, np.zeros(int(sr * GAP), dtype=audio.dtype)]
wav = mp3_path[:-4] + ".wav"
sf.write(wav, np.concatenate(chunks), sr)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "44100",
                "-b:a", "64k", mp3_path], check=True)
os.remove(wav)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", mp3_path], capture_output=True, text=True).stdout)
size = os.path.getsize(mp3_path)
mmss = f"{int(dur // 60)}:{int(dur % 60):02d}"

# 2. Feed
pretty = d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")
pub = format_datetime(datetime.datetime(d.year, d.month, d.day, 10, 30, tzinfo=datetime.timezone.utc))
item = f"""    <item>
      <title>BioMarket Pulse — {html.escape(pretty)} (Edition {o.edition})</title>
      <description>{html.escape(o.summary)}</description>
      <enclosure url="{SITE}/{mp3_name}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="false">biomarket-pulse-{o.date}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{mmss}</itunes:duration>
      <link>{SITE}/</link>
    </item>"""
old_items = []
try:
    old = urllib.request.urlopen(RAW_FEED, timeout=20).read().decode("utf8")
    old_items = [i for i in re.findall(r"    <item>.*?</item>", old, re.S)
                 if f"biomarket-pulse-{o.date}<" not in i]
except Exception as e:
    print("No existing feed found (starting a new one):", e)
items = "\n".join([item] + old_items[: KEEP - 1])
feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>BioMarket Pulse</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>A two-minute daily briefing on the deals, science, regulation and markets moving biotech, pharma, synthetic biology, biocatalysis and agriculture.</description>
    <language>en-us</language>
    <itunes:author>BioMarket Pulse</itunes:author>
    <itunes:category text="Business"/>
    <itunes:category text="Science"/>
    <itunes:explicit>false</itunes:explicit>
    <lastBuildDate>{pub}</lastBuildDate>
{items}
  </channel>
</rss>
"""
open(os.path.join(o.out, "feed.xml"), "w", encoding="utf8").write(feed)

# 3. Page with player
page = open(o.page, encoding="utf8").read()
player = f"""
  <section class="listen-bar" aria-label="Audio briefing" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;margin:14px 0 4px;padding:12px 16px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink)">
    <div style="flex:1 1 220px;min-width:0">
      <div style="font-weight:600">Listen to today's briefing</div>
      <div style="color:var(--muted);font-size:.9em">{html.escape(pretty)} · {mmss} · <a href="{SITE}/feed.xml" style="color:var(--accent)">Podcast feed (RSS)</a></div>
    </div>
    <audio controls preload="none" src="{mp3_name}" style="flex:1 1 260px;max-width:100%;min-width:0"></audio>
  </section>
"""
page = re.sub(r'\s*<section class="listen-bar".*?</section>\s*', "\n", page, flags=re.S)
m = re.search(r'<header class="masthead">.*?</header>', page, re.S)
if not m:
    raise SystemExit("masthead not found; page left without player")
page = page[: m.end()] + player + page[m.end():]
open(os.path.join(o.out, "index.html"), "w", encoding="utf8").write(page)
print(f"OK {mp3_name} {mmss} {size} bytes; feed items: {1 + min(len(old_items), KEEP - 1)}")
