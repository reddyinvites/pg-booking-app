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

    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

    # FILTER
    if "gender" in df.columns:
        df = df[df["gender"] == gender]

    # ---------------- SCORING ----------------
    def calculate_score(row):

        score = 0
        price = row["price"]

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

        if location.lower() in str(row["location"]).lower():
            score += 25
        else:
            score += 10

        try:
            clean = int(row.get("cleanliness", 5))
            diff = abs(clean - cleanliness_pref)
            score += max(0, 15 - diff*2)
        except:
            score += 5

        if str(row.get("food_type","")).lower() == food_type.lower():
            score += 10

        if str(row.get("crowd","")).lower() == crowd.lower():
            score += 10

        if str(row.get("room_type","")).lower() == room_type.lower():
            score += 10

        return score

    df["score"] = df.apply(calculate_score, axis=1)

    df = df.sort_values(by="score", ascending=False).head(3)

    # ---------------- AI EXPLANATION ----------------
    def explain(row):

        why_match = []
        why_choose = []
        consider = []

        price = int(row.get("price", 0))
        clean = int(row.get("cleanliness", 5))
        beds = int(row.get("available_beds", 0))
        sharing = int(row.get("sharing", 1))

        # WHY MATCH
        if price <= budget:
            why_match.append(f"Perfect budget match (₹{price})")
        else:
            why_match.append(f"Slightly above budget (₹{price})")

        if location.lower() in str(row["location"]).lower():
            why_match.append(f"Exact location match ({location})")

        if str(row.get("food_type","")).lower() == food_type.lower():
            why_match.append("Food preference matched")

        if str(row.get("crowd","")).lower() == crowd.lower():
            why_match.append("Crowd type matched")

        # WHY CHOOSE
        if clean >= 8:
            why_choose.append("High cleanliness standards")
        elif clean >= 5:
            why_choose.append("Decent cleanliness")

        if beds > 0:
            why_choose.append("Beds available immediately")

        if price < budget:
            why_choose.append("Budget friendly option")

        if sharing <= 2:
            why_choose.append("Less crowded room")

        # CONSIDER
        if price > budget:
            consider.append(f"₹{price - budget} above your budget")

        if clean < cleanliness_pref:
            consider.append("Cleanliness lower than expected")

        if beds == 0:
            consider.append("Limited availability")

        if sharing >= 3:
            consider.append("More sharing (crowded)")

        return why_match, why_choose, consider

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches For You")

    if df.empty:
        st.error("No PGs found ❌")

    else:
        for _, row in df.iterrows():

            match_percent = int(row["score"])

            why_match, why_choose, consider = explain(row)

            st.markdown(f"## 🏠 {row['pg_name']} — {match_percent}% Match")

            st.success("Why this match?")
            for item in why_match:
                st.write(f"• {item}")

            st.info("Why choose this PG?")
            for item in why_choose:
                st.write(f"• {item}")

            st.warning("Things to consider:")
            for item in consider:
                st.write(f"• {item}")

            st.divider()