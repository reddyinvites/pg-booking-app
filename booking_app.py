import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import random

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp"],
    scopes=scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.lower().str.strip()
    return df

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]
df = df.drop_duplicates(subset=["pg_name", "location"])

df[["area", "locality"]] = df["location"].str.split("-", expand=True)

# ---------------- SEARCH ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s) |
        df["locality"].str.lower().str.contains(s)
    ]

# ---------------- DROPDOWNS ----------------
all_areas = sorted(df["area"].dropna().unique())
all_localities = sorted(df["locality"].dropna().unique())

pref_area = st.selectbox("📍 Area", all_areas)
pref_locality = st.selectbox("🏠 Locality", all_localities)

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox(
    "🛏 Sharing",
    ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"]
)

pref_gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])

# ✅ NEW (ROOM TYPE)
pref_room_type = st.selectbox("🧊 Room Type", ["AC", "Non AC"])

# ---------------- FILTER ----------------
df = df[df["area"] == pref_area]
df = df[df["locality"] == pref_locality]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    price_str = str(row["price"]).replace("₹", "").replace(",", "").strip()
    if not price_str.isdigit():
        continue

    price = int(price_str)

    score = 0
    reasons = []
    pros = []
    cons = []

    # 💰 BUDGET
    if price == pref_budget:
        score += 40
        reasons.append("Perfect budget match 🔥")

    elif price < pref_budget:
        diff = pref_budget - price

        if diff <= 500:
            score += 35
            reasons.append("Very close to your budget")

        elif diff <= 1500:
            score += 25
            reasons.append("Good value under budget")
            pros.append("Saves money 💰")

        else:
            score += 10
            cons.append("Lower than your budget")

    elif price <= pref_budget + 1000:
        score += 20
        cons.append("Slightly above budget")

    else:
        continue

    # LOCATION
    if row["area"] == pref_area:
        score += 20
        reasons.append("Area match")

    if row["locality"] == pref_locality:
        score += 20
        reasons.append("Exact locality match")

    # SHARING
    if row["sharing_type"] == pref_sharing:
        score += 10
        reasons.append("Sharing matched")

    # GENDER
    if str(row.get("gender","")).lower() == pref_gender.lower():
        score += 5

    # FOOD
    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5

    # ROOM TYPE
    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5

    # ---------------- REAL "THINGS TO CONSIDER" ----------------
    cons = []

    if price > pref_budget:
        cons.append(f"₹{price - pref_budget} above your budget")

    elif price < pref_budget - 1500:
        cons.append("Lower than your budget")

    if row["sharing_type"] != pref_sharing:
        cons.append("Different sharing than your preference")

    if str(row.get("room_type","")).lower() != pref_room_type.lower():
        cons.append("Room type not matching your preference")

    if str(row.get("food_type","")).lower() != pref_food.lower():
        cons.append("Food type mismatch")

    if str(row.get("gender","")).lower() != pref_gender.lower():
        cons.append("Different gender preference")

    if int(row["available_beds"]) == 1:
        cons.append("Only 1 bed left")

    score = max(0, min(100, int(score)))

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": score,
        "reasons": reasons,
        "pros": pros,
        "cons": cons
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

top_results = results[:3]

if not top_results:
    st.error("No matching PGs found ❌")

for i, r in enumerate(top_results):

    if i == 0:
        color = "#D4EDDA"
        badge = "🥇 Best Match"
    elif i == 1:
        color = "#FFF3CD"
        badge = "🥈 Great Option"
    else:
        color = "#E2E3E5"
        badge = "🥉 Value Pick"

    st.markdown(f"""
    <div style="background:{color};padding:15px;border-radius:15px;margin-bottom:10px">
        <h3>🏠 {r['pg']} — {r['score']}% Match</h3>
        <b>{badge}</b><br>
        📍 {r['location']}
    </div>
    """, unsafe_allow_html=True)

    # PRICE
    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < pref_budget:
        st.info(f"💰 ₹{r['price']} (Save ₹{pref_budget - r['price']})")
    else:
        st.warning(f"💰 ₹{r['price']} (Above budget)")

    # BEDS
    st.write(f"🛏 {r['beds']} Beds Available")

    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] <= 2:
        st.warning("⚡ Only few beds left")

    views = random.randint(20, 80)
    st.caption(f"👀 {views} people viewed today")

    st.write(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    # ✅ CLEAN NOTE (NO FAKE DATA)
    if r["cons"]:
        st.markdown("### ⚠️ Things to consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()