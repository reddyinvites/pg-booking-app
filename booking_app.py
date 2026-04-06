import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import random

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

# ---------------- CLEAN ----------------
df = df.dropna(subset=["location", "sharing_type", "food_type"])
df = df[df["available_beds"] > 0]

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

col1, col2, col3, col4 = st.columns(4)

locations = sorted(df["location"].unique())
pref_location = col1.selectbox("📍 Location", locations)

pref_budget = col2.number_input("💰 Budget", value=8000)

sharing_types = sorted(df["sharing_type"].unique())
pref_sharing = col3.selectbox("🛏 Sharing", sharing_types)

food_types = sorted(df["food_type"].unique())
pref_food = col4.selectbox("🍽 Food", food_types)

# ---------------- FILTER ----------------
filtered_df = df[
    (df["location"] == pref_location) &
    (df["food_type"] == pref_food)
]

# ---------------- GROUP BY PG ----------------
grouped = filtered_df.groupby("pg_name")

results = []

for pg, group in grouped:

    best_score = -1
    best_data = None

    for _, row in group.iterrows():

        try:
            price = int(float(row["price"]))
        except:
            continue

        score = 0
        reasons = []
        pros = []
        cons = []

        # 💰 BUDGET
        if price == pref_budget:
            score += 100
            reasons.append("Perfect budget match 🔥")

        elif price < pref_budget:
            diff = pref_budget - price
            score += 80 - diff / 100

            if diff <= 500:
                reasons.append("Very close to your budget")
            else:
                reasons.append("Good value under budget")
                pros.append("Saves money 💰")

        elif price <= pref_budget + 1000:
            diff = price - pref_budget
            score += 60 - diff / 100
            cons.append("Slightly above budget")

        else:
            continue

        # 📍 LOCATION
        score += 40
        reasons.append("Exact location match 📍")

        # 🛏 SHARING
        if row["sharing_type"] == pref_sharing:
            score += 25
            reasons.append("Preferred sharing matched")

        # 🍽 FOOD
        score += 20
        reasons.append("Food preference matched 🍽")

        if score > best_score:
            best_score = score
            best_data = {
                "pg": row["pg_name"],
                "location": row["location"],
                "price": price,
                "beds": int(row["available_beds"]),
                "phone": row["owner_number"],
                "score": int(score),
                "reasons": reasons,
                "pros": pros,
                "cons": cons
            }

    if best_data:
        results.append(best_data)

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

if not results:
    st.error("No matching PGs found ❌")

for i, r in enumerate(results):

    badge = ["🥇 Best Match", "🥈 Great Option", "🥉 Value Pick"][i]

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
    st.markdown(f"### {badge}")
    st.markdown(f"📍 {r['location']}")

    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < pref_budget:
        st.info(f"💰 ₹{r['price']} (₹{pref_budget - r['price']} cheaper)")
    else:
        st.warning(f"💰 ₹{r['price']} (above budget)")

    st.markdown(f"🛏 {r['beds']} Beds Available")

    # 🔥 URGENCY
    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] == 2:
        st.warning("⚡ Only 2 beds left")
    elif r["beds"] <= 4:
        st.info("⏳ Filling fast")

    # 👀 SOCIAL PROOF
    views = random.randint(20, 80)
    st.caption(f"👀 {views} people viewed today")
    st.caption("⏰ Prices may increase soon")

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