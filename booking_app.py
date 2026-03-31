import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine")

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

# ---------------- USER DETAILS ----------------
st.subheader("👤 Your Details")
name = st.text_input("Name")
phone = st.text_input("Phone")

# ---------------- PREFERENCES ----------------
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

        # -------- AVAILABILITY --------
        if row["available_beds"] > 0:
            pros.append("Beds available immediately")
        else:
            cons.append("Currently full")

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "reasons": reasons,
            "pros": pros,
            "cons": cons
        })

    # ---------------- SORT ----------------
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- OUTPUT ----------------
    st.subheader("🏆 Top Matches For You")

    if not results:
        st.error("No PGs found ❌")

    for r in results:

        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        st.success("Why this match?")
        for i in r["reasons"]:
            st.write("•", i)

        st.info("Why choose this PG?")
        for i in r["pros"]:
            st.write("✓", i)

        st.warning("Things to consider:")
        for i in r["cons"]:
            st.write("•", i)

        st.divider()