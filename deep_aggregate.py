"""
Deep aggregation over the full Spotify archive.

Mines the seams the earlier dashboards dropped: local-time clock, skip anatomy,
shuffle, listening sessions, geography, device history, completion rate.

Output: deep.json  (consumed by the dashboard build step)
"""
import json, glob, os, sys, datetime, statistics
from collections import defaultdict, Counter

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/New_York")
except Exception:                                    # pragma: no cover
    TZ = datetime.timezone(datetime.timedelta(hours=-5))

import paths
_P   = paths.resolve_all()
EXT  = _P["extended"]
ACCT = _P["account"]
TECH = _P["technical"]
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep.json")

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SESSION_GAP = 30 * 60          # seconds of silence that ends a session
MIN_PLAY_MS = 30_000           # Spotify's own "counts as a play" threshold


def load_all(pattern):
    rows = []
    for f in sorted(glob.glob(os.path.join(EXT, pattern))):
        with open(f, encoding="utf-8") as fh:
            rows.extend(json.load(fh))
    return rows


def parse(ts):
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)


print("loading extended streaming history ...", flush=True)
audio = load_all("Streaming_History_Audio_*.json")
video = load_all("Streaming_History_Video_*.json")
print(f"  {len(audio):,} audio rows, {len(video):,} video rows", flush=True)

# ---------------------------------------------------------------- decorate
for r in audio:
    utc = parse(r["ts"])
    loc = utc.astimezone(TZ)
    r["_utc"] = utc
    r["_loc"] = loc
    r["_hour"] = loc.hour
    r["_dow"] = loc.weekday()
    r["_year"] = loc.year
    r["_ym"] = f"{loc.year}-{loc.month:02d}"
    r["_mon"] = loc.month
    r["_date"] = loc.date().isoformat()

audio.sort(key=lambda r: r["_utc"])

songs = [r for r in audio if r.get("master_metadata_track_name")]
pods  = [r for r in audio if r.get("episode_name")]
books = [r for r in audio if r.get("audiobook_title")]
# a "play" = the >=30s bar Spotify itself uses
plays = [r for r in songs if r["ms_played"] >= MIN_PLAY_MS]

print(f"  songs={len(songs):,} plays>=30s={len(plays):,} "
      f"podcast={len(pods):,} audiobook={len(books):,}", flush=True)

# ---------------------------------------------------------------- foreign days
# Someone else on the account leaves two marks at once: artists that appear on
# no other day of a fifteen-year record, AND a device-country pair the account
# otherwise never uses. Either alone misfires — a day of rain-sound content
# farms on the home speaker trips the taste test; a trip abroad on the usual
# phone trips the device test. Both together do not.
def _fam(p):
    p = (p or "").lower()
    return ("ios" if "ios" in p or "iphone" in p or "ipad" in p else
            "android" if "android" in p else
            "mac" if "osx" in p or "mac" in p else
            "windows" if "win" in p else
            "cast" if "cast" in p else "web" if "web" in p else "other")

_day_art = defaultdict(Counter)
_day_pc = defaultdict(Counter)
_pc_all = Counter()
for r in plays:
    _day_art[r["_date"]][r["master_metadata_album_artist_name"]] += 1
    pc = (_fam(r["platform"]), r["conn_country"])
    _day_pc[r["_date"]][pc] += 1
    _pc_all[pc] += 1
_art_days = defaultdict(set)
for d, c in _day_art.items():
    for a in c:
        _art_days[a].add(d)
_total = len(plays)
foreign = []
for d, c in _day_art.items():
    n = sum(c.values())
    if n < 50:
        continue
    alien = sum(k for a, k in c.items() if len(_art_days[a]) == 1)
    top_pc, top_n = _day_pc[d].most_common(1)[0]
    rare_device = _pc_all[top_pc] / _total < 0.01 and top_n / n >= 0.5
    if alien / n >= 0.70 and rare_device:
        plats = Counter(r["platform"] for r in plays if r["_date"] == d)
        ctry = Counter(r["conn_country"] for r in plays if r["_date"] == d)
        foreign.append({"date": d, "streams": n, "alien_share": round(alien / n * 100, 1),
                        "device": f"{top_pc[0]} in {top_pc[1]}",
                        "device_lifetime_share": round(_pc_all[top_pc] / _total * 100, 2),
                        "top_artists": [a for a, _ in c.most_common(5)],
                        "platforms": dict(plats.most_common(4)),
                        "countries": dict(ctry.most_common(4))})
