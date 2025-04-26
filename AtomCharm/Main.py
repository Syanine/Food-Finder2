"""
NYC Food Swipe – v2.5
Small QoL upgrades + NameError fix
"""

from __future__ import annotations
import datetime as _dt, json, math, random, urllib.parse, hashlib, urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple
import streamlit as st, folium
from streamlit_extras.card import card
from streamlit_extras.stylable_container import stylable_container
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# ───────── paths / constants ─────────
ROOT,FOODS_PATH,REST_PATH = Path(__file__).parent, Path("realfoods.json"), Path("resturantstemp.json")
CACHE_DIR = ROOT/".cache_imgs"; CACHE_DIR.mkdir(exist_ok=True)
PLACEHOLDER="https://via.placeholder.com/640x420.png?text=No+Image"
NYC_CENTER=(40.7580,-73.9855)
MOOD_KEYWORDS={"Comforting":"comfort","Healthy":"healthy","Adventurous":"spicy"}
BADGE_THRESH=[(3,"Taster ×3"),(7,"Foodie ×7"),(15,"Gourmand ×15")]

# ───────── utility helpers ─────────
def _load_json(p:Path)->List[Dict[str,Any]]:
    try: return json.loads(p.read_text("utf-8"))
    except Exception as e: st.warning(f"⚠️ {p.name}: {e}"); return []

def _norm(s:str)->str: return s.strip().lower()
@lru_cache(maxsize=256)
def _haversine(lat1,lon1,lat2,lon2):
    R=6371; φ1,φ2=map(math.radians,(lat1,lat2))
    dφ,dλ=map(math.radians,(lat2-lat1,lon2-lon1))
    a=math.sin(dφ/2)**2+math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))
def _maps(addr:str)->str: return f"[{addr}](https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(addr)})"
def _tweet(txt:str)->str: return f"https://twitter.com/intent/tweet?text={urllib.parse.quote_plus(txt)}"

# image cache
def _cache_path(url:str)->Path:
    h=hashlib.md5(url.encode()).hexdigest(); ext=(Path(url).suffix or ".jpg").split("?")[0]
    return CACHE_DIR/f"{h}{ext}"
@st.cache_data(show_spinner=False)
def _get_bytes(url:str)->bytes|None:
    if not url: return None
    if "images.unsplash.com" in url and "?" not in url: url+="?auto=format&fit=crop&w=900&q=80"
    p=_cache_path(url)
    if p.exists(): return p.read_bytes()
    try: data=urllib.request.urlopen(url,timeout=6).read(); p.write_bytes(data); return data
    except Exception: return None

# geocode (missing coords)
geolocator=Nominatim(user_agent="nyc_swipe", timeout=8)
@st.cache_data(show_spinner=False)
def _geocode(addr:str)->Tuple[float,float]|None:
    try:
        loc=geolocator.geocode(addr+", New York")
        if loc: return loc.latitude,loc.longitude
    except Exception: pass
    return None

# data
foods=_load_json(FOODS_PATH)
restaurants=_load_json(REST_PATH)
by_cuisine:Dict[str,List[Dict[str,Any]]]={}
for r in restaurants: by_cuisine.setdefault(_norm(r["cuisine"]),[]).append(r)

# state
if "idx" not in st.session_state:
    st.session_state.update(idx=0,likes=[],dislikes=[],notes={},badges=set(),reviews={},xp=0)

# quick helpers
def _current(): st.session_state.idx%=len(foods); return foods[st.session_state.idx]
def _next(): st.session_state.idx+=1
def _find_food(name:str): return next((f for f in foods if f["name"]==name),None)

def _award(b):
    if b not in st.session_state.badges:
        st.session_state.badges.add(b); st.toast(f"🏆 Badge unlocked: {b}",icon="🥇"); st.balloons()
def _check_badges(): [ _award(b) for k,b in BADGE_THRESH if len(st.session_state.likes)>=k ]

def _like():
    nm=_current()["name"]
    if nm not in st.session_state.likes:
        st.session_state.likes.append(nm); st.session_state.xp+=10; _check_badges()
    _next();
def _dislike(): st.session_state.dislikes.append(_current()["name"]); _next();
def _surprise(): st.session_state.idx=random.randrange(len(foods));

