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
df["location"] = df["location"].astype(str).str.strip()

df["area"] = df["location"].apply(lambda x: x.split("-")[0].strip() if "-" in x else "")
df["locality"] = df["location"].apply(lambda x: x.split("-")[1].strip() if "-" in x else "")

df = df[(df["area"] != "") & (df["locality"] != "")]
df = df.drop_duplicates()

df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["available_beds"] = pd.to_numeric(df["available_beds"], errors="coerce")

df = df[df["available_beds"] > 0]

# ---------------- UI ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s) |
        df["locality"].str.lower().str.contains(s)
    ]

# ---------------- DROPDOWNS ----------------
areas = sorted(df["area"].dropna().unique())
pref_area = st.selectbox("📍 Area", areas)

localities = df[df["area"] == pref_area]["locality"]
localities = sorted(localities.dropna().unique())

pref_locality = st.selectbox("🏠 Locality", localities)

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox(
    "🛏 Sharing",
    ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"]
)

pref_gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])

# ✅ NEW ROOM TYPE FILTER
pref_room_type = st.selectbox("🧊 Room Type", ["AC", "Non AC"])

# ---------------- FILTER ----------------
df = df[
    (df["area"] == pref_area) &
    (df["locality"] == pref_locality)
]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    price = int(row["price"])
    score = 0
    reasons = []
    note = []

    # 💰 PRICE
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
            note.append(f"Save ₹{diff}")

        else:
            score += 10
            note.append(f"Lower than your budget (Save ₹{diff})")

    elif price <= pref_budget + 1000:
        score += 20
        note.append("Slightly above budget")

    else:
        continue

    # LOCATION
    score += 20
    reasons.append("Exact locality match 📍")

    # SHARING
    if row["sharing_type"] == pref_sharing:
        score += 10
        reasons.append("Sharing matched 🛏")

    # GENDER
    if str(row.get("gender", "")).lower() == pref_gender.lower():
        score += 5
        reasons.append("Gender matched 👤")

    # FOOD
    if str(row.get("food_type", "")).lower() == pref_food.lower():
        score += 5
        reasons.append("Food matched 🍽")

    # ✅ ROOM TYPE MATCH
    if str(row.get("room_type", "")).lower() == pref_room_type.lower():
        score += 10
        reasons.append("Room type matched 🧊")

    score = min(100, int(score))

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": score,
        "reasons": reasons,
        "note": note
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

if not results:
    st.error("No matching PGs found ❌")

for i, r in enumerate(results):

    colors = ["#D4EDDA", "#FFF3CD", "#E2E3E5"]
    badges = ["🥇 Best Match", "🥈 Great Option", "🥉 Value Pick"]

    st.markdown(f"""
    <div style="background:{colors[i]};padding:15px;border-radius:15px;margin-bottom:10px">
        <h3>🏠 {r['pg']} — {r['score']}% Match</h3>
        <b>{badges[i]}</b><br>
        📍 {r['location']}
    </div>
    """, unsafe_allow_html=True)

    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < pref_budget:
        diff = pref_budget - r["price"]
        st.info(f"💰 ₹{r['price']} (Save ₹{diff})")
    else:
        st.warning(f"💰 ₹{r['price']} (Above budget)")

    st.write(f"🛏 {r['beds']} Beds Available")

    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] <= 2:
        st.warning("⚡ Only few beds left")

    st.caption(f"👀 {random.randint(30,80)} people viewed today")

    st.write(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    if r["note"]:
        st.markdown("### 💡 Note")
        for n in r["note"]:
            st.write("•", n)

    st.divider()