foreign.sort(key=lambda x: x["date"])
_fdays = {f["date"] for f in foreign}
if foreign:
    print(f"  excluding {len(foreign)} foreign day(s): "
          + ", ".join(f"{f['date']} ({f['streams']} streams)" for f in foreign), flush=True)
    songs = [r for r in songs if r["_date"] not in _fdays]
    plays = [r for r in plays if r["_date"] not in _fdays]

D = {}
D["foreign_days"] = foreign
D["generated"] = datetime.datetime.now(TZ).isoformat()
D["window"] = {"first": songs[0]["_date"], "last": songs[-1]["_date"]}

# ---------------------------------------------------------------- 1. clock
clock = [[0] * 24 for _ in range(7)]          # dow x hour, plays
clock_ms = [[0] * 24 for _ in range(7)]
for r in plays:
    clock[r["_dow"]][r["_hour"]] += 1
    clock_ms[r["_dow"]][r["_hour"]] += r["ms_played"]

hour_tot = [0] * 24
for r in plays:
    hour_tot[r["_hour"]] += 1

D["clock"] = {"dow_hour": clock, "dow_hour_ms": clock_ms,
              "hour_total": hour_tot, "dow_labels": DOW}

# what defines each hour: top artist whose share of that hour most exceeds
# its share of the whole record  (distinctiveness, not just volume)
art_tot = Counter(r["master_metadata_album_artist_name"] for r in plays)
grand = sum(art_tot.values())
hour_art = defaultdict(Counter)
for r in plays:
    hour_art[r["_hour"]][r["master_metadata_album_artist_name"]] += 1

hour_signature = []
for h in range(24):
    c = hour_art[h]
    tot = sum(c.values()) or 1
    best, bestscore, bestn = None, 0, 0
    for a, n in c.items():
        if n < 40 or not a:
            continue
        lift = (n / tot) / (art_tot[a] / grand)
        if lift > bestscore:
            best, bestscore, bestn = a, lift, n
    hour_signature.append({"hour": h, "artist": best,
                           "lift": round(bestscore, 2), "plays": bestn,
                           "total": tot})
D["hour_signature"] = hour_signature

# ---------------------------------------------------------------- 2. skips
def skipped(r):
    """A real skip: cut short by a forward press, not a natural end."""
    return r["reason_end"] in ("fwdbtn", "endplay") or r.get("skipped")

sk_year = defaultdict(lambda: {"plays": 0, "skips": 0})
for r in songs:
    y = r["_year"]
    sk_year[y]["plays"] += 1
    if skipped(r):
        sk_year[y]["skips"] += 1

D["skip_by_year"] = [
    {"year": y, "plays": v["plays"], "skips": v["skips"],
     "rate": round(v["skips"] / v["plays"] * 100, 1)}
    for y, v in sorted(sk_year.items())]

reason_year = defaultdict(Counter)
for r in songs:
    reason_year[r["_year"]][r["reason_end"] or "unknown"] += 1
D["reason_by_year"] = {str(y): dict(c.most_common(8))
                       for y, c in sorted(reason_year.items())}

# per-artist skip rate (artists with real volume only)
a_sk = defaultdict(lambda: {"n": 0, "s": 0})
for r in songs:
    a = r["master_metadata_album_artist_name"]
    if not a:
        continue
    a_sk[a]["n"] += 1
    if skipped(r):
        a_sk[a]["s"] += 1
D["artist_skip"] = sorted(
    [{"artist": a, "plays": v["n"], "skips": v["s"],
      "rate": round(v["s"] / v["n"] * 100, 1)}
     for a, v in a_sk.items() if v["n"] >= 150],
    key=lambda x: -x["rate"])

