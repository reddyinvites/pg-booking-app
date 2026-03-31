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

# ⚠️ MAKE SURE NAME IS EXACT
room_sheet = sheet.worksheet("Sheet1")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    df = pd.DataFrame(room_sheet.get_all_records())
    return df

room_df = load_data()

# ---------------- SAFE JSON PARSE ----------------
def parse_json_safe(x):
    try:
        data = json.loads(x)[0]
        return data
    except:
        return {}

room_df["parsed"] = room_df["sharing_json"].apply(parse_json_safe)

room_df["price"] = room_df["parsed"].apply(lambda x: int(x.get("price", 0)))
room_df["available_beds"] = room_df["parsed"].apply(lambda x: int(x.get("available_beds", 0)))
room_df["total_beds"] = room_df["parsed"].apply(lambda x: int(x.get("total_beds", 0)))

# FIX SHARING
def get_sharing(x):
    try:
        return int(x.get("type", "1").split()[0])
    except:
        return 1

room_df["sharing"] = room_df["parsed"].apply(get_sharing)

# ---------------- USER DETAILS ----------------
st.subheader("👤 Your Details")

name = st.text_input("Name")
phone = st.text_input("Phone")

# ---------------- PREFERENCES ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", value=6000)

location = st.selectbox(
    "Location",
    sorted(room_df["location"].dropna().unique())
)

# If column not exists → fallback
if "gender" in room_df.columns:
    gender = st.selectbox("Gender", sorted(room_df["gender"].dropna().unique()))
else:
    gender = st.selectbox("Gender", ["Male", "Female"])

food_type = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])

crowd = st.selectbox("Preferred Crowd", ["Employees", "Students", "Mixed"])

if "room_type" in room_df.columns:
    room_type = st.selectbox("Room Type", sorted(room_df["room_type"].dropna().unique()))
else:
    room_type = st.selectbox("Room Type", ["Non-AC", "AC"])

cleanliness_pref = st.slider("Cleanliness Expectation", 1, 10, 7)

# ---------------- MATCH BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    df = room_df.copy()

    # ---------------- HARD FILTER ----------------
    if "gender" in df.columns:
        df = df[df["gender"] == gender]

    # ---------------- SCORING ----------------
    def calculate_score(row):

        score = 0

        # Budget (30)
        if row["price"] <= budget:
            score += 30
        else:
            score += 10

        # Location (25)
        if location.lower() in str(row["location"]).lower():
            score += 25
        else:
            score += 10

        # Cleanliness (15)
        try:
            clean = int(row.get("cleanliness", 5))
            diff = abs(clean - cleanliness_pref)
            score += max(0, 15 - diff*2)
        except:
            pass

        # Food (10)
        if str(row.get("food_type","")).lower() == food_type.lower():
            score += 10

        # Crowd (10)
        if str(row.get("crowd","")).lower() == crowd.lower():
            score += 10

        # Room Type (10)
        if str(row.get("room_type","")).lower() == room_type.lower():
            score += 10

        return score

    df["score"] = df.apply(calculate_score, axis=1)

    df = df.sort_values(by="score", ascending=False).head(3)

    # ---------------- NO RESULT ----------------
    if df.empty:
        st.error("No PGs found ❌")
        st.stop()

    st.subheader("🏆 Top Matches For You")

    # ---------------- AI EXPLANATION ----------------
    def explain(row):

        text = ""

        if row["price"] <= budget:
            text += "✅ Perfect budget match. "
        else:
            text += "⚠️ Slightly above your budget. "

        if location.lower() in str(row["location"]).lower():
            text += "📍 Exact location match. "
        else:
            text += "📍 Nearby location. "

        if str(row.get("food_type","")).lower() == food_type.lower():
            text += "🍽 Food matches your preference. "

        if str(row.get("crowd","")).lower() == crowd.lower():
            text += "👥 Crowd suits your lifestyle. "

        try:
            clean = int(row.get("cleanliness",5))
            if clean >= cleanliness_pref:
                text += "🧼 Cleanliness is good. "
            else:
                text += "🧼 Cleanliness slightly lower. "
        except:
            pass

        return text

    # ---------------- DISPLAY ----------------
    for _, row in df.iterrows():

        match_percent = int((row["score"] / 100) * 100)

        st.markdown(f"## 🏠 {row['pg_name']} — {match_percent}% Match")

        st.success("Why this match?")
        st.write(explain(row))

        st.info("Why choose this PG?")
        st.write("✔ Good balance of price & features")
        st.write("✔ Matches most of your preferences")

        st.warning("Things to consider:")
        if row["price"] > budget:
            st.write("• Slightly above budget")
        if location.lower() not in str(row["location"]).lower():
            st.write("• Location not exact match")

        st.divider()