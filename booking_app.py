import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import ast

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart AI Matching)")

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

df = load_data()

# ---------------- PARSE JSON ----------------
def parse_json(x):
    try:
        return ast.literal_eval(x)[0]
    except:
        return {}

df["parsed"] = df["sharing_json"].apply(parse_json)

df["price"] = df["parsed"].apply(lambda x: int(x.get("price", 0)))
df["sharing"] = df["parsed"].apply(lambda x: int(x.get("type", "1").split()[0]))

# ---------------- USER DETAILS ----------------
st.subheader("👤 Your Details")

name = st.text_input("Name")
phone = st.text_input("Phone")

# ---------------- PREFERENCES ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget (₹)", min_value=1000, value=6000)

locations = df["location"].dropna().unique().tolist()
location = st.selectbox("Location", locations)

food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])
food_rating = st.slider("Food Quality Expectation ⭐", 1, 10, 5)

crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])
room_type = st.selectbox("Room Type", ["AC", "Non-AC"])
cleanliness = st.slider("Cleanliness Expectation 🧼", 1, 10, 5)

# ---------------- MATCH BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    results = []

    for _, row in df.iterrows():

        price = int(row["price"])

        # ---------------- HARD FILTER ----------------
        if price > budget:
            continue

        score = 0
        reasons = []
        pros = []
        cons = []

        # ---------------- BUDGET ----------------
        diff = budget - price

        score += 30

        if diff == 0:
            reasons.append(f"Perfect budget match (₹{price})")
        elif diff <= 1000:
            reasons.append(f"Very close to your budget (₹{price})")
        elif diff <= 3000:
            reasons.append(f"Good deal — ₹{diff} cheaper")
        else:
            reasons.append(f"Great deal — save ₹{diff}")

        pros.append("Budget friendly")

        # ---------------- LOCATION ----------------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append(f"Exact location match ({location})")
        else:
            cons.append("Different location")

        # ---------------- FOOD ----------------
        pg_food = str(row.get("food_type", "")).lower()

        if food.lower() in pg_food:
            score += 10
            reasons.append("Food matches preference")
        else:
            cons.append("Food mismatch")

        # ---------------- CROWD ----------------
        pg_crowd = str(row.get("crowd", "")).lower()

        if crowd.lower() in pg_crowd:
            score += 10
        else:
            cons.append("Crowd mismatch")

        # ---------------- CLEANLINESS ----------------
        pg_clean = int(row.get("cleanliness", 5))

        if pg_clean >= cleanliness:
            score += 15
            pros.append("High cleanliness")
        else:
            cons.append("Below expected cleanliness")

        # ---------------- ROOM TYPE ----------------
        pg_room = str(row.get("room_type", "")).lower()

        if room_type.lower() in pg_room:
            score += 5
        else:
            cons.append("Room type mismatch")

        results.append({
            "name": row["pg_name"],
            "score": score,
            "reasons": reasons,
            "pros": pros,
            "cons": cons
        })

    # ---------------- SORT ----------------
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches For You")

    if not results:
        st.error("No PGs found ❌")

    for pg in results:

        st.markdown(f"## 🏠 {pg['name']} — {pg['score']}% Match")

        st.success("👍 Good Choice")

        # WHY THIS PG
        st.markdown("### 💡 Why this PG?")
        for r in pg["reasons"]:
            st.write(f"• {r}")

        # WHY CHOOSE
        st.markdown("### 👍 Why choose this PG?")
        for p in pg["pros"]:
            st.write(f"• {p}")

        # CONS
        if pg["cons"]:
            st.markdown("### ⚠️ Things to consider")
            for c in pg["cons"]:
                st.write(f"• {c}")

        st.divider()