# ---------------------------------------------------------------- 3. shuffle / offline
sh_year = defaultdict(lambda: {"n": 0, "sh": 0, "off": 0, "inc": 0})
for r in songs:
    y = r["_year"]
    sh_year[y]["n"] += 1
    if r.get("shuffle"):
        sh_year[y]["sh"] += 1
    if r.get("offline"):
        sh_year[y]["off"] += 1
    if r.get("incognito_mode"):
        sh_year[y]["inc"] += 1
D["shuffle_by_year"] = [
    {"year": y, "plays": v["n"],
     "shuffle_pct": round(v["sh"] / v["n"] * 100, 1),
     "offline_pct": round(v["off"] / v["n"] * 100, 1),
     "incognito": v["inc"]}
    for y, v in sorted(sh_year.items())]

# ---------------------------------------------------------------- 4. sessions
sessions = []
cur = None
for r in plays:
    if cur and (r["_utc"] - cur["end_utc"]).total_seconds() <= SESSION_GAP:
        cur["n"] += 1
        cur["ms"] += r["ms_played"]
        cur["end_utc"] = r["_utc"] + datetime.timedelta(
            milliseconds=r["ms_played"])
        cur["artists"][r["master_metadata_album_artist_name"]] += 1
        cur["last"] = r
    else:
        if cur:
            sessions.append(cur)
        cur = {"start": r["_loc"], "n": 1, "ms": r["ms_played"],
               "end_utc": r["_utc"] + datetime.timedelta(
                   milliseconds=r["ms_played"]),
               "artists": Counter([r["master_metadata_album_artist_name"]]),
               "first": r, "last": r}
if cur:
    sessions.append(cur)

sess_lens = [s["ms"] / 3600000 for s in sessions]
D["sessions"] = {
    "count": len(sessions),
    "median_min": round(statistics.median(s["ms"] for s in sessions) / 60000, 1),
    "mean_min": round(statistics.mean(s["ms"] for s in sessions) / 60000, 1),
    "median_tracks": statistics.median(s["n"] for s in sessions),
    "over_1h": sum(1 for h in sess_lens if h >= 1),
    "over_4h": sum(1 for h in sess_lens if h >= 4),
    "over_8h": sum(1 for h in sess_lens if h >= 8),
}
D["longest_sessions"] = [
    {"date": s["start"].date().isoformat(),
     "start_hour": s["start"].hour,
     "hours": round(s["ms"] / 3600000, 1),
     "tracks": s["n"],
     "top_artist": s["artists"].most_common(1)[0][0],
     "opened_with": s["first"]["master_metadata_track_name"],
     "opened_by": s["first"]["master_metadata_album_artist_name"]}
    for s in sorted(sessions, key=lambda s: -s["ms"])[:25]]

# session length by year
sy = defaultdict(list)
for s in sessions:
    sy[s["start"].year].append(s["ms"] / 60000)
D["session_by_year"] = [
    {"year": y, "sessions": len(v),
     "median_min": round(statistics.median(v), 1)}
    for y, v in sorted(sy.items())]

# what opens a session
D["session_openers"] = [
    {"artist": a, "n": n} for a, n in
    Counter(s["first"]["master_metadata_album_artist_name"]
            for s in sessions).most_common(20)]

# ---------------------------------------------------------------- 5. geography
geo = defaultdict(Counter)
for r in songs:
    geo[r["_year"]][r["conn_country"] or "??"] += 1
D["country_by_year"] = {str(y): dict(c.most_common()) for y, c in sorted(geo.items())}

# distinct days abroad
abroad = defaultdict(set)
for r in songs:
    if r["conn_country"] and r["conn_country"] != "US":
        abroad[r["conn_country"]].add(r["_date"])
D["abroad"] = sorted(
    [{"country": k, "days": len(v), "first": min(v), "last": max(v)}
     for k, v in abroad.items()], key=lambda x: -x["days"])

