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
ROOT = Path(__file__).parent
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
foods= [
    {
        "name": "Beef Bulgogi Banh Mi",
        "culture": "Vietnamese",
        "main_ingredient": "Beef",
        "average_price": 10.00,
        "image": "https://chrisseenplace.com/wp-content/uploads/2022/07/Bulgogi-Banh-Mi-01.jpg",
        "resturant": "Joju",
        "Dietary_Restrictions": "Halal",
        "mood": "Comforting"
    },
    {
        "name": "Vegetable Soup Dumplings",
        "culture": "Chinese",
        "main_ingredient": "Dough, Filling, Broth",
        "average_price": 10.07,
        "image": "https://static01.nyt.com/images/2024/02/08/multimedia/ND-SoupDumplings1-zgvf/ND-SoupDumplings1-zgvf-superJumbo.jpg",
        "resturant": "Nan Xiang Xiao Long Bao",
        "Dietary_Restrictions": "Vegeterian",
        "mood": "Healthy"
    },
    {
        "name": "Butter Chicken",
        "culture": "Indian",
        "main_ingredient": "Chicken",
        "average_price": 12.40,
        "image": "https://static01.nyt.com/images/2024/10/29/multimedia/Butter-Chickenrex-tbvz/Butter-Chickenrex-tbvz-threeByTwoMediumAt2X.jpg",
        "restaurant": "NYC TIKKA MASALA",
        "Dietary_Restrictions": "kosher",
        "mood": "Adventurous"
    },
    {
        "name": "Steam Rice Rolls",
        "culture": "Chinese",
        "main_ingredient": "Rice Flour",
        "average_price": 5.0,
        "image": "https://cdn.shortpixel.ai/spai2/q_glossy+ret_img+to_auto/www.hungryhuy.com/wp-content/uploads/cheung-fun-recipe.jpg",
        "resturant": "Joe's Steam Rice Roll",
        "Dietary_Restrictions": "vegan",
        "mood": "Healthy"
    },
    {
        "name": "Beef Rice Noodles",
        "culture": "Chinese",
        "main_ingredient": "Rice Noodles",
        "average_price": 10.50,
        "image": "https://i.redd.it/umadhqznskv61.jpg",
        "resturant": "Niuddo",
        "Dietary_Restrictions": "gluten-free",
        "mood": "Healthy"
    },
    {
        "name": "Hotpot",
        "culture": "Chinese",
        "main_ingredient": "Meat, Vegetables, Broth",
        "average_price": 40.0,
        "image": "https://vickypham.com/wp-content/uploads/2024/08/fc66c-after-7576.jpg",
        "resturant": "Xiao Long Kan Hotpot",
        "Dietary_Restrictions": "vegetarian",
        "mood": "Adventurous"
    },
    {
        "name": "Curry Mixed Stuff Food Noodle",
        "culture": "Malaysian",
        "main_ingredient": "Curry Noodle",
        "average_price": 13.95,
        "image": "https://s23209.pcdn.co/wp-content/uploads/2018/04/241218_DD_thai-red-curry-noodle-soup_584edit-500x500.jpg",
        "resturant": "Pho Hoang",
        "Dietary_Restrictions": "halal",
        "mood": "Comforting"
    },
    {
        "name": "Chole Bhature",
        "culture": "Indian",
        "main_ingredient": "Spicy Chicken Pea Curry, Deep-fried Bread",
        "average_price": 8.5,
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Chole_Bhature_At_Local_Street.jpg/1200px-Chole_Bhature_At_Local_Street.jpg",
        "resturant": "Bhatura King",
        "Dietary_Restrictions": "vegan",
        "mood": "Adventurous"
    },
    {
        "name": "Peking Duck",
        "culture": "Chinese",
        "main_ingredient": "Duck, Cucumber, Bread",
        "average_price": 2.50,
        "image": "https://ducknbao.com/wp-content/uploads/2024/05/Peking-Duck-By-Jenn-Duncan.jpg.webp",
        "resturant": "Shanghai You Garden",
        "Dietary_Restrictions": "kosher",
        "mood": "Adventurous"
    },
    {
        "name": "Banana Pudding",
        "culture": "Southern U.S.",
        "main_ingredient": "Bananas, Milk",
        "average_price": 9.50,
        "image": "https://cdn.shopify.com/s/files/1/0652/5429/3748/files/marys-favorite-banana-pudding-with-nilla-wafers-mary-disomma-recipe-link_1000x.jpg?v=1704995996",
        "resturant": "Magnolia Bakery",
        "Dietary_Restrictions": "gluten-free",
        "mood": "Comforting"
    },
    {
        "name": "Chocolate Cake",
        "culture": "Universal",
        "main_ingredient": "Flour, Sugar, Cocoa powder",
        "average_price": 55.00,
        "image": "https://imgstore.sndimg.com/magnolia/images/3352b149-cae0-47f6-94ad-0cf962e0335f.jpg",
        "resturant": "Magnolia Bakery",
        "Dietary_Restrictions": "vegetarian",
        "mood": "Comforting"
    },
    {
        "name": "Chcolate Chunck Cookies",
        "culture": "American",
        "main_ingredient": "Flour, batter, sugar, chocolate chunks",
        "average_price": 2.50,
        "image": "https://www.magnoliabakery.com/cdn/shop/products/Choc_Chunk_Cookie_6PK_25829.png?v=1633533285",
        "resturant": "Magnolia Bakery",
        "Dietary_Restrictions": "halal",
        "mood": "Comforting"
    },
    {
        "name": "Tulip Cutout Cookies",
        "culture": "American/European",
        "main_ingredient": "Flour, Butter, Sugar, Eggs",
        "average_price": 3.00,
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6wZT0vnEunlZztLh7QL1__W1nxAmPcgMXRQ&s",
        "resturant": "Magnolia Bakery",
        "Dietary_Restrictions": "vegan",
        "mood": "Comforting"
    },
    {
        "name": "Tiramisu",
        "culture": "Italian",
        "main_ingredient": "Mascarpone Cheese, Ladyfinger biscuits",
        "average_price": 7.00,
        "image": "https://staticcookist.akamaized.net/wp-content/uploads/sites/22/2024/09/THUMB-VIDEO-2_rev1-56.jpeg?im=Resize,width=742;",
        "resturant": "Sweet Moment",
        "Dietary_Restrictions": "kosher",
        "mood": "Comforting"
    },
    {
        "name": "Mango & Cheesecake Milk Shaved Ice",
        "culture": "East Asian",
        "main_ingredient": "Shaved milk ice, fresh mango chuncks",
        "average_price": 12.50,
        "image": "https://s3-media0.fl.yelpcdn.com/bphoto/7R-89E_1xpeeMnC8TIS_Fw/o.jpg",
        "resturant": "Sweet Moment",
        "Dietary_Restrictions": "gluten-free",
        "mood": "Adventurous"
    },
    {
        "name": "Matcha Croissant",
        "culture": "French, Japanese",
        "main_ingredient": "Flour, butter, matcha powder",
        "average_price": 5.00,
        "image": "https://cdn.prod.website-files.com/67243e4511dd4088a21979d9/67482abb3ff76363294252f0_Matcha%20Croissant-p-500.jpg",
        "resturant": "SALSWEE",
        "Dietary_Restrictions": "vegetarian",
        "mood": "Comforting"
    },
    {
        "name": "Strawberry Tarts",
        "culture": "French",
        "main_ingredient": "Tart crust, pastry cream, strawberries",
        "average_price": 6.00,
        "image": "https://cdn.prod.website-files.com/67243e4511dd4088a21979d9/67482949f32b8fbebe69f178_Strawberry%20tart-p-500.jpg",
        "resturant": "SALSWEE",
        "Dietary_Restrictions": "halal",
        "mood": "Comforting"
    },
    {
        "name": "Cummin Lamb Fried Rice",
        "culture": "Chinese",
        "main_ingredient": "Rice, lamb, cuming, garlic, ginger",
        "average_price": 10.50,
        "image": "https://www.popricenyc.com/maglev/assets/8c7d40cd-6832-4ae5-8637-77e65170893f-item-100000013911912530_1637731218.jpg",
        "resturant": "Pop Rice",
        "Dietary_Restrictions": "vegan",
        "mood": "Adventurous"
    },
    {
        "name": "Pineapple Garlic Shrimp Fried Rice",
        "culture": "Chinese",
        "main_ingredient": "Rice, Shrimp, Pineapple, Garlic",
        "average_price": 9.50,
        "image": "https://www.popricenyc.com/maglev/assets/c1e8d7e6-025b-46c5-ade1-578d66bdfb7c-item-100000013911912532_1637731241.jpg",
        "resturant": "Pop Rice",
        "Dietary_Restrictions": "kosher",
        "mood": "Comforting"
    },
    {
        "name": "Fried Rice & Wings",
        "culture": "Chinese",
        "main_ingredient": "Rice, Chicken Wings, Soy Sauce",
        "average_price": 11.00,
        "image": "https://www.popricenyc.com/maglev/assets/6e78e4ba-dd4b-461c-998f-a71443347201-item-100000013909557480_1637731112.jpg",
        "resturant": "Pop Rice",
        "Dietary_Restrictions": "vegetarian",
        "mood": "Comforting"
    },
    {
        "name": "Chicken Seekh Kabab",
        "culture": "Indian",
        "main_ingredient": "Minced Chicken, garlic, onions, green chilies",
        "average_price": 3.00,
        "image": "https://bakefresh.net/wp-content/uploads/2024/03/IMG_8834-scaled-735x1102.jpg",
        "resturant": "Sagar Resturant",
        "Dietary_Restrictions": "gluten-free",
        "mood": "Adventurous"
    },
    {
        "name": "Tandoori Chicken",
        "culture": "Indian",
        "main_ingredient": "Chicken, yogurt, tandoori masala",
        "average_price": 12.00,
        "image": "https://simshomekitchen.com/wp-content/uploads/2022/04/tandoori-skewers.png",
        "resturant": "Sagar Resturant",
        "Dietary_Restrictions": "halal",
        "mood": "Comforting"
    },
    {
        "name": "Shredded Pork and Preseerved Vegetable Noodle Soup",
        "culture": "Chinese",
        "main_ingredient": "Shredded Pork, Preserved Vegetable, Noodle",
        "average_price": 13.50,
        "image": "https://images.squarespace-cdn.com/content/v1/56801b350e4c11744888ec37/843fc327-312c-4ae1-8216-cf1bc6daa1f4/Pickled+Mustard+and+Pork+Noodle+Soup.jpg",
        "resturant": "Shanghai You Garden",
        "Dietary_Restrictions": "Not Gluten-free",
        "mood": "Healthy"
    },
        {
        "name": "Suateed Crystal Shrimp",
        "culture": "Chinese",
        "main_ingredient": "Fresh Shrimp, minimal seasoning",
        "average_price": 16.50,
        "image": "https://data.chinatravel.com/images/china-guide/shanghai/shrimps.webp",
        "resturant": "Shanghai You Garden",
        "Dietary_Restrictions": "Not Gluten-free",
        "mood": "Healthy"
    },
        {
        "name": "Garlic Cucumber Cold Dish",
        "culture": "Chinese",
        "main_ingredient": "Cucumber Slices, garlic, light vinegar dressing",
        "average_price": 8.50,
        "image": "https://redcook.net/wp-content/uploads/2008/08/cucumbersalad2-440x270.jpg",
        "resturant": "Shanghai You Garden",
        "Dietary_Restrictions": "Vegeterian",
        "mood": "Healthy"
    }
]

