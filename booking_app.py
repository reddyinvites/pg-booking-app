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

df["price"] = df["parsed"].apply(lambda x: int(x.get("price", 0)))
df["available_beds"] = df["parsed"].apply(lambda x: int(x.get("available_beds", 0)))

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

        # ---------------- BUDGET ----------------
        if price <= budget:
            score += 30
            reasons.append(f"Within your budget ₹{budget} (PG ₹{price})")
        elif price <= budget + 1000:
            score += 20
            reasons.append(f"Slightly above budget ₹{price}")
            cons.append("Slightly expensive")
        else:
            continue

        diff = budget - price
        if diff >= 0:
            if diff == 0:
                reasons.append(f"Perfect match ₹{price}")
            elif diff <= 1000:
                reasons.append(f"Close to budget ₹{price}")
            elif diff <= 3000:
                reasons.append(f"Good deal — ₹{diff} cheaper")
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
        food_rating = min(5, float(row.get("food_rating", 3)))

        if food.lower() == pg_food:
            score += 5
        elif pg_food == "mixed":
            score += 3
        else:
            cons.append("Food mismatch")

        diff_food = abs(food_expect - food_rating)
        score += max(0, 10 - diff_food * 2)

        if diff_food <= 1:
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

        # ---------------- CLEAN ----------------
        pg_clean = int(row.get("cleanliness", 5))
        diff_clean = abs(cleanliness_user - pg_clean)

        score += max(0, 15 - diff_clean * 2)

        if diff_clean <= 2:
            pros.append("High cleanliness")
        else:
            cons.append("Cleanliness below expectation")

        # ---------------- LEARNING ----------------
        if not user_history.empty:
            past = user_history.iloc[-1]
            if str(past["location"]).lower() == str(row["location"]).lower():
                score += 5
            if str(past["food"]).lower() == pg_food:
                score += 5

        # ---------------- PAIN SCORE ----------------
        food_r = min(5, float(row.get("food_rating", 3)))
        clean_r = min(5, float(row.get("cleanliness", 5)) / 2)
        noise_r = min(5, float(row.get("noise_rating", 3)))
        safety_r = min(5, float(row.get("safety_rating", 3)))
        crowd_r = min(5, float(row.get("crowd_rating", 3)))

        pain_avg = round((food_r + clean_r + noise_r + safety_r + crowd_r) / 5, 1)

        pain_dict = {
            "Food": food_r,
            "Cleanliness": clean_r,
            "Noise": noise_r,
            "Safety": safety_r,
            "Crowd": crowd_r
        }

        results.append({
            "pg": row["pg_name"],
            "score": int(score),
            "price": price,
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "pain": pain_avg,
            "pain_dict": pain_dict
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- HIGHLIGHTS ----------------
    if results:
        top_score = max(results, key=lambda x: x["score"])["score"]
        cheapest_price = min(r["price"] for r in results)

        def value_score(r):
            return r["score"] / (r["price"] if r["price"] > 0 else 1)

        best_value_pg = max(results, key=value_score)["pg"]

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches For You")

    for r in results:

        st.markdown("----")
        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        badge = ""
        if r["score"] == top_score:
            badge += "🏆 Top Match  "
        if r["price"] == cheapest_price:
            badge += "💰 Cheapest  "
        if r["pg"] == best_value_pg:
            badge += "⭐ Best Value  "

        if badge:
            st.markdown(f"**{badge}**")

        st.markdown("### 💡 Why this PG?")
        for i in r["reasons"]:
            st.write("•", i)

        st.markdown("### 👍 Why choose this PG?")
        for i in r["pros"]:
            st.write("✓", i)

        if r["cons"]:
            st.markdown("### ⚠️ Things to consider")
            for i in r["cons"]:
                st.write("•", i)

        # ---------------- PAIN UI ----------------
        st.markdown(f"### ⭐ Pain Score: {r['pain']} / 5")

        st.markdown("#### 🔍 Detailed Breakdown")
        for k, v in r["pain_dict"].items():
            st.write(f"{k} → ⭐ {round(v,1)} / 5")

        # ---------------- TOP 2 PAINS ----------------
        st.markdown("#### ⚠️ Biggest Pain")

        sorted_pains = sorted(r["pain_dict"].items(), key=lambda x: x[1])
        top_2_pains = sorted_pains[:2]

        for factor, score_val in top_2_pains:

            if score_val <= 2:
                st.error(f"⚠️ {factor} is poor")

            elif score_val <= 3:
                if factor == "Food":
                    st.warning("⚠️ Food is average")
                elif factor == "Cleanliness":
                    st.warning("⚠️ Cleanliness could be better")
                elif factor == "Noise":
                    st.warning("⚠️ Slight noise issues (not peaceful)")
                elif factor == "Safety":
                    st.warning("⚠️ Area safety is average")
                elif factor == "Crowd":
                    st.warning("⚠️ Mixed crowd — may not suit everyone")

            else:
                st.success(f"✅ {factor} is good")