# ---------------------------------------------------------------- 6. platforms
plat = defaultdict(Counter)
for r in songs:
    p = (r["platform"] or "unknown").strip()
    # normalise the long user-agent style strings into a family
    low = p.lower()
    if "ios" in low or "iphone" in low or "ipad" in low:
        fam = "iPhone / iPad"
    elif "android" in low:
        fam = "Android"
    elif "windows" in low or "win32" in low or "winrt" in low:
        fam = "Windows"
    elif "osx" in low or "mac" in low:
        fam = "Mac"
    elif "cast" in low or "chromecast" in low:
        fam = "Cast / speaker"
    elif "web" in low or "webplayer" in low:
        fam = "Web player"
    elif "partner" in low or "sonos" in low or "car" in low:
        fam = "Car / partner device"
    else:
        fam = "Other"
    plat[r["_year"]][fam] += 1
D["platform_by_year"] = {str(y): dict(c.most_common()) for y, c in sorted(plat.items())}

# ---------------------------------------------------------------- 7. completion
# no track duration in the export; approximate it by the longest listen ever
# recorded for that track, then measure how much of it is typically heard.
tmax = defaultdict(int)
for r in songs:
    u = r["spotify_track_uri"]
    if u:
        tmax[u] = max(tmax[u], r["ms_played"])

comp = defaultdict(lambda: {"n": 0, "sum": 0.0})
for r in songs:
    u = r["spotify_track_uri"]
    if not u or tmax[u] < 60000:
        continue
    frac = min(1.0, r["ms_played"] / tmax[u])
    comp[u]["n"] += 1
    comp[u]["sum"] += frac

meta = {}
for r in songs:
    u = r["spotify_track_uri"]
    if u and u not in meta:
        meta[u] = (r["master_metadata_track_name"],
                   r["master_metadata_album_artist_name"])

comp_rows = [{"track": meta[u][0], "artist": meta[u][1], "plays": v["n"],
              "completion": round(v["sum"] / v["n"] * 100, 1)}
             for u, v in comp.items() if v["n"] >= 25 and u in meta]
D["completion_low"] = sorted(comp_rows, key=lambda x: x["completion"])[:30]
D["completion_high"] = sorted(comp_rows,
                              key=lambda x: (-x["completion"], -x["plays"]))[:30]

# ---------------------------------------------------------------- 8. artist arcs
arc = defaultdict(lambda: {"n": 0, "ms": 0, "first": None, "last": None,
                           "years": Counter(), "tracks": set()})
for r in plays:
    a = r["master_metadata_album_artist_name"]
    if not a:
        continue
    v = arc[a]
    v["n"] += 1
    v["ms"] += r["ms_played"]
    v["years"][r["_year"]] += 1
    v["tracks"].add(r["spotify_track_uri"])
    if v["first"] is None:
        v["first"] = r["_date"]
    v["last"] = r["_date"]

arc_rows = []
for a, v in arc.items():
    if v["n"] < 100:
        continue
    peak_year, peak_n = v["years"].most_common(1)[0]
    span = (datetime.date.fromisoformat(v["last"]) -
            datetime.date.fromisoformat(v["first"])).days
    arc_rows.append({
        "artist": a, "plays": v["n"], "hours": round(v["ms"] / 3600000, 1),
        "first": v["first"], "last": v["last"], "span_days": span,
        "peak_year": peak_year, "peak_plays": peak_n,
        "concentration": round(peak_n / v["n"] * 100, 1),
        "tracks": len(v["tracks"]),
        "years_active": len(v["years"]),
    })
arc_rows.sort(key=lambda x: -x["plays"])
D["artist_arcs"] = arc_rows[:200]

# lifers: present across the most calendar years
D["lifers"] = sorted(arc_rows, key=lambda x: (-x["years_active"], -x["plays"]))[:25]
# flares: huge but concentrated in one year
D["flares"] = sorted([r for r in arc_rows if r["plays"] >= 300],
                     key=lambda x: -x["concentration"])[:25]

# ---------------------------------------------------------------- 9. seasonality
seas = Counter()
seas_ms = Counter()
for r in plays:
    seas[r["_mon"]] += 1
    seas_ms[r["_mon"]] += r["ms_played"]
