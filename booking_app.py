import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (AI + Smart Matching)")

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
history_sheet = sheet.worksheet("user_history")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    rooms = pd.DataFrame(room_sheet.get_all_records())
    history = pd.DataFrame(history_sheet.get_all_records())
    return rooms, history

df, history_df = load_data()

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
st.subheader("👤 Your Details")
name = st.text_input("Name")
phone = st.text_input("Phone")

st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget (₹)", min_value=1000, value=6000)

location = st.selectbox("Location", df["location"].dropna().unique())

food = st.selectbox("Food Type", ["Veg", "Non Veg", "Mixed"])

food_expect = st.slider("Food Quality Expectation ⭐", 1, 5, 3)

crowd = st.selectbox("Preferred Crowd", ["Students", "Employees", "Mixed"])
room_type = st.selectbox("Room Type", ["AC", "Non-AC"])

cleanliness_user = st.slider("Cleanliness Expectation", 1, 10, 5)

# ---------------- USER HISTORY ----------------
user_history = history_df[history_df["phone"] == phone] if not history_df.empty else pd.DataFrame()

# ---------------- BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    st.info(f"Showing PGs under your budget ₹{budget}")

    # SAVE USER DATA
    if phone:
        history_sheet.append_row([
            phone,
            location,
            budget,
            food,
            crowd,
            room_type,
            cleanliness_user,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

    results = []

    for _, row in df.iterrows():

        score = 0
        reasons = []
        pros = []
        cons = []

        price = int(row["price"])

        # ---------------- ORIGINAL BUDGET LOGIC (UNCHANGED) ----------------
        if price <= budget:
            score += 30
            reasons.append(f"Within your budget (₹{budget}). PG price ₹{price}")
        elif price <= budget + 1000:
            score += 20
            reasons.append(f"Slightly above your budget (₹{budget}). PG price ₹{price}")
            cons.append("Slightly expensive")
        else:
            continue

        # ---------------- NEW SMART BUDGET EXPLANATION ----------------
        diff = budget - price

        if diff >= 0:
            if diff == 0:
                reasons.append(f"Perfect match — exactly ₹{price}")
            elif diff <= 1000:
                reasons.append(f"Close to your budget — ₹{price}")
            elif diff <= 3000:
                reasons.append(f"Good deal — ₹{diff} cheaper than your budget")
            else:
                reasons.append(f"Best deal — save ₹{diff}")

        # ---------------- LOCATION ----------------
        if str(row["location"]).lower() == location.lower():
            score += 25
            reasons.append("Exact location match")
        else:
            score += 10
            cons.append("Different location")

        # ---------------- FOOD ----------------
        pg_food = str(row.get("food_type", "")).lower()

        food_rating = float(row["food_rating"]) if "food_rating" in df.columns else 3

        if food.lower() == pg_food:
            score += 5
        elif pg_food == "mixed":
            score += 3
        else:
            cons.append("Food type mismatch")

        diff_food = abs(food_expect - food_rating)
        score += max(0, 10 - diff_food * 2)

        if diff_food <= 1:
            reasons.append("Food quality matches expectation")
            pros.append("Good food quality")
        else:
            cons.append("Food quality below expectation")

        # ---------------- CROWD ----------------
        pg_crowd = str(row.get("crowd", "")).lower()

        if crowd.lower() == pg_crowd:
            score += 10
        elif pg_crowd == "mixed":
            score += 5
        else:
            cons.append("Crowd mismatch")

        # ---------------- CLEANLINESS ----------------
        pg_clean = int(row.get("cleanliness", 5))

        diff_clean = abs(cleanliness_user - pg_clean)
        score += max(0, 15 - diff_clean * 2)

        if diff_clean <= 2:
            pros.append("High cleanliness")
        else:
            cons.append("Cleanliness below expectation")

        # ---------------- LEARNING SYSTEM ----------------
        if not user_history.empty:
            past = user_history.iloc[-1]

            if str(past["location"]).lower() == str(row["location"]).lower():
                score += 5

            if str(past["food"]).lower() == pg_food:
                score += 5

        # ---------------- PAIN SCORE ----------------
        food_r = float(row.get("food_rating", 3))
        clean_r = float(row.get("cleanliness", 5)) / 2
        noise_r = float(row.get("noise_rating", 3))
        safety_r = float(row.get("safety_rating", 3))
        crowd_r = float(row.get("crowd_rating", 3))

        pain_avg = round((food_r + clean_r + noise_r + safety_r + crowd_r) / 5, 1)

        pain_dict = {
            "Food": food_r,
            "Cleanliness": clean_r,
            "Noise": noise_r,
            "Safety": safety_r,
            "Crowd": crowd_r
        }

        worst = min(pain_dict, key=pain_dict.get)

        if pain_dict[worst] <= 2:
            pain_msg = f"⚠️ {worst} is poor"
        else:
            pain_msg = "✅ Overall good living conditions"

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "pain": pain_avg,
            "pain_msg": pain_msg
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    st.success(f"Top {len(results)} PGs selected based on your budget ₹{budget}")

    # ---------------- OUTPUT ----------------
    st.subheader("🏆 Top Matches For You")

    if not results:
        st.error("No PGs found ❌")

    for r in results:

        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        # SMART TAG
        if r["score"] >= 80:
            st.success("🔥 Highly Recommended")
        elif r["score"] >= 60:
            st.info("👍 Good Choice")
        else:
            st.warning("⚖️ Consider Carefully")

        st.markdown("### 💡 Why this PG?")
        for i in r["reasons"]:
            st.write("•", i)

        st.markdown("### 👍 Why choose this PG?")
        for i in r["pros"]:
            st.write("✓", i)

        st.markdown("### ⚠️ Things to consider")
        for i in r["cons"]:
            st.write("•", i)

        st.markdown(f"### ⭐ Pain Score: {r['pain']} / 5")
        st.warning(r["pain_msg"])

        st.divider()