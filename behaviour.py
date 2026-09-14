"""
Behaviour layer: love arcs, repeat loops, rediscovery, retention, exploration,
session styles, eras, albums, breadth, reason-start, monthly series, library
gap, search conversion.

Called from deep_aggregate.py with the parsed rows. Every timestamp has already
been converted to America/New_York upstream — nothing here touches UTC.

Definitions are stated once, here, and repeated verbatim on the page.
"""
import os, json, datetime, statistics
from collections import defaultdict, Counter

LOVE_N = 5              # the Nth stream ...
LOVE_WINDOW = 30        # ... inside this many trailing days = the love signal
LOOP_MIN = 3            # consecutive streams of one recording = a loop
DURABLE = 25            # lifetime streams that make a track "durable"
NEW_DAYS = 30           # a track is "new" for this long after its first stream
DORMANT_DAYS = 365


def _d(s):
    return datetime.date.fromisoformat(s[:10])


def compute(plays, songs, acct_dir):
    out = {}
    end = plays[-1]["_loc"].date()

    # ---------------------------------------------------------------- index
    meta, streams, all_rows = {}, defaultdict(list), defaultdict(list)
    for r in plays:
        u = r["spotify_track_uri"]
        if not u:
            continue
        streams[u].append(r)
        if u not in meta:
            meta[u] = (r["master_metadata_track_name"],
                       r["master_metadata_album_artist_name"],
                       r["master_metadata_album_album_name"])
    for r in songs:
        u = r["spotify_track_uri"]
        if u:
            all_rows[u].append(r)

    first_date = {u: v[0]["_loc"].date() for u, v in streams.items()}
    last_date = {u: v[-1]["_loc"].date() for u, v in streams.items()}

    def name(u):
        m = meta.get(u, ("?", "?", "?"))
        return {"uri": u, "track": m[0], "artist": m[1], "album": m[2]}

    # ------------------------------------------------------------ love arcs
    # The love signal: the 5th stream inside a trailing 30-day window.
    arcs = []
    for u, rows in streams.items():
        if len(rows) < DURABLE:
            continue
        dates = [r["_loc"].date() for r in rows]
        love = None
        for i in range(LOVE_N - 1, len(dates)):
            if (dates[i] - dates[i - LOVE_N + 1]).days <= LOVE_WINDOW:
                love = dates[i]
                break
        if love is None:
            continue
        months = Counter(r["_ym"] for r in rows)
        peak_m, peak_n = months.most_common(1)[0]
        # strongest 30-day burst, sliding
        best, j = 0, 0
        for i in range(len(dates)):
            while (dates[i] - dates[j]).days > 30:
                j += 1
            best = max(best, i - j + 1)
        days_to = (love - dates[0]).days
        kind = ("Instant love" if days_to <= 7 else
                "Quick rise" if days_to <= 30 else
                "Slow burn" if days_to <= 365 else "Late rediscovery")
        arcs.append({**name(u), "streams": len(rows),
                     "first": dates[0].isoformat(), "love": love.isoformat(),
                     "days_to_love": days_to, "kind": kind,
                     "peak_month": peak_m, "peak_month_streams": peak_n,
                     "burst30": best, "last": dates[-1].isoformat(),
                     "years": len(set(d.year for d in dates)),
                     "spark": sorted(months.items())})
    arcs.sort(key=lambda a: -a["streams"])
    out["love_arcs"] = arcs[:120]
    out["love_kinds"] = dict(Counter(a["kind"] for a in arcs))
    out["love_total"] = len(arcs)
    out["love_slowest"] = sorted(arcs, key=lambda a: -a["days_to_love"])[:12]
    out["love_fastest"] = sorted(arcs, key=lambda a: (a["days_to_love"], -a["streams"]))[:12]
    out["love_burst"] = sorted(arcs, key=lambda a: -a["burst30"])[:12]

    # --------------------------------------------------------- repeat loops
    loops = {}
    run_u, run_n, run_start = None, 0, None
    for r in plays:
        u = r["spotify_track_uri"]
        if u == run_u:
            run_n += 1
        else:
            if run_u and run_n >= LOOP_MIN:
                cur = loops.get(run_u)
                if not cur or run_n > cur["run"]:
                    loops[run_u] = {"run": run_n, "start": run_start,
                                    "end": prev_ts}
            run_u, run_n, run_start = u, 1, r["_loc"].isoformat(timespec="minutes")
        prev_ts = r["_loc"].isoformat(timespec="minutes")
    if run_u and run_n >= LOOP_MIN:
        cur = loops.get(run_u)
        if not cur or run_n > cur["run"]:
            loops[run_u] = {"run": run_n, "start": run_start, "end": prev_ts}
    lp = [{**name(u), **v, "streams": len(streams[u])} for u, v in loops.items() if u in meta]
    lp.sort(key=lambda x: (-x["run"], -x["streams"]))
    out["repeat_loops"] = lp[:40]
    out["repeat_loop_tracks"] = len(lp)

    # ---------------------------------------------------- rediscovery queue
    q = []
    for u, rows in streams.items():
        if len(rows) < DURABLE:
            continue
        yrs = set(r["_year"] for r in rows)
        away = (end - last_date[u]).days
        if len(yrs) >= 2 and away >= 365:
            q.append({**name(u), "streams": len(rows), "years": len(yrs),
                      "last": last_date[u].isoformat(), "away_days": away,
                      "away_years": round(away / 365, 1)})
    q.sort(key=lambda x: (-x["streams"]))
    out["rediscovery"] = q[:80]
    out["rediscovery_buckets"] = {
        "1+": sum(1 for x in q if x["away_days"] >= 365),
        "2+": sum(1 for x in q if x["away_days"] >= 730),
        "4+": sum(1 for x in q if x["away_days"] >= 1460),
        "7+": sum(1 for x in q if x["away_days"] >= 2555)}

    # -------------------------------------------------- discovery retention
    cohort = defaultdict(lambda: {"n": 0, "r90": 0, "r365": 0})
    for u, rows in streams.items():
        f = first_date[u]
        y = f.year
        c = cohort[y]
        c["n"] += 1
        later = [r["_loc"].date() for r in rows[1:]]
        if any((d - f).days >= 90 for d in later):
            c["r90"] += 1
        if any((d - f).days >= 365 for d in later):
            c["r365"] += 1
    ret = []
    for y in sorted(cohort):
        c = cohort[y]
        if c["n"] < 50:
            continue
        yend = datetime.date(y, 12, 31)
        ok90 = (end - yend).days >= 90
        ok365 = (end - yend).days >= 365
        ret.append({"year": y, "tracks": c["n"],
                    "r90": round(c["r90"] / c["n"] * 100, 1) if ok90 else None,
                    "r365": round(c["r365"] / c["n"] * 100, 1) if ok365 else None})
    out["retention"] = ret

    # ----------------------------------------------- monthly + exploration
    mon = defaultdict(lambda: {"streams": 0, "ms": 0, "new": 0, "explore": 0,
                               "rows": 0, "cut": 0, "skip": 0})
    for r in plays:
        u = r["spotify_track_uri"]
        m = mon[r["_ym"]]
        m["streams"] += 1
        m["ms"] += r["ms_played"]
        d = r["_loc"].date()
        if d == first_date[u]:
            pass
        if (d - first_date[u]).days <= NEW_DAYS:
            m["explore"] += 1
    seen = set()
    for r in plays:
        u = r["spotify_track_uri"]
        if u not in seen:
            seen.add(u)
            mon[r["_ym"]]["new"] += 1
    for r in songs:
        m = mon[r["_ym"]]
        m["rows"] += 1
        cut = r["reason_end"] in ("fwdbtn", "endplay") or bool(r.get("skipped"))
        if cut:
            m["cut"] += 1
            if r["ms_played"] < 30000:
                m["skip"] += 1
    out["monthly"] = [
        {"ym": k, "streams": v["streams"], "hours": round(v["ms"] / 3600000, 1),
         "new_tracks": v["new"],
         "explore_pct": round(v["explore"] / v["streams"] * 100, 1) if v["streams"] else 0,
         "cut_pct": round(v["cut"] / v["rows"] * 100, 1) if v["rows"] else 0,
         "skip_pct": round(v["skip"] / v["rows"] * 100, 1) if v["rows"] else 0}
        for k, v in sorted(mon.items()) if v["streams"] > 0]

    # strict skip (cut short inside 30s) by year, alongside the loose one
    sy = defaultdict(lambda: {"n": 0, "strict": 0, "loose": 0})
    for r in songs:
        v = sy[r["_year"]]
        v["n"] += 1
        cut = r["reason_end"] in ("fwdbtn", "endplay") or bool(r.get("skipped"))
        if cut:
            v["loose"] += 1
            if r["ms_played"] < 30000:
                v["strict"] += 1
    out["skip_strict_by_year"] = [
        {"year": y, "rows": v["n"], "strict": round(v["strict"] / v["n"] * 100, 1),
         "loose": round(v["loose"] / v["n"] * 100, 1)}
        for y, v in sorted(sy.items()) if v["n"] > 300]

    # ------------------------------------------------------ session styles
    sessions, cur = [], None
    for r in plays:
        if cur and (r["_utc"] - cur["end"]).total_seconds() <= 1800:
            cur["rows"].append(r)
            cur["end"] = r["_utc"] + datetime.timedelta(milliseconds=r["ms_played"])
        else:
            if cur:
                sessions.append(cur)
            cur = {"rows": [r], "end": r["_utc"] + datetime.timedelta(milliseconds=r["ms_played"])}
    if cur:
        sessions.append(cur)

    styles = defaultdict(lambda: {"n": 0, "streams": [], "mins": [], "cut": 0, "rows": 0})
    style_def = {
        "Loop": "one recording is at least half the streams, and there are five or more",
        "Deep dive": "one artist is at least 60% of the streams, eight or more, without looping",
        "Exploration": "at least half the streams are tracks in their first 30 days in your history",
        "Mixed": "everything else",
    }
    for s in sessions:
        rows = s["rows"]
        n = len(rows)
        tc = Counter(r["spotify_track_uri"] for r in rows)
        ac = Counter(r["master_metadata_album_artist_name"] for r in rows)
        top_t = tc.most_common(1)[0][1] / n
        top_a = ac.most_common(1)[0][1] / n
        newish = sum(1 for r in rows
                     if (r["_loc"].date() - first_date[r["spotify_track_uri"]]).days <= NEW_DAYS) / n
        if n >= 5 and top_t >= 0.5:
            st = "Loop"
        elif n >= 8 and top_a >= 0.6:
            st = "Deep dive"
        elif newish >= 0.5:
            st = "Exploration"
        else:
            st = "Mixed"
        v = styles[st]
        v["n"] += 1
        v["streams"].append(n)
        v["mins"].append(sum(r["ms_played"] for r in rows) / 60000)
    tot = len(sessions)
    out["session_styles"] = [
        {"style": k, "definition": style_def[k], "sessions": v["n"],
         "share": round(v["n"] / tot * 100, 1),
         "median_streams": statistics.median(v["streams"]),
         "median_min": round(statistics.median(v["mins"]), 1)}
        for k, v in sorted(styles.items(), key=lambda kv: -kv[1]["n"])]

    # --------------------------------------------------------- taste eras
    ya = defaultdict(Counter)
    yms = defaultdict(int)
    for r in plays:
        ya[r["_year"]][r["master_metadata_album_artist_name"]] += 1
        yms[r["_year"]] += r["ms_played"]
    out["eras"] = [
        {"year": y, "hours": round(yms[y] / 3600000),
         "top": [{"artist": a, "streams": n} for a, n in c.most_common(5)]}
        for y, c in sorted(ya.items()) if sum(c.values()) >= 100]

    # -------------------------------------------------------------- albums
    alb = defaultdict(lambda: {"n": 0, "ms": 0, "tracks": set(), "years": set()})
    for r in plays:
        k = (r["master_metadata_album_artist_name"], r["master_metadata_album_album_name"])
        if not k[1]:
            continue
        v = alb[k]
        v["n"] += 1
        v["ms"] += r["ms_played"]
        v["tracks"].add(r["spotify_track_uri"])
        v["years"].add(r["_year"])
    albums = [{"artist": k[0], "album": k[1], "streams": v["n"],
               "hours": round(v["ms"] / 3600000, 1), "tracks": len(v["tracks"]),
               "years": len(v["years"])}
              for k, v in alb.items()]
    out["albums_top"] = sorted(albums, key=lambda a: -a["streams"])[:30]
    out["albums_inside"] = sorted([a for a in albums if a["tracks"] >= 8],
                                  key=lambda a: (-a["tracks"], -a["streams"]))[:30]

    # ------------------------------------------------------- artist breadth
    ab = defaultdict(lambda: {"tracks": set(), "n": 0, "ms": 0})
    for r in plays:
        a = r["master_metadata_album_artist_name"]
        ab[a]["tracks"].add(r["spotify_track_uri"])
        ab[a]["n"] += 1
        ab[a]["ms"] += r["ms_played"]
    out["breadth"] = sorted(
        [{"artist": a, "tracks": len(v["tracks"]), "streams": v["n"],
          "hours": round(v["ms"] / 3600000, 1)} for a, v in ab.items()],
        key=lambda x: -x["tracks"])[:30]

    # -------------------------------------------------------- reason start
    rsy = defaultdict(Counter)
    for r in songs:
        rsy[r["_year"]][r.get("reason_start") or "unknown"] += 1
    out["reason_start_by_year"] = {str(y): dict(c.most_common(7))
                                   for y, c in sorted(rsy.items()) if sum(c.values()) > 300}
    lab = {"trackdone": "flowed from the previous track", "fwdbtn": "forward button",
           "clickrow": "clicked a specific row", "backbtn": "back button",
           "appload": "app opened", "remote": "another device", "playbtn": "play button",
           "trackerror": "error recovery", "unknown": "unknown"}
    out["reason_start_labels"] = lab

    # ------------------------------------------------------- library gap
    lib_path = os.path.join(acct_dir, "YourLibrary.json")
    saved = []
    if os.path.exists(lib_path):
        L = json.load(open(lib_path, encoding="utf-8"))
        saved = [t for t in L.get("tracks", []) if t.get("uri")]
    saved_uris = {t["uri"] for t in saved}
    gap = Counter()
    gap_rows = defaultdict(list)
    for t in saved:
        u = t["uri"]
        n = len(streams.get(u, []))
        if n == 0:
            st = "Never heard"
        elif n < 5:
            st = "Sampled"
        elif (end - last_date[u]).days >= DORMANT_DAYS:
            st = "Dormant"
        else:
            st = "Active"
        gap[st] += 1
        gap_rows[st].append({"track": t.get("track"), "artist": t.get("artist"),
                             "streams": n,
                             "last": last_date[u].isoformat() if n else None})
    for st in gap_rows:
        gap_rows[st].sort(key=lambda x: (-x["streams"], x["artist"] or ""))
    out["saved_total"] = len(saved)
    out["saved_gap"] = dict(gap)
    out["saved_examples"] = {st: rows[:12] for st, rows in gap_rows.items()}
    out["loved_not_saved"] = sorted(
        [{**name(u), "streams": len(v), "last": last_date[u].isoformat()}
         for u, v in streams.items() if len(v) >= DURABLE and u not in saved_uris],
        key=lambda x: -x["streams"])[:40]
    out["loved_not_saved_total"] = sum(
        1 for u, v in streams.items() if len(v) >= DURABLE and u not in saved_uris)

    # ---------------------------------------------------- search conversion
    sq_path = os.path.join(acct_dir, "SearchQueries.json")
    sc = {"queries": 0, "with_interaction": 0, "converted": 0, "top": []}
    if os.path.exists(sq_path):
        S = json.load(open(sq_path, encoding="utf-8"))
        qc = Counter()
        for row in S:
            q = (row.get("searchQuery") or "").strip()
            if not q:
                continue
            sc["queries"] += 1
            qc[q.lower()] += 1
            uris = row.get("searchInteractionURIs") or []
            if not uris:
                continue
            sc["with_interaction"] += 1
            ts = (row.get("searchTime") or "")[:10]
            try:
                sd = _d(ts)
            except Exception:
                continue
            hit = False
            for u in uris:
                for r in streams.get(u, []):
                    dd = r["_loc"].date()
                    if 0 <= (dd - sd).days <= 7:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                sc["converted"] += 1
        sc["top"] = qc.most_common(24)
    out["search"] = sc

    # a compact track index so the technical-log pass can name URIs
    idx = {u: [meta[u][0], meta[u][1], len(v)] for u, v in streams.items() if len(v) >= 3}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "track_index.json"),
              "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False)

    return out