D["seasonality"] = [{"month": MONTHS[m - 1], "plays": seas[m],
                     "hours": round(seas_ms[m] / 3600000)} for m in range(1, 13)]

# most-played *day* ever
day = Counter(r["_date"] for r in plays)
day_ms = Counter()
for r in plays:
    day_ms[r["_date"]] += r["ms_played"]
D["biggest_days"] = [{"date": d, "plays": n,
                      "hours": round(day_ms[d] / 3600000, 1)}
                     for d, n in day.most_common(20)]
D["active_days"] = len(day)

# ---------------------------------------------------------------- 10. night vs day
buckets = {"Late night 0-5": range(0, 5), "Morning 5-11": range(5, 11),
           "Afternoon 11-17": range(11, 17), "Evening 17-21": range(17, 21),
           "Night 21-24": range(21, 24)}
bk = {}
for label, hrs in buckets.items():
    sub = [r for r in plays if r["_hour"] in hrs]
    c = Counter(r["master_metadata_album_artist_name"] for r in sub)
    bk[label] = {"plays": len(sub),
                 "top": [{"artist": a, "n": n} for a, n in c.most_common(8)]}
D["day_parts"] = bk

# ---------------------------------------------------------------- 11. podcasts / books / video
D["podcasts"] = [{"show": s, "eps": n} for s, n in
                 Counter(r["episode_show_name"] for r in pods
                         if r["episode_show_name"]).most_common(25)]
D["podcast_hours"] = round(sum(r["ms_played"] for r in pods) / 3600000, 1)
D["audiobooks"] = [{"title": t, "n": n} for t, n in
                   Counter(r["audiobook_title"] for r in books
                           if r["audiobook_title"]).most_common(25)]
D["audiobook_hours"] = round(sum(r["ms_played"] for r in books) / 3600000, 1)
D["video_rows"] = len(video)
D["video_hours"] = round(sum(r.get("ms_played", 0) for r in video) / 3600000, 1)

# ---------------------------------------------------------------- 11b. by year
yr = defaultdict(lambda: {"plays": 0, "ms": 0, "tracks": set(), "artists": set()})
for r in plays:
    v = yr[r["_year"]]
    v["plays"] += 1
    v["ms"] += r["ms_played"]
    v["tracks"].add(r["spotify_track_uri"])
    v["artists"].add(r["master_metadata_album_artist_name"])

seen_art = set()
new_by_year = {}
for y in sorted(yr):
    fresh = yr[y]["artists"] - seen_art
    new_by_year[y] = len(fresh)
    seen_art |= yr[y]["artists"]

D["by_year"] = [
    {"year": y, "plays": v["plays"], "hours": round(v["ms"] / 3600000),
     "tracks": len(v["tracks"]), "artists": len(v["artists"]),
     "new_artists": new_by_year[y]}
    for y, v in sorted(yr.items())]

# ---------------------------------------------------------------- 11c. song layer
import songs as song_layer
D.update(song_layer.compute(plays, songs, ACCT))

# ---------------------------------------------------------------- 11d. behaviour layer
import behaviour
D.update(behaviour.compute(plays, songs, ACCT))

# ---------------------------------------------------------------- 12. headline totals
D["totals"] = {
    "rows": len(audio),
    "songs": len(songs),
    "plays30": len(plays),
    "hours": round(sum(r["ms_played"] for r in songs) / 3600000),
    "days": round(sum(r["ms_played"] for r in songs) / 86400000, 1),
    "artists": len(set(r["master_metadata_album_artist_name"] for r in plays)),
    "tracks": len(set(r["spotify_track_uri"] for r in plays)),
    "active_days": len(day),
    "span_days": (datetime.date.fromisoformat(songs[-1]["_date"]) -
                  datetime.date.fromisoformat(songs[0]["_date"])).days,
}

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(D, fh, ensure_ascii=False)

print(f"\nwrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")
print(json.dumps(D["totals"], indent=2))
print("sessions:", json.dumps(D["sessions"], indent=2))
