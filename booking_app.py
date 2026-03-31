import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="PG Match AI", layout="centered")
st.title("🏠 PG Match AI Engine")

# ---------------- GOOGLE AUTH ----------------
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
room_sheet = sheet.get_worksheet(0)
booking_sheet = sheet.worksheet("orders")

# ---------------- LOAD ----------------
@st.cache_data(ttl=10)
def load_data():
    rooms = pd.DataFrame(room_sheet.get_all_records())
    bookings = pd.DataFrame(booking_sheet.get_all_records())
    return rooms, bookings

room_df, booking_df = load_data()

# ---------------- JSON PARSE ----------------
def safe_parse(val):
    try:
        data = json.loads(val)
        return data[0] if isinstance(data, list) else data
    except:
        return {}

if not room_df.empty:
    room_df["parsed"] = room_df["sharing_json"].apply(safe_parse)

    room_df["sharing"] = room_df["parsed"].apply(
        lambda x: int(str(x.get("type","0")).split()[0]) if x else 0
    )

    room_df["price"] = room_df["parsed"].apply(
        lambda x: int(str(x.get("price",0)).replace(",","")) if x else 0
    )

    room_df["available_beds"] = room_df["parsed"].apply(
        lambda x: int(x.get("available_beds",0))
    )

    room_df["total_beds"] = room_df["parsed"].apply(
        lambda x: int(x.get("total_beds",0))
    )

# =========================================================
# 👤 USER
# =========================================================
st.subheader("👤 Your Details")
name = st.text_input("Name")
phone = st.text_input("Phone")

# =========================================================
# 🎯 DYNAMIC FILTERS
# =========================================================
def get_unique(df, col):
    return ["All"] + sorted(df[col].dropna().astype(str).unique()) if col in df.columns else ["All"]

st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget", value=6000)
location = st.selectbox("Location", get_unique(room_df, "location"))
gender = st.selectbox("Gender", get_unique(room_df, "gender"))
food_type = st.selectbox("Food Type", get_unique(room_df, "food_type"))
crowd = st.selectbox("Crowd", get_unique(room_df, "crowd"))
room_type = st.selectbox("Room Type", get_unique(room_df, "room_type"))
cleanliness_pref = st.selectbox("Cleanliness", ["All","Low","Medium","High"])

# =========================================================
# FILTER
# =========================================================
def hard_filter(df):
    f = df.copy()

    if location != "All":
        f = f[f["location"] == location]

    if gender != "All" and "gender" in f.columns:
        f = f[f["gender"] == gender]

    if food_type != "All":
        f = f[f["food_type"] == food_type]

    if crowd != "All":
        f = f[f["crowd"] == crowd]

    if room_type != "All":
        f = f[f["room_type"] == room_type]

    return f

# =========================================================
# 🤖 HUMAN AI EXPLANATION
# =========================================================
def generate_explanation(row, score):

    text = ""

    if row["price"] <= budget:
        text += "Perfectly fits your budget. "
    else:
        text += "Slightly above your budget but may offer better quality. "

    if location != "All":
        if location.lower() in str(row["location"]).lower():
            text += "Located exactly in your preferred area. "
        else:
            text += "Located near your preferred area. "

    if str(row.get("food_type","")).lower() == food_type.lower():
        text += "Food preference matches well. "

    if str(row.get("crowd","")).lower() == crowd.lower():
        text += "Crowd type suits your lifestyle. "

    try:
        clean = int(row.get("cleanliness",5))
        if clean >= 8:
            text += "Very clean and well maintained. "
        else:
            text += "Decent cleanliness. "
    except:
        pass

    return text

# =========================================================
# SCORING
# =========================================================
def calculate_score(row):

    score = 0

    # Budget
    if row["price"] <= budget:
        score += 30
    else:
        score += 10

    # Location
    if location != "All":
        if location.lower() in str(row["location"]).lower():
            score += 25
        else:
            score += 10

    # Cleanliness
    try:
        score += (int(row.get("cleanliness",5)) / 10) * 15
    except:
        pass

    # Food
    if food_type != "All":
        if str(row.get("food_type","")).lower() == food_type.lower():
            score += 10

    # Crowd
    if crowd != "All":
        if str(row.get("crowd","")).lower() == crowd.lower():
            score += 10

    # Room type
    if room_type != "All":
        if str(row.get("room_type","")).lower() == room_type.lower():
            score += 10

    return score

# =========================================================
# MATCH ENGINE
# =========================================================
if st.button("🔍 Find Best PGs"):

    if name == "" or phone == "":
        st.error("Enter details")
        st.stop()

    df = hard_filter(room_df)

    if df.empty:
        st.error("No PGs found ❌")
        st.stop()

    df["score"] = df.apply(calculate_score, axis=1)

    top = df.sort_values(by="score", ascending=False).head(3)

    st.subheader("🏆 Top Matches")

    for i, row in top.iterrows():

        score = int(row["score"])
        explanation = generate_explanation(row, score)

        st.markdown(f"## 🏠 {row.get('pg_name','PG')} — {score}% Match")

        st.markdown("### 🤖 AI Insight")
        st.write(explanation)

        st.markdown(f"""
💰 ₹{row['price']}  
📍 {row.get('location')}  
🍽 {row.get('food_type')}  
👥 {row.get('crowd')}  
🧼 {row.get('cleanliness')}/10  
🛏 {row.get('room_type')}  
""")

        if row["available_beds"] > 0:
            if st.button(f"Book", key=i):

                new_beds = row["available_beds"] - 1

                new_json = {
                    "type": f"{row['sharing']} Sharing",
                    "price": row["price"],
                    "deposit": 2000,
                    "total_beds": row["total_beds"],
                    "available_beds": new_beds
                }

                room_sheet.update(f"A{i+2}", [[json.dumps([new_json])]])

                booking_sheet.append_row([
                    name,
                    phone,
                    row.get("pg_name"),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                st.success("Booked ✅")
                st.cache_data.clear()
                st.rerun()

        else:
            st.error("Full")

        st.divider()

# =========================================================
# BOOKINGS
# =========================================================
st.subheader("📜 Bookings")

if not booking_df.empty:
    st.dataframe(booking_df)