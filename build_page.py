"""Assemble the trimmed payload, write the dashboard HTML and the CSV exports."""
import json, os, csv

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "deep.json"), encoding="utf-8"))
T = json.load(open(os.path.join(HERE, "tech.json"), encoding="utf-8"))
IDX = json.load(open(os.path.join(HERE, "track_index.json"), encoding="utf-8"))

# ----------------------------------------------------------------- payload
P = {k: D[k] for k in (
    "window", "totals", "by_year", "clock", "hour_signature", "skip_by_year",
    "shuffle_by_year", "sessions", "session_by_year", "platform_by_year", "abroad",
    "seasonality", "day_parts", "recent_window", "playlists",
    "love_kinds", "love_total", "rediscovery_buckets", "retention", "monthly",
    "skip_strict_by_year", "session_styles", "eras", "reason_start_by_year",
    "reason_start_labels", "saved_total", "saved_gap", "saved_examples",
    "loved_not_saved_total", "search", "repeat_loop_tracks")}
P.update({
    "generated": D["generated"][:10],
    "artist_skip_high": D["artist_skip"][:14],
    "artist_skip_low": D["artist_skip"][-14:][::-1],
    "longest_sessions": D["longest_sessions"][:12],
    "session_openers": D["session_openers"][:12],
    "completion_low": D["completion_low"][:14],
    "lifers": D["lifers"][:12], "flares": D["flares"][:12],
    "top_tracks": D["top_tracks"][:40],
    "first_encounters": D["first_encounters"][:12],
    "slow_burns": D["slow_burns"][:10], "instant_hits": D["instant_hits"][:10],
    "rising_tracks": D["rising_tracks"][:16], "rising_artists": D["rising_artists"][:12],
    "recent_top": D["recent_top"][:16],
    "love_arcs": D["love_arcs"][:60],
    "love_slowest": D["love_slowest"], "love_fastest": D["love_fastest"], "love_burst": D["love_burst"],
    "repeat_loops": D["repeat_loops"][:24],
    "rediscovery": D["rediscovery"][:40],
    "albums_top": D["albums_top"][:16], "albums_inside": D["albums_inside"][:16],
    "breadth": D["breadth"][:16],
    "loved_not_saved": D["loved_not_saved"][:24],
})

inf = T.get("inferences", [])
def pretty(tag):
    return (tag.replace("1P_Custom_", "").replace("[Advertiser-Restricted]", "")
            .replace("[Advertiser-Specific]", "").replace("_", " ").strip())
P["inferences_1p"] = [pretty(i) for i in inf if i.startswith("1P_Custom")
                      and "ArtistAffinity" not in i][:24]
brands = sorted({i.split("_")[1].strip() for i in inf if i.startswith("2P_") and len(i.split("_")) > 1})
P["inference_brands"] = [b for b in brands if b and len(b) < 40][:24]
P["inference_artist_affinities"] = sum(1 for i in inf if "ArtistAffinity" in i)

# wrapped: name the tracks we can
wr = T.get("wrapped2025", {}) or {}
wtracks = []
for t in ((wr.get("topTracks") or {}).get("topTracks") or [])[:10]:
    m = IDX.get(t.get("trackUri"))
    wtracks.append({"track": m[0] if m else "(not in history)", "artist": m[1] if m else "",
                    "count": t.get("count"), "hours": round((t.get("msPlayed") or 0) / 3600000, 1)})
ta = (wr.get("topArtists") or {})
P["wrapped"] = {
    "hours": round(((wr.get("yearlyMetrics") or {}).get("totalMsListened") or 0) / 3600000),
    "unique_artists": ta.get("numUniqueArtists"),
    "top_fan_pct": round((ta.get("topNPercentileFan") or 0) * 100, 2),
    "genres": (wr.get("topGenres") or {}).get("totalNumGenres"),
    "listening_age": (wr.get("listeningAge") or {}).get("listeningAge"),
    "tracks": wtracks,
}
P["taste_identity"] = T.get("taste_identity", "")
P["foreign_days"] = D.get("foreign_days", [])

P["tech"] = {
    "routes": T["routes"][:8], "routes_window": T.get("routes_window"),
    "discovered": T["discovered"], "os_versions": T["os_versions"],
    "lyrics": T["lyrics"], "car": {k: v for k, v in T["car"].items() if k != "days"},
    "search_top": T["search_top"][:22], "search_count": T["search_count"],
    "inference_count": T.get("inference_count"), "library": T.get("library", {}),
    "merged_from": T.get("merged_from", []), "health": T.get("health", {}),
    "on_repeat_joined": T.get("on_repeat_joined", []), "on_repeat_snapshots": T.get("on_repeat_snapshots"),
    "daylist_titles": T.get("daylist_titles", []),
}
payload = json.dumps(P, ensure_ascii=False, separators=(",", ":"))

# ----------------------------------------------------------------- CSVs
CSV = os.path.join(HERE, "csv")
os.makedirs(CSV, exist_ok=True)
def wcsv(name, rows, drop=("spark", "uri", "opening")):
    if not rows:
        return
    keys = [k for k in rows[0].keys() if k not in drop]
    with open(os.path.join(CSV, name), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                        for k, v in r.items() if k in keys})
wcsv("top-tracks.csv", D["top_tracks"])
wcsv("love-arcs.csv", D["love_arcs"])
wcsv("repeat-loops.csv", D["repeat_loops"])
wcsv("rediscovery-queue.csv", D["rediscovery"])
wcsv("monthly.csv", D["monthly"])
wcsv("discovery-retention.csv", D["retention"])
wcsv("session-styles.csv", D["session_styles"])
wcsv("taste-eras.csv", [{"year": e["year"], "hours": e["hours"],
                         **{f"artist_{i+1}": a["artist"] for i, a in enumerate(e["top"])}} for e in D["eras"]])
wcsv("albums.csv", D["albums_top"])
wcsv("playlists.csv", D["playlists"])
wcsv("loved-not-saved.csv", D["loved_not_saved"])
wcsv("artist-arcs.csv", D["artist_arcs"])
wcsv("skip-by-year.csv", D["skip_strict_by_year"])
csv_files = sorted(os.listdir(CSV))

