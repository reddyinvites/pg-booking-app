import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Full AI + Pain System)")

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

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", min_value=1000, value=6000)
location = st.selectbox("Location", df["location"].dropna().unique())
food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])
crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])
room_type = st.selectbox("Room Type", ["AC", "Non-AC"])
cleanliness_user = st.slider("Cleanliness Expectation", 1, 10, 5)

# ---------------- BUTTON ----------------
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
            reasons.append(f"Slightly above budget (₹{price})")
            cons.append("Slightly expensive")
        else:
            continue

        # -------- LOCATION --------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append("Exact location match")
        else:
            score += 10
            cons.append("Different location")

        # -------- FOOD --------
        pg_food = str(row.get("food_type", "")).lower()
        if food.lower() == pg_food:
            score += 10
            reasons.append("Food matches preference")
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
            cons.append("Cleanliness below expectation")

        # -------- ROOM TYPE --------
        pg_room = str(row.get("room_type", "")).lower()
        if room_type.lower() == pg_room:
            score += 5
        else:
            cons.append("Room type mismatch")

        # -------- DISTANCE --------
        metro = int(row.get("metro_dist", 1000))
        bus = int(row.get("bus_dist", 1000))
        rail = int(row.get("rail_dist", 1000))

        avg_dist = (metro + bus + rail) / 3

        if avg_dist <= 200:
            score += 10
            pros.append("Excellent transport connectivity")
        elif avg_dist <= 500:
            score += 5
        else:
            cons.append("Far from transport")

        # -------- NOTES AI --------
        notes = str(row.get("notes", "")).lower()

        if "peaceful" in notes:
            pros.append("Peaceful environment")
        if "noisy" in notes:
            cons.append("Noisy surroundings")
        if "family" in notes:
            pros.append("Safe & family-friendly")
        if "party" in notes:
            cons.append("Party environment")

        # ==================================================
        # ⭐ PAIN SCORE SYSTEM
        # ==================================================
        food_rating = float(row.get("food_rating", 3))
        clean_rating = float(row.get("cleanliness", 5)) / 2
        noise_rating = float(row.get("noise_rating", 3))
        safety_rating = float(row.get("safety_rating", 3))
        crowd_rating = float(row.get("crowd_rating", 3))

        pain_avg = round((food_rating + clean_rating + noise_rating + safety_rating + crowd_rating) / 5, 1)

        pain_dict = {
            "Food": food_rating,
            "Cleanliness": clean_rating,
            "Noise": noise_rating,
            "Safety": safety_rating,
            "Crowd": crowd_rating
        }

        worst = min(pain_dict, key=pain_dict.get)

        if pain_dict[worst] <= 2:
            pain_msg = f"⚠️ {worst} is poor"
        else:
            pain_msg = "✅ Overall good living conditions"

        # -------- SMART TAG --------
        if score >= 80:
            highlight = "🔥 Highly Recommended"
        elif score >= 60:
            highlight = "👍 Good Choice"
        else:
            highlight = "⚖️ Consider Carefully"

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "pain": pain_avg,
            "pain_msg": pain_msg,
            "food": food_rating,
            "clean": clean_rating,
            "noise": noise_rating,
            "safety": safety_rating,
            "crowd": crowd_rating,
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

        # WHY MATCH
        st.markdown("### 💡 Why this PG?")
        for i in r["reasons"]:
            st.write("•", i)

        # WHY CHOOSE
        st.markdown("### 👍 Why choose this PG?")
        for i in r["pros"]:
            st.write("✓", i)

        # CONS
        st.markdown("### ⚠️ Things to consider")
        for i in r["cons"]:
            st.write("•", i)

        # PAIN SCORE
        st.markdown(f"### ⭐ Pain Score: {r['pain']} / 5")
        st.write(f"🍛 Food → {r['food']}")
        st.write(f"🧼 Cleanliness → {r['clean']}")
        st.write(f"🔇 Noise → {r['noise']}")
        st.write(f"🔐 Safety → {r['safety']}")
        st.write(f"👥 Crowd → {r['crowd']}")

        st.warning(f"Biggest Pain: {r['pain_msg']}")

        st.divider()