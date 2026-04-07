import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import random

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ AUTH FIX (SAFE)
try:
    creds_dict = dict(st.secrets["gcp"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scope
    )

    client = gspread.authorize(creds)

except Exception as e:
    st.error(f"❌ Auth Error: {e}")
    st.stop()

# ---------------- SAFE CONNECTION ----------------
try:
    sh = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")

    sheet = sh.sheet1   # ✅ ONLY CHANGE (removed rooms)

except Exception as e:
    st.error(f"❌ Sheet Error: {e}")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower().str.strip()

        # FIX sharing format
        df["sharing_type"] = (
            df["sharing_type"]
            .astype(str)
            .str.replace("Sharing", "")
            .str.strip()
        )

        return df
    except Exception as e:
        st.error(e)
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]

location_split = df["location"].astype(str).str.split("-", n=1, expand=True)
df["area"] = location_split[0].fillna("").str.strip()
df["locality"] = location_split[1].fillna("").str.strip()

# ---------------- SEARCH ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s, na=False) |
        df["locality"].str.lower().str.contains(s, na=False)
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

grouped = df.groupby(["pg_id", "pg_name", "location"])

for (pg_id, pg_name, location), group in grouped:

    row = group.iloc[0]

    price_str = str(row["price"]).replace("₹", "").replace(",", "").strip()
    if not price_str.isdigit():
        continue

    price = int(price_str)

    score = 0
    reasons = []
    cons = []

    # PRICE
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

    # MATCH
    if row["area"] == pref_area:
        score += 20
        reasons.append("Area match")

    if row["locality"] == pref_locality:
        score += 20
        reasons.append("Exact locality match")

    if str(row["sharing_type"]) == pref_sharing.split()[0]:
        score += 10
        reasons.append("Sharing matched")

    if str(row.get("gender","")).lower() == pref_gender.lower():
        score += 5

    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5

    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5

    # RATINGS
    food_s = safe_float(row.get("food_rating"))
    clean_s = safe_float(row.get("cleanliness"))
    safety_s = safe_float(row.get("safety"))
    maint_s = safe_float(row.get("maintenance_score"))

    noise_map = {"low": 5, "medium": 3.5, "high": 1.5}
    noise_raw = str(row.get("noise_level","medium")).lower()
    noise_s = noise_map.get(noise_raw, 3.5)

    pain_score = round((food_s + clean_s + safety_s + maint_s + noise_s) / 5, 1)

    if int(row["available_beds"]) == 1:
        cons.append("Only 1 bed left")

    score = max(0, min(100, int(score)))

    results.append({
        "pg_id": pg_id,
        "pg": pg_name,
        "location": location,
        "price": price,
        "beds": int(group["available_beds"].sum()),
        "score": score,
        "reasons": reasons,
        "cons": cons,
        "pain": pain_score
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for i, r in enumerate(results[:3]):  # ✅ UNIQUE INDEX FIX

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < pref_budget:
        st.info(f"💰 ₹{r['price']}")
    else:
        st.warning(f"💰 ₹{r['price']} (Above budget)")

    st.write(f"🛏 {r['beds']} Beds Available")

    # BOOKING
    with st.form(f"book_form_{i}"):

        name = st.text_input("👤 Your Name")
        phone = st.text_input("📞 Phone Number")
        move_date = st.date_input("📅 Move-in Date")

        submit = st.form_submit_button("🚀 Confirm Booking")

        if submit:

            clean_phone = phone.replace("+91", "").replace("+", "").replace(" ", "").strip()

            if not (clean_phone.isdigit() and len(clean_phone) == 10):
                st.error("Enter valid phone number ❌")

            else:
                try:
                    booking_sheet = client.open_by_key(PG_APP_ID).worksheet("Bookings")

                    booking_sheet.append_row([
                        r["pg_id"], r["pg"],
                        r["location"], r["price"],
                        name.strip(), clean_phone,
                        str(move_date), "CONFIRMED"
                    ])

                    st.success("🎉 Booking Confirmed!")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()