HTML = r"""<title>The Listening Machine</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  color-scheme: light;
  --ground:#EDECE6; --surface:#FAF9F5; --sunk:#E4E2DA;
  --ink:#16151B; --ink-2:#413E4B; --muted:#6C6879;
  --line:#D6D3CA; --line-2:#BFBBB0;
  --accent:#4C3A8C; --accent-soft:#EDE9F8;
  --warm:#A8452C; --cool:#2F6B66;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4;
  --q0:#F1EFF8; --q1:#DED6F1; --q2:#C6B9E7; --q3:#AB99DA;
  --q4:#8E76C9; --q5:#7159B3; --q6:#573F99; --q7:#3E2B77;
  --shadow:0 1px 2px rgba(22,21,27,.06),0 8px 24px rgba(22,21,27,.05);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --ground:#121116; --surface:#1B1A21; --sunk:#24222C;
    --ink:#ECEAF2; --ink-2:#C3BFCE; --muted:#918BA0;
    --line:#2E2B37; --line-2:#433E50;
    --accent:#A392E4; --accent-soft:#251F3B;
    --warm:#E08A70; --cool:#6FAAA4;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
    --q0:#1E1C27; --q1:#292440; --q2:#372F5A; --q3:#483C77;
    --q4:#5C4C95; --q5:#7361B2; --q6:#8F7ECD; --q7:#B3A4E6;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --ground:#121116; --surface:#1B1A21; --sunk:#24222C;
  --ink:#ECEAF2; --ink-2:#C3BFCE; --muted:#918BA0;
  --line:#2E2B37; --line-2:#433E50;
  --accent:#A392E4; --accent-soft:#251F3B;
  --warm:#E08A70; --cool:#6FAAA4;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
  --q0:#1E1C27; --q1:#292440; --q2:#372F5A; --q3:#483C77;
  --q4:#5C4C95; --q5:#7361B2; --q6:#8F7ECD; --q7:#B3A4E6;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.mono{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
h1,h2,h3,h4{font-family:"Bricolage Grotesque","IBM Plex Sans",system-ui,sans-serif;
  font-weight:700;letter-spacing:-.02em;text-wrap:balance;margin:0}
.wrap{max-width:1120px;margin:0 auto;padding:0 32px}
@media(max-width:720px){.wrap{padding:0 18px}}

.plate{border-bottom:1px solid var(--line);background:var(--surface)}
.plate .wrap{display:flex;flex-wrap:wrap;gap:20px;align-items:flex-end;justify-content:space-between;padding-top:22px;padding-bottom:18px}
.mark{display:flex;align-items:center;gap:11px}
.mark svg{display:block;flex:none}
.mark .nm{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}
.mark .nm b{display:block;font-family:"Bricolage Grotesque",sans-serif;font-size:17px;letter-spacing:-.01em;text-transform:none;color:var(--ink);font-weight:700}
.span{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--muted);text-align:right;line-height:1.8}
.span b{color:var(--ink-2);font-weight:600}

/* tab bar */
.tabs{position:sticky;top:0;z-index:20;background:var(--surface);border-bottom:1px solid var(--line)}
.tabs .wrap{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;padding-top:0;padding-bottom:0}
.tabs .wrap::-webkit-scrollbar{display:none}
.tabs button{font:inherit;font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);background:none;border:none;border-bottom:2px solid transparent;
  padding:13px 13px 11px;cursor:pointer;white-space:nowrap}
.tabs button:hover{color:var(--ink)}
.tabs button[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
.tab{display:none}.tab.on{display:block}

header.top{padding:44px 0 36px}
.kicker{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);margin:0 0 18px}
h1{font-size:clamp(32px,5.2vw,58px);line-height:1.02;max-width:20ch;font-weight:800}
h1 em{font-style:normal;color:var(--accent)}
.lede{max-width:64ch;color:var(--ink-2);font-size:clamp(15.5px,1.5vw,17.5px);margin:22px 0 0}
.lede b{color:var(--ink);font-weight:600}
.readout{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden;margin-top:30px}
@media(max-width:820px){.readout{grid-template-columns:repeat(2,1fr)}}
.ro{background:var(--surface);padding:15px 16px 13px}
.ro .v{font-family:"IBM Plex Mono",monospace;font-size:clamp(20px,2.6vw,27px);font-weight:600;letter-spacing:-.02em;line-height:1.1}
.ro .l{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin-top:7px}

section{padding:44px 0;border-top:1px solid var(--line)}
.tab section:first-child{border-top:none}
.shead{margin-bottom:24px;max-width:74ch}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.19em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;gap:9px;margin-bottom:13px}
.eyebrow::after{content:"";flex:1;height:1px;background:var(--line)}
h2{font-size:clamp(22px,3vw,32px);line-height:1.14}
.sub{color:var(--ink-2);margin:12px 0 0;max-width:66ch}
.sub b{color:var(--ink);font-weight:600}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:22px;box-shadow:var(--shadow)}
.panel h3{font-size:15px;margin-bottom:4px}
.scroll{overflow-x:auto;padding-bottom:4px}
svg.chart{display:block;height:auto;max-width:100%}
.cap{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);margin-top:12px;line-height:1.7}
.cap b{color:var(--ink-2);font-weight:600}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
@media(max-width:880px){.grid2,.grid3{grid-template-columns:1fr}.grid4{grid-template-columns:1fr 1fr}}
.mt{margin-top:20px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);font-weight:500;padding:0 10px 9px 0;border-bottom:1px solid var(--line-2)}
td{padding:8px 10px 8px 0;border-bottom:1px solid var(--line);vertical-align:baseline}
tr:last-child td{border-bottom:none}
td.n{font-family:"IBM Plex Mono",monospace;text-align:right;white-space:nowrap;font-size:12.5px}
td.who{color:var(--muted);font-size:12.5px}
.bar-cell{position:relative;min-width:76px}
.bar-cell i{position:absolute;left:0;top:50%;transform:translateY(-50%);height:9px;border-radius:0 2px 2px 0;display:block}
.kind{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:2px;background:var(--sunk);color:var(--ink-2);white-space:nowrap}
.kind.k1{background:var(--accent-soft);color:var(--accent)}
.kind.k4{color:var(--warm)}
.spark{display:inline-block;vertical-align:middle}
.controls-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px}
.seg{display:flex;border:1px solid var(--line-2);border-radius:3px;overflow:hidden;flex-wrap:wrap}
.seg button{font:inherit;font-size:12px;padding:5px 11px;background:none;border:none;cursor:pointer;color:var(--ink-2);border-right:1px solid var(--line-2)}
.seg button:last-child{border-right:none}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--surface);font-weight:600}
input[type=search]{flex:1;min-width:170px;background:var(--sunk);color:var(--ink);border:1px solid var(--line-2);border-radius:3px;padding:6px 10px;font:inherit;font-size:13px}
input[type=search]::placeholder{color:var(--muted)}
.enc-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
@media(max-width:880px){.enc-grid{grid-template-columns:1fr}}
.enc{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:20px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:14px}
.enc-head{display:flex;justify-content:space-between;gap:14px;align-items:baseline}
.enc-head .t{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;font-size:16.5px;letter-spacing:-.01em;line-height:1.25}
.enc-head .a{color:var(--muted);font-size:12.5px;margin-top:3px}
.enc-head .tot{font-family:"IBM Plex Mono",monospace;font-size:20px;font-weight:600;color:var(--accent);white-space:nowrap;line-height:1}
.enc-head .tot small{display:block;font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);font-weight:500;margin-top:4px;text-align:right}
.opens{display:grid;grid-template-columns:auto 1fr auto;gap:0 12px;font-family:"IBM Plex Mono",monospace;font-size:11.5px}
.opens .row{display:contents}
.opens .row>*{padding:6px 0;border-top:1px dashed var(--line)}
.opens .row:first-child>*{border-top:none}
.opens .ix{color:var(--accent);font-weight:600}
.opens .wh{color:var(--ink-2)}
.opens .dv{color:var(--muted);text-align:right;white-space:nowrap}
.enc-foot{font-size:12.5px;color:var(--ink-2);border-top:1px solid var(--line);padding-top:12px}
.enc-foot b{font-family:"IBM Plex Mono",monospace;color:var(--ink);font-weight:600}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:16px 18px}
.stat .v{font-family:"IBM Plex Mono",monospace;font-size:24px;font-weight:600;letter-spacing:-.02em;line-height:1.1}
.stat .l{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin-top:7px}
.stat .d{font-size:12.5px;color:var(--ink-2);margin-top:8px;line-height:1.5}
.pillrow{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}
.pill{font-family:"IBM Plex Mono",monospace;font-size:11px;padding:3px 9px;border-radius:2px;border:1px solid var(--line-2);color:var(--ink-2);background:var(--sunk)}
.note{border-left:2px solid var(--accent);background:var(--accent-soft);padding:14px 18px;border-radius:0 3px 3px 0;margin-top:18px;font-size:13.5px;color:var(--ink-2)}
.note b{color:var(--ink)}
.warnnote{border-left-color:var(--warm);background:transparent;border:1px solid var(--line);border-left:2px solid var(--warm)}
.quote{font-family:"Bricolage Grotesque",sans-serif;font-size:17px;line-height:1.5;color:var(--ink);font-weight:500;max-width:70ch}
.quote b{font-weight:700;color:var(--accent)}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:14px;font-size:12px;color:var(--ink-2)}
.legend span{display:flex;align-items:center;gap:7px}
.sw{width:11px;height:11px;border-radius:2px;flex:none;display:inline-block}
.lin{display:grid;grid-template-columns:auto 1fr;gap:0 22px}
.lin .rail{position:relative;width:11px}
.lin .rail::before{content:"";position:absolute;left:5px;top:6px;bottom:6px;width:1px;background:var(--line-2)}
.lin .dot{position:absolute;left:0;width:11px;height:11px;border-radius:50%;background:var(--surface);border:2px solid var(--line-2)}
.lin .dot.now{border-color:var(--accent);background:var(--accent)}
.lincard{padding:0 0 26px}
.lincard h4{margin:0;font-size:17px}
.lincard .when{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-top:4px}
.lincard p{margin:9px 0 0;font-size:13.5px;color:var(--ink-2);max-width:62ch}
.cmp{width:100%;border-collapse:collapse;font-size:13px}
.cmp th{padding:0 10px 9px 0}
.cmp td{padding:8px 10px 8px 0;vertical-align:top}
.cmp td.y{color:var(--cool);font-weight:600}
.cmp td.nn{color:var(--muted)}
.tip{position:fixed;z-index:60;pointer-events:none;opacity:0;transition:opacity .09s;background:var(--ink);color:var(--ground);border-radius:3px;padding:7px 10px;font-family:"IBM Plex Mono",monospace;font-size:11.5px;line-height:1.55;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:260px}
.tip b{color:var(--surface)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
footer{padding:34px 0 60px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
footer .mono{line-height:2}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="plate"><div class="wrap">
  <div class="mark">
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="12" fill="none" stroke="currentColor" stroke-width="1" opacity=".28"/>
      <circle cx="13" cy="13" r="7.5" fill="none" stroke="currentColor" stroke-width="1" opacity=".28"/>
      <circle cx="13" cy="13" r="1.8" fill="currentColor"/>
      <line x1="13" y1="13" x2="13" y2="3.2" stroke="currentColor" stroke-width="1.6" transform="rotate(214 13 13)"/>
    </svg>
    <div class="nm"><b>The Listening Machine</b>How, not what · local time</div>
  </div>
  <div class="span mono">RECORD <b id="spanTxt">—</b><br>SOURCE <b>three Spotify export categories, merged</b></div>
</div></div>

<nav class="tabs" aria-label="Sections"><div class="wrap" id="tabbar"></div></nav>

<div class="wrap">

<!-- ======================================================= OVERVIEW -->
<div class="tab" id="tab-overview" data-label="Overview">
  <header class="top">
    <p class="kicker">Fifth pass over the archive · behaviour, in your own time zone</p>
    <h1>Four dashboards asked what you played. This one asks <em>how you listen.</em></h1>
    <p class="lede">Every play row carries a timestamp, a skip flag, a shuffle flag, a country and a platform. Read across the full <b><span id="nSongs">—</span></b> plays — and, unlike every earlier build, <b>converted from UTC to Eastern time first</b>, so a 2am listen is a 2am listen — this is the shape of the listening rather than the list of it.</p>
    <div class="readout" id="readout"></div>
  </header>

  <section id="clock">
    <div class="shead"><div class="eyebrow">The clock</div>
      <h2>Your week, by the hour</h2>
      <p class="sub"><span id="nPlays30a">—</span> plays of thirty seconds or more, placed in local Eastern time. The earlier builds — and the other lab on this machine — chart hours in UTC, which slides every play four to five hours out of place.</p></div>
    <div class="panel"><div class="scroll"><div id="heat"></div></div>
      <div class="legend" id="heatLegend"></div><p class="cap" id="clockCap"></p></div>
    <div class="note" id="clockNote"></div>
  </section>

  <section id="hours">
    <div class="shead"><div class="eyebrow">Signature</div>
      <h2>Which artist owns each hour</h2>
      <p class="sub">Not the loudest artist in each hour — the most <b>over-represented</b> one, scored by how far its share of that hour exceeds its share of the whole record.</p></div>
    <div class="panel"><div class="scroll"><div id="sig"></div></div>
      <p class="cap">Lift = share of that hour ÷ share of all plays. Artists with fewer than 40 plays in an hour are excluded.</p></div>
    <div class="grid3 mt" id="parts"></div>
  </section>

  <section id="volume">
    <div class="shead"><div class="eyebrow">Volume</div>
      <h2>Fifteen years of hours</h2>
      <p class="sub">The one measure every earlier dashboard covered, kept because the current year needs a correction they never gave it.</p></div>
    <div class="panel"><div class="scroll"><div id="yearChart"></div></div><p class="cap" id="yearCap"></p></div>
    <div class="note" id="yearNote"></div>
  </section>

  <section id="monthly">
    <div class="shead"><div class="eyebrow">Monthly</div>
      <h2>Every month since 2015</h2>
      <p class="sub">Hours of music per month. Hover any bar for streams, new tracks and that month's exploration share.</p></div>
    <div class="panel"><div class="scroll"><div id="monthChart"></div></div>
      <p class="cap" id="monthCap"></p></div>
  </section>
</div>

<!-- ======================================================= SONGS -->
<div class="tab" id="tab-songs" data-label="Songs">
  <section id="faves">
    <div class="shead"><div class="eyebrow">Favourites</div>
      <h2>The songs, ranked</h2>
      <p class="sub">Every song you have played thirty seconds or more, across fifteen years — with the span it covers, how many separate days you reached for it, and how often you cut it short. All <b><span id="nPlays30b">—</span></b> streams.</p></div>
    <div class="panel">
      <div class="controls-row">
        <div class="seg" role="group" aria-label="Sort songs">
          <button data-sort="plays" aria-pressed="true">Most played</button>
          <button data-sort="days" aria-pressed="false">Most days</button>
          <button data-sort="hours" aria-pressed="false">Most hours</button>
          <button data-sort="years_active" aria-pressed="false">Longest running</button>
        </div>
        <input type="search" id="trkQ" placeholder="Filter by song or artist…" aria-label="Filter songs">
      </div>
      <div class="scroll" id="topTracks"></div>
    </div>
  </section>

  <section id="encounters">
    <div class="shead"><div class="eyebrow">First encounters</div>
      <h2>The night each favourite arrived</h2>
      <p class="sub">For the songs that ended up mattering most, the archive still holds the opening plays — the exact minute, the device, and how much of it you sat through.</p></div>
    <div class="enc-grid" id="enc"></div>
  </section>

  <section id="arcs-love">
    <div class="shead"><div class="eyebrow">Love arcs</div>
      <h2>How favourites became favourites</h2>
      <p class="sub">A <b>love signal</b> is the fifth thirty-second stream inside a trailing thirty-day window — the moment a song broke through in <i>your</i> listening. Every song with 25+ lifetime streams that ever reached one is classified by how long it took from the very first play.</p></div>
    <div class="grid4" id="loveKinds"></div>
    <div class="panel mt">
      <div class="controls-row">
        <div class="seg" role="group" aria-label="Filter arcs" id="arcSeg">
          <button data-kind="" aria-pressed="true">All</button>
          <button data-kind="Instant love" aria-pressed="false">Instant love</button>
          <button data-kind="Quick rise" aria-pressed="false">Quick rise</button>
          <button data-kind="Slow burn" aria-pressed="false">Slow burn</button>
          <button data-kind="Late rediscovery" aria-pressed="false">Late rediscovery</button>
        </div>
        <div class="seg" role="group" aria-label="Sort arcs" id="arcSort">
          <button data-sort="streams" aria-pressed="true">Most streams</button>
          <button data-sort="days_to_love" aria-pressed="false">Longest to love</button>
          <button data-sort="burst30" aria-pressed="false">Strongest burst</button>
        </div>
      </div>
      <div class="scroll" id="arcTbl"></div>
      <p class="cap">The sparkline is monthly streams across the song's whole life; the marked bar is the month the love signal landed. <b>Burst</b> is the most streams in any thirty-day span.</p>
    </div>
    <div class="note" id="loveNote"></div>
  </section>

  <section id="loops">
    <div class="shead"><div class="eyebrow">Loops</div>
      <h2>Your strongest listening loops</h2>
      <p class="sub">At least three consecutive thirty-second streams of the same recording with no other track between them. <b><span id="loopCount">—</span></b> recordings have ever been looped; these are the longest single runs.</p></div>
    <div class="panel"><div class="scroll" id="loopTbl"></div></div>
  </section>

  <section id="lately">
    <div class="shead"><div class="eyebrow">Lately</div>
      <h2>What was rising when the record stops</h2>
      <p class="sub">The last <b id="rwDays">—</b> days of the archive (<b id="rwRange">—</b>) against the year before it. Lift is recent streams over baseline, so a song you have just found outranks one you have always played.</p></div>
    <div class="grid2">
      <div class="panel"><h3>Climbing fastest</h3><p class="cap" style="margin:0 0 14px">Ranked by lift, not volume.</p><div class="scroll" id="rising"></div></div>
      <div class="panel"><h3>Simply most played</h3><p class="cap" style="margin:0 0 14px">Raw streams in the same window.</p><div class="scroll" id="recentTop"></div></div>
    </div>
    <div class="panel mt"><h3 style="margin-bottom:14px">Artists on the way up</h3><div class="scroll" id="risingArt"></div></div>
    <div class="note" id="latelyNote"></div>
  </section>

  <section id="rediscover">
    <div class="shead"><div class="eyebrow">Rediscovery</div>
      <h2>Durable favourites you have left behind</h2>
      <p class="sub">Songs with 25+ streams across at least two different years that have not been heard for a year or more. A queue, not a verdict.</p></div>
    <div class="grid4" id="redBuckets"></div>
    <div class="panel mt"><div class="scroll" id="redTbl"></div></div>
  </section>
</div>

<!-- ======================================================= BEHAVIOUR -->
<div class="tab" id="tab-behaviour" data-label="Behaviour">
  <section id="skip">
    <div class="shead"><div class="eyebrow">Friction</div>
      <h2>The skip curve, and its reversal</h2>
      <p class="sub">Two definitions, both shown. A <b>skip</b> is a track you abandoned inside thirty seconds. <b>Cut short</b> is any track you ended with the forward button, however far in. The story is the same under both: the rate fell for eight years, then doubled in 2025.</p></div>
    <div class="panel"><div class="scroll"><div id="skipChart"></div></div>
      <div class="legend">
        <span><i class="sw" style="background:var(--s1)"></i>Skipped inside 30s</span>
        <span><i class="sw" style="background:var(--s2)"></i>Cut short at any point</span>
        <span><i class="sw" style="background:var(--s3)"></i>Shuffle share</span></div>
      <p class="cap" id="skipCap"></p></div>
    <div class="grid2 mt">
      <div class="panel"><h3 style="margin-bottom:14px">Cut short most</h3><div id="skipHigh"></div></div>
      <div class="panel"><h3 style="margin-bottom:14px">Cut short least</h3><div id="skipLow"></div></div>
    </div>
    <div class="note" id="skipNote"></div>
  </section>

  <section id="begin">
    <div class="shead"><div class="eyebrow">Intent</div>
      <h2>How each track began</h2>
      <p class="sub">Spotify records why a track started. Flowing from the previous track is passive; clicking a row or pressing forward is a decision. The balance is a direct read of how hands-on the listening is.</p></div>
    <div class="panel"><div class="scroll"><div id="beginChart"></div></div>
      <div class="legend" id="beginLegend"></div><p class="cap" id="beginCap"></p></div>
  </section>

  <section id="explore">
    <div class="shead"><div class="eyebrow">Exploration</div>
      <h2>Exploration versus comfort</h2>
      <p class="sub">Share of each month's streams given to tracks within their first thirty days in your history. High means you were listening to things you had just found; low means you were living in what you already knew.</p></div>
    <div class="panel"><div class="scroll"><div id="exploreChart"></div></div><p class="cap" id="exploreCap"></p></div>
  </section>

  <section id="retention">
    <div class="shead"><div class="eyebrow">Retention</div>
      <h2>Do discoveries stick?</h2>
      <p class="sub">Of every track first heard in a given year, the share that received another stream at least ninety days later, and at least a year later. Recent cohorts appear only once they are old enough to be judged.</p></div>
    <div class="panel"><div class="scroll"><div id="retChart"></div></div>
      <div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Returned after 90 days</span><span><i class="sw" style="background:var(--s2)"></i>Returned after a year</span></div>
      <p class="cap" id="retCap"></p></div>
    <div class="note" id="retNote"></div>
  </section>

  <section id="sessions">
    <div class="shead"><div class="eyebrow">Sessions</div>
      <h2>How long the music stays on, and what kind of sitting it is</h2>
      <p class="sub">Consecutive streams separated by less than thirty minutes of silence form one sitting — <b id="sessCount">—</b> of them. Each is then classified by what happened inside it.</p></div>
    <div class="grid4" id="styles"></div>
    <div class="grid2 mt">
      <div class="panel"><div class="scroll"><div id="sessChart"></div></div><p class="cap">Median minutes per sitting, by year.</p></div>
      <div class="panel" id="sessStats"></div>
    </div>
    <div class="panel mt"><h3>The longest sittings on record</h3><p class="cap" style="margin:0 0 14px">Ranked by sound actually played.</p><div class="scroll" id="longTbl"></div></div>
    <div class="note warnnote"><b>Read the longest with suspicion.</b> A 57-hour sitting is a speaker left running, not attention. The median (<b id="medMin">—</b> minutes) is the honest number.</div>
  </section>

  <section id="unfinished">
    <div class="shead"><div class="eyebrow">Unfinished</div>
      <h2>Songs you start and never finish</h2>
      <p class="sub">Each track's longest recorded listen stands in for its duration; completion is the share of that you typically hear. Only tracks with 25+ plays qualify — songs you return to <b>and</b> abandon.</p></div>
    <div class="panel"><div class="scroll" id="compTbl"></div></div>
  </section>
</div>

<!-- ======================================================= ERAS -->
<div class="tab" id="tab-eras" data-label="Eras">
  <section id="eras">
    <div class="shead"><div class="eyebrow">Eras</div>
      <h2>The artists that led each year</h2>
      <p class="sub">Five per year by streams. Incomplete years stay visible rather than projected.</p></div>
    <div class="panel"><div class="scroll" id="eraTbl"></div></div>
  </section>

  <section id="arcs">
    <div class="shead"><div class="eyebrow">Arcs</div>
      <h2>Lifers and flares</h2>
      <p class="sub">Two ways to matter over fifteen years: turn up in almost every one of them, or burn through a single year and leave.</p></div>
    <div class="grid2">
      <div class="panel"><h3>Lifers</h3><p class="cap" style="margin:0 0 14px">Present across the most separate calendar years.</p><div class="scroll" id="lifers"></div></div>
      <div class="panel"><h3>Flares</h3><p class="cap" style="margin:0 0 14px">300+ plays, concentrated hardest into one year.</p><div class="scroll" id="flares"></div></div>
    </div>
  </section>

  <section id="albums">
    <div class="shead"><div class="eyebrow">Albums</div>
      <h2>Records you lived inside</h2>
      <p class="sub">Two lists. The albums you streamed most, and the albums you actually explored — eight or more distinct tracks heard.</p></div>
    <div class="grid2">
      <div class="panel"><h3>Most streamed</h3><p class="cap" style="margin:0 0 14px">Total streams from the album.</p><div class="scroll" id="albTop"></div></div>
      <div class="panel"><h3>Explored deepest</h3><p class="cap" style="margin:0 0 14px">Distinct tracks heard, then streams.</p><div class="scroll" id="albInside"></div></div>
    </div>
  </section>

  <section id="breadth">
    <div class="shead"><div class="eyebrow">Breadth</div>
      <h2>Artists explored broadly</h2>
      <p class="sub">Ranked by distinct recordings heard rather than streams — the catalogues you went through, not the songs you repeated.</p></div>
    <div class="panel"><div class="scroll" id="breadthTbl"></div></div>
  </section>
</div>

<!-- ======================================================= LIBRARY -->
<div class="tab" id="tab-library" data-label="Library">
  <section id="saved">
    <div class="shead"><div class="eyebrow">Saved</div>
      <h2>Your library, audited against the record</h2>
      <p class="sub">Every one of your <b><span id="savedTotal">—</span></b> saved tracks, cross-referenced with lifetime listening. <b>Never heard</b>: no stream at all. <b>Sampled</b>: fewer than five. <b>Dormant</b>: five or more, but silent for a year. <b>Active</b>: heard within the year.</p></div>
    <div class="grid4" id="savedStats"></div>
    <div class="grid2 mt">
      <div class="panel"><h3>Saved, never heard</h3><p class="cap" style="margin:0 0 14px">In the library; no thirty-second stream on record.</p><div class="scroll" id="savedNever"></div></div>
      <div class="panel"><h3>Saved, then abandoned</h3><p class="cap" style="margin:0 0 14px">The most-played of the dormant.</p><div class="scroll" id="savedDormant"></div></div>
    </div>
  </section>

  <section id="unsaved">
    <div class="shead"><div class="eyebrow">Unsaved</div>
      <h2>Loved, but not saved</h2>
      <p class="sub">Songs with 25+ streams that are absent from the saved-track snapshot — <b><span id="lnsTotal">—</span></b> of them. The library does not know about your actual favourites.</p></div>
    <div class="panel"><div class="scroll" id="lnsTbl"></div></div>
  </section>

  <section id="playlists">
    <div class="shead"><div class="eyebrow">Playlists</div>
      <h2>Which of your playlists actually get played</h2>
      <p class="sub">Your <span id="plCount">—</span> playlists, ranked by how much their contents were played in the recent window.</p></div>
    <div class="panel"><div class="scroll" id="plTbl"></div>
      <p class="cap"><b>How this is measured.</b> The streaming history does not record which playlist a play came from — that field is blank in 97% of Spotify's own logs. So this counts plays of the <i>tracks a playlist contains</i>, wherever you played them. Pull-through, not usage.</p></div>
  </section>

  <section id="search">
    <div class="shead"><div class="eyebrow">Search</div>
      <h2>What you looked for, and whether you listened</h2>
      <p class="sub">Spotify logs each search burst and any result you tapped. A search <b>converted</b> if a tapped track was streamed within seven days.</p></div>
    <div class="grid4" id="searchStats"></div>
    <div class="panel mt"><h3>Most repeated queries</h3><p class="cap" style="margin:0 0 6px">Partial strings are real — Spotify logs each keystroke burst.</p><div class="pillrow" id="searches"></div></div>
  </section>
</div>

<!-- ======================================================= THE ROOM -->
<div class="tab" id="tab-room" data-label="The room">
  <section id="rooms">
    <div class="shead"><div class="eyebrow">The room</div>
      <h2>What the sound came out of</h2>
      <p class="sub">Two records. The fifteen-year history knows only broad platforms; the technical logs know the actual hardware, but Spotify keeps those for roughly ninety days — so that column is merged from every export on disk into one window.</p></div>
    <div class="grid2">
      <div class="panel"><div class="scroll"><div id="platChart"></div></div><div class="legend" id="platLegend"></div>
        <p class="cap">Share of plays per year by platform family. The cast column is the arrival of a speaker.</p></div>
      <div class="panel" id="devPanel"></div>
    </div>
  </section>

  <section id="health">
    <div class="shead"><div class="eyebrow">System</div>
      <h2>How the listening system behaved</h2>
      <p class="sub">Aggregate counts from the merged technical-log window. Device identifiers and addresses stay in the source export.</p></div>
    <div class="grid4" id="healthStats"></div>
    <div class="grid2 mt">
      <div class="panel"><h3>Spotify's On Repeat, checked against the record</h3><p class="cap" style="margin:0 0 14px">Tracks most often placed in your On Repeat mix across <span id="orSnaps">—</span> snapshots, beside their lifetime streams.</p><div class="scroll" id="orTbl"></div></div>
      <div class="panel"><h3>The daylist's language for you</h3><p class="cap" style="margin:0 0 6px">Titles Spotify generated for your day-part mixes.</p><div class="pillrow" id="daylists"></div></div>
    </div>
  </section>

  <section id="anomaly">
    <div class="shead"><div class="eyebrow">Anomaly</div>
      <h2>Days that were not you</h2>
      <p class="sub">Someone else on the account leaves two marks at once: artists that appear on no other day of a fifteen-year record, <b>and</b> a device-country pair the account otherwise never uses. The pipeline flags any day of 50+ streams where at least 70% comes from artists heard on that day alone <b>and</b> the dominant device-country pair carries under 1% of lifetime streams — then <b>excludes it from every figure on this page</b>. A trip abroad on your own phone does not trip this; nor does an afternoon of rain-sound content farms on the home speaker.</p></div>
    <div id="foreignBox"></div>
  </section>

  <section id="where">
    <div class="shead"><div class="eyebrow">Elsewhere</div>
      <h2>The music followed you abroad</h2>
      <p class="sub">Every play records the country it was streamed from. <span id="countryCount">—</span> countries appear across fifteen years.</p></div>
    <div class="panel"><div class="scroll" id="geoTbl"></div>
      <p class="cap"><b>ZZ</b> is Spotify's code for a country it could not resolve — almost always a VPN. <span id="zzNote"></span></p></div>
  </section>
</div>

<!-- ======================================================= SPOTIFY'S VIEW -->
<div class="tab" id="tab-spotify" data-label="Spotify's view">
  <section id="mirror">
    <div class="shead"><div class="eyebrow">Mirror</div>
      <h2>Its musical read of you</h2>
      <p class="sub">Spotify's own written summary of your taste, from the account export. Verbatim.</p></div>
    <div class="panel"><p class="quote" id="tasteQuote"></p></div>
  </section>

  <section id="wrapped">
    <div class="shead"><div class="eyebrow">Wrapped 2025</div>
      <h2>Spotify's official 2025 snapshot</h2>
      <p class="sub">Its numbers beside this page's. They will not match exactly — Wrapped closes in November and counts differently — but they should rhyme.</p></div>
    <div class="grid4" id="wrapStats"></div>
    <div class="panel mt"><h3>Its top tracks for 2025</h3><p class="cap" style="margin:0 0 14px">Named from your own history where the URI matches.</p><div class="scroll" id="wrapTbl"></div></div>
  </section>

  <section id="machine">
    <div class="shead"><div class="eyebrow">Inference</div>
      <h2>What the machine infers about you</h2>
      <p class="sub">The audience segments Spotify's advertising side has filed you under. The other lab on this machine hides these on principle; they are shown here because they are yours to see.</p></div>
    <div class="grid2">
      <div class="panel"><h3>Spotify's own segments</h3><p class="cap" style="margin:0 0 6px">First-party audiences built from listening and device.</p><div class="pillrow" id="inf1p"></div></div>
      <div class="panel"><h3>Advertiser lookalike pools</h3><p class="cap" style="margin:0 0 6px">Brands whose modelled audiences you have been matched into.</p><div class="pillrow" id="infBrands"></div></div>
    </div>
    <div class="note" id="infNote"></div>
  </section>
</div>

<!-- ======================================================= METHOD -->
<div class="tab" id="tab-method" data-label="Method">
  <section id="lineage">
    <div class="shead"><div class="eyebrow">Lineage</div>
      <h2>What each pass has covered</h2>
      <p class="sub">Five builds, each answering a different question of the same archive. Nothing here replaces the earlier ones — they hold material this page does not.</p></div>
    <div class="panel"><div class="lin" id="lin"></div></div>
    <div class="note" id="refreshNote"></div>
  </section>

  <section id="compare">
    <div class="shead"><div class="eyebrow">The other lab</div>
      <h2>Beside the parallel build</h2>
      <p class="sub">A second pipeline on this machine reads the same three exports. Where it led, this build adopted the analysis; where it differs, the difference is stated rather than hidden.</p></div>
    <div class="panel"><div class="scroll"><table class="cmp"><thead><tr><th>Question</th><th>Parallel build</th><th>Listening Machine (this page)</th></tr></thead><tbody id="cmpBody"></tbody></table></div></div>
  </section>

  <section id="defs">
    <div class="shead"><div class="eyebrow">Definitions</div>
      <h2>Every term, once</h2></div>
    <div class="panel"><div class="scroll"><table><tbody id="defBody"></tbody></table></div></div>
  </section>

  <section id="exports">
    <div class="shead"><div class="eyebrow">Exports</div>
      <h2>The same tables as files</h2>
      <p class="sub">Written next to the page on every rebuild, in <span class="mono">csv/</span>. Open in Excel or feed to anything.</p></div>
    <div class="panel"><div class="pillrow" id="csvList" style="margin-top:0"></div></div>
  </section>

  <footer>
    <div class="mono">
      SOURCES · Spotify Extended Streaming History, <span id="fRows">—</span> rows · Spotify Account Data (library, playlists, searches, taste profile, inferences, Wrapped) · Spotify Technical Log Information, merged from every export on disk<br>
      LIMITS · history ends <span id="fEnd">—</span> · technical logs cover <span id="fTech">—</span> · 2013–2014 absent from Spotify's export · the current year is partial and is annotated as such wherever it appears
    </div>
  </footer>
</div>

</div>
<div class="tip" id="tip" role="status"></div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById('payload').textContent);
const CSVS = __CSVS__;
const $ = s => document.querySelector(s);
const nf = n => (n == null ? '—' : Number(n).toLocaleString('en-US'));
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SVGNS = 'http://www.w3.org/2000/svg';
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const MONO = 'IBM Plex Mono, monospace';
const fmtD = s => new Date(s + 'T00:00:00').toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric'});

/* ---------- tabs ---------- */
(function(){
  const tabs = [...document.querySelectorAll('.tab')];
  const bar = $('#tabbar');
  tabs.forEach(t => {
    const b = document.createElement('button');
    b.textContent = t.dataset.label; b.dataset.tab = t.id; b.setAttribute('role', 'tab');
    b.addEventListener('click', () => show(t.id, true));
    bar.appendChild(b);
  });
  function show(id, push){
    tabs.forEach(t => t.classList.toggle('on', t.id === id));
    bar.querySelectorAll('button').forEach(b => b.setAttribute('aria-selected', b.dataset.tab === id));
    if (push) history.replaceState(null, '', '#' + id.replace('tab-', ''));
    window.scrollTo({top: 0});
  }
  window.showTabFor = function(hash){
    const h = (hash || '').replace('#', '');
    if (!h) return show('tab-overview');
    const direct = document.getElementById('tab-' + h);
    if (direct) return show('tab-' + h);
    const sec = document.getElementById(h);
    const tab = sec && sec.closest('.tab');
    if (tab){ show(tab.id); setTimeout(() => sec.scrollIntoView({block: 'start'}), 30); }
    else show('tab-overview');
  };
  window.addEventListener('hashchange', () => showTabFor(location.hash));
  showTabFor(location.hash);
})();

/* ---------- tooltip + svg helpers ---------- */
const tip = $('#tip');
function showTip(e, html){
  tip.innerHTML = html; tip.style.opacity = 1;
  const r = tip.getBoundingClientRect();
  let x = e.clientX + 14, y = e.clientY - r.height - 10;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
  if (y < 8) y = e.clientY + 18;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
const hideTip = () => tip.style.opacity = 0;
function hoverable(el, html){ el.addEventListener('mousemove', e => showTip(e, html)); el.addEventListener('mouseleave', hideTip); }
function svg(w, h){ const s = document.createElementNS(SVGNS, 'svg'); s.setAttribute('viewBox', `0 0 ${w} ${h}`); s.setAttribute('width', w); s.setAttribute('height', h); s.setAttribute('class', 'chart'); return s; }
function el(tag, attrs, parent){ const n = document.createElementNS(SVGNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }
function txt(s, x, y, t, o){ const n = el('text', Object.assign({x, y, fill: css('--muted'), 'font-size': 10.5, 'font-family': MONO}, o || {}), s); n.textContent = t; return n; }
function sparkline(pairs, mark, w, h){
  if (!pairs.length) return '';
  const vals = pairs.map(p => p[1]); const max = Math.max(...vals);
  const bw = Math.max(1.5, w / pairs.length);
  const A = css('--accent'), W = css('--warm'), L = css('--q2');
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` + pairs.map((p, i) => {
    const bh = Math.max(1, p[1] / max * (h - 1));
    return `<rect x="${(i * bw).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${Math.max(1, bw - .6).toFixed(1)}" height="${bh.toFixed(1)}" fill="${p[0] === mark ? W : (p[1] === max ? A : L)}"/>`;
  }).join('') + '</svg>';
}
const statTile = (v, l, d) => `<div class="stat"><div class="v">${v}</div><div class="l">${l}</div>${d ? `<div class="d">${d}</div>` : ''}</div>`;

/* ---------- readout + live prose ---------- */
const t = D.totals;
$('#spanTxt').textContent = D.window.first + ' → ' + D.window.last;
$('#readout').innerHTML = [[nf(t.plays30), 'Streams counted'], [nf(t.hours) + 'h', 'Sound played'],
  [nf(t.artists), 'Distinct artists'], [nf(t.active_days), 'Days with music'], [nf(D.sessions.count), 'Listening sittings']]
  .map(([v, l]) => `<div class="ro"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
$('#nSongs').textContent = nf(t.songs); $('#nPlays30a').textContent = nf(t.plays30); $('#nPlays30b').textContent = nf(t.plays30);
const WORDS = ['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty'];
$('#plCount').textContent = WORDS[D.playlists.length] || D.playlists.length;
(function(){ const n = D.abroad.length + 1; const w = WORDS[n] || String(n); $('#countryCount').textContent = w.charAt(0).toUpperCase() + w.slice(1); })();
(function(){ const zz = D.abroad.find(a => a.country === 'ZZ');
  let s = zz ? `Yours covers ${zz.days} days between ${zz.first.slice(0, 7)} and ${zz.last.slice(0, 7)}.` : 'None in your record.';
  if ((D.foreign_days || []).length) s += ` ${D.foreign_days.length} day${D.foreign_days.length > 1 ? 's' : ''} flagged as not yours ${D.foreign_days.length > 1 ? 'are' : 'is'} already excluded — see Anomaly, above.`;
  $('#zzNote').textContent = s; })();
$('#fRows').textContent = nf(t.rows); $('#fEnd').textContent = D.window.last;
$('#fTech').textContent = D.tech.routes_window ? D.tech.routes_window.first + ' → ' + D.tech.routes_window.last : 'n/a';

/* ---------- clock heatmap ---------- */
(function(){
  const M = D.clock.dow_hour, days = D.clock.dow_labels;
  const cw = 40, ch = 30, padL = 46, padT = 26, padB = 30, padR = 10;
  const W = padL + cw * 24 + padR, H = padT + ch * 7 + padB; const s = svg(W, H);
  let max = 0; M.forEach(r => r.forEach(v => { if (v > max) max = v; }));
  const ramp = ['--q0','--q1','--q2','--q3','--q4','--q5','--q6','--q7'].map(css);
  const step = v => v === 0 ? ramp[0] : ramp[Math.min(7, 1 + Math.floor((v / max) ** 0.62 * 7))];
  for (let h = 0; h < 24; h += 2) txt(s, padL + h * cw + cw / 2, padT - 10, String(h).padStart(2, '0'), {'text-anchor': 'middle'});
  days.forEach((d, i) => { txt(s, padL - 12, padT + i * ch + ch / 2 + 4, d, {'text-anchor': 'end', 'font-size': 11});
    for (let h = 0; h < 24; h++){ const v = M[i][h];
      const r = el('rect', {x: padL + h * cw + 1, y: padT + i * ch + 1, width: cw - 2, height: ch - 2, rx: 2, fill: step(v)}, s);
      r.style.cursor = 'crosshair'; hoverable(r, `<b>${d} ${String(h).padStart(2,'0')}:00</b><br>${nf(v)} streams`); } });
  txt(s, padL, H - 10, 'hour of day, Eastern time →');
  $('#heat').appendChild(s);
  $('#heatLegend').innerHTML = `<span style="gap:9px">Streams per cell<b class="mono" style="font-weight:500;color:var(--muted)">0</b>` + ramp.map(c => `<i class="sw" style="background:${c};margin-right:2px"></i>`).join('') + `<b class="mono" style="font-weight:500;color:var(--muted)">${nf(max)}</b></span>`;
  let best = {v: -1}; M.forEach((row, i) => row.forEach((v, h) => { if (v > best.v) best = {v, i, h}; }));
  const tot = D.clock.hour_total.reduce((a, b) => a + b, 0), night = D.clock.hour_total.slice(0, 6).reduce((a, b) => a + b, 0), work = D.clock.hour_total.slice(9, 17).reduce((a, b) => a + b, 0);
  $('#clockCap').innerHTML = `Busiest cell: <b>${days[best.i]} at ${String(best.h).padStart(2,'0')}:00</b> — ${nf(best.v)} streams.`;
  $('#clockNote').innerHTML = `<b>${(night / tot * 100).toFixed(1)}% of everything you have ever played happened between midnight and 6am</b> — ${nf(night)} streams. The eight working hours from 9 to 5 hold ${(work / tot * 100).toFixed(1)}%. The week is flat: no weekend spike, no Monday trough. Music is not an occasion for you, it is a substrate. <i>In UTC this whole picture shifts right by four or five hours and the nocturnal peak reads as breakfast.</i>`;
})();

/* ---------- hour signature + day parts ---------- */
(function(){
  const rows = D.hour_signature.filter(r => r.artist); const cw = 40, padL = 46, padT = 16, barH = 132, padB = 136;
  const W = padL + cw * 24 + 78, H = padT + barH + padB; const s = svg(W, H); const max = Math.max(...rows.map(r => r.lift)); const A = css('--accent');
  D.hour_signature.forEach(r => { const x = padL + r.hour * cw; if (!r.artist) return; const h = Math.max(3, (r.lift / max) * barH);
    const rect = el('rect', {x: x + 6, y: padT + barH - h, width: cw - 12, height: h, rx: 3, fill: A}, s);
    hoverable(rect, `<b>${String(r.hour).padStart(2,'0')}:00 — ${esc(r.artist)}</b><br>${r.lift}× over-represented<br>${nf(r.plays)} of ${nf(r.total)} streams in this hour`);
    txt(s, x + cw / 2, padT + barH + 13, String(r.hour).padStart(2, '0'), {'text-anchor': 'middle', 'font-size': 10});
    const lab = txt(s, x + cw / 2, padT + barH + 24, r.artist.length > 17 ? r.artist.slice(0, 16) + '…' : r.artist, {fill: css('--ink-2'), 'font-size': 11.5, 'font-family': 'IBM Plex Sans, sans-serif', transform: `rotate(58 ${x + cw / 2} ${padT + barH + 24})`}); });
  el('line', {x1: padL, y1: padT + barH, x2: padL + cw * 24, y2: padT + barH, stroke: css('--line-2'), 'stroke-width': 1}, s);
  $('#sig').appendChild(s);
  $('#parts').innerHTML = Object.entries(D.day_parts).map(([label, v]) => `<div class="panel"><div class="eyebrow" style="margin-bottom:8px">${esc(label)}</div><div class="mono" style="font-size:19px;font-weight:600">${nf(v.plays)}</div><div class="cap" style="margin:2px 0 12px">streams</div><table><tbody>${v.top.slice(0, 5).map(a => `<tr><td>${esc(a.artist)}</td><td class="n">${nf(a.n)}</td></tr>`).join('')}</tbody></table></div>`).join('');
})();

/* ---------- hours by year ---------- */
(function(){
  const rows = D.by_year.filter(r => r.hours > 5); const padL = 46, padR = 14, padT = 18, padB = 38, W = 760, H = 290; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H);
  const max = Math.max(...rows.map(r => r.hours)) * 1.1; const bw = iw / rows.length;
  for (let g = 0; g <= 2000; g += 500){ el('line', {x1: padL, y1: padT + ih - g / max * ih, x2: W - padR, y2: padT + ih - g / max * ih, stroke: css('--line')}, s); txt(s, padL - 9, padT + ih - g / max * ih + 4, nf(g), {'text-anchor': 'end', 'font-size': 10}); }
  const lastD = new Date(D.window.last + 'T00:00:00'); const curYear = lastD.getFullYear(); const dayOfYear = Math.round((lastD - new Date(curYear, 0, 1)) / 86400000) + 1; const isPartial = dayOfYear < 365; const lastNice = lastD.toLocaleDateString('en-GB', {day: 'numeric', month: 'long'});
  rows.forEach((r, i) => { const h = r.hours / max * ih, partial = isPartial && r.year === curYear;
    const rect = el('rect', {x: padL + i * bw + 4, y: padT + ih - h, width: bw - 8, height: h, rx: 3, fill: partial ? 'none' : css('--accent'), stroke: partial ? css('--accent') : 'none', 'stroke-width': partial ? 1.6 : 0, 'stroke-dasharray': partial ? '4 3' : 'none'}, s);
    hoverable(rect, `<b>${r.year}${partial ? ' (to ' + lastNice + ')' : ''}</b><br>${nf(r.hours)} hours<br>${nf(r.plays)} streams · ${nf(r.artists)} artists<br>${nf(r.new_artists)} first heard this year`);
    txt(s, padL + i * bw + bw / 2, H - 14, String(r.year).slice(2), {'text-anchor': 'middle', 'font-size': 10}); });
  txt(s, padL - 9, padT - 5, 'hrs', {'text-anchor': 'end', 'font-size': 9.5}); $('#yearChart').appendChild(s);
  const y26 = rows.find(r => r.year === curYear), y25 = rows.find(r => r.year === curYear - 1); const rate26 = y26.hours / dayOfYear * 365, rate25 = y25.hours; const peak = rows.reduce((a, b) => b.hours > a.hours ? b : a);
  $('#yearCap').innerHTML = `Peak <b>${nf(peak.hours)} hours in ${peak.year}</b>.` + (isPartial ? ` The dashed ${curYear} bar is a partial year — 1 January to ${lastNice} only.` : '');
  $('#yearNote').innerHTML = rate26 > rate25 ? `<b>${curYear} is not a continued decline; it is a recovery.</b> The bar ${y26.hours > y25.hours ? 'already exceeds' : 'looks similar to'} ${curYear - 1}'s and covers only ${dayOfYear} days. At ${(y26.hours / dayOfYear).toFixed(2)} hours a day, ${curYear} annualises to roughly <b>${nf(Math.round(rate26))} hours</b> — about ${(rate26 / rate25).toFixed(1)}× the ${curYear - 1} rate, the first upturn since 2022. The spring ran hotter than the summer.` : `<b>${curYear} is running below ${curYear - 1}.</b> At ${(y26.hours / dayOfYear).toFixed(2)} hours a day it annualises to roughly ${nf(Math.round(rate26))} hours.`;
})();

/* ---------- monthly ---------- */
(function(){
  const rows = D.monthly.filter(m => m.ym >= '2015-12'); const padL = 42, padR = 12, padT = 16, padB = 34, W = 1000, H = 250; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H);
  const max = Math.max(...rows.map(r => r.hours)) * 1.08; const bw = iw / rows.length;
  for (let g = 0; g <= 250; g += 50){ el('line', {x1: padL, y1: padT + ih - g / max * ih, x2: W - padR, y2: padT + ih - g / max * ih, stroke: css('--line')}, s); txt(s, padL - 8, padT + ih - g / max * ih + 4, g, {'text-anchor': 'end', 'font-size': 10}); }
  rows.forEach((r, i) => { const h = r.hours / max * ih; const rect = el('rect', {x: padL + i * bw + .6, y: padT + ih - h, width: Math.max(1, bw - 1.2), height: h, fill: css('--accent')}, s);
    hoverable(rect, `<b>${r.ym}</b><br>${r.hours} hours · ${nf(r.streams)} streams<br>${nf(r.new_tracks)} new tracks · exploration ${r.explore_pct}%<br>skipped ${r.skip_pct}%`);
    if (r.ym.endsWith('-01')) txt(s, padL + i * bw + bw / 2, H - 14, r.ym.slice(0, 4), {'text-anchor': 'middle', 'font-size': 10}); });
  $('#monthChart').appendChild(s);
  const top = rows.reduce((a, b) => b.hours > a.hours ? b : a);
  $('#monthCap').innerHTML = `Biggest month: <b>${top.ym}</b>, ${nf(top.hours)} hours and ${nf(top.streams)} streams. Y axis is hours.`;
})();

/* ---------- favourites ---------- */
(function(){
  const host = $('#topTracks'); let sort = 'plays', q = '';
  function draw(){ const rows = D.top_tracks.filter(r => !q || (r.track + ' ' + r.artist).toLowerCase().includes(q)).slice().sort((a, b) => b[sort] - a[sort]); const max = Math.max(...rows.map(r => r.plays), 1);
    host.innerHTML = rows.length ? `<table><thead><tr><th style="width:26px"></th><th>Song</th><th>Artist</th><th style="width:70px"></th><th style="text-align:right">Streams</th><th style="text-align:right">Days</th><th style="text-align:right">Hours</th><th style="text-align:right">Span</th><th style="text-align:right">Cut short</th><th style="text-align:right">Mostly on</th></tr></thead><tbody>` +
      rows.map((r, i) => `<tr><td class="n" style="color:var(--muted);text-align:left">${i + 1}</td><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="bar-cell"><i style="width:${(r.plays / max * 64).toFixed(1)}px;background:var(--accent)"></i></td><td class="n"><b>${nf(r.plays)}</b></td><td class="n" style="color:var(--muted)">${nf(r.days)}</td><td class="n" style="color:var(--muted)">${r.hours}</td><td class="n" style="color:var(--muted)">${r.first.slice(2, 7)}–${r.last.slice(2, 7)}</td><td class="n" style="color:var(--muted)">${r.skip_rate}%</td><td class="n" style="color:var(--muted)">${esc(r.top_device)}</td></tr>`).join('') + `</tbody></table>` : `<p class="cap">No song matches that filter.</p>`; }
  document.querySelectorAll('#faves .seg button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('#faves .seg button').forEach(x => x.setAttribute('aria-pressed', x === b)); sort = b.dataset.sort; draw(); }));
  $('#trkQ').addEventListener('input', e => { q = e.target.value.toLowerCase().trim(); draw(); }); draw();
})();

/* ---------- first encounters ---------- */
(function(){
  const when = s => new Date(s).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'}) + ' · ' + s.slice(11, 16);
  $('#enc').innerHTML = D.first_encounters.map(e => `<article class="enc"><div class="enc-head"><div><div class="t">${esc(e.track)}</div><div class="a">${esc(e.artist)}</div></div><div class="tot">${nf(e.plays)}<small>streams since</small></div></div>
    <div class="opens">${e.opening.map((o, i) => `<div class="row"><span class="ix">${i + 1}</span><span class="wh">${when(o.when)}</span><span class="dv">${esc(o.device)} · ${o.secs}s</span></div>`).join('')}</div>
    <div class="enc-foot">First play to fifth: <b>${e.days_to_5} day${e.days_to_5 === 1 ? '' : 's'}</b>${e.days_to_10 != null ? ` · to tenth: <b>${e.days_to_10}</b>` : ''} · still playing it in <b>${e.last.slice(0, 4)}</b></div></article>`).join('');
})();

/* ---------- love arcs ---------- */
(function(){
  const K = D.love_kinds, tot = D.love_total; const desc = {'Instant love': 'love signal within 7 days of the first play', 'Quick rise': 'within 30 days', 'Slow burn': 'within a year', 'Late rediscovery': 'more than a year after the first play'};
  $('#loveKinds').innerHTML = ['Instant love', 'Quick rise', 'Slow burn', 'Late rediscovery'].map(k => statTile(nf(K[k] || 0), k, `${((K[k] || 0) / tot * 100).toFixed(0)}% · ${desc[k]}`)).join('');
  let kind = '', sort = 'streams'; const host = $('#arcTbl'); const kcls = {'Instant love': 'k1', 'Quick rise': 'k2', 'Slow burn': 'k3', 'Late rediscovery': 'k4'};
  function draw(){ const rows = D.love_arcs.filter(a => !kind || a.kind === kind).slice().sort((a, b) => b[sort] - a[sort]).slice(0, 30);
    host.innerHTML = `<table><thead><tr><th>Song</th><th>Artist</th><th>Arc</th><th style="text-align:right">First</th><th style="text-align:right">Love signal</th><th style="text-align:right">To love</th><th>Life</th><th style="text-align:right">Peak month</th><th style="text-align:right">Burst</th><th style="text-align:right">Streams</th></tr></thead><tbody>` +
      rows.map(a => `<tr><td>${esc(a.track)}</td><td class="who">${esc(a.artist)}</td><td><span class="kind ${kcls[a.kind]}">${a.kind}</span></td><td class="n" style="color:var(--muted)">${a.first.slice(0, 7)}</td><td class="n" style="color:var(--muted)">${a.love.slice(0, 7)}</td><td class="n">${a.days_to_love >= 365 ? (a.days_to_love / 365).toFixed(1) + ' yr' : a.days_to_love + 'd'}</td><td>${sparkline(a.spark, a.love.slice(0, 7), 96, 18)}</td><td class="n" style="color:var(--muted)">${a.peak_month} · ${a.peak_month_streams}</td><td class="n">${a.burst30}</td><td class="n"><b>${nf(a.streams)}</b></td></tr>`).join('') + `</tbody></table>`; }
  document.querySelectorAll('#arcSeg button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('#arcSeg button').forEach(x => x.setAttribute('aria-pressed', x === b)); kind = b.dataset.kind; draw(); }));
  document.querySelectorAll('#arcSort button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('#arcSort button').forEach(x => x.setAttribute('aria-pressed', x === b)); sort = b.dataset.sort; draw(); }));
  draw();
  const late = K['Late rediscovery'] || 0, inst = K['Instant love'] || 0; const slow = D.love_slowest[0]; const burst = D.love_burst[0];
  $('#loveNote').innerHTML = `<b>You fall for songs late.</b> ${nf(late)} of your ${nf(tot)} durable favourites — ${(late / tot * 100).toFixed(0)}% — were heard once and then ignored for over a year before they took hold; only ${(inst / tot * 100).toFixed(0)}% caught instantly. The slowest on record is <b>${esc(slow.track)}</b> (${esc(slow.artist)}): ${(slow.days_to_love / 365).toFixed(1)} years from first play to love signal, ${nf(slow.streams)} streams since. The strongest burst is <b>${esc(burst.track)}</b> — ${nf(burst.burst30)} streams in one thirty-day span.`;
})();

/* ---------- loops ---------- */
(function(){
  $('#loopCount').textContent = nf(D.repeat_loop_tracks);
  $('#loopTbl').innerHTML = `<table><thead><tr><th>Recording</th><th>Artist</th><th style="text-align:right">Longest run</th><th style="text-align:right">Began</th><th style="text-align:right">Ended</th><th style="text-align:right">Lifetime</th></tr></thead><tbody>` +
    D.repeat_loops.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n"><b>${nf(r.run)}</b> in a row</td><td class="n" style="color:var(--muted)">${r.start.replace('T', ' ')}</td><td class="n" style="color:var(--muted)">${r.end.replace('T', ' ')}</td><td class="n" style="color:var(--muted)">${nf(r.streams)}</td></tr>`).join('') + `</tbody></table>`;
})();

/* ---------- lately ---------- */
(function(){
  const w = D.recent_window; $('#rwDays').textContent = w.days; $('#rwRange').textContent = w.from + ' → ' + w.to;
  const tbl = (rows, sel, lift) => $(sel).innerHTML = `<table><thead><tr><th>Song</th><th>Artist</th>${lift ? '<th style="text-align:right">Lift</th>' : ''}<th style="text-align:right">Lately</th><th style="text-align:right">Before</th></tr></thead><tbody>` + rows.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td>${lift ? `<td class="n" style="color:var(--accent);font-weight:600">${r.lift}×</td>` : ''}<td class="n"><b>${nf(r.recent)}</b></td><td class="n" style="color:var(--muted)">${nf(r.base)}</td></tr>`).join('') + `</tbody></table>`;
  tbl(D.rising_tracks, '#rising', true); tbl(D.recent_top, '#recentTop', false);
  $('#risingArt').innerHTML = `<table><thead><tr><th>Artist</th><th style="text-align:right">Lift</th><th style="text-align:right">Lately</th><th style="text-align:right">Year before</th><th style="text-align:right">All time</th></tr></thead><tbody>` + D.rising_artists.map(r => `<tr><td>${esc(r.artist)}</td><td class="n" style="color:var(--accent);font-weight:600">${r.lift}×</td><td class="n"><b>${nf(r.recent)}</b></td><td class="n" style="color:var(--muted)">${nf(r.base)}</td><td class="n" style="color:var(--muted)">${nf(r.plays)}</td></tr>`).join('') + `</tbody></table>`;
  const top = D.recent_top[0]; const a = D.rising_artists.filter(x => x.base === 0).slice(0, 2);
  $('#latelyNote').innerHTML = `<b>The pattern in the last four months is return, not discovery.</b> The most-played is ${esc(top.track)} — first played in ${top.first.slice(0, 4)}, ${nf(top.plays)} streams since. ${a.length === 2 ? `Alongside it sit ${esc(a[0].artist)} and ${esc(a[1].artist)}, both at zero in the preceding year. ` : ''}This matches the skip curve: reaching for known things deliberately and rejecting the rest.`;
})();

/* ---------- rediscovery ---------- */
(function(){
  const B = D.rediscovery_buckets;
  $('#redBuckets').innerHTML = [['1+', 'away a year or more'], ['2+', 'two years or more'], ['4+', 'four years or more'], ['7+', 'seven years or more']].map(([k, l]) => statTile(nf(B[k]), `${k} years`, l)).join('');
  $('#redTbl').innerHTML = `<table><thead><tr><th>Song</th><th>Artist</th><th style="text-align:right">Streams</th><th style="text-align:right">Years active</th><th style="text-align:right">Last heard</th><th style="text-align:right">Away</th></tr></thead><tbody>` + D.rediscovery.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n"><b>${nf(r.streams)}</b></td><td class="n" style="color:var(--muted)">${r.years}</td><td class="n" style="color:var(--muted)">${r.last}</td><td class="n">${r.away_years} yr</td></tr>`).join('') + `</tbody></table>`;
})();

/* ---------- skip curve (strict + loose + shuffle) ---------- */
(function(){
  const sk = D.skip_strict_by_year; const sh = Object.fromEntries(D.shuffle_by_year.map(r => [r.year, r.shuffle_pct]));
  const padL = 44, padR = 16, padT = 18, padB = 40, W = 760, H = 300; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H);
  const x = i => padL + i * iw / (sk.length - 1), y = v => padT + ih - (v / 80) * ih;
  for (let g = 0; g <= 80; g += 20){ el('line', {x1: padL, y1: y(g), x2: W - padR, y2: y(g), stroke: css('--line')}, s); txt(s, padL - 9, y(g) + 4, g + '%', {'text-anchor': 'end'}); }
  const line = (vals, c) => el('path', {d: vals.map((v, i) => (i ? 'L' : 'M') + x(i) + ' ' + y(v)).join(' '), fill: 'none', stroke: c, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}, s);
  line(sk.map(r => r.strict), css('--s1')); line(sk.map(r => r.loose), css('--s2')); line(sk.map(r => sh[r.year] ?? 0), css('--s3'));
  sk.forEach((r, i) => { [[r.strict, '--s1'], [r.loose, '--s2'], [sh[r.year] ?? 0, '--s3']].forEach(([v, c]) => el('circle', {cx: x(i), cy: y(v), r: 4, fill: css(c), stroke: css('--surface'), 'stroke-width': 2}, s));
    txt(s, x(i), H - 14, String(r.year).slice(2), {'text-anchor': 'middle'});
    hoverable(el('rect', {x: x(i) - iw / (sk.length * 2), y: padT, width: iw / sk.length, height: ih, fill: 'transparent'}, s), `<b>${r.year}</b><br>skipped inside 30s ${r.strict}%<br>cut short ${r.loose}%<br>shuffle ${sh[r.year] ?? 0}%<br>${nf(r.rows)} rows`); });
  $('#skipChart').appendChild(s);
  const lo = sk.reduce((a, b) => b.strict < a.strict ? b : a), last = sk[sk.length - 1], prev = sk[sk.length - 2];
  $('#skipCap').innerHTML = `Low-water mark <b>${lo.strict}% in ${lo.year}</b>; ${last.strict}% in ${last.year}. Years with fewer than 300 rows are excluded.`;
  const j = sk.find(r => r.year === 2025), b = sk.find(r => r.year === 2024);
  $('#skipNote').innerHTML = `<b>Two opposite habits, moving together.</b> Shuffle went from ~10% of plays to effectively zero — you stopped letting the machine choose. But skipping, after eight years of decline, jumped from ${b ? b.strict : '?'}% in 2024 to ${j ? j.strict : '?'}% in 2025 under the strict definition (${b ? b.loose : '?'}% → ${j ? j.loose : '?'}% counting any cut). You are choosing what to play far more deliberately, and rejecting far more of it once it starts.`;
  const bars = (rows, sel, color) => { const max = Math.max(...rows.map(r => r.rate)); $(sel).innerHTML = `<table><thead><tr><th>Artist</th><th style="width:74px"></th><th style="text-align:right">Rate</th><th style="text-align:right">Rows</th></tr></thead><tbody>` + rows.map(r => `<tr><td>${esc(r.artist)}</td><td class="bar-cell"><i style="width:${(r.rate / max * 70).toFixed(1)}px;background:${color}"></i></td><td class="n">${r.rate}%</td><td class="n" style="color:var(--muted)">${nf(r.plays)}</td></tr>`).join('') + `</tbody></table>`; };
  bars(D.artist_skip_high, '#skipHigh', css('--warm')); bars(D.artist_skip_low, '#skipLow', css('--cool'));
})();

/* ---------- how tracks begin ---------- */
(function(){
  const R = D.reason_start_by_year, L = D.reason_start_labels; const years = Object.keys(R).sort();
  const keys = ['trackdone', 'fwdbtn', 'clickrow', 'backbtn', 'appload']; const cols = ['--s1', '--s2', '--s3', '--s4', '--s5'].map(css);
  const padL = 40, padR = 12, padT = 14, padB = 34, W = 760, H = 260; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H); const bw = iw / years.length;
  years.forEach((y, i) => { const row = R[y], tot = Object.values(row).reduce((a, b) => a + b, 0); let acc = 0;
    keys.forEach((k, j) => { const v = row[k] || 0; if (!v) return; const f = v / tot; const rect = el('rect', {x: padL + i * bw + 3, y: padT + ih - (acc + f) * ih, width: bw - 6, height: Math.max(0, f * ih - 2), fill: cols[j]}, s); hoverable(rect, `<b>${y} · ${L[k]}</b><br>${(f * 100).toFixed(1)}% — ${nf(v)} rows`); acc += f; });
    txt(s, padL + i * bw + bw / 2, H - 13, y.slice(2), {'text-anchor': 'middle', 'font-size': 10}); });
  [0, 50, 100].forEach(g => txt(s, padL - 8, padT + ih - g / 100 * ih + 4, g + '%', {'text-anchor': 'end', 'font-size': 10}));
  $('#beginChart').appendChild(s); $('#beginLegend').innerHTML = keys.map((k, j) => `<span><i class="sw" style="background:${cols[j]}"></i>${L[k]}</span>`).join('');
  const last = R[years[years.length - 1]], tot = Object.values(last).reduce((a, b) => a + b, 0), first = R[years[0]], ftot = Object.values(first).reduce((a, b) => a + b, 0);
  $('#beginCap').innerHTML = `In ${years[years.length - 1]}, <b>${((last.fwdbtn || 0) / tot * 100).toFixed(0)}%</b> of tracks began because you pressed forward and <b>${((last.clickrow || 0) / tot * 100).toFixed(0)}%</b> because you clicked a specific row — against ${((first.fwdbtn || 0) / ftot * 100).toFixed(0)}% and ${((first.clickrow || 0) / ftot * 100).toFixed(0)}% in ${years[0]}.`;
})();

/* ---------- exploration ---------- */
(function(){
  const rows = D.monthly.filter(m => m.ym >= '2016-01' && m.streams >= 40); const padL = 42, padR = 12, padT = 16, padB = 34, W = 1000, H = 230; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H);
  const x = i => padL + i * iw / (rows.length - 1), y = v => padT + ih - v / 100 * ih;
  for (let g = 0; g <= 100; g += 25){ el('line', {x1: padL, y1: y(g), x2: W - padR, y2: y(g), stroke: css('--line')}, s); txt(s, padL - 8, y(g) + 4, g + '%', {'text-anchor': 'end', 'font-size': 10}); }
  el('path', {d: rows.map((r, i) => (i ? 'L' : 'M') + x(i) + ' ' + y(r.explore_pct)).join(' ') + ` L${x(rows.length - 1)} ${y(0)} L${x(0)} ${y(0)} Z`, fill: css('--accent'), opacity: .12}, s);
  el('path', {d: rows.map((r, i) => (i ? 'L' : 'M') + x(i) + ' ' + y(r.explore_pct)).join(' '), fill: 'none', stroke: css('--accent'), 'stroke-width': 2, 'stroke-linejoin': 'round'}, s);
  rows.forEach((r, i) => { if (r.ym.endsWith('-01')) txt(s, x(i), H - 14, r.ym.slice(0, 4), {'text-anchor': 'middle', 'font-size': 10}); hoverable(el('rect', {x: x(i) - iw / rows.length / 2, y: padT, width: iw / rows.length, height: ih, fill: 'transparent'}, s), `<b>${r.ym}</b><br>exploration ${r.explore_pct}%<br>${nf(r.new_tracks)} new tracks · ${nf(r.streams)} streams`); });
  $('#exploreChart').appendChild(s);
  const hi = rows.reduce((a, b) => b.explore_pct > a.explore_pct ? b : a), recent = rows.slice(-6); const avgR = recent.reduce((a, b) => a + b.explore_pct, 0) / recent.length;
  $('#exploreCap').innerHTML = `Most exploratory month: <b>${hi.ym}</b> at ${hi.explore_pct}%. The last six months average <b>${avgR.toFixed(0)}%</b> — ${avgR < 25 ? 'comfort listening, by a wide margin' : avgR < 45 ? 'mostly comfort, with a live edge of discovery' : 'genuinely exploratory'}.`;
})();

/* ---------- retention ---------- */
(function(){
  const rows = D.retention.filter(r => r.year >= 2015); const padL = 42, padR = 14, padT = 16, padB = 36, W = 760, H = 260; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H); const bw = iw / rows.length;
  for (let g = 0; g <= 60; g += 20){ el('line', {x1: padL, y1: padT + ih - g / 65 * ih, x2: W - padR, y2: padT + ih - g / 65 * ih, stroke: css('--line')}, s); txt(s, padL - 8, padT + ih - g / 65 * ih + 4, g + '%', {'text-anchor': 'end', 'font-size': 10}); }
  rows.forEach((r, i) => { const x0 = padL + i * bw + 4, w = (bw - 10) / 2;
    if (r.r90 != null){ const h = r.r90 / 65 * ih; hoverable(el('rect', {x: x0, y: padT + ih - h, width: w, height: h, rx: 2, fill: css('--s1')}, s), `<b>${r.year} cohort</b> · ${nf(r.tracks)} tracks<br>${r.r90}% returned after 90 days`); }
    if (r.r365 != null){ const h = r.r365 / 65 * ih; hoverable(el('rect', {x: x0 + w + 2, y: padT + ih - h, width: w, height: h, rx: 2, fill: css('--s2')}, s), `<b>${r.year} cohort</b> · ${nf(r.tracks)} tracks<br>${r.r365}% returned after a year`); }
    txt(s, padL + i * bw + bw / 2, H - 14, String(r.year).slice(2), {'text-anchor': 'middle', 'font-size': 10}); });
  $('#retChart').appendChild(s);
  const a = rows.find(r => r.year === 2016), b = rows.filter(r => r.r365 != null).slice(-1)[0], big = rows.reduce((p, c) => c.tracks > p.tracks ? c : p);
  $('#retCap').innerHTML = `Cohort sizes range from ${nf(Math.min(...rows.map(r => r.tracks)))} to <b>${nf(big.tracks)} (${big.year})</b> tracks first heard.`;
  $('#retNote').innerHTML = `<b>Discoveries stick less and less.</b> Of the tracks you first heard in ${a.year}, ${a.r365}% came back a year later. Of the ${nf(big.tracks)} first heard in ${big.year} — your biggest year of discovery by far — <b>${big.r365}%</b> did. By ${b.year} it was ${b.r365}%. You hear far more new music than you used to, and keep almost none of it; the favourites are old.`;
})();

/* ---------- sessions + styles ---------- */
(function(){
  const S = D.sessions; $('#sessCount').textContent = nf(S.count); $('#medMin').textContent = S.median_min;
  $('#styles').innerHTML = D.session_styles.map(s => statTile(s.share + '%', s.style, `${nf(s.sessions)} sittings · median ${s.median_streams} streams, ${s.median_min} min<br><span style="color:var(--muted)">${s.definition}</span>`)).join('');
  const rows = D.session_by_year.filter(r => r.sessions > 40); const padL = 44, padR = 14, padT = 16, padB = 36, W = 480, H = 260; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H); const max = Math.max(...rows.map(r => r.median_min)) * 1.15; const bw = iw / rows.length;
  for (let g = 0; g <= 90; g += 30){ el('line', {x1: padL, y1: padT + ih - g / max * ih, x2: W - padR, y2: padT + ih - g / max * ih, stroke: css('--line')}, s); txt(s, padL - 8, padT + ih - g / max * ih + 4, g, {'text-anchor': 'end', 'font-size': 10}); }
  rows.forEach((r, i) => { const h = r.median_min / max * ih; hoverable(el('rect', {x: padL + i * bw + 3, y: padT + ih - h, width: bw - 6, height: h, rx: 3, fill: css('--accent')}, s), `<b>${r.year}</b><br>median ${r.median_min} min<br>${nf(r.sessions)} sittings`); txt(s, padL + i * bw + bw / 2, H - 14, String(r.year).slice(2), {'text-anchor': 'middle', 'font-size': 10}); });
  txt(s, padL - 8, padT - 4, 'min', {'text-anchor': 'end', 'font-size': 9.5}); $('#sessChart').appendChild(s);
  $('#sessStats').innerHTML = `<h3 style="margin-bottom:14px">Shape of a sitting</h3><table><tbody><tr><td>Median length</td><td class="n">${S.median_min} min</td></tr><tr><td>Median tracks</td><td class="n">${S.median_tracks}</td></tr><tr><td>Mean length</td><td class="n">${S.mean_min} min</td></tr><tr><td>Over 1 hour</td><td class="n">${nf(S.over_1h)}</td></tr><tr><td>Over 4 hours</td><td class="n">${nf(S.over_4h)}</td></tr><tr><td>Over 8 hours</td><td class="n">${nf(S.over_8h)}</td></tr></tbody></table><p class="cap" style="margin-top:14px"><b>${(S.over_1h / S.count * 100).toFixed(0)}%</b> of sittings run past an hour.</p><h3 style="margin:22px 0 10px">What starts a sitting</h3><div class="pillrow">${D.session_openers.slice(0, 9).map(o => `<span class="pill">${esc(o.artist)} · ${o.n}</span>`).join('')}</div>`;
  $('#longTbl').innerHTML = `<table><thead><tr><th>Date</th><th style="text-align:right">Began</th><th style="text-align:right">Hours</th><th style="text-align:right">Tracks</th><th>Dominated by</th><th>Opened with</th></tr></thead><tbody>` + D.longest_sessions.map(r => `<tr><td class="n" style="text-align:left">${r.date}</td><td class="n">${String(r.start_hour).padStart(2,'0')}:00</td><td class="n">${r.hours}</td><td class="n">${r.tracks}</td><td>${esc(r.top_artist)}</td><td class="who">${esc(r.opened_with)}</td></tr>`).join('') + `</tbody></table>`;
})();

/* ---------- completion ---------- */
$('#compTbl').innerHTML = `<table><thead><tr><th>Track</th><th>Artist</th><th style="width:80px"></th><th style="text-align:right">Heard</th><th style="text-align:right">Plays</th></tr></thead><tbody>` + D.completion_low.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="bar-cell"><i style="width:${(r.completion / 100 * 76).toFixed(1)}px;background:var(--warm)"></i></td><td class="n">${r.completion}%</td><td class="n" style="color:var(--muted)">${r.plays}</td></tr>`).join('') + `</tbody></table>`;

/* ---------- eras, arcs, albums, breadth ---------- */
$('#eraTbl').innerHTML = `<table><thead><tr><th>Year</th><th>Leading artist</th><th>Also defining the year</th><th style="text-align:right">Leader streams</th><th style="text-align:right">Hours</th></tr></thead><tbody>` + D.eras.map(e => `<tr><td class="n" style="text-align:left"><b>${e.year}</b></td><td>${esc(e.top[0].artist)}</td><td class="who">${e.top.slice(1).map(a => esc(a.artist)).join(' · ')}</td><td class="n">${nf(e.top[0].streams)}</td><td class="n" style="color:var(--muted)">${nf(e.hours)}</td></tr>`).join('') + `</tbody></table>`;
(function(){ const tbl = (rows, sel, life) => $(sel).innerHTML = `<table><thead><tr><th>Artist</th><th style="text-align:right">${life ? 'Years' : 'Peak'}</th><th style="text-align:right">${life ? 'Span' : 'In peak yr'}</th><th style="text-align:right">Streams</th></tr></thead><tbody>` + rows.map(r => `<tr><td>${esc(r.artist)}</td><td class="n">${life ? r.years_active : r.peak_year}</td><td class="n" style="color:var(--muted)">${life ? r.first.slice(0, 4) + '–' + r.last.slice(0, 4) : r.concentration + '%'}</td><td class="n">${nf(r.plays)}</td></tr>`).join('') + `</tbody></table>`; tbl(D.lifers, '#lifers', true); tbl(D.flares, '#flares', false); })();
const albTbl = rows => `<table><thead><tr><th>Album</th><th>Artist</th><th style="text-align:right">Streams</th><th style="text-align:right">Tracks</th><th style="text-align:right">Hours</th></tr></thead><tbody>` + rows.map(a => `<tr><td>${esc(a.album)}</td><td class="who">${esc(a.artist)}</td><td class="n"><b>${nf(a.streams)}</b></td><td class="n" style="color:var(--muted)">${a.tracks}</td><td class="n" style="color:var(--muted)">${a.hours}</td></tr>`).join('') + `</tbody></table>`;
$('#albTop').innerHTML = albTbl(D.albums_top); $('#albInside').innerHTML = albTbl(D.albums_inside);
$('#breadthTbl').innerHTML = `<table><thead><tr><th>Artist</th><th style="text-align:right">Distinct recordings</th><th style="text-align:right">Streams</th><th style="text-align:right">Hours</th></tr></thead><tbody>` + D.breadth.map(a => `<tr><td>${esc(a.artist)}</td><td class="n"><b>${nf(a.tracks)}</b></td><td class="n" style="color:var(--muted)">${nf(a.streams)}</td><td class="n" style="color:var(--muted)">${a.hours}</td></tr>`).join('') + `</tbody></table>`;

/* ---------- library ---------- */
(function(){
  const G = D.saved_gap, tot = D.saved_total; $('#savedTotal').textContent = nf(tot);
  $('#savedStats').innerHTML = ['Never heard', 'Sampled', 'Dormant', 'Active'].map(k => statTile(nf(G[k] || 0), k, `${((G[k] || 0) / tot * 100).toFixed(0)}% of the library`)).join('');
  const t = (rows, sel) => $(sel).innerHTML = `<table><thead><tr><th>Track</th><th>Artist</th><th style="text-align:right">Streams</th><th style="text-align:right">Last heard</th></tr></thead><tbody>` + rows.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n">${nf(r.streams)}</td><td class="n" style="color:var(--muted)">${r.last || '—'}</td></tr>`).join('') + `</tbody></table>`;
  t((D.saved_examples['Never heard'] || []).slice(0, 10), '#savedNever'); t((D.saved_examples['Dormant'] || []).slice(0, 10), '#savedDormant');
  $('#lnsTotal').textContent = nf(D.loved_not_saved_total);
  $('#lnsTbl').innerHTML = `<table><thead><tr><th>Song</th><th>Artist</th><th style="text-align:right">Streams</th><th style="text-align:right">Last heard</th></tr></thead><tbody>` + D.loved_not_saved.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n"><b>${nf(r.streams)}</b></td><td class="n" style="color:var(--muted)">${r.last}</td></tr>`).join('') + `</tbody></table>`;
  const max = Math.max(...D.playlists.map(p => p.recent), 1);
  $('#plTbl').innerHTML = `<table><thead><tr><th>Playlist</th><th style="width:70px"></th><th style="text-align:right">Lately</th><th style="text-align:right">All time</th><th style="text-align:right">Tracks</th><th style="text-align:right">Never played</th><th style="text-align:right">Last edited</th><th>Most played track</th></tr></thead><tbody>` + D.playlists.map(p => `<tr><td>${esc(p.name)}</td><td class="bar-cell"><i style="width:${(p.recent / max * 64).toFixed(1)}px;background:var(--accent)"></i></td><td class="n"><b>${nf(p.recent)}</b></td><td class="n" style="color:var(--muted)">${nf(p.plays)}</td><td class="n" style="color:var(--muted)">${p.size}</td><td class="n" style="color:${p.never ? 'var(--warm)' : 'var(--muted)'}">${p.never || '—'}</td><td class="n" style="color:var(--muted)">${esc(p.modified || '—')}</td><td class="who">${esc(p.top)}</td></tr>`).join('') + `</tbody></table>`;
  const S = D.search;
  $('#searchStats').innerHTML = [statTile(nf(S.queries), 'Search bursts', 'recorded in the account export'), statTile(nf(S.with_interaction), 'Tapped a result', `${(S.with_interaction / S.queries * 100).toFixed(0)}% of searches`), statTile(nf(S.converted), 'Led to a listen', `within seven days · ${S.with_interaction ? (S.converted / S.with_interaction * 100).toFixed(0) : 0}% of taps`), statTile(nf(S.queries - S.with_interaction), 'Abandoned', 'typed, nothing tapped')].join('');
  $('#searches').innerHTML = S.top.map(([q, n]) => `<span class="pill">${esc(q)}${n > 1 ? ' · ' + n : ''}</span>`).join('');
})();

/* ---------- platform + devices + health ---------- */
(function(){
  const P = D.platform_by_year; const years = Object.keys(P).filter(y => Object.values(P[y]).reduce((a, b) => a + b, 0) > 300).sort(); const fams = ['iPhone / iPad', 'Cast / speaker', 'Windows', 'Android', 'Web player', 'Mac']; const cols = ['--s1', '--s2', '--s3', '--s4', '--s5', '--q5'].map(css);
  const padL = 40, padR = 12, padT = 14, padB = 34, W = 480, H = 260; const iw = W - padL - padR, ih = H - padT - padB; const s = svg(W, H); const bw = iw / years.length;
  years.forEach((y, i) => { const row = P[y], tot = Object.values(row).reduce((a, b) => a + b, 0); let acc = 0; fams.forEach((f, k) => { const v = row[f] || 0; if (!v) return; const frac = v / tot; hoverable(el('rect', {x: padL + i * bw + 3, y: padT + ih - (acc + frac) * ih, width: bw - 6, height: Math.max(0, frac * ih - 2), fill: cols[k]}, s), `<b>${y} · ${f}</b><br>${(frac * 100).toFixed(1)}% — ${nf(v)} plays`); acc += frac; }); txt(s, padL + i * bw + bw / 2, H - 13, y.slice(2), {'text-anchor': 'middle', 'font-size': 10}); });
  [0, 50, 100].forEach(g => txt(s, padL - 8, padT + ih - g / 100 * ih + 4, g + '%', {'text-anchor': 'end', 'font-size': 10}));
  $('#platChart').appendChild(s); $('#platLegend').innerHTML = fams.filter(f => years.some(y => P[y][f])).map((f) => `<span><i class="sw" style="background:${cols[fams.indexOf(f)]}"></i>${f}</span>`).join('');
  const T = D.tech, w = T.routes_window;
  $('#devPanel').innerHTML = `<h3>Actual hardware</h3><p class="cap" style="margin:0 0 14px">Technical logs, <b>${w ? w.first + ' → ' + w.last : 'n/a'}</b>, merged from ${T.merged_from.length} exports.</p><table><thead><tr><th>Output</th><th style="text-align:right">Segments</th><th style="text-align:right">Days</th></tr></thead><tbody>` + T.routes.map(r => `<tr><td>${esc(r.name)}</td><td class="n">${nf(r.n)}</td><td class="n" style="color:var(--muted)">${r.days}</td></tr>`).join('') + `</tbody></table><p class="cap" style="margin-top:14px">Lyrics opened on <b>${T.lyrics.days}</b> separate days. ${T.car.events} car-detection events, none resolving to a connected car. <b>${(T.discovered.cast_audio || 0) + (T.discovered.cast_video || 0)}</b> cast targets and ${T.discovered.tv || 0} TVs seen on your network.</p>`;
  const H2 = T.health;
  $('#healthStats').innerHTML = [statTile(nf(H2.library_adds), 'Library adds', 'tracks saved in the window'), statTile(nf(H2.playlist_adds) + ' / ' + nf(H2.playlist_removes), 'Playlist adds / removes', `${H2.playlists_created} playlists created`), statTile(nf(H2.release_radar_tracks), 'Release Radar tracks served', `across ${nf(H2.release_radar_batches)} batches`), statTile(nf(H2.dj_tracks_served), 'DJ tracks served', `${H2.dj_sessions} session · ${H2.dj_heard} you had heard before`), statTile(nf(H2.stutters), 'Stutters', 'buffer underruns logged'), statTile(nf(H2.playback_errors), 'Playback errors', `${H2.fatal_errors} fatal`), statTile(nf(T.lyrics.n), 'Lyrics views', `on ${T.lyrics.days} days`), statTile(nf(T.on_repeat_snapshots), 'On Repeat snapshots', 'mix regenerations logged')].join('');
  $('#orSnaps').textContent = nf(T.on_repeat_snapshots);
  $('#orTbl').innerHTML = `<table><thead><tr><th>Track</th><th>Artist</th><th style="text-align:right">Snapshots</th><th style="text-align:right">Lifetime</th></tr></thead><tbody>` + T.on_repeat_joined.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n"><b>${r.snapshots}</b></td><td class="n" style="color:var(--muted)">${nf(r.streams)}</td></tr>`).join('') + `</tbody></table>`;
  $('#daylists').innerHTML = T.daylist_titles.map(d => `<span class="pill">${esc(d)}</span>`).join('') || '<span class="cap">None in the window.</span>';
})();

/* ---------- foreign days ---------- */
(function(){
  const F = D.foreign_days || [];
  if (!F.length){ $('#foreignBox').innerHTML = '<div class="panel"><p class="cap" style="margin:0">None detected. Every day of the record plays like you.</p></div>'; return; }
  $('#foreignBox').innerHTML = F.map(f => `<div class="note warnnote" style="margin-top:0"><b>${fmtD(f.date)} — ${nf(f.streams)} streams, ${f.alien_share}% from artists heard on no other day.</b><br>
    Played: ${f.top_artists.map(esc).join(', ')}.<br>
    From: ${Object.entries(f.platforms).map(([p, n]) => `${esc(p)} ×${n}`).join(', ')} · in: ${Object.entries(f.countries).map(([c, n]) => `${esc(c)} ×${n}`).join(', ')}. The dominant pair — <b>${esc(f.device)}</b> — accounts for ${f.device_lifetime_share}% of everything you have ever streamed.<br>
    <span style="color:var(--muted)">Nothing on this day matches your listening on any other day of the record. It is treated as someone else on the account and left out of every figure above. If you did not recognise it at the time, Spotify's account page has "Sign out everywhere".</span></div>`).join('');
})();

/* ---------- geography ---------- */
(function(){ const names = {FR:'France', DE:'Germany', PL:'Poland', CA:'Canada', AU:'Australia', RU:'Russia', IL:'Israel', GB:'United Kingdom', ZZ:'Unresolved (VPN)', NL:'Netherlands', IT:'Italy', ES:'Spain', MX:'Mexico', UA:'Ukraine', BR:'Brazil', CO:'Colombia', AR:'Argentina'};
  $('#geoTbl').innerHTML = `<table><thead><tr><th>Country</th><th style="text-align:right">Days with plays</th><th style="text-align:right">First</th><th style="text-align:right">Last</th></tr></thead><tbody>` + D.abroad.map(r => `<tr><td>${esc(names[r.country] || r.country)} <span class="mono" style="color:var(--muted);font-size:11px">${r.country}</span></td><td class="n">${r.days}</td><td class="n" style="color:var(--muted)">${r.first}</td><td class="n" style="color:var(--muted)">${r.last}</td></tr>`).join('') + `</tbody></table>`; })();

/* ---------- Spotify's view ---------- */
(function(){
  $('#tasteQuote').innerHTML = D.taste_identity ? esc(D.taste_identity).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>') : 'No taste profile in the export.';
  const W2 = D.wrapped, mine = D.by_year.find(y => y.year === 2025);
  $('#wrapStats').innerHTML = [statTile(nf(W2.hours) + 'h', 'Hours, per Spotify', `this page counts ${mine ? nf(mine.hours) : '—'}h for 2025`), statTile(nf(W2.unique_artists), 'Unique artists', `this page: ${mine ? nf(mine.artists) : '—'}`), statTile(W2.top_fan_pct + '%', 'Top-fan percentile', 'of your #1 artist\'s listeners'), statTile(nf(W2.listening_age), 'Listening age', `Spotify's estimate · ${nf(W2.genres)} genres touched`)].join('');
  $('#wrapTbl').innerHTML = `<table><thead><tr><th>Track</th><th>Artist</th><th style="text-align:right">Wrapped count</th><th style="text-align:right">Hours</th></tr></thead><tbody>` + W2.tracks.map(r => `<tr><td>${esc(r.track)}</td><td class="who">${esc(r.artist)}</td><td class="n"><b>${nf(r.count)}</b></td><td class="n" style="color:var(--muted)">${r.hours}</td></tr>`).join('') + `</tbody></table>`;
  const T = D.tech;
  $('#inf1p').innerHTML = D.inferences_1p.map(i => `<span class="pill">${esc(i)}</span>`).join(''); $('#infBrands').innerHTML = D.inference_brands.map(i => `<span class="pill">${esc(i)}</span>`).join('');
  $('#infNote').innerHTML = `Spotify files you under <b>${nf(T.inference_count)}</b> audience segments, <b>${D.inference_artist_affinities}</b> of them opaque artist-affinity hashes. The advertiser pools are the notable part: pharmaceutical brands, telecoms and carmakers. None of this is derived from anything you told Spotify; it is inferred from listening, device and location.`;
})();

/* ---------- method ---------- */
(function(){
  const builds = [
    {t: 'dashboard.html (143 KB)', w: '25 May 2026 · local file', p: 'Read the technical logs — 7,693 plays over six months — and got real per-song depth: play counts, first and last play, skips, distinct days, top device, hour-of-day and weekday charts in UTC. Answered <b>how much, lately</b>.'},
    {t: 'dashboard.html (1 MB)', w: '26 May 2026 · local file', p: 'Swapped in the fifteen-year history but kept only aggregate views: plays per year, per month, discovery per month, genres. Answered <b>how much, ever</b>.'},
    {t: 'Windows Down · A Listening Life', w: '31 July 2026 · published artifact', p: 'Folded in a 2011 iPhone library, a 2012 iTunes screenshot and 56 playlist exports; cross-referenced every saved track to surface 4,476 saved and never played. Answered <b>what, and since when</b>.'},
    {t: 'Listening Dossier — 2,395 Liked Songs', w: '6 August 2026 · published artifact', p: 'The Liked Songs collection on its own terms — hours against hearts, then eight recommendation lanes. Answered <b>what you keep</b>.'},
    {t: 'The Listening Machine', w: 'This page', now: true, p: 'The behavioural pass, in local time: the clock, skips, sessions, love arcs, loops, retention, exploration, the library audit, the hardware, and what Spotify infers. Answers <b>how</b>.'},
  ];
  $('#lin').innerHTML = builds.map(b => `<div class="rail"><span class="dot${b.now ? ' now' : ''}"></span></div><div class="lincard"><h4>${b.t}</h4><div class="when">${b.w}</div><p>${b.p}</p></div>`).join('');
  const last = new Date(D.window.last + 'T00:00:00'), gen = new Date(D.generated + 'T00:00:00'); const stale = Math.round((gen - last) / 86400000); const tw = D.tech.routes_window; const fmt = d => d.toLocaleDateString('en-GB', {day: 'numeric', month: 'long', year: 'numeric'}); const nextBy = fmt(new Date(new Date(tw.last + 'T00:00:00').getTime() + 85 * 86400000));
  $('#refreshNote').innerHTML = `<b>Rebuilt ${fmt(gen)} from the September export.</b> The history runs to ${fmt(last)} (${stale} days behind the rebuild). The technical logs are merged from <b>${D.tech.merged_from.length}</b> separate exports into one record, ${tw.first} → ${tw.last}, with a gap where no export covered late May to mid June. Spotify discards those logs after about ninety days, so to keep the record continuous, <b>request the next export before ${nextBy}</b>.`;

  const rows = [
    ['Time zone for hours and weekdays', 'UTC, as supplied', 'Converted to Eastern before any hour or weekday is derived', 'y'],
    ['Hour × weekday heatmap', 'Separate hour and weekday charts', 'One 7 × 24 grid, plus the over-represented artist per hour', 'y'],
    ['Love arcs (love signal = 5th stream in 30 days)', 'Yes, with monthly sparkline and four arc types', 'Adopted, same definition, same four types', '='],
    ['Dated opening plays of each favourite', 'First listen date only', 'First five plays with minute, device and seconds heard', 'y'],
    ['Repeat loops', 'Yes', 'Adopted', '='],
    ['Rediscovery queue', 'Yes', 'Adopted', '='],
    ['Discovery retention by cohort', 'Yes', 'Adopted', '='],
    ['Exploration share', 'Yes', 'Adopted', '='],
    ['Session styles', 'Yes, four types', 'Adopted, own definitions stated', '='],
    ['Skip rate', 'Per track and session; strict definition', 'By year, both definitions; per-artist most and least', 'y'],
    ['Reason a track began', 'Yes', 'Adopted', '='],
    ['Taste eras, albums, breadth', 'Yes', 'Adopted', '='],
    ['Saved-library audit; loved-but-not-saved', 'Yes', 'Adopted', '='],
    ['Search-to-listen conversion', 'Yes', 'Adopted', '='],
    ['Playlist pull-through', 'Yes', 'Yes', '='],
    ['Country of play', 'No', 'Yes, with the VPN and single-day artifacts flagged', 'y'],
    ['Advertiser inference segments', 'Counted, hidden on principle', 'Shown — they are yours to see', 'y'],
    ['Wrapped 2025, taste profile, On Repeat, daylist', 'Yes', 'Adopted', '='],
    ['Recommendations', 'From an August audio-feature cache', 'Not here; the Listening Dossier holds eight lanes', 'n'],
    ['CSV exports', 'Yes', 'Adopted', '='],
    ['Hosted copy with a stable link', 'No', 'Yes', 'y'],
    ['Accepts Spotify\'s zip directly', 'Yes', 'No — extract first', 'n'],
  ];
  $('#cmpBody').innerHTML = rows.map(([q, a, b, m]) => `<tr><td>${q}</td><td class="nn">${a}</td><td class="${m === 'y' ? 'y' : m === 'n' ? 'nn' : ''}">${b}</td></tr>`).join('');
  const defs = [['Stream', 'a play of at least thirty seconds — Spotify\'s own bar'], ['Skip', 'a track ended by the forward button, or flagged skipped, inside thirty seconds'], ['Cut short', 'a track ended by the forward button at any point'], ['Sitting / session', 'consecutive streams with no gap over thirty minutes'], ['Love signal', 'the fifth stream of a track inside a trailing thirty-day window'], ['Durable favourite', 'a track with twenty-five or more lifetime streams'], ['Repeat loop', 'three or more consecutive streams of one recording, nothing between'], ['Exploration share', 'streams of tracks within thirty days of their first stream ÷ all streams in the month'], ['Retention', 'a track streamed again at least 90 / 365 days after its first stream'], ['Dormant', 'saved, five or more streams, none in the last year'], ['Completion', 'a track\'s longest recorded listen stands in for its length'], ['Lift', 'recent share ÷ baseline share; or an hour\'s share ÷ the all-time share'], ['Local time', 'every timestamp converted from UTC to America/New_York before any hour, weekday, date or month is derived']];
  $('#defBody').innerHTML = defs.map(([k, v]) => `<tr><td style="white-space:nowrap"><b>${k}</b></td><td class="who" style="font-size:13.5px;color:var(--ink-2)">${v}</td></tr>`).join('');
  $('#csvList').innerHTML = CSVS.map(f => `<span class="pill">${esc(f)}</span>`).join('');
})();
</script>
"""

out = os.path.join(HERE, "listening-machine.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(HTML.replace("__PAYLOAD__", payload).replace("__CSVS__", json.dumps(csv_files)))
print(f"wrote {out} ({os.path.getsize(out)/1024:.0f} KB) · payload {len(payload)/1024:.0f} KB · {len(csv_files)} CSVs")
