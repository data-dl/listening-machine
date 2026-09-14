"""
Locate the newest Spotify export on disk.

Spotify mails each data category as its own zip, and every one of them is named
`my_spotify_data.zip` — which is why the browser produced `my_spotify_data`,
`my_spotify_data_1` and `my_spotify_data_2`. Those names carry no information,
so rather than depend on them this module searches for Spotify's *own* folder
names and picks whichever copy holds the most recent data.

Drop a new export anywhere under one of ROOTS and the pipeline finds it.
"""
import os, glob, json, re

# Where to look. SPOTIFY_EXPORT_ROOTS (os.pathsep-separated) wins; otherwise the usual
# download folders under the home directory. Exports can sit anywhere below a root.
ROOTS = [r for r in os.environ.get("SPOTIFY_EXPORT_ROOTS", "").split(os.pathsep) if r] or [
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]

EXTENDED = "Spotify Extended Streaming History"
TECHNICAL = "Spotify Technical Log Information"
ACCOUNT = "Spotify Account Data"


def _candidates(kind, max_depth=3):
    """Every folder with Spotify's own name for this category."""
    found = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        root_depth = root.rstrip("\\/").count(os.sep)
        for dirpath, dirnames, _ in os.walk(root):
            if dirpath.count(os.sep) - root_depth >= max_depth:
                dirnames[:] = []
                continue
            if os.path.basename(dirpath) == kind:
                found.append(dirpath)
                dirnames[:] = []
    return found


def _latest_stream_ts(folder):
    """Max play timestamp, read from the newest year file only (cheap)."""
    files = glob.glob(os.path.join(folder, "Streaming_History_Audio_*.json"))
    if not files:
        return ""
    years = []
    for f in files:
        m = re.search(r"Audio_(\d{4})", os.path.basename(f))
        if m:
            years.append((int(m.group(1)), f))
    if not years:
        return ""
    newest_year = max(y for y, _ in years)
    best = ""
    for y, f in years:
        if y != newest_year:
            continue
        try:
            for r in json.load(open(f, encoding="utf-8")):
                if r.get("ts", "") > best:
                    best = r["ts"]
        except Exception:
            pass
    return best


def _newest_mtime(folder):
    best = 0
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        if os.path.isfile(p):
            best = max(best, os.path.getmtime(p))
    return best


def resolve(kind, verbose=True):
    """Return the path to the freshest copy of one export category."""
    cands = _candidates(kind)
    if not cands:
        raise FileNotFoundError(
            f'No folder named "{kind}" under any of:\n  ' + "\n  ".join(ROOTS))

    if kind == EXTENDED:
        scored = [(_latest_stream_ts(c), c) for c in cands]
    else:
        scored = [(_newest_mtime(c), c) for c in cands]
    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = scored[0][1]

    if verbose:
        print(f'  {kind}')
        for mark, (score, c) in enumerate(scored):
            tag = "USING " if c == chosen else "  skip"
            detail = score if kind == EXTENDED else ""
            print(f'    {tag} {c}  {detail}')
    return chosen


def all_copies(kind):
    """Every copy of a category, newest first.

    Technical logs are ~90-day windows, so successive exports are disjoint and
    must be unioned rather than replaced. Extended history and account data are
    cumulative snapshots — for those, resolve() alone is the right call.
    """
    cands = _candidates(kind)
    if kind == EXTENDED:
        scored = [(_latest_stream_ts(c), c) for c in cands]
    else:
        scored = [(_newest_mtime(c), c) for c in cands]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def resolve_all(verbose=True):
    if verbose:
        print("resolving Spotify export locations ...")
    return {
        "extended": resolve(EXTENDED, verbose),
        "technical": resolve(TECHNICAL, verbose),
        "account": resolve(ACCOUNT, verbose),
    }


if __name__ == "__main__":
    for k, v in resolve_all().items():
        print(f"\n{k:10s} -> {v}")
