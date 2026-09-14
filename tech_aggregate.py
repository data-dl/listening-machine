"""
Second pass: the Technical Log Information + Account Data folders.

Neither earlier dashboard opened these. They hold the physical layer of the
listening — which headphones, which car, which speaker, what was searched for,
what Spotify's ad models infer about the listener.

Output: tech.json
"""
import json, os, datetime
from collections import Counter, defaultdict

import paths
_P   = paths.resolve_all()
TECH = _P["technical"]
ACCT = _P["account"]
TECH_ALL = paths.all_copies(paths.TECHNICAL)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tech.json")

T = {}
_merge_report = {}


def _read(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        print(f"  ! {os.path.basename(p)}: {e}")
        return None


def load(folder, name):
    """Account data: the single newest snapshot.

    Technical logs: Spotify keeps only ~90 days, so each export is a different
    window. Union every copy on disk and drop exact duplicate rows, which turns
    two disjoint quarters into one continuous record.
    """
    if folder != TECH:
        p = os.path.join(folder, name)
        return _read(p) if os.path.exists(p) else None

    merged, seen, per_copy = [], set(), []
    for copy in TECH_ALL:
        p = os.path.join(copy, name)
        if not os.path.exists(p):
            continue
        rows = _read(p)
        if not isinstance(rows, list):
            continue
        added = 0
        for r in rows:
            key = json.dumps(r, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
            added += 1
        per_copy.append((os.path.basename(os.path.dirname(copy)), len(rows), added))
    if per_copy:
        _merge_report[name] = per_copy
    return merged or None


def day(ts):
    """Timestamps arrive as ISO strings in some files, epoch ints in others."""
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        if ts > 1e11:          # milliseconds
            ts = ts / 1000.0
        try:
            return datetime.datetime.utcfromtimestamp(ts).date().isoformat()
        except Exception:
            return ""
    return str(ts)[:10]


# ------------------------------------------------------------ audio routes
# Where the sound physically went: which headphones, speaker, car.
routes = load(TECH, "AudioRouteSegmentEnd.json") or []
rc = Counter()
rtype = Counter()
rdays = defaultdict(set)
for r in routes:
    nm = (r.get("message_current_route_name") or "").strip()
    tp = (r.get("message_current_route_type") or "").strip()
    if nm:
        rc[nm] += 1
        rdays[nm].add(day(r.get("timestamp_utc") or r.get("context_time")))
    if tp:
        rtype[tp] += 1
T["routes"] = [{"name": n, "n": c, "days": len(rdays[n])}
               for n, c in rc.most_common(30)]
T["route_types"] = dict(rtype.most_common(15))
T["routes_total"] = len(routes)
if routes:
    ds = sorted(d for d in (day(r.get("timestamp_utc") or r.get("context_time"))
                            for r in routes) if d)
    T["routes_window"] = {"first": ds[0], "last": ds[-1]} if ds else None

# ------------------------------------------------------------ the car
car = load(TECH, "CarDetectionEvent.json") or []
cc = Counter()
cdays = set()
for r in car:
    if r.get("message_is_car_connected"):
        cdays.add(day(r.get("timestamp_utc") or r.get("context_time")))
    cc[str(r.get("message_reason") or "?")] += 1
T["car"] = {"events": len(car), "connected_days": len(cdays),
            "reasons": dict(cc.most_common(8)),
            "days": sorted(cdays)[-40:]}

# ------------------------------------------------------------ devices seen
disc = load(TECH, "ConnectDeviceDiscovered.json") or []
T["discovered"] = dict(Counter(
    str(r.get("message_discovered_device_type") or "?") for r in disc).most_common(12))

dev = load(TECH, "DeviceIdentifier.json") or []
T["device_models"] = dict(Counter(
    f"{r.get('context_device_manufacturer','?')} {r.get('context_device_model','?')}"
    for r in dev).most_common(12))

# hardware families across every technical event we can cheaply scan
osv = Counter()
for r in routes:
    o = r.get("context_os_name")
    v = str(r.get("context_os_version") or "")
    if o:
        osv[f"{o} {v.split('.')[0]}"] += 1
T["os_versions"] = dict(osv.most_common(14))

# ------------------------------------------------------------ lyrics
lyr = load(TECH, "MinimumLyricsCharactersSeen.json") or []
T["lyrics"] = {"n": len(lyr),
               "days": len({day(r.get("timestamp_utc") or r.get("context_time"))
                            for r in lyr})}

# ------------------------------------------------------------ on repeat
rep = load(TECH, "OnRepeatContents.json") or []
T["on_repeat_snapshots"] = len(rep)
rep_tracks = Counter()
for r in rep:
    c = r.get("message_contents")
    if isinstance(c, list):
        for u in c:
            rep_tracks[str(u)] += 1
    elif isinstance(c, str):
        for u in c.replace("[", "").replace("]", "").split(","):
            u = u.strip().strip('"')
            if u:
                rep_tracks[u] += 1
T["on_repeat_top"] = rep_tracks.most_common(40)

# ------------------------------------------------------------ daylist
dl = load(TECH, "DaylistGenerated.json") or []
T["daylists"] = [{"title": r.get("message_playlist_title"),
                  "daypart": r.get("message_daypart"),
                  "time": day(r.get("context_time"))} for r in dl][:20]

# ------------------------------------------------------------ shares
sh = load(TECH, "Share.json") or []
T["shares"] = len(sh)

# ------------------------------------------------------------ account data
sq = load(ACCT, "SearchQueries.json") or []
qs = []
for r in sq:
    q = r.get("searchQuery") or r.get("query") or r.get("searchInteraction")
    if isinstance(q, str) and q.strip():
        qs.append(q.strip())
T["search_count"] = len(qs)
T["search_top"] = Counter(q.lower() for q in qs).most_common(40)

inf = load(ACCT, "Inferences.json") or {}
il = inf.get("inferences") if isinstance(inf, dict) else None
if isinstance(il, list):
    T["inferences"] = [str(x) for x in il][:400]
    T["inference_count"] = len(il)

tp = load(ACCT, "TasteProfile.json") or {}
T["taste_identity"] = ((tp.get("tasteProfile") or {}).get("musicalIdentity") or "") if isinstance(tp, dict) else ""

wr = load(ACCT, "Wrapped2025.json") or {}
if wr:
    T["wrapped2025"] = {
        k: wr.get(k) for k in
        ("topArtists", "topTracks", "topGenres", "yearlyMetrics",
         "listeningAge", "topAlbums") if k in wr}

sc = load(ACCT, "YourSoundCapsule.json") or {}
if sc:
    T["sound_capsule"] = sc

fo = load(ACCT, "Follow.json") or {}
T["follow"] = {k: (len(v) if isinstance(v, list) else v)
               for k, v in fo.items()} if isinstance(fo, dict) else {}

mq = load(ACCT, "Marquee.json") or []
T["marquee_count"] = len(mq) if isinstance(mq, list) else 0

# playlists + library for cross-reference
pl = load(ACCT, "Playlist1.json") or {}
pls = pl.get("playlists") if isinstance(pl, dict) else None
if isinstance(pls, list):
    T["playlists"] = [{"name": p.get("name"),
                       "n": len(p.get("items") or []),
                       "modified": p.get("lastModifiedDate")}
                      for p in pls]
    T["playlist_count"] = len(pls)

lib = load(ACCT, "YourLibrary.json") or {}
if isinstance(lib, dict):
    T["library"] = {k: (len(v) if isinstance(v, list) else v)
                    for k, v in lib.items()}

# ------------------------------------------------------ system health
# Counts only. No device ids, IPs or raw rows leave the export.
idx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "track_index.json")
IDX = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}

