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

# Split
df["area"] = df["location"].apply(lambda x: x.split("-")[0] if "-" in x else x)
df["locality"] = df["location"].apply(lambda x: x.split("-")[1] if "-" in x else "")

# Remove invalid
df = df[(df["area"] != "") & (df["locality"] != "")]

# Remove duplicates (important fix)
df = df.drop_duplicates(subset=["pg_name", "location"])

# Convert numeric
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["available_beds"] = pd.to_numeric(df["available_beds"], errors="coerce")

# ---------------- FILTER AVAILABLE ----------------
df = df[df["available_beds"] > 0]

# ---------------- DROPDOWN DATA ----------------
area_list = sorted(df["area"].dropna().unique())

# ---------------- UI ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

# Apply search filter
if search:
    filtered = df[
        df["area"].str.contains(search, case=False, na=False) |
        df["locality"].str.contains(search, case=False, na=False)
    ]
    area_list = sorted(filtered["area"].unique())

# AREA
selected_area = st.selectbox("📍 Area", area_list)

# LOCALITY
localities = df[df["area"].str.lower() == selected_area.lower()]["locality"]
localities = sorted(localities.dropna().unique())

selected_locality = st.selectbox("🏠 Locality", localities)

# OTHER FILTERS
budget = st.number_input("💰 Budget", value=8000, step=500)

sharing = st.selectbox("🛏 Sharing", ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"])
gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])
food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    # FILTER MATCH FIRST
    if selected_area.lower() not in row["area"].lower():
        continue
    if selected_locality.lower() not in row["locality"].lower():
        continue
    if row["sharing_type"] != sharing:
        continue
    if str(row.get("gender","")).lower() != gender.lower():
        continue
    if food not in str(row.get("food_type","")):
        continue

    price = int(row["price"])
    score = 0
    reasons = []
    note = []

    # PRICE LOGIC (FIXED)
    if price == budget:
        score += 40
        reasons.append("Perfect budget match 🔥")

    elif price < budget:
        diff = budget - price
        score += 30
        reasons.append("Good value under budget")
        note.append(f"Save ₹{diff}")

    elif price <= budget + 1000:
        score += 20
        note.append("Slightly above budget")

    else:
        continue

    # LOCATION
    score += 20
    reasons.append("Exact locality match 📍")

    # SHARING
    score += 15
    reasons.append("Sharing matched 🛏")

    # GENDER
    score += 10
    reasons.append("Gender matched 👤")

    # FOOD
    score += 10
    reasons.append("Food preference matched 🍽")

    match_percent = min(100, int(score))

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": match_percent,
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

    badge = ["🥇 Best Match", "🥈 Great Option", "🥉 Value Pick"][i]

    st.markdown(f"### 🏠 {r['pg']} — {r['score']}% Match")
    st.caption(badge)

    st.write(f"📍 {r['location']}")

    # PRICE DISPLAY FIXED
    if r["price"] == budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < budget:
        diff = budget - r["price"]
        st.info(f"💰 ₹{r['price']} (Save ₹{diff})")
    else:
        st.warning(f"💰 ₹{r['price']} (Above budget)")

    # BEDS
    st.write(f"🛏 {r['beds']} Beds Available")

    if r["beds"] == 1:
        st.error("🔥 Last bed available!")
    elif r["beds"] <= 3:
        st.warning("⚡ Filling fast")

    # SOCIAL PROOF
    st.caption(f"👀 {random.randint(30,80)} people viewed today")

    # CONTACT
    st.write(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    # WHY
    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    # NOTE
    if r["note"]:
        st.markdown("### 💡 Note")
        for n in r["note"]:
            st.write("•", n)

    st.divider()