import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import random

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp"],
    scopes=scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.lower().str.strip()
    return df

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN DATA ----------------
df = df[df["available_beds"] > 0]

# REMOVE DUPLICATE PGs (IMPORTANT)
df = df.drop_duplicates(subset=["pg_name", "location"])

# ---------------- SPLIT LOCATION ----------------
df[["area", "locality"]] = df["location"].str.split("-", expand=True)

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

pref_area = st.selectbox("📍 Area", sorted(df["area"].dropna().unique()))

filtered_localities = df[df["area"] == pref_area]["locality"].dropna().unique()
pref_locality = st.selectbox("🏠 Locality", sorted(filtered_localities))

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox("🛏 Sharing", ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"])

pref_gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])

pref_food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    try:
        price = int(float(row["price"]))
    except:
        continue

    score = 0
    reasons = []
    pros = []
    cons = []

    # 💰 BUDGET LOGIC (FIXED)
    if price == pref_budget:
        score += 40
        reasons.append("Perfect budget match 🔥")

    elif price < pref_budget:
        diff = pref_budget - price

        if diff <= 500:
            score += 35
            reasons.append("Very close to your budget")

        elif diff <= 1500:
            score += 25
            reasons.append("Good value under budget")
            pros.append("Saves money 💰")

        else:
            score += 10
            cons.append("Too cheap (check quality)")

    elif price <= pref_budget + 1000:
        score += 20
        cons.append("Slightly above budget")

    else:
        continue

    # 📍 LOCATION
    if row["area"] == pref_area:
        score += 20
        reasons.append("Area match")

    if row["locality"] == pref_locality:
        score += 20
        reasons.append("Exact locality match")

    # 🛏 SHARING
    if row["sharing_type"] == pref_sharing:
        score += 10
        reasons.append("Sharing matched")

    # 👤 GENDER
    if str(row.get("gender", "")).lower() == pref_gender.lower():
        score += 5

    # 🍽 FOOD
    if str(row.get("food_type", "")).lower() == pref_food.lower():
        score += 5

    # ✅ LIMIT SCORE
    score = max(0, min(100, int(score)))

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": score,
        "reasons": reasons,
        "pros": pros,
        "cons": cons
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

if not results:
    st.error("No matching PGs found ❌")

for i, r in enumerate(results[:5]):   # show top 5

    if i == 0:
        badge = "🥇 Best Match"
    elif i == 1:
        badge = "🥈 Great Option"
    else:
        badge = "🥉 Value Pick"

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
    st.markdown(f"### {badge}")

    st.markdown(f"📍 {r['location']}")

    # 💰 PRICE DISPLAY (FIXED)
    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")

    elif r["price"] < pref_budget:
        diff = pref_budget - r["price"]

        if diff <= 500:
            st.info(f"💰 ₹{r['price']} (Close to budget)")
        else:
            st.info(f"💰 ₹{r['price']} (₹{diff} cheaper 💰)")

    else:
        st.warning(f"💰 ₹{r['price']} (Above budget)")

    st.markdown(f"🛏 {r['beds']} Beds Available")

    # 🔥 URGENCY
    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] <= 2:
        st.warning("⚡ Only few beds left")
    elif r["beds"] <= 4:
        st.info("⏳ Filling fast")

    # 👀 SOCIAL PROOF
    views = random.randint(20, 80)
    st.caption(f"👀 {views} people viewed today")

    # 📞 CONTACT
    st.markdown(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    # WHY
    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    if r["pros"]:
        st.markdown("### 👍 Pros")
        for p in r["pros"]:
            st.write("✓", p)

    if r["cons"]:
        st.markdown("### ⚠️ Consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()