def named(uri):
    m = IDX.get(uri)
    return {"uri": uri, "track": m[0], "artist": m[1], "streams": m[2]} if m else None

stut = load(TECH, "Stutter.json") or []
perr = load(TECH, "PlaybackError.json") or []
dj = load(TECH, "DJTrackServed.json") or []
rr = load(TECH, "ReleaseRadarServedRecs.json") or []
aset = load(TECH, "AudioSettingsReport.json") or []
addc = load(TECH, "AddedToCollection.json") or []
addp = load(TECH, "AddedToPlaylist.json") or []
remp = load(TECH, "RemovedFromPlaylist.json") or []
crp = load(TECH, "CreatePlaylist.json") or []

latest_audio = {}
if aset:
    last = max(aset, key=lambda r: r.get("context_time") or 0)
    for k in ("message_play_bitrate", "message_user_selected_bitrate",
              "message_low_bitrate_on_cellular", "message_offline_mode"):
        if k in last:
            latest_audio[k.replace("message_", "")] = last[k]

dj_tracks = Counter()
for r in dj:
    u = r.get("message_track_uri")
    if u:
        dj_tracks[u] += 1
rr_count = 0
for r in rr:
    v = r.get("message_track_uris")
    if isinstance(v, list):
        rr_count += len(v)
    elif isinstance(v, str):
        rr_count += v.count("spotify:track")

T["health"] = {
    "stutters": len(stut), "playback_errors": len(perr),
    "fatal_errors": sum(1 for r in perr if r.get("message_fatal")),
    "dj_sessions": len({r.get("message_session_id") for r in dj if r.get("message_session_id")}),
    "dj_tracks_served": len(dj),
    "dj_heard": sum(1 for u in dj_tracks if u in IDX),
    "release_radar_batches": len(rr), "release_radar_tracks": rr_count,
    "library_adds": len(addc), "playlist_adds": len(addp),
    "playlist_removes": len(remp), "playlists_created": len(crp),
    "latest_audio": latest_audio,
}

# On Repeat snapshots joined back to lifetime listening
joined = []
for u, n in T["on_repeat_top"]:
    m = named(u)
    if m:
        joined.append({**m, "snapshots": n})
T["on_repeat_joined"] = joined[:16]
T["daylist_titles"] = [d["title"] for d in T["daylists"] if d.get("title")][:12]

T["merged_from"] = [os.path.dirname(c) for c in TECH_ALL]
T["merge_report"] = _merge_report

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(T, fh, ensure_ascii=False)

print(f"wrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)\n")
print("technical-log merge (copy, rows in file, rows new after dedup):")
for name, parts in _merge_report.items():
    if len(parts) > 1:
        print(f"   {name}: " + " + ".join(f"{c}={n}->{a}" for c, n, a in parts))
print("routes window:", T.get("routes_window"))
print("\ntop audio routes:")
for r in T["routes"][:14]:
    print(f"   {r['n']:6,}  {r['days']:4d}d  {r['name'][:52]}")
print("\nroute types:", T["route_types"])
print("\ncar:", {k: v for k, v in T["car"].items() if k != "days"})
print("\ndiscovered device types:", T["discovered"])
print("\nOS:", T["os_versions"])
print("\nlyrics:", T["lyrics"], "| shares:", T["shares"],
      "| on-repeat snapshots:", T["on_repeat_snapshots"])
print("searches:", T["search_count"], "| inferences:", T.get("inference_count"))
print("playlists:", T.get("playlist_count"), "| library:", T.get("library"))
