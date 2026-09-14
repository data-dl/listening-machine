# The Listening Machine

Fifteen years of one Spotify account — 264,000 streams from the extended streaming history,
the account-data export (library, playlists, searches, taste profile, ad inferences, Wrapped)
and every technical-log export on disk, merged — read as *behaviour* rather than as a top-ten
list: the 7×24 clock in local time, the skip curve, sessions, love arcs, repeat loops, the
rediscovery queue, discovery retention by cohort, a library audit, and the days that were not me.

**Live page:** https://data-dl.github.io/listening-machine/ · eight tabs, 35 sections, one 285 KB file.

This one runs on real listening data by choice — there is nothing in a play log worth hiding and
everything in it worth reading. The pipeline itself is the portfolio piece. The only thing removed
from the published aggregates is the handful of advertiser segments that named an internet provider,
carrier or phone model; the rest of what Spotify infers is shown as-is on the *Spotify's view* tab.

## Pipeline

```
Spotify exports (3 zips) ─► paths.py ─► deep_aggregate.py (+ songs.py, behaviour.py) ─► deep.json ─┐
                                    └─► tech_aggregate.py ─────────────────────────────► tech.json ─┴─► build_page.py ─► listening-machine.html + csv/
```

- **`paths.py`** finds exports by Spotify's *own* folder names rather than the zip names (every
  category zip is called `my_spotify_data.zip`, so the browser numbers them meaninglessly) and
  picks whichever copy holds the newest data. Drop a new export under any root and nothing needs
  editing.
- **`deep_aggregate.py`** does the heavy pass over the streaming history: local-time conversion
  first (Spotify exports UTC; an uncorrected clock puts the 2 a.m. peak at breakfast), then
  sessions, eras, lifers and flares, seasonality, the skip curve under two definitions, podcasts
  and audiobooks split out. `songs.py` computes the *first encounters* — for each song that became
  a favourite, the dated first five plays with device and seconds heard — and `behaviour.py` the
  love arcs (a love signal is the fifth stream in a trailing 30 days; four arc shapes), repeat
  loops, rediscovery candidates, discovery retention by cohort, session styles and the library audit.
- **`tech_aggregate.py`** merges the technical logs across every export on disk with exact-row
  dedup, because Spotify discards them after about ninety days and the windows of two exports
  turned out to be disjoint — replacing one with the other would have lost a quarter. It also
  reconciles Spotify's *On Repeat* against the record and reads the ad-inference segments.
- **`build_page.py`** trims the payload, writes the single-file page and thirteen CSV exports.

## Things the data forced

- **Days that were not me.** On 9 January 2025 the account played 269 streams from a Mac in
  Brazil and an Android in Colombia and Mexico — sertanejo and reggaeton, 81% from artists heard
  on no other day. Someone else had the login. The aggregator now detects such days on its own:
  at least 50 streams, at least 70% from single-day artists, *and* a device-country pair under 1%
  of lifetime. Taste alone misfires (a day of rain-sound content farms on my own speaker); device
  alone misfires (a VPN year of Beethoven). Both together are needed, and flagged days are
  excluded from every figure.
- **Local time before anything else.** Every hour-of-day and weekday figure is in Eastern time;
  the raw `ts` is UTC and the shift is four to five hours.
- **The technical-log expiry.** The extended history is permanent; the technical logs are not.
  The page's *system health*, device and route sections only exist because every export's logs
  were kept and merged.

## Rebuilding

```bash
export SPOTIFY_EXPORT_ROOTS="/path/to/exports"   # optional; defaults to ~/Downloads and ~/Documents
python deep_aggregate.py       # streaming history + account data -> deep.json (~3 min)
python tech_aggregate.py       # technical logs, merged across exports -> tech.json
python build_page.py           # deep.json + tech.json + track_index.json -> listening-machine.html, csv/
```

Request all three categories from Spotify's privacy settings (extended streaming history,
technical log information, account data); unzip them under a root without renaming the folders
Spotify puts inside. The aggregates (`deep.json`, `tech.json`, `track_index.json`) are committed,
so `build_page.py` runs from a clone; the raw exports are not.

## Provenance

The fourth pass over this archive (September 2026); the *Method* tab lists what each earlier
build covered. Built with an AI coding assistant as pair programmer, as one of two parallel
builds from the same brief — several analyses (love arcs, repeat loops, discovery retention)
were adopted from the other build, and the page says so; the local-time correction, the
intrusion detector and the merged technical logs are what this one adds. MIT licensed.
