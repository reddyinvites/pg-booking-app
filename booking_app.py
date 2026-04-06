import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import urllib.parse

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- CONFIG ----------------
BUSINESS_NUMBER = "917702656073"

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

# SAFE CONNECTION
try:
    sh = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")
    sheet = sh.sheet1
except:
    st.error("❌ Unable to connect to Google Sheet")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower().str.strip()
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]
df = df.drop_duplicates(subset=["pg_name", "location"])
df[["area", "locality"]] = df["location"].str.split("-", expand=True)

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s) |
        df["locality"].str.lower().str.contains(s)
    ]

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
df = df[(df["area"] == pref_area) & (df["locality"] == pref_locality)]

# ---------------- SAFE FLOAT ----------------
def safe_float(val, default=5):
    try:
        if val == "" or val is None:
            return default
        return float(val) / 2
    except:
        return default

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

    # BUDGET
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

    # MATCHES
    if row["sharing_type"] == pref_sharing:
        score += 10
    if str(row.get("gender","")).lower() == pref_gender.lower():
        score += 5
    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5
    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5

    # ---------------- PAIN SCORE ----------------
    food_s = safe_float(row.get("food_rating"))
    clean_s = safe_float(row.get("cleanliness"))
    safety_s = safe_float(row.get("safety"))
    maint_s = safe_float(row.get("maintenance_score"))

    noise_map = {"low":5, "medium":3.5, "high":1.5}
    noise_raw = str(row.get("noise_level","medium")).lower()
    noise_s = noise_map.get(noise_raw, 3.5)

    pain_score = round((food_s + clean_s + safety_s + maint_s + noise_s)/5,1)

    issues = {
        "Food not good": food_s,
        "Not very clean": clean_s,
        "Maintenance issue": maint_s,
        "Safety concern": safety_s,
        "Too noisy": noise_s
    }

    biggest_issue = min(issues, key=issues.get)

    # CONS
    if row["sharing_type"] != pref_sharing:
        cons.append("Different sharing")
    if int(row["available_beds"]) == 1:
        cons.append("Only 1 bed left")

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "score": int(score),
        "reasons": reasons,
        "cons": cons,
        "pain": pain_score,
        "food_s": food_s,
        "clean_s": clean_s,
        "safety_s": safety_s,
        "maint_s": maint_s,
        "noise": noise_raw.capitalize(),
        "issue": biggest_issue
    })

# SORT
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for r in results[:3]:

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

    st.write(f"💰 ₹{r['price']}")
    st.write(f"🛏 {r['beds']} Beds Available")

    # -------- BOOK BUTTON --------
    msg = f"""Hi 👋

I'm interested in booking:

🏠 PG: {r['pg']}
💰 Price: ₹{r['price']}
📍 Location: {r['location']}
🛏 Sharing: {pref_sharing}

Looking for immediate move-in.

Please share:
• Availability
• Photos & Videos
• House Rules

Thanks 🙂
"""

    st.link_button(
        "🚀 Book Now",
        f"https://wa.me/{BUSINESS_NUMBER}?text={urllib.parse.quote(msg)}"
    )

    # PAIN SCORE
    st.markdown("### 😣 PG Condition Score")
    st.write(f"⭐ {r['pain']} / 5")

    st.write(f"🍛 Food → {r['food_s']}")
    st.write(f"🧼 Cleanliness → {r['clean_s']}")
    st.write(f"🔐 Safety → {r['safety_s']}")
    st.write(f"🛠 Maintenance → {r['maint_s']}")
    st.write(f"🔇 Noise → {r['noise']}")

    st.markdown("### 🚨 Biggest Issue")
    st.error(r["issue"])

    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    if r["cons"]:
        st.markdown("### ⚠️ Things to consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()