restaurants=[
{
    "name": "Nuan Xin Rice Roll",
    "cuisine": "Chinese",
    "price": "$",
    "address": "136 - 55 Roosevelt Ave Flushing, NY 11354 Downtown Flushing, Flushing",
    "photo": "https://storage.fantuan.ca/fantuan/us/default/blob/ada129ca80d94e03a7f0cc60015b477d/1603438633099014144.",
    "rating": "4.9",
    "lat": 40.760311,
    "long": -73.828156
  },
  {
    "name": "Pop Rice",
    "cuisine": "Chinese",
    "price": "$$",
    "address": "162-16 Union Tpke Unit 103, Flushing, NY 11367",
    "photo": "https://img.cdn4dd.com/p/fit=cover,width=1200,height=1200,format=auto,quality=90/media/photosV2/3bb7366e-dd29-4ab3-9d3e-b14883ea88f1-retina-large.jpg",
    "rating": "3.7",
    "lat":40.719356,
    "long": -73.811286
  },
  {
    "name": "Shanghai You Garden",
    "cuisine": "Chinese",
    "price": "$$",
    "address": "135-33 40th Rd, Flushing, NY 11354",
    "photo": "https://res.cloudinary.com/the-infatuation/image/upload/q_auto,f_auto/cms/KatePrevite_NYC_ShanghaiYou_PekingDuck_18",
    "rating": "3.9",
    "lat": 40.758972,
    "long": -73.830528
  },
  {
    "name": "Nan Xiang Xiao Long Bao",
    "cuisine": "Chinese",
    "price": "$$$",
    "address": "39-16 Prince St #104, Flushing, NY 11354",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/lmcpkjW6fo_uJqBnxxqk4w/348s.jpg",
    "rating": "4.5",
    "lat": 40.759313,
    "long": -73.832556
  },
  {
    "name": "Joe's Steam Rice  Roll",
    "cuisine": "Chinese",
    "price": "$",
    "address": "136-21 Roosevelt Ave # A1, Flushing, NY 11354",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/6HK_YSUR3BW0siX8YDcKuQ/348s.jpg",
    "rating": "4.4",
    "lat": 40.760105,
    "long": -73.829414
  },
  {
    "name": "Niuddo",
    "cuisine": "Chinese",
    "price": "$",
    "address": "41-42 Main St, Flushing, NY 11355",
    "photo": "https://apis3.fantuan.ca/image/object_image_1630569147.7468157_cover.jpg",
    "rating": "4.4",
    "lat": 40.756992,
    "long": -73.829269
  },
  {
    "name": "Yunan Rice Noodles House",
    "cuisine": "Chinese",
    "price": "$$",
    "address": "53 Bayard St, New York, NY 10013",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/WvGN3CshoNGIiFgSfwo0pA/348s.jpg",
    "rating": "4.0",
    "lat": 40.715215,
    "long": -73.997676
  },
  {
    "name": "Shoo Looong Kan HotPot",
    "cuisine": "Chinese",
    "price": "$$$$",
    "address": "133-36 37th Ave, Flushing, NY 11354",
    "photo": "https://rockfork.it/wp-content/uploads/2024/09/lHotpot-i-brodi-di-Shoo-Loong-Kan-Milano.jpeg",
    "rating": "4.7",
    "lat": 40.760054,
    "long": -73.833996
  },
  {
    "name": "Nonna Delia's",
    "cuisine": "Italian",
    "price": "$$",
    "address": "18-32 College Point Blvd, Flushing, NY 11356",
    "photo": "https://slicelife.imgix.net/21223/photos/original/nonnaDelia's_bbqChicken.jpg?auto=compress&auto=format",
    "rating": "4.3",
    "lat": 40.782253,
    "long": -73.846214
  },
  {
    "name": "Royal Pizza",
    "cuisine": "Italian",
    "price": "$",
    "address": "55-06 Myrtle Ave, Ridgewood, NY 11385",
    "photo": "https://img.cdn4dd.com/cdn-cgi/image/fit=cover,width=600,height=400,format=auto,quality=80/https://doordash-static.s3.amazonaws.com/media/store/header/97cefae7-4560-4967-9d7b-1130c8355f98.jpg",
    "rating": "4.1",
    "lat": 40.699734,
    "long": -73.908211
  },
  {
    "name": "La Bottega Glen Cove",
    "cuisine": "Italian",
    "price": "$$",
    "address": "190 Glen St, Glen Cove, NY 11542",
    "photo": "https://img.cdn4dd.com/p/fit=cover,width=1200,height=1200,format=auto,quality=90/media/photosV2/141043e5-afe3-444b-a3ae-e1c83aabcbb7-retina-large.jpg",
    "rating": "4.3",
    "lat": 40.863721,
    "long": -73.628292
  },
  {
    "name": "NYC TIKKA MASALA",
    "cuisine": "Indian",
    "price": "$$",
    "address": "44-27 Kissena Blvd, Queens, NY 11355",
    "photo": "https://img.cdn4dd.com/p/fit=cover,width=1200,height=1200,format=auto,quality=90/media/photosV2/fc13486a-ec3f-4b70-b1e0-1d5e17686d9c-retina-large.jpeg",
    "rating": "4.4",
    "lat": 40.753430,
    "long": -73.821964
  },
  {
    "name": "Sagar Restaurant",
    "cuisine": "Bangladeshi",
    "price": "$$",
    "address": "168-25B Hillside Ave., Jamaica, NY 11432",
    "photo": "https://sagarchinese.com/sagarfood/wp-content/uploads/2020/02/Desi-Combo-1.jpg",
    "rating": "3.6",
    "lat": 40.714524,
    "long": -73.776220
  },
  {
    "name": "Dhaka Garden",
    "cuisine": "Banglasdeshi",
    "price": "$$",
    "address": "72-23 37th Ave, Jackson Heights, NY 11372",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/OiuULB_BcrHMvLNxrY2-rA/348s.jpg",
    "rating": "3.4",
    "lat": 40.749096,
    "long": -73.892960
  },
  {
    "name": "Shahi Catering",
    "cuisine": "Indian",
    "price": "$$",
    "address": "236-03 Braddock Ave, Queens, NY 11426",
    "photo": "https://www.skipthedishes.com/_next/image?url=https%3A%2F%2Fstatic.skipthedishes.com%2Fshahi-catering-menu-image-large-1536877533975.jpg&w=3840&q=75",
    "rating": "4.4",
    "lat": 40.727646,
    "long": -73.731171
  },
  {
    "name": "Varli Indian Street Kitchen",
    "cuisine": "Indian",
    "price": "$$$",
    "address": "78 Hillside Ave., Williston Park, NY 11596",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/XlcN6ocMY39IluIy-7AKTw/348s.jpg",
    "rating": "4.6",
    "lat": 40.757371,
    "long": -73.642635
  },
  {
    "name": "Kabab King",
    "cuisine": "Halal",
    "price": "$$",
    "address": "7301 37th Rd, Jackson Heights, NY 11372",
    "photo": "https://s3-media0.fl.yelpcdn.com/bphoto/-bPPldzQS-HJvcFdEK4wCA/348s.jpg",
    "rating": "3.6",
    "lat": 40.747281,
    "long": -73.892271
  },
  {
    "name": "Bhatura King",
    "cuisine": "Indian",
    "price": "$$",
    "address": "241-23 Braddock Ave, Jamaica, NY 11426",
    "photo": "https://img.cdn4dd.com/p/fit=cover,width=1200,height=1200,format=auto,quality=90/media/photosV2/ba40ada3-6932-409d-937b-668d682dd640-retina-large.jpg",
    "rating": "4.7",
    "lat": 40.726480,
    "long": -73.726502
  },
  {
    "name": "Lucky Dhaba",
    "cuisine": "Indian",
    "price": "$$",
    "address": "114-06 Jamaica Ave, Jamaica, NY 11418",
    "photo": "https://static.spotapps.co/spots/76/b94bd3da9e442897eeb89fdd1d828d/full",
    "rating": "4.0",
    "lat": 40.698174,
    "long": -73.834503
  },
  {
    "name": "Pho Hoang",
    "cuisine": "Vietnamese",
    "price": "$$",
    "address": "41-01 Kissena Blvd, Flushing, NY 11355",
    "photo": "https://burgersbarbecueandeverythingelse.com/wp-content/uploads/2017/07/img_6380-1.jpg",
    "rating": "4.4",
    "lat": 40.758329,
    "long": -73.828950
  },
  {
    "name": "Joju",
    "cuisine": "Vietnamese",
    "price": "$$",
    "address": "37-12 Prince St, Flushing, NY 11354",
    "photo": "https://d1w7312wesee68.cloudfront.net/s4MRrDbpXIeSo0NFKpo2tjxrO0nmIFKT4ic6qB8qxTw/resize:fit:720:720/plain/s3://toasttab/restaurants/restaurant-112675000000000000/menu/items/5/item-500000017473327225_1683142655.jpg",
    "rating": "3.8",
    "lat": 40.760410,
    "long": -73.833150
  }
]
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
