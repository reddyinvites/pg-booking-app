import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine + Pain Score")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
sheet = client.open_by_key(SHEET_ID)
room_sheet = sheet.worksheet("Sheet1")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    return pd.DataFrame(room_sheet.get_all_records())

df = load_data()

# ---------------- PARSE JSON ----------------
def parse_json(val):
    try:
        return json.loads(val)[0]
    except:
        return {}

df["parsed"] = df["sharing_json"].apply(parse_json)

df["price"] = df["parsed"].apply(lambda x: x.get("price", 0))
df["available_beds"] = df["parsed"].apply(lambda x: x.get("available_beds", 0))
df["sharing"] = df["parsed"].apply(lambda x: int(x.get("type","0").split()[0]) if x else 0)

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", min_value=1000, value=6000)
location = st.selectbox("Location", df["location"].dropna().unique())
food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])
crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])
room_type = st.selectbox("Room Type", ["AC", "Non-AC"])
cleanliness_user = st.slider("Cleanliness Expectation", 1, 10, 5)

# ---------------- FIND BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    results = []

    for _, row in df.iterrows():

        score = 0
        reasons = []
        pros = []
        cons = []

        # -------- BUDGET --------
        price = row["price"]

        if price <= budget:
            score += 30
            reasons.append(f"Perfect budget match (₹{price})")
        elif price <= budget + 1000:
            score += 20
            cons.append("Slightly expensive")
        else:
            continue

        # -------- LOCATION --------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append("Exact location match")

        # -------- CLEANLINESS --------
        pg_clean = int(row.get("cleanliness", 5))
        diff = abs(cleanliness_user - pg_clean)
        score += max(0, 15 - diff * 2)

        # ==================================================
        # ⭐ PAIN SCORE SYSTEM (NEW 🔥)
        # ==================================================

        food_rating = float(row.get("food_rating", 3))
        clean_rating = float(row.get("cleanliness", 5)) / 2   # convert to /5
        noise_rating = float(row.get("noise_rating", 3))
        safety_rating = float(row.get("safety_rating", 3))
        crowd_rating = float(row.get("crowd_rating", 3))

        pain_avg = round((food_rating + clean_rating + noise_rating + safety_rating + crowd_rating) / 5, 1)

        # -------- BIGGEST PAIN --------
        pain_dict = {
            "Food": food_rating,
            "Cleanliness": clean_rating,
            "Noise": noise_rating,
            "Safety": safety_rating,
            "Crowd": crowd_rating
        }

        worst = min(pain_dict, key=pain_dict.get)

        pain_message = ""

        if pain_dict[worst] <= 2:
            if worst == "Food":
                pain_message = "⚠️ Food not good"
            elif worst == "Cleanliness":
                pain_message = "⚠️ Bathrooms not clean"
            elif worst == "Noise":
                pain_message = "⚠️ Too noisy"
            elif worst == "Safety":
                pain_message = "⚠️ Unsafe area"
            elif worst == "Crowd":
                pain_message = "⚠️ Bad crowd"
        else:
            pain_message = "✅ Very clean & peaceful"

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "pain": pain_avg,
            "food": food_rating,
            "clean": clean_rating,
            "noise": noise_rating,
            "safety": safety_rating,
            "crowd": crowd_rating,
            "pain_msg": pain_message
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- OUTPUT ----------------
    st.subheader("🏆 Top Matches")

    for r in results:

        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        # ⭐ PAIN SCORE DISPLAY
        st.markdown(f"### ⭐ Pain Score: {r['pain']} / 5")

        st.write(f"🍛 Food → {r['food']} ⭐")
        st.write(f"🧼 Cleanliness → {r['clean']} ⭐")
        st.write(f"🔇 Noise → {r['noise']} ⭐")
        st.write(f"🔐 Safety → {r['safety']} ⭐")
        st.write(f"👥 Crowd → {r['crowd']} ⭐")

        st.warning(f"Biggest Pain: {r['pain_msg']}")

        st.divider()