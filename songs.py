"""
Song-level layer: favourites, first encounters, risers, playlist pull-through.

Called from deep_aggregate.py with the already-parsed rows so the 227 MB archive
is read once.

The centrepiece is `first_encounters`: for the songs that ended up mattering,
the actual dated first few plays — the night a song entered the record, and how
long it then took to take hold.
"""
import os, json, datetime
from collections import defaultdict, Counter

RECENT_DAYS = 120        # the trailing window that counts as "lately"
BASELINE_DAYS = 365      # what "lately" is measured against


def platform_family(p):
    low = (p or "").lower()
    if "ios" in low or "iphone" in low or "ipad" in low:
        return "iPhone"
    if "android" in low:
        return "Android"
    if "windows" in low or "win32" in low or "winrt" in low:
        return "Windows"
    if "osx" in low or "mac" in low:
        return "Mac"
    if "cast" in low or "chromecast" in low:
        return "Speaker"
    if "web" in low:
        return "Web"
    return "Other"


def compute(plays, songs, acct_dir):
    """plays = >=30s song rows (chronological); songs = every song row."""
    out = {}
    last_date = plays[-1]["_loc"].date()
    recent_from = last_date - datetime.timedelta(days=RECENT_DAYS)
    base_from = recent_from - datetime.timedelta(days=BASELINE_DAYS)

    # ---------------------------------------------------------- per track
    T = defaultdict(lambda: {
        "n": 0, "ms": 0, "days": set(), "years": Counter(), "plat": Counter(),
        "head": [],          # first 10 qualifying plays, capped
        "last": None, "recent": 0, "base": 0,
    })
    meta = {}
    for r in plays:
        u = r["spotify_track_uri"]
        if not u:
            continue
        v = T[u]
        v["n"] += 1
        v["ms"] += r["ms_played"]
        v["days"].add(r["_date"])
        v["years"][r["_year"]] += 1
        v["plat"][platform_family(r["platform"])] += 1
        if len(v["head"]) < 10:
            v["head"].append((r["_loc"].isoformat(timespec="minutes"),
                              platform_family(r["platform"]),
                              round(r["ms_played"] / 1000)))
        v["last"] = r["_date"]
        d = r["_loc"].date()
        if d >= recent_from:
            v["recent"] += 1
        elif d >= base_from:
            v["base"] += 1
        if u not in meta:
            meta[u] = (r["master_metadata_track_name"],
                       r["master_metadata_album_artist_name"],
                       r["master_metadata_album_album_name"])

    # skip rate needs every row, not just the >=30s ones
    S = defaultdict(lambda: {"n": 0, "s": 0})
    for r in songs:
        u = r["spotify_track_uri"]
        if not u:
            continue
        S[u]["n"] += 1
        if r["reason_end"] in ("fwdbtn", "endplay") or r.get("skipped"):
            S[u]["s"] += 1

    def row(u):
        v, m = T[u], meta[u]
        sk = S.get(u, {"n": 0, "s": 0})
        peak_y, peak_n = v["years"].most_common(1)[0]
        return {
            "uri": u, "track": m[0], "artist": m[1], "album": m[2],
            "plays": v["n"], "hours": round(v["ms"] / 3600000, 1),
            "first": v["head"][0][0][:10], "last": v["last"],
            "days": len(v["days"]), "peak_year": peak_y, "peak_plays": peak_n,
            "skip_rate": round(sk["s"] / sk["n"] * 100, 1) if sk["n"] else 0,
            "top_device": v["plat"].most_common(1)[0][0] if v["plat"] else "—",
            "recent": v["recent"], "base": v["base"],
            "years_active": len(v["years"]),
        }

    ranked = sorted((u for u in T if u in meta), key=lambda u: -T[u]["n"])
    out["top_tracks"] = [row(u) for u in ranked[:80]]

    # ------------------------------------------------- first encounters
    # For the songs that ended up mattering: the actual opening plays.
    enc = []
    for u in ranked[:60]:
        v = T[u]
        head = v["head"]
        if len(head) < 5:
            continue
        d1 = datetime.date.fromisoformat(head[0][0][:10])
        d5 = datetime.date.fromisoformat(head[4][0][:10])
        d10 = (datetime.date.fromisoformat(head[9][0][:10])
               if len(head) >= 10 else None)
        r = row(u)
        r["opening"] = [{"when": h[0], "device": h[1], "secs": h[2]}
                        for h in head[:5]]
        r["days_to_5"] = (d5 - d1).days
        r["days_to_10"] = (d10 - d1).days if d10 else None
        enc.append(r)
    enc.sort(key=lambda x: -x["plays"])
    out["first_encounters"] = enc[:28]

    # slow burns: longest gap between the first play and the fifth
    out["slow_burns"] = sorted([e for e in enc if e["days_to_5"] is not None],
                               key=lambda x: -x["days_to_5"])[:12]
    # instant hits: five plays inside the shortest span
    out["instant_hits"] = sorted([e for e in enc if e["days_to_5"] is not None],
                                 key=lambda x: (x["days_to_5"], -x["plays"]))[:12]

    # ------------------------------------------------------------ risers
    rising = []
    for u in T:
        if u not in meta:
            continue
        v = T[u]
        if v["recent"] < 8:
            continue
        lift = v["recent"] / (v["base"] + 2)
        r = row(u)
        r["lift"] = round(lift, 2)
        rising.append(r)
    rising.sort(key=lambda x: (-x["lift"], -x["recent"]))
    out["rising_tracks"] = rising[:24]
    out["recent_window"] = {"from": recent_from.isoformat(),
                            "to": last_date.isoformat(),
                            "days": RECENT_DAYS,
                            "baseline_days": BASELINE_DAYS}

    # most played in the recent window, regardless of lift
    out["recent_top"] = sorted(
        [row(u) for u in T if u in meta and T[u]["recent"] > 0],
        key=lambda x: -x["recent"])[:24]

    # rising artists
    A = defaultdict(lambda: {"recent": 0, "base": 0, "n": 0})
    for r in plays:
        a = r["master_metadata_album_artist_name"]
        if not a:
            continue
        d = r["_loc"].date()
        A[a]["n"] += 1
        if d >= recent_from:
            A[a]["recent"] += 1
        elif d >= base_from:
            A[a]["base"] += 1
    ra = [{"artist": a, "recent": v["recent"], "base": v["base"],
           "plays": v["n"], "lift": round(v["recent"] / (v["base"] + 2), 2)}
          for a, v in A.items() if v["recent"] >= 12]
    ra.sort(key=lambda x: (-x["lift"], -x["recent"]))
    out["rising_artists"] = ra[:18]

    # --------------------------------------------------------- playlists
    # The history records no playlist context, so this is membership-based:
    # how much each playlist's tracks actually get played.
    pl_path = os.path.join(acct_dir, "Playlist1.json")
    out["playlists"] = []
    if os.path.exists(pl_path):
        data = json.load(open(pl_path, encoding="utf-8"))
        for p in data.get("playlists", []):
            items = p.get("items") or []
            uris, added = [], {}
            for it in items:
                tr = it.get("track") or {}
                u = tr.get("trackUri")
                if u:
                    uris.append(u)
                    added[u] = it.get("addedDate")
            if not uris:
                continue
            tot = rec = 0
            never = 0
            best = None
            for u in uris:
                v = T.get(u)
                if not v:
                    never += 1
                    continue
                tot += v["n"]
                rec += v["recent"]
                if best is None or v["n"] > T[best]["n"]:
                    best = u
            out["playlists"].append({
                "name": p.get("name", "").strip() or "(untitled)",
                "size": len(uris),
                "modified": p.get("lastModifiedDate"),
                "plays": tot, "recent": rec, "never": never,
                "top": (meta[best][0] + " — " + meta[best][1]) if best and best in meta else "—",
                "top_plays": T[best]["n"] if best else 0,
            })
        out["playlists"].sort(key=lambda x: -x["recent"])

    return out