# ─────── Sidebar UI ───────
with st.sidebar:
    st.subheader("🍽️ Filters")
    diet_filter=st.multiselect("Dietary tags",["vegan","vegetarian","gluten-free","halal","kosher"])
    mood=st.radio("I'm craving…",["Any","Comforting","Healthy","Adventurous"],horizontal=True)
    if st.button("Clear filters"): diet_filter.clear(); mood="Any"; st.rerun()

    st.markdown("---")
    st.write(f"👍 **Likes** {len(st.session_state.likes)}")
    st.write(f"👎 **Dislikes** {len(st.session_state.dislikes)}")
    st.write(f"⭐ **XP** {st.session_state.xp}")

    if st.button("⚠️  Clear stats"): st.session_state.likes.clear(); st.session_state.dislikes.clear(); st.session_state.badges.clear(); st.session_state.xp=0; st.rerun()

page=st.sidebar.radio("Navigate",("Swipe","Favorites","Recommended","Achievements","Profile"))

# global css
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');
html,body,[class*="css"]{font-family:'Poppins',sans-serif;} button:hover{transform:scale(1.05);transition:.15s}
[data-testid="stImage"] img{transition:transform .3s} [data-testid="stImage"]:hover img{transform:scale(1.05)}
div[data-baseweb="progress-bar"]>div:first-child{animation:glow 2s infinite alternate}
@keyframes glow{from{box-shadow:0 0 4px #ffb}to{box-shadow:0 0 12px #ffd}}
h1,h2,h3,h4{background:linear-gradient(90deg,#ff512f,#dd2476);-webkit-background-clip:text;color:transparent;}
#toTop{position:fixed;bottom:15px;right:20px;font-size:28px;text-decoration:none}
</style>
""",unsafe_allow_html=True)

# ---- Swipe Page ----
if page=="Swipe":
    # surprise me button
    st.button("🎲 Surprise me (S)",on_click=_surprise)

    while st.session_state.idx<len(foods):
        d=_current()
        if all(t.lower() in d.get("Dietary_Restrictions","").lower() for t in diet_filter) and (mood=="Any" or d.get("mood")==mood):
            break
        _next()
    if st.session_state.idx>=len(foods):
        st.header("No more matches 🙌"); st.button("Restart",on_click=lambda:st.session_state.update(idx=0)); st.stop()

    dish=_current()
    st.image(_get_bytes(dish["image"]) or PLACEHOLDER,caption=dish["name"],use_container_width=True)
    st.markdown(f"### {dish['name']}")
    st.write(f"**Cuisine:** {dish['culture']} • **Main ingredient:** {dish['main_ingredient']} • **Price:** ${dish['average_price']}")

    # mini progress indicator
    total_matches=sum(1 for f in foods if all(t.lower() in f.get("Dietary_Restrictions","").lower() for t in diet_filter) and (mood=="Any" or f.get("mood")==mood))
    cur_index=sum(1 for i,f in enumerate(foods) if i<=st.session_state.idx and all(t.lower() in f.get("Dietary_Restrictions","").lower() for t in diet_filter) and (mood=="Any" or f.get("mood")==mood))
    st.progress(cur_index/total_matches,text=f"{cur_index}/{total_matches} matches")

    match=random.choice(by_cuisine.get(_norm(dish["culture"]),[])) if by_cuisine.get(_norm(dish["culture"])) else None
    st.markdown("---")
    if match:
        st.markdown(f"#### Eat it at **{match['name']}** ({match['price']})")
        st.markdown(_maps(match['address']),unsafe_allow_html=True)
    else: st.info("No NYC restaurant recorded for this cuisine.")

    col1,col2=st.columns(2)
    col1.button("👍 Like",on_click=_like,help="or press →")
    col2.button("👎 Dislike",on_click=_dislike,help="or press ←")

    note_key=dish["name"]; note=st.text_area("Personal note",st.session_state.notes.get(note_key,""))
    if note.strip(): st.session_state.notes[note_key]=note

# ---- Favorites ----
elif page=="Favorites":
    if not st.session_state.likes: st.info("No favourites yet."); st.stop()
    search=st.text_input("Search favourites")
    visible=[n for n in st.session_state.likes if search.lower() in n.lower()]
    sort=st.selectbox("Sort by",("Name","Price","Cuisine"))
    keyfn={"Name":lambda n:n,"Price":lambda n:_find_food(n)["average_price"],"Cuisine":lambda n:_find_food(n)["culture"]}[sort]
    for nm in sorted(visible,key=keyfn):
        f=_find_food(nm);  # assume exists
        with stylable_container(key=nm,css_styles="border:1px solid #ddd;padding:8px;border-radius:6px;"):
            st.markdown(f"**{nm}** — {f['culture']} (${f['average_price']})")
            st.caption(st.session_state.notes.get(nm,"—"))
            cols=st.columns([1,1])
            cols[0].markdown(f"[Share]({_tweet(f'I love {nm}! #FoodSwipe')})",unsafe_allow_html=True)
            if cols[1].button("🗑️ Remove",key=f"del_{nm}"): st.session_state.likes.remove(nm); st.rerun()
    st.markdown('<a id="toTop" href="#">⬆️</a>',unsafe_allow_html=True)

# ---- Recommended ----
elif page=="Recommended":
    st.header("Recommended Restaurants")
    if not st.session_state.likes:
        st.info("Like dishes first!")
        st.stop()

    liked_cuis = [_find_food(n)["culture"] for n in st.session_state.likes if _find_food(n)]
    freq = {_norm(c): liked_cuis.count(c) for c in set(liked_cuis)}


    def _score(r):
        base = freq.get(_norm(r["cuisine"]), 0) * 2
        if mood != "Any" and MOOD_KEYWORDS[mood] in _norm(r["cuisine"]):
            base += 1
        lat, lon = (r.get(k) for k in ("lat", "lon"))
        if not lat or not lon:
            geo = _geocode(r["address"])
            lat, lon = geo if geo else (None, None)
        return _haversine(lat, lon, *NYC_CENTER) / 2 - base if lat and lon else 1e9


    ranked = sorted(restaurants, key=_score)[:len(st.session_state.likes)]

    m = folium.Map(NYC_CENTER, zoom_start=11)
    folium.Marker(NYC_CENTER, tooltip="Times Sq").add_to(m)

    # Generate and store random red points only once
    if "red_points" not in st.session_state:
        red_points = []
        for _ in range(100):
            lat_offset = random.uniform(-0.05, 0.05)
            lon_offset = random.uniform(-0.05, 0.05)
            lat = NYC_CENTER[0] + lat_offset
            lon = NYC_CENTER[1] + lon_offset
            red_points.append((lat, lon))
        st.session_state["red_points"] = red_points
    else:
        red_points = st.session_state["red_points"]

    for lat, lon in red_points:
        folium.Marker(
            [lat, lon],
            radius=3,
            color="red",
            icon=folium.Icon(color="red")
        ).add_to(m)

    for r in ranked:
        lat, lon = (r.get(k) for k in ("lat", "lon"))
        if not lat or not lon:
            geo = _geocode(r["address"])
            lat, lon = geo if geo else (None, None)
        if lat and lon:
            dist = _haversine(lat, lon, *NYC_CENTER)
            html = (
                f"<b>{r['name']}</b><br>{r['address']}<br>"
                f"<i>{dist:.1f} km from TSQ</i><br>"
                f"<img src='{r.get('photo', '')}' width='120'>"
            )
            folium.Marker(
                [lat, lon],
                tooltip=f"{r['name']} \u2022 {r['cuisine']}",
                popup=folium.Popup(html, max_width=220)
            ).add_to(m)

    st_folium(m, key="map", height=500, width=700)
    st.markdown("---")
    for r in ranked:
        st.markdown(f"**{r['name']}** — {r['price']} • {r['cuisine']}")
        st.write(_maps(r['address']))
        st.markdown("---")
    st.markdown('<a id="toTop" href="#">⬆️</a>', unsafe_allow_html=True)
# ---- Achievements ----
elif page=="Achievements":
    st.header("🏆 Badges")
    unlocked=st.session_state.badges
    for req,b in BADGE_THRESH:
        border="2px solid lime" if b in unlocked else "1px solid #888"
        card(title=b if b in unlocked else "???",
             text=f"{len(st.session_state.likes)}/{req} likes",
             image=PLACEHOLDER,
             key=b,
             styles={"card":{"border":border}})

# ---- Profile ----
else:
    liked_cuis=[_find_food(n)["culture"] for n in st.session_state.likes if _find_food(n)]
    levels=[("Foodie",0),("Gourmet",150),("Epicurean",300)]
    curr,nxt=levels[0],None
    for i,lv in enumerate(levels):
        if st.session_state.xp>=lv[1]: curr=lv; nxt=levels[i+1] if i+1<len(levels) else None
    st.header("🍔 Your Food Profile")
    st.subheader(f"Level: {curr[0]}")
    if nxt:
        pct=(st.session_state.xp-curr[1])/(nxt[1]-curr[1])
        st.progress(pct,text=f"{st.session_state.xp}/{nxt[1]} XP")
    else: st.write("Max level reached! 🎉")

    tot=len(st.session_state.likes)
    fav=max(set(liked_cuis),key=liked_cuis.count) if liked_cuis else "—"
    avg=sum(_find_food(n)["average_price"] for n in st.session_state.likes)/tot if tot else 0

    st.markdown(f"* **Total liked dishes:** {tot}\n* **Favourite cuisine:** {fav}\n* **Average preferred price:** ${avg:.2f}")
    st.markdown('<a id="toTop" href="#">⬆️</a>',unsafe_allow_html=True)