"""YouTube comment collector for UrbanPulse (stricter version).

Only reads videos that are actually about Mangalore, keeps comments that describe a
civic problem in English, throws away ads / other cities / chapter lists, and keeps
only the best comments (capped at MAX_TOTAL).

Setup: put   YOUTUBE_API_KEY=your_key   in a .env file in the project root.
Run by hand from the project root:   python -m collectors.youtube_collector
Or use the "Refresh data" button on the admin Overview page.
To start fresh, delete data/raw/youtube_comments.csv and run again.
"""
import os
import re
import sys
from collections import Counter
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
from nlp.predict import analyze_text  # noqa: E402

load_dotenv()

OUT_PATH = "data/raw/youtube_comments.csv"
CACHE_PATH = "data/raw/youtube_raw_cache.csv"   # every comment ever fetched (lets us re-filter offline)
API = "https://www.googleapis.com/youtube/v3"
AREAS = ["Hampankatta", "Kankanady", "Surathkal", "Lalbagh",
         "Bejai", "Kadri", "Pumpwell", "Jyothi"]

# ---- how much to keep -------------------------------------------------------
MAX_TOTAL = 60          # the CSV never holds more than this many comments
MAX_PER_AREA = 12       # so one area can't take over the map
MIN_SCORE = 3           # relevance score a comment needs (see _score)
MIN_LEN, MAX_LEN = 20, 500

# ---- searching (each search costs 100 quota units; free quota is 10,000/day) --
AREA_QUERIES = ["{area} Mangalore road traffic", "{area} Mangalore drainage flooding garbage"]
CITY_QUERIES = ["Mangalore drainage problem", "Mangalore potholes road condition",
                "Mangalore garbage waste problem", "Mangalore water supply problem",
                "Mangalore footpath encroachment", "Mangaluru MCC complaints",
                "Mangalore traffic bus stand"]
VIDEOS_PER_SEARCH = 25     # same 100-unit cost for 10 or 50 results, so take more
COMMENTS_PER_VIDEO = 100

# ---- filters ----------------------------------------------------------------
MANGALORE_RE = re.compile(r"mangalor|mangaluru|mangalooru|\bmcc\b|dakshina kannada|kudla|karavali", re.I)
OTHER_CITIES_RE = re.compile(
    r"bangalore|banglore|bengaluru|bengalooru|\bblr\b|chennai|mumbai|delhi|hyderabad|vijayawada|"
    r"amaravati|amaravathi|kolkata|pune\b|andhra|tamil nadu|vizag|guntur|madhya pradesh|assam|"
    r"rajasthan|indonesia|florida|australia|singapore|dubai|hebbal|silk board|whitefield|hitech|"
    r"mount road|anna salai|bhopal|jaipur|lucknow|nellore|kerala only", re.I)
BAD_PATTERNS = re.compile(
    r"\d{1,2}:\d{2}|https?://|www\.|\.com\b|\b\d{10}\b|\+?\d[\d\s-]{9,}\d|"
    r"contact us|subscribe|whatsapp|follow me|check out my|promo", re.I)

CATEGORY_WORDS = {
    "Road": ["road", "roads", "pothole", "potholes", "traffic", "footpath", "footpaths", "signal",
             "highway", "flyover", "u turn", "u-turn", "junction", "congestion", "parking"],
    "Drainage": ["drain", "drains", "drainage", "sewage", "sewer", "flood", "flooding", "flooded",
                 "waterlogging", "gutter", "storm drain", "rajakaluve"],
    "Water": ["water supply", "no water", "water shortage", "tap water", "pipeline", "borewell",
              "tanker", "water problem"],
    "Garbage": ["garbage", "waste", "trash", "dustbin", "litter", "dumping", "stink", "smell"],
    "Transport": ["bus", "buses", "bus stand", "busstand", "auto", "rickshaw", "metro", "railway"],
}
PROBLEM_WORDS = re.compile(
    r"\b(no|not|never|lack|lacks|lacking|problem|problems|issue|issues|bad|worst|terrible|horrible|"
    r"poor|pathetic|disaster|broken|damaged|blocked|block|jam|suffer|suffering|dirty|unsafe|illegal|"
    r"need|needs|should|must|please|pls|fix|fixed|solve|solution|every year|negligence|useless|"
    r"irresponsible|encroach\w*|failed|failure|pollution)\b", re.I)
ENGLISH_WORDS = set("""the a an is are was were be been being of in on at for and or but it its this that
these those there their they them we you your i my our have has had with from by as can will would should
could must may might need if all very more only when which what why how does did just than also too because
still even much many no not here where who about into over after before every some any during while then
such other another again same most each both few less around near along since until without within between
against under above below one two out up down people nobody""".split())

def _get(endpoint, **params):
    params["key"] = os.getenv("YOUTUBE_API_KEY")
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _find_area(text):
    low = text.lower()
    return next((a for a in AREAS if a.lower() in low), None)


def _hits(text, words):
    low = text.lower()
    return sum(bool(re.search(rf"\b{re.escape(w)}\b", low)) for w in words)


def _english_ratio(text):
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if len(tokens) < 4 or len(tokens) < 0.8 * len(text.split()):   # too short, or lots of non-Latin script
        return 0
    hits = [t for t in tokens if t in ENGLISH_WORDS]
    return len(hits) / len(tokens) if len(set(hits)) >= 2 else 0   # need 2+ different English words


