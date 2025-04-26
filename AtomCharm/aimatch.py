"""
NYC Food Swipe – offline-friendly, crash-proof rev.
--------------------------------------------------
* Like / dislike dishes, match one NYC restaurant
* Dietary filter, mood selector, XP + badges
* Recommended-map tab, favourites, profile
* Works fully offline: JSON only, no API calls
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import random
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import folium
import streamlit as st
from streamlit_extras.card import card
from streamlit_extras.stylable_container import stylable_container
from streamlit_shortcuts import add_keyboard_shortcuts
from streamlit_folium import st_folium

# ──────────────────────────── paths & constants ────────────────────────────
ROOT           = Path(__file__).parent
FOODS_PATH     = ROOT / "foods.json"
REST_PATH      = ROOT / "restaurants.json"
PLACEHOLDER    = "https://via.placeholder.com/400x300.png?text=No+Image"
NYC_CENTER     = (40.7580, -73.9855)           # Times Sq anchor
MOOD_TAG       = {"Comforting": "comfort", "Healthy": "salad", "Adventurous": "spicy"}

# ───────────────────────────── helper functions ────────────────────────────
def _safe_json(path: Path) -> List[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:                                           # noqa: BLE001
        st.warning(f"⚠️ Failed to load {path.name}: {exc}")
        return []

def _norm(s: str) -> str:
    return s.strip().lower()

@lru_cache(maxsize=256)
def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _maps(addr: str) -> str:
    return f"[{addr}](https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(addr)})"

def _tweet(txt: str) -> str:
    return f"https://twitter.com/intent/tweet?text={urllib.parse.quote_plus(txt)}"

def _fix_img(url: str | None) -> str:
    if url and "images.unsplash.com" in url and "?" not in url:
        return url + "?auto=format&fit=crop&w=800&q=80"
    return url or PLACEHOLDER

# ─────────────────────────────── load + clean ──────────────────────────────
foods_raw        = _safe_json(FOODS_PATH)
restaurants_raw  = _safe_json(REST_PATH)

foods = [f for f in foods_raw if f.get("name") and f.get("culture")]
restaurants = [r for r in restaurants_raw if r.get("name") and r.get("cuisine")]

by_cuisine: Dict[str, List[Dict[str, Any]]] = {}
for r in restaurants:
    by_cuisine.setdefault(_norm(r["cuisine"]), []).append(r)

# ─────────────────────────── session state init ────────────────────────────
if "idx" not in st.session_state:
    st.session_state.update(
        idx=0, likes=[], dislikes=[], notes={}, badges=set(), reviews={}, xp=0
    )

# ───────────────────────────── sidebar controls ────────────────────────────
with st.sidebar:
    st.subheader("🍽️ Filters")
    diet_filter = st.multiselect(
        "Dietary preference (dish must include all)",
        ["vegan", "vegetarian", "gluten-free", "halal", "kosher"],
    )
    mood = st.radio("I'm craving…", ["Any", "Comforting", "Healthy", "Adventurous"], horizontal=True)

page = st.sidebar.radio("Navigate", ("Swipe", "Favorites", "Recommended", "Achievements", "Profile"))

# ──────────────────────── tiny state-mutating helpers ──────────────────────
def _dish() -> Dict[str, Any]:         return foods[st.session_state.idx]
def _advance() -> None:                st.session_state.idx += 1
def _award(b: str) -> None:
    if b not in st.session_state.badges:
        st.session_state.badges.add(b); st.balloons(); st.toast(f"Unlocked **{b}**!", icon="🏆")

def _check_badges() -> None:
    ln = len(st.session_state.likes)
    for n, b in ((10, "Taster ×10"), (25, "Foodie ×25"), (50, "Gourmand ×50")):
        if ln >= n: _award(b)
    week_ago = _dt.date.today() - _dt.timedelta(days=7)
    if len({d["culture"] for d in st.session_state.likes if _dt.date.fromisoformat(d["date"]) >= week_ago}) >= 3:
        _award("Weekly Explorer")

def _left():
    st.session_state.dislikes.append(_dish()); _advance(); st.rerun()

def _right():
    st.session_state.likes.append(_dish() | {"date": str(_dt.date.today())})
    st.session_state.xp += 10; _check_badges(); _advance(); st.rerun()

add_keyboard_shortcuts({"ArrowLeft": _left, "ArrowRight": _right})

# ────────────────────────────────── 1) SWIPE ───────────────────────────────
if page == "Swipe":
    while st.session_state.idx < len(foods):
        d = _dish()
        if all(t in d.get("tags", []) for t in diet_filter):
            if mood == "Any" or d.get("mood") == mood:
                break
        _advance()

    if st.session_state.idx >= len(foods):
        st.header("🎉 You’ve browsed every matching dish!")
        fav_cui = None
        if st.session_state.likes:
            fav_cui = max(
                {d["culture"] for d in st.session_state.likes},
                key=lambda c: sum(1 for d in st.session_state.likes if d["culture"] == c),
            )
        candidates = by_cuisine.get(_norm(fav_cui), []) if fav_cui else []
        rec = random.choice(candidates) if candidates else None
        if rec:
            st.subheader("Try this place next")
            st.markdown(f"**{rec['name']}** — {rec['price']} • {rec['cuisine']}")
            st.markdown(_maps(rec['address']), unsafe_allow_html=True)
            st.image(_fix_img(rec.get("photo")), width=260)
        if st.button("🔄 Restart"): st.session_state.idx = 0; st.rerun()
        st.stop()

    d = _dish()
    st.image(_fix_img(d.get("image")), use_container_width=True)
    st.markdown(f"## {d['name']}")
    st.write(f"**Cuisine:** {d['culture']}   •   **Main ingredient:** {d['main_ingredient']}")
    st.write(f"**Typical price:** ${d['avg_price']}")

    match_list = by_cuisine.get(_norm(d["culture"]), [])
    match = random.choice(match_list) if match_list else None
    st.markdown("---")
    if match:
        st.markdown("### Where to eat this in NYC")
        st.markdown(f"**{match['name']}** — {match['price']} • {match['cuisine']}")
        st.markdown(_maps(match['address']), unsafe_allow_html=True)
    else:
        st.info("No matching restaurant in list.")

    c1, c2 = st.columns(2)
    if c1.button("👎 Dislike", key=f"d_{st.session_state.idx}"): _left()
    if c2.button("👍 Like",    key=f"l_{st.session_state.idx}"): _right()

    nk = f"note_{st.session_state.idx}"
    note = st.text_area("Your note", st.session_state.notes.get(nk, ""), key=nk)
    if note.strip(): st.session_state.notes[nk] = note

    if match:
        rk = match["name"]
        st.markdown("#### Your rating")
        stars = st.slider(" ", 1, 5, 3, key=f"s_{rk}", label_visibility="collapsed")
        comment = st.text_input("Add a comment", key=f"c_{rk}")
        if st.button("Submit review", key=f"b_{rk}") and comment.strip():
            st.session_state.reviews.setdefault(rk, []).append((stars, comment))
            st.success("Thanks for reviewing!")
        rv = st.session_state.reviews.get(rk, [])
        if rv: st.markdown(f"**Community rating:** {sum(x[0] for x in rv)/len(rv):.1f} ★ ({len(rv)} reviews)")

    st.caption("Tip: use ← / → keys to swipe faster!")

# ───────────────────────────────── 2) FAVES ────────────────────────────────
elif page == "Favorites":
    if not st.session_state.likes: st.info("No liked dishes yet."); st.stop()

    unique = {d['name']: d for d in st.session_state.likes}.values()
    sort_by = st.selectbox("Sort by", ("Name", "Price", "Cuisine"))
    key_map = {"Name": "name", "Price": "avg_price", "Cuisine": "culture"}

    for d in sorted(unique, key=lambda x: x[key_map[sort_by]]):
        with stylable_container(key=f"fav_{d['name']}",
                                css_styles="border:1px solid #ddd;padding:8px;border-radius:6px;"):
            st.markdown(f"**{d['name']}** — {d['culture']} (${d['avg_price']})")
            st.markdown(f"[Share]({_tweet(f'I love {d['name']}! #FoodSwipeApp')})", unsafe_allow_html=True)
            idx = foods.index(d)
            st.caption(f"Note: {st.session_state.notes.get(f'note_{idx}', '—')}")

# ────────────────────────────── 3) RECOMMENDED ─────────────────────────────
elif page == "Recommended":
    st.header("Recommended Restaurants")
    if not st.session_state.likes: st.info("Like some dishes first!"); st.stop()

    liked = [_norm(d["culture"]) for d in st.session_state.likes]
    freq  = {c: liked.count(c) for c in set(liked)}

    def _score(r: Dict[str, Any]) -> float:
        base = freq.get(_norm(r["cuisine"]), 0) * 2
        if MOOD_TAG.get(mood) in r.get("tags", []): base += 1
        lat, lon = r.get("lat"), r.get("lon")
        if lat and lon: return _haversine(lat, lon, *NYC_CENTER)/2 - base
        return 1e9

    ranked = sorted(restaurants, key=_score)[:20]
    fmap   = folium.Map(location=NYC_CENTER, zoom_start=11)
    folium.Marker(NYC_CENTER, tooltip="Times Square").add_to(fmap)
    for r in ranked:
        if "lat" in r and "lon" in r:
            folium.Marker([r["lat"], r["lon"]],
                          tooltip=f"{r['name']} • {r['cuisine']}",
                          popup=f"{r['name']}<br>{r['address']}").add_to(fmap)
    st_folium(fmap, key="map", height=500, width=700)

    st.markdown("---")
    for r in ranked:
        st.markdown(f"**{r['name']}** — {r['price']} • {r['cuisine']}")
        st.write(r["address"]); st.markdown("---")

# ─────────────────────────────── 4) BADGES ────────────────────────────────
elif page == "Achievements":
    st.header("🏆 Badges")
    for b in ("Taster ×10", "Foodie ×25", "Gourmand ×50", "Weekly Explorer"):
        card(title=b if b in st.session_state.badges else "???", text=" ", image=PLACEHOLDER, key=b)

# ──────────────────────────────── 5) PROFILE ──────────────────────────────
else:
    if not st.session_state.likes: st.info("Like dishes first!"); st.stop()

    levels = [("Foodie", 0), ("Gourmet", 200), ("Epicurean", 500)]
    curr, nxt = levels[0], None
    for i, lv in enumerate(levels):
        if st.session_state.xp >= lv[1]:
            curr, nxt = lv, levels[i+1] if i+1 < len(levels) else None

    st.header("🍔 Your Food Profile")
    st.subheader(f"Level: {curr[0]}")
    if nxt:
        pct = (st.session_state.xp - curr[1]) / (nxt[1] - curr[1])
        st.progress(pct, text=f"{st.session_state.xp}/{nxt[1]} XP to {nxt[0]}")
    else:
        st.write("Max level reached! 🎉")

    total = len(st.session_state.likes)
    fav   = max({d["culture"] for d in st.session_state.likes},
                key=lambda c: sum(1 for d in st.session_state.likes if d["culture"] == c))
    avg   = sum(d["avg_price"] for d in st.session_state.likes) / total

    st.markdown(f"* **Total liked dishes:** {total}\n* **Favourite cuisine:** {fav}\n* **Average preferred price:** ${avg:.2f}")
