import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp"],
    scopes=scope
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

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

col1, col2, col3 = st.columns(3)

pref_location = col1.selectbox("Area", df["location"].dropna().unique())
pref_budget = col2.number_input("Budget", value=6000)
pref_sharing = col3.selectbox("Sharing", ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"])

# ---------------- FILTER AVAILABLE ----------------
df = df[df["available_beds"] > 0]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    score = 0
    reasons = []
    pros = []
    cons = []

    price = float(row.get("price", 0))

    # ✅ BUDGET
    if price <= pref_budget:
        score += 40
        reasons.append(f"Within budget ₹{pref_budget}")
        pros.append("Affordable")
    elif price <= pref_budget + 1000:
        score += 25
        cons.append("Slightly expensive")
    else:
        continue

    # ✅ LOCATION
    if pref_location.lower() in str(row["location"]).lower():
        score += 30
        reasons.append("Exact location match")
    else:
        score += 10
        cons.append("Different location")

    # ✅ SHARING
    if row["sharing_type"] == pref_sharing:
        score += 20
        reasons.append("Preferred sharing matched")
    else:
        cons.append("Different sharing type")

    # ---------------- SIMPLE QUALITY DEFAULTS ----------------
    food_rating = 3
    clean_rating = 3
    safety_rating = 3

    avg_quality = (food_rating + clean_rating + safety_rating) / 3
    score += avg_quality * 3

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": int(price),
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": int(score),
        "reasons": reasons,
        "pros": pros,
        "cons": cons
    })

# ---------------- TOP 3 ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

if not results:
    st.error("No matching PGs found")
else:
    for r in results:

        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        st.markdown(f"📍 {r['location']}")
        st.markdown(f"💰 ₹{r['price']}")
        st.markdown(f"🛏 {r['beds']} Beds Available")
        st.markdown(f"📞 {r['phone']}")

        st.markdown("### 💡 Why this PG?")
        for i in r["reasons"]:
            st.write("•", i)

        if r["pros"]:
            st.markdown("### 👍 Pros")
            for i in r["pros"]:
                st.write("✓", i)

        if r["cons"]:
            st.markdown("### ⚠️ Consider")
            for i in r["cons"]:
                st.write("•", i)

        st.divider()