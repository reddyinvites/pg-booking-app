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

    # ---------------- PAIN SCORE ----------------
    def norm(x):
        try:
            return round(float(x) / 2, 1)
        except:
            return 3

    food_s = norm(row.get("food_rating", 6))
    clean_s = norm(row.get("cleanliness_score", 6))
    safety_s = norm(row.get("safety", 6))

    noise_map = {"low":5, "medium":3, "high":1}
    noise_s = noise_map.get(str(row.get("noise_level","medium")).lower(), 3)

    pain_score = round((food_s + clean_s + safety_s + noise_s) / 4, 1)

    pain_dict = {
        "Food": food_s,
        "Cleanliness": clean_s,
        "Noise": noise_s,
        "Safety": safety_s
    }

    worst = min(pain_dict, key=pain_dict.get)

    pain_msg = {
        "Food": "⚠️ Food quality is low",
        "Cleanliness": "⚠️ Not very clean",
        "Noise": "⚠️ Too noisy",
        "Safety": "⚠️ Safety concerns"
    }

    biggest_pain = pain_msg.get(worst, "")
    if pain_score >= 4:
        biggest_pain = "✅ Clean & peaceful stay"

    # ---------------- WHY THIS PG ----------------
    if price == pref_budget:
        score += 40
        reasons.append("Perfect budget match 🔥")
    elif price < pref_budget:
        score += 30
        reasons.append("Fits within your budget")
    elif price <= pref_budget + 1000:
        score += 20
        reasons.append("Slightly above your budget")
    else:
        continue

    if row["area"] == pref_area:
        score += 20
        reasons.append("Located in your preferred area")

    if row["locality"] == pref_locality:
        score += 20
        reasons.append("Exact locality match")

    if row["sharing_type"] == pref_sharing:
        score += 10
        reasons.append("Sharing preference matched")

    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5
        reasons.append("Food preference matched")

    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5
        reasons.append("Room type matched")

    # ---------------- WHY CHOOSE THIS PG (SMART) ----------------
    if price < pref_budget:
        pros.append("Budget friendly 💰")

    if food_s >= 4:
        pros.append("Good food quality 🍛")

    if clean_s >= 4:
        pros.append("Very clean & hygienic 🧼")

    if safety_s >= 4:
        pros.append("Safe environment 🔐")

    if noise_s >= 4:
        pros.append("Peaceful stay 🔇")

    if int(row["available_beds"]) > 2:
        pros.append("Good availability")

    # ---------------- THINGS TO CONSIDER ----------------
    if price > pref_budget:
        cons.append(f"₹{price - pref_budget} above your budget")

    elif price < pref_budget - 1500:
        cons.append("Lower than your budget")

    if row["sharing_type"] != pref_sharing:
        cons.append("Different sharing than your preference")

    if str(row.get("room_type","")).lower() != pref_room_type.lower():
        cons.append("Room type not matching")

    if str(row.get("food_type","")).lower() != pref_food.lower():
        cons.append("Food type mismatch")

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
        "cons": cons,
        "pain_score": pain_score,
        "food_s": food_s,
        "clean_s": clean_s,
        "safety_s": safety_s,
        "noise_s": noise_s,
        "biggest_pain": biggest_pain
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

    # PAIN SCORE UI
    st.markdown("### 😣 PG Condition Score")
    st.write(f"⭐ {r['pain_score']} / 5")
    st.write(f"🍛 Food → {r['food_s']}")
    st.write(f"🧼 Cleanliness → {r['clean_s']}")
    st.write(f"🔐 Safety → {r['safety_s']}")
    st.write(f"🔇 Noise → {r['noise_s']}")

    st.markdown("### 🚨 Biggest Issue")
    st.write(r["biggest_pain"])

    # WHY THIS PG
    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    # WHY CHOOSE
    if r["pros"]:
        st.markdown("### ✅ Why choose this PG?")
        for p in r["pros"]:
            st.write("✔", p)

    # CONSIDER
    if r["cons"]:
        st.markdown("### ⚠️ Things to consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()