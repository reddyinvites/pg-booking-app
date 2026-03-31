import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
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

PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=10)
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    return df

df = load_data()

# ---------------- PARSE JSON ----------------
def parse_json(x):
    try:
        return json.loads(x)[0]
    except:
        return {}

df["parsed"] = df["sharing_json"].apply(parse_json)

df["price"] = df["parsed"].apply(lambda x: int(x.get("price", 0)))
df["available_beds"] = df["parsed"].apply(lambda x: int(x.get("available_beds", 0)))

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget ₹", value=6000)

locations = df["location"].dropna().unique()
location = st.selectbox("Location", locations)

food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])

crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])

room_type = st.selectbox("Room Type", ["AC", "Non-AC"])

cleanliness = st.slider("Cleanliness Expectation", 1, 10, 5)

# ---------------- FIND BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    results = []

    for _, row in df.iterrows():

        price = int(row["price"])

        # ✅ FIXED FILTER (IMPORTANT)
        if price > budget:
            continue

        score = 0
        reasons = []
        pros = []
        cons = []

        # ---------------- PRICE LOGIC ----------------
        diff = budget - price

        score += 30

        if diff == 0:
            reasons.append(f"Perfect budget match ₹{price}")
        elif diff <= 1000:
            reasons.append(f"Very close to your budget ₹{price}")
        elif diff <= 3000:
            reasons.append(f"Good deal — ₹{diff} cheaper")
        else:
            reasons.append(f"Great deal — save ₹{diff}")

        pros.append("Budget friendly")

        # ---------------- LOCATION ----------------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append("Exact location match")
        else:
            cons.append("Different location")

        # ---------------- FOOD ----------------
        if food.lower() in str(row.get("food_type", "")).lower():
            score += 10
            reasons.append("Food matches preference")
        else:
            cons.append("Food mismatch")

        # ---------------- CROWD ----------------
        if crowd.lower() in str(row.get("crowd", "")).lower():
            score += 10
        else:
            cons.append("Crowd mismatch")

        # ---------------- CLEANLINESS ----------------
        pg_clean = int(row.get("cleanliness_rating", 5))

        if pg_clean >= cleanliness:
            score += 15
            reasons.append("Cleanliness is good")
        else:
            cons.append("Cleanliness below expectation")

        # ---------------- ROOM TYPE ----------------
        if room_type.lower() in str(row.get("room_type", "")).lower():
            score += 5
        else:
            cons.append("Room type mismatch")

        results.append({
            "name": row["pg_name"],
            "score": score,
            "price": price,
            "reasons": reasons,
            "pros": pros,
            "cons": cons
        })

    # ---------------- SORT ----------------
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches For You")

    if not results:
        st.error("No PGs found ❌")

    else:
        for pg in results[:3]:

            st.markdown(f"## 🏠 {pg['name']} — {pg['score']}% Match")

            st.success("👍 Good Choice")

            # WHY THIS PG
            st.markdown("### 💡 Why this PG?")
            for r in pg["reasons"]:
                st.write("•", r)

            # WHY CHOOSE
            st.markdown("### 👍 Why choose this PG?")
            for p in pg["pros"]:
                st.write("•", p)

            # CONS
            if pg["cons"]:
                st.markdown("### ⚠️ Things to consider")
                for c in pg["cons"]:
                    st.write("•", c)

            st.divider()