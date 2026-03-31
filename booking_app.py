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
@st.cache_data(ttl=10)
def load_data():
    return pd.DataFrame(room_sheet.get_all_records())

room_df = load_data()

# ---------------- SAFE JSON PARSE ----------------
def parse_json_safe(x):
    try:
        return json.loads(x)[0]
    except:
        return {}

room_df["parsed"] = room_df["sharing_json"].apply(parse_json_safe)

room_df["price"] = room_df["parsed"].apply(lambda x: int(x.get("price", 0)))
room_df["available_beds"] = room_df["parsed"].apply(lambda x: int(x.get("available_beds", 0)))

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

# ---------------- FILTERS ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", value=6000)

location = st.selectbox(
    "Location",
    sorted(room_df["location"].dropna().unique())
)

gender = st.selectbox(
    "Gender",
    sorted(room_df["gender"].dropna().unique()) if "gender" in room_df.columns else ["Male", "Female"]
)

food_type = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])
crowd = st.selectbox("Preferred Crowd", ["Employees", "Students", "Mixed"])

room_type = st.selectbox(
    "Room Type",
    sorted(room_df["room_type"].dropna().unique()) if "room_type" in room_df.columns else ["Non-AC", "AC"]
)

cleanliness_pref = st.slider("Cleanliness Expectation", 1, 10, 7)

# ---------------- FIND BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    df = room_df.copy()

    # FIX PRICE TYPE
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

    # HARD FILTER
    if "gender" in df.columns:
        df = df[df["gender"] == gender]

    # ---------------- SCORING ----------------
    def calculate_score(row):

        score = 0
        price = row["price"]

        # 💰 Budget Logic (SMART)
        if price <= budget:
            score += 30
        else:
            diff = price - budget
            if diff <= 1000:
                score += 20
            elif diff <= 2000:
                score += 10
            else:
                score += 5

        # 📍 Location
        if location.lower() in str(row["location"]).lower():
            score += 25
        else:
            score += 10

        # 🧼 Cleanliness
        try:
            clean = int(row.get("cleanliness", 5))
            diff = abs(clean - cleanliness_pref)
            score += max(0, 15 - diff*2)
        except:
            score += 5

        # 🍽 Food
        if str(row.get("food_type","")).lower() == food_type.lower():
            score += 10

        # 👥 Crowd
        if str(row.get("crowd","")).lower() == crowd.lower():
            score += 10

        # 🛏 Room Type
        if str(row.get("room_type","")).lower() == room_type.lower():
            score += 10

        return score

    df["score"] = df.apply(calculate_score, axis=1)

    # SORT TOP 3
    df = df.sort_values(by="score", ascending=False).head(3)

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches For You")

    if df.empty:
        st.error("No PGs found ❌")

    else:

        def explain(row):

            text = ""

            if row["price"] <= budget:
                text += "✅ Perfect budget match. "
            else:
                text += f"⚠️ ₹{int(row['price'] - budget)} above budget. "

            if location.lower() in str(row["location"]).lower():
                text += "📍 Exact location match. "

            if str(row.get("food_type","")).lower() == food_type.lower():
                text += "🍽 Food matches. "

            if str(row.get("crowd","")).lower() == crowd.lower():
                text += "👥 Good crowd match. "

            try:
                clean = int(row.get("cleanliness",5))
                if clean >= cleanliness_pref:
                    text += "🧼 Clean. "
                else:
                    text += "🧼 Average cleanliness. "
            except:
                pass

            return text

        for _, row in df.iterrows():

            match_percent = int(row["score"])

            st.markdown(f"## 🏠 {row['pg_name']} — {match_percent}% Match")

            st.success("Why this match?")
            st.write(explain(row))

            st.info("Why choose this PG?")
            st.write("✔ Good balance of price & features")
            st.write("✔ Matches most of your needs")

            st.warning("Things to consider:")

            if row["price"] > budget:
                st.write("• Slightly expensive")

            if location.lower() not in str(row["location"]).lower():
                st.write("• Different location")

            st.divider()