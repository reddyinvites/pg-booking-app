import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import ast

st.set_page_config(page_title="PG Match Engine", layout="centered")

st.title("🏠 PG Match Engine (AI Recommendation)")

# ---------------- GOOGLE SHEET ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)

client = gspread.authorize(creds)

PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
sheet = client.open_by_key(PG_DATA_ID)
ws = sheet.worksheet("Sheet1")

@st.cache_data(ttl=30)
def load_data():
    return pd.DataFrame(ws.get_all_records())

df = load_data()

# ---------------- SAFE PARSE ----------------
def parse_json_safe(x):
    try:
        return ast.literal_eval(x)[0]
    except:
        return {}

df["parsed"] = df["sharing_json"].apply(parse_json_safe)

# ---------------- CLEAN DATA ----------------
def safe_int(x):
    try:
        return int(x)
    except:
        return 0

df["price"] = df["parsed"].apply(lambda x: safe_int(x.get("price")))
df["sharing"] = df["parsed"].apply(lambda x: safe_int(x.get("type","0").split()[0]))

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget ₹", 1000, 20000, 6000)

locations = df["location"].dropna().unique().tolist()
location = st.selectbox("Location", locations)

food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])

crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])

room_type = st.selectbox("Room Type", ["AC", "Non-AC"])

food_exp = st.slider("Food Quality Expectation ⭐", 1, 10, 5)
clean_exp = st.slider("Cleanliness Expectation ⭐", 1, 10, 5)

# ---------------- BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    results = []

    for _, row in df.iterrows():

        price = int(row["price"])
        pg_location = str(row.get("location","")).lower()
        pg_name = row.get("pg_name","PG")

        score = 0
        reasons = []
        pros = []
        cons = []

        # ---------------- HARD FILTER ----------------
        if price > budget:
            continue   # ❗ FIXED

        # ---------------- BUDGET LOGIC ----------------
        diff = budget - price

        score += 30

        if diff == 0:
            reasons.append(f"Perfect budget match (₹{price})")

        elif diff <= 1000:
            reasons.append(f"Very close to your budget (₹{price})")

        elif diff <= 3000:
            reasons.append(f"Good deal — save ₹{diff}")

        else:
            reasons.append(f"Great deal — save ₹{diff}")

        pros.append("Budget friendly")

        # ---------------- LOCATION ----------------
        if location.lower() in pg_location:
            score += 25
            reasons.append(f"Exact location match ({location})")
        else:
            cons.append("Different location")

        # ---------------- FOOD ----------------
        pg_food = str(row.get("food_type","")).lower()

        if food.lower() in pg_food:
            score += 10
            reasons.append("Food matches your preference")
        else:
            cons.append("Food mismatch")

        # ---------------- CROWD ----------------
        pg_crowd = str(row.get("crowd","")).lower()

        if crowd.lower() in pg_crowd:
            score += 10
        else:
            cons.append("Crowd mismatch")

        # ---------------- CLEANLINESS ----------------
        clean_score = safe_int(row.get("cleanliness",5))

        score += (clean_score / 10) * 15

        if clean_score >= clean_exp:
            reasons.append("Cleanliness meets expectation")
        else:
            cons.append("Cleanliness below expectation")

        # ---------------- FOOD RATING ----------------
        food_score = safe_int(row.get("food_rating",5))

        score += (food_score / 10) * 10

        if food_score >= food_exp:
            reasons.append("Food quality is good")
        else:
            cons.append("Food quality average")

        # ---------------- FINAL SCORE ----------------
        match = int(score)

        # ---------------- OUTPUT ----------------
        results.append({
            "pg": pg_name,
            "score": match,
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "price": price
        })

    # ---------------- SORT ----------------
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- DISPLAY ----------------
    if results:

        st.subheader("🏆 Top Matches For You")

        for r in results:

            st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

            # WHY THIS PG
            st.markdown("### 💡 Why this PG?")
            for x in r["reasons"]:
                st.write("•", x)

            # WHY CHOOSE
            st.markdown("### 👍 Why choose this PG?")
            for x in r["pros"]:
                st.write("•", x)

            # CONS
            st.markdown("### ⚠️ Things to consider")
            if r["cons"]:
                for x in r["cons"]:
                    st.write("•", x)
            else:
                st.write("• No major issues")

            st.divider()

    else:
        st.error("❌ No PGs found under your budget")