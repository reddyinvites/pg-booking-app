import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (AI Powered)")

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
st.subheader("👤 Your Details")
name = st.text_input("Name")
phone = st.text_input("Phone")

st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", min_value=1000, value=6000)

location_list = df["location"].dropna().unique()
location = st.selectbox("Location", location_list)

gender = st.selectbox("Gender", ["Male", "Female"])
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

        # -------- HARD FILTER --------
        if "gender" in df.columns:
            if str(row.get("gender", "")).lower() != gender.lower():
                continue

        # -------- BUDGET --------
        price = row["price"]

        if price <= budget:
            score += 30
            reasons.append(f"Perfect budget match (₹{price})")
        elif price <= budget + 1000:
            score += 20
            reasons.append(f"Slightly above budget (₹{price})")
            cons.append("Slightly expensive")
        else:
            continue

        # -------- LOCATION --------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append(f"Exact location match ({location})")
        else:
            score += 10
            cons.append("Different location")

        # -------- FOOD --------
        pg_food = str(row.get("food_type", "")).lower()

        if food.lower() == pg_food:
            score += 10
            reasons.append("Food matches your preference")
        elif pg_food == "mixed":
            score += 5
        else:
            cons.append("Food mismatch")

        # -------- CROWD --------
        pg_crowd = str(row.get("crowd", "")).lower()

        if crowd.lower() == pg_crowd:
            score += 10
            reasons.append("Preferred crowd matches")
        elif pg_crowd == "mixed":
            score += 5
        else:
            cons.append("Crowd mismatch")

        # -------- CLEANLINESS --------
        pg_clean = int(row.get("cleanliness", 5))
        diff = abs(cleanliness_user - pg_clean)
        clean_score = max(0, 15 - diff * 2)
        score += clean_score

        if diff <= 2:
            reasons.append("Cleanliness is good")
            pros.append("High cleanliness standards")
        else:
            cons.append("Cleanliness lower than expectation")

        # -------- ROOM TYPE --------
        pg_room = str(row.get("room_type", "")).lower()

        if room_type.lower() == pg_room:
            score += 5
        else:
            cons.append("Room type mismatch")

        # ==================================================
        # 📍 DISTANCE SCORING (NEW 🔥)
        # ==================================================
        metro = int(row.get("metro_dist", 1000))
        bus = int(row.get("bus_dist", 1000))
        rail = int(row.get("rail_dist", 1000))

        avg_dist = (metro + bus + rail) / 3

        if avg_dist <= 200:
            score += 10
            pros.append("Very well connected (transport nearby)")
        elif avg_dist <= 500:
            score += 5
        else:
            cons.append("Far from transport")

        # ==================================================
        # 🧠 NOTES AI ANALYSIS (NEW 🔥)
        # ==================================================
        notes = str(row.get("notes", "")).lower()

        if "peaceful" in notes and crowd == "Employees":
            score += 5
            reasons.append("Peaceful environment suits employees")

        if "noisy" in notes:
            cons.append("Noisy surroundings")

        if "family" in notes:
            pros.append("Safe & family environment")

        if "party" in notes:
            cons.append("Party environment")

        # ==================================================
        # ⭐ SMART AI TEXT (NEW 🔥)
        # ==================================================
        highlight = ""

        if score >= 80:
            highlight = "🔥 Highly recommended"
        elif score >= 60:
            highlight = "👍 Good choice"
        else:
            highlight = "⚖️ Consider carefully"

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "highlight": highlight
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- OUTPUT ----------------
    st.subheader("🏆 Top Matches For You")

    if not results:
        st.error("No PGs found ❌")

    for r in results:

        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
        st.success(r["highlight"])

        st.markdown("### 💡 Why this match?")
        for i in r["reasons"]:
            st.write("•", i)

        st.markdown("### 👍 Why choose this PG?")
        for i in r["pros"]:
            st.write("✓", i)

        st.markdown("### ⚠️ Things to consider")
        for i in r["cons"]:
            st.write("•", i)

        st.divider()