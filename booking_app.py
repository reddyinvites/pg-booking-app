import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import ast

st.set_page_config(page_title="PG Match Engine AI", layout="centered")
st.title("🏠 PG Match Engine (AI + Pain + Learning)")

# ---------------- GOOGLE ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")
room_sheet = sheet.worksheet("Sheet1")

@st.cache_data(ttl=10)
def load_data():
    return pd.DataFrame(room_sheet.get_all_records())

df = load_data()

# ---------------- PARSE ----------------
def parse_json(x):
    try:
        return ast.literal_eval(x)[0]
    except:
        return {}

df["parsed"] = df["sharing_json"].apply(parse_json)
df["price"] = df["parsed"].apply(lambda x: int(x.get("price", 0)))

# ---------------- USER ----------------
st.subheader("👤 Your Details")
name = st.text_input("Name")
phone = st.text_input("Phone")

# ---------------- PREF ----------------
st.subheader("🎯 Preferences")

budget = st.number_input("Budget", 1000, 50000, 6000)
location = st.selectbox("Location", df["location"].dropna().unique())

food = st.selectbox("Food", ["Veg", "Non Veg", "Mixed"])
food_expect = st.slider("Food Expectation ⭐", 1, 10, 5)

crowd = st.selectbox("Crowd", ["Students", "Employees", "Mixed"])
room_type = st.selectbox("Room Type", ["AC", "Non-AC"])

clean_expect = st.slider("Cleanliness Expectation", 1, 10, 5)

# ---------------- LEARNING MEMORY ----------------
if "user_history" not in st.session_state:
    st.session_state.user_history = []

# ---------------- BUTTON ----------------
if st.button("🔍 Find Best PGs"):

    # Save user preference
    st.session_state.user_history.append({
        "budget": budget,
        "location": location,
        "food": food
    })

    results = []

    for _, row in df.iterrows():

        price = int(row["price"])

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
            reasons.append(f"Perfect budget match ₹{price}")
        elif diff <= 2000:
            reasons.append(f"Good price ₹{price}")
        else:
            reasons.append(f"Save ₹{diff}")

        # ---------------- LOCATION ----------------
        if row["location"] == location:
            score += 25
            reasons.append("Exact location match")
        else:
            cons.append("Different location")

        # ---------------- FOOD ----------------
        if food.lower() in str(row.get("food_type","")).lower():
            score += 10
            reasons.append("Food matches")
        else:
            cons.append("Food mismatch")

        # ---------------- CLEAN ----------------
        clean = int(row.get("cleanliness", 5))
        if clean >= clean_expect:
            score += 15
            pros.append("Clean environment")
        else:
            cons.append("Less clean")

        # ---------------- DISTANCE ----------------
        metro = int(row.get("metro_dist", 1000))
        bus = int(row.get("bus_dist", 1000))

        distance_score = max(0, 10 - (metro + bus)/200)
        score += distance_score

        if metro < 500:
            pros.append("Near metro")
        else:
            cons.append("Far from transport")

        # ---------------- PAIN SCORE ----------------
        food_r = float(row.get("food_rating", 3))
        clean_r = float(row.get("cleanliness", 3))
        noise_r = float(row.get("noise", 3))
        safety_r = float(row.get("safety", 3))
        crowd_r = float(row.get("crowd_rating", 3))

        pain_avg = round((food_r + clean_r + noise_r + safety_r + crowd_r)/5, 1)

        pains = {
            "Food": food_r,
            "Cleanliness": clean_r,
            "Noise": noise_r,
            "Safety": safety_r,
            "Crowd": crowd_r
        }

        biggest_pain = min(pains, key=pains.get)

        # ---------------- LEARNING BOOST ----------------
        for past in st.session_state.user_history:
            if past["location"] == row["location"]:
                score += 5

        results.append({
            "name": row["pg_name"],
            "score": int(score),
            "reasons": reasons,
            "pros": pros,
            "cons": cons,
            "pain": pain_avg,
            "big_pain": biggest_pain
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    # ---------------- DISPLAY ----------------
    st.subheader("🏆 Top Matches")

    for pg in results:

        st.markdown(f"## 🏠 {pg['name']} — {pg['score']}%")

        st.success("👍 Good Choice")

        # WHY
        st.markdown("### 💡 Why this PG?")
        for r in pg["reasons"]:
            st.write(f"• {r}")

        # PROS
        st.markdown("### 👍 Why choose?")
        for p in pg["pros"]:
            st.write(f"• {p}")

        # CONS
        if pg["cons"]:
            st.markdown("### ⚠️ Things to consider")
            for c in pg["cons"]:
                st.write(f"• {c}")

        # PAIN SCORE
        st.markdown("### ⭐ Pain Score")
        st.write(f"⭐ {pg['pain']} / 5")

        st.warning(f"⚠️ Biggest Issue: {pg['big_pain']}")

        st.divider()