def judge(text, why=None):
    """Return (category, score) if the comment is a useful civic complaint, else None.
    If a Counter is passed as `why`, the rejection reason is counted in it."""
    def no(reason):
        if why is not None:
            why[reason] += 1
        return None

    if not (MIN_LEN <= len(text) <= MAX_LEN):
        return no("too short/long")
    if BAD_PATTERNS.search(text):
        return no("ad/link/timestamp")
    if OTHER_CITIES_RE.search(text) and not MANGALORE_RE.search(text):
        return no("other city")
    if _english_ratio(text) < 0.15:
        return no("not English")
    cats = {c: _hits(text, w) for c, w in CATEGORY_WORDS.items()}
    category = max(cats, key=cats.get)
    if cats[category] == 0:
        return no("no civic topic")
    problems = len(PROBLEM_WORDS.findall(text))
    if problems == 0 and cats[category] < 2:
        return no("no complaint/suggestion")
    score = 2 * min(cats[category], 2) + min(problems, 3) + (2 if _find_area(text) else 0) \
        + (1 if MANGALORE_RE.search(text) else 0)
    return (category, score) if score >= MIN_SCORE else no("low score")


def _saved():
    if not os.path.exists(OUT_PATH):
        return pd.DataFrame(columns=["id", "area"])
    return pd.read_csv(OUT_PATH, dtype={"id": str})


def _load_cache():
    if os.path.exists(CACHE_PATH):
        return pd.read_csv(CACHE_PATH, dtype={"id": str}).fillna("")
    return pd.DataFrame(columns=["id", "text", "title", "search_area", "published"])


def _fetch(known_ids):
    """Search YouTube and return (raw comment rows, videos checked, videos skipped)."""
    queries = [(a, t.format(area=a)) for a in AREAS for t in AREA_QUERIES] + [(None, q) for q in CITY_QUERIES]
    rows, videos_done, skipped = [], set(), 0
    for search_area, query in queries:
        search = _get("search", part="snippet", type="video", maxResults=VIDEOS_PER_SEARCH,
                      q=query, regionCode="IN", relevanceLanguage="en")
        for video in search.get("items", []):
            vid = video["id"]["videoId"]
            if vid in videos_done:
                continue
            videos_done.add(vid)
            title = video["snippet"]["title"]
            about = title + " " + video["snippet"].get("description", "")
            if not MANGALORE_RE.search(about):
                skipped += 1                         # video isn't about Mangalore
                continue
            try:
                threads = _get("commentThreads", part="snippet", videoId=vid,
                               maxResults=COMMENTS_PER_VIDEO, order="relevance", textFormat="plainText")
            except requests.HTTPError:
                continue                             # comments disabled, or quota used up
            for t in threads.get("items", []):
                cid = "yt-" + t["id"]
                if cid in known_ids:
                    continue
                known_ids.add(cid)
                snip = t["snippet"]["topLevelComment"]["snippet"]
                rows.append({"id": cid, "text": re.sub(r"\s+", " ", snip["textDisplay"]).strip(),
                             "title": title, "search_area": search_area or "",
                             "published": snip["publishedAt"]})
    return rows, len(videos_done), skipped


def collect(refilter=False):
    """Fetch comments (unless refilter=True), keep the best ones, save, return how many were added.

    refilter=True skips YouTube completely and just re-runs the filters on the cached comments,
    so you can tune the rules without using any API quota.
    """
    old = _saved()
    room = MAX_TOTAL - len(old)
    if room <= 0:
        print(f"Already holding {len(old)} comments (limit {MAX_TOTAL}). "
              f"Delete {OUT_PATH} to start fresh.")
        return 0

    cache = _load_cache()
    info = ""
    if not refilter:
        if not os.getenv("YOUTUBE_API_KEY"):
            raise RuntimeError("YOUTUBE_API_KEY not found. Add it to a .env file in the project root.")
        new_rows, n_videos, skipped = _fetch(set(cache["id"]) | set(old["id"]))
        if new_rows:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            pd.DataFrame(new_rows).to_csv(CACHE_PATH, mode="a", header=not os.path.exists(CACHE_PATH), index=False)
            cache = pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True)
        info = f"Checked {n_videos} videos ({skipped} skipped: not about Mangalore), {len(new_rows)} new comments. "

    seen, why, candidates = set(old["id"]), Counter(), []
    for r in cache.itertuples():
        if r.id in seen:
            continue
        verdict = judge(r.text, why)
        if not verdict:
            continue
        category, score = verdict
        area = _find_area(r.text) or _find_area(r.title) or (r.search_area or None)
        if not area:
            why["no area"] += 1                      # can't place it on the map
            continue
        candidates.append({"id": r.id, "text": r.text, "area": area, "category": category,
                           "source": "youtube", "timestamp": r.published, "score": score})

    # keep the best-scoring comments, with a cap per area
    per_area = Counter(old["area"])
    chosen = []
    for c in sorted(candidates, key=lambda c: c["score"], reverse=True):
        if len(chosen) >= room:
            break
        if per_area[c["area"]] >= MAX_PER_AREA:
            continue
        c["emotion"], c["intensity"] = analyze_text(c["text"])
        per_area[c["area"]] += 1
        chosen.append(c)

    if chosen:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        df = pd.DataFrame(chosen).drop(columns="score")
        df.to_csv(OUT_PATH, mode="a", header=not os.path.exists(OUT_PATH), index=False)
    print(f"{info}{len(cache)} comments in cache, {len(candidates)} passed filters, kept {len(chosen)}.")
    if why:
        print("Rejected because:", ", ".join(f"{k}: {v}" for k, v in why.most_common()))
    return len(chosen)


if __name__ == "__main__":
    n = collect(refilter="--refilter" in sys.argv)
    print(f"{datetime.now():%H:%M:%S}  Added {n} new comments to {OUT_PATH}")
