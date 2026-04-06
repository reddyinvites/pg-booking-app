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

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]
df = df.drop_duplicates(subset=["pg_name", "location"])

df[["area", "locality"]] = df["location"].str.split("-", expand=True)

# ---------------- SEARCH ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s) |
        df["locality"].str.lower().str.contains(s)
    ]

# ---------------- DROPDOWNS ----------------
all_areas = sorted(df["area"].dropna().unique())
all_localities = sorted(df["locality"].dropna().unique())

pref_area = st.selectbox("📍 Area", all_areas)
pref_locality = st.selectbox("🏠 Locality", all_localities)

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox(
    "🛏 Sharing",
    ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"]
)

pref_gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])
pref_room_type = st.selectbox("🧊 Room Type", ["AC", "Non AC"])

# ---------------- FILTER ----------------
df = df[df["area"] == pref_area]
df = df[df["locality"] == pref_locality]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    price_str = str(row["price"]).replace("₹", "").replace(",", "").strip()
    if not price_str.isdigit():
        continue

    price = int(price_str)

    score = 0
    reasons = []
    cons = []

    # 💰 BUDGET
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

        else:
            score += 10
            cons.append("Lower than your budget")

    elif price <= pref_budget + 1000:
        score += 20
        cons.append("Slightly above budget")

    else:
        continue

    # LOCATION
    if row["area"] == pref_area:
        score += 20
        reasons.append("Area match")

    if row["locality"] == pref_locality:
        score += 20
        reasons.append("Exact locality match")

    # SHARING
    if row["sharing_type"] == pref_sharing:
        score += 10
        reasons.append("Sharing matched")

    # GENDER
    if str(row.get("gender","")).lower() == pref_gender.lower():
        score += 5

    # FOOD
    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5

    # ROOM TYPE
    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5

    if int(row["available_beds"]) == 1:
        cons.append("Only 1 bed left")

    score = max(0, min(100, int(score)))

    results.append({
        "row": row,
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": score,
        "reasons": reasons,
        "cons": cons
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

top_results = results[:3]

for r in top_results:

    st.markdown(f"""
    <div style="background:#D4EDDA;padding:15px;border-radius:15px">
    <h3>🏠 {r['pg']} — {r['score']}% Match</h3>
    📍 {r['location']}
    </div>
    """, unsafe_allow_html=True)

    # PRICE
    if r["price"] < pref_budget:
        st.info(f"💰 ₹{r['price']} (Save ₹{pref_budget - r['price']})")
    elif r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} Perfect match")
    else:
        st.warning(f"💰 ₹{r['price']} Above budget")

    # BEDS
    st.write(f"🛏 {r['beds']} Beds Available")

    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] <= 2:
        st.warning("⚡ Only few beds left")

    views = random.randint(30, 90)
    st.caption(f"👀 {views} people viewed today")

    st.write(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    row = r["row"]

    # ---------------- CONDITION SCORE ----------------
    food = float(row.get("food_rating") or 5)
    clean = float(row.get("cleanliness") or 5)
    safety = float(row.get("safety") or 5)
    maint = float(row.get("maintenance_score") or 5)

    noise_map = {"low":5, "medium":3, "high":1}
    noise_raw = str(row.get("noise_level","medium")).lower()
    noise = noise_map.get(noise_raw, 3)

    pain_score = round((food + clean + safety + maint + noise)/5, 1)

    st.markdown("### 😣 PG Condition Score")
    st.write(f"⭐ {pain_score} / 5")

    st.write(f"🍛 Food → {food}")
    st.write(f"🧼 Cleanliness → {clean}")
    st.write(f"🔐 Safety → {safety}")
    st.write(f"🔧 Maintenance → {maint}")
    st.write(f"🔇 Noise → {noise_raw.capitalize()}")

    # BIGGEST ISSUE
    issues = {
        "Food not good": food,
        "Not clean": clean,
        "Maintenance issues": maint,
        "Safety concern": safety,
        "Too noisy": noise
    }

    worst = min(issues, key=issues.get)

    if pain_score >= 4:
        st.success("✅ Very good PG condition")
    else:
        st.warning(f"⚠️ {worst}")

    # WHY
    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    # CONSIDER
    if r["cons"]:
        st.markdown("### ⚠️ Things to consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()