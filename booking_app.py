import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine")

# ---------------- GOOGLE AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# ---------------- SHEET ----------------
SHEET_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

sheet = client.open_by_key(SHEET_ID)

room_sheet = sheet.get_worksheet(0)   # Sheet1
booking_sheet = sheet.worksheet("orders")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=10)
def load_data():
    rooms = pd.DataFrame(room_sheet.get_all_records())
    bookings = pd.DataFrame(booking_sheet.get_all_records())
    return rooms, bookings

room_df, booking_df = load_data()

# ---------------- SAFE JSON PARSE ----------------
def safe_parse(val):
    try:
        data = json.loads(val)
        if isinstance(data, list):
            return data[0]
        return data
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
# 👤 USER DETAILS
# =========================================================
st.subheader("👤 Your Details")

name = st.text_input("Name")
phone = st.text_input("Phone")

# =========================================================
# 🎯 DYNAMIC FILTERS
# =========================================================
def get_unique_options(df, column):
    if column in df.columns:
        return sorted(df[column].dropna().astype(str).unique().tolist())
    return []

st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget (₹)", value=6000)

location = st.selectbox("Location", ["All"] + get_unique_options(room_df, "location"))
gender = st.selectbox("Gender", ["All"] + get_unique_options(room_df, "gender"))
food_required = st.selectbox("Food", ["All"] + get_unique_options(room_df, "food"))
crowd = st.selectbox("Preferred Crowd", ["All"] + get_unique_options(room_df, "crowd"))
room_type = st.selectbox("Room Type", ["All"] + get_unique_options(room_df, "room_type"))
cleanliness = st.selectbox("Cleanliness", ["All"] + get_unique_options(room_df, "cleanliness"))

# =========================================================
# 🧠 HARD FILTER
# =========================================================
def hard_filter(df):

    filtered = df.copy()

    if location != "All" and "location" in filtered.columns:
        filtered = filtered[filtered["location"] == location]

    if gender != "All" and "gender" in filtered.columns:
        filtered = filtered[filtered["gender"] == gender]

    if food_required != "All" and "food" in filtered.columns:
        filtered = filtered[filtered["food"] == food_required]

    if crowd != "All" and "crowd" in filtered.columns:
        filtered = filtered[filtered["crowd"] == crowd]

    if room_type != "All" and "room_type" in filtered.columns:
        filtered = filtered[filtered["room_type"] == room_type]

    return filtered

# =========================================================
# 🧠 SCORING ENGINE
# =========================================================
def calculate_score(row):

    score = 0
    reasons = []
    drawbacks = []

    # Budget (30)
    if row["price"] <= budget:
        score += 30
        reasons.append("Perfect budget match")
    else:
        diff = row["price"] - budget

        if diff <= 500:
            score += 20
        elif diff <= 1000:
            score += 10

        drawbacks.append(f"₹{diff} above budget")

    # Location (25)
    if location != "All":
        if location.lower() in str(row.get("location","")).lower():
            score += 25
            reasons.append("Exact location match")
        else:
            score += 10
            drawbacks.append("Different location")

    # Cleanliness (15)
    clean_map = {"Low":5, "Medium":10, "High":15}
    if cleanliness != "All":
        score += clean_map.get(cleanliness, 10)

    # Food (10)
    if food_required != "All":
        if str(row.get("food","")).lower() == food_required.lower():
            score += 10
            reasons.append("Food match")

    # Crowd (10)
    if crowd != "All":
        if str(row.get("crowd","")).lower() == crowd.lower():
            score += 10
            reasons.append("Preferred crowd match")

    # Room Type (5)
    if room_type != "All":
        if str(row.get("room_type","")).lower() == room_type.lower():
            score += 5
            reasons.append("Room type match")

    return score, reasons, drawbacks

# =========================================================
# 🔍 MATCH ENGINE
# =========================================================
if st.button("🔍 Find Best PGs"):

    if name.strip()=="" or phone.strip()=="":
        st.error("Enter name & phone ❌")
        st.stop()

    filtered_df = hard_filter(room_df)

    if filtered_df.empty:
        st.error("No PGs found ❌")
        st.stop()

    results = filtered_df.apply(lambda row: calculate_score(row), axis=1)

    filtered_df["score"] = [r[0] for r in results]
    filtered_df["reasons"] = [r[1] for r in results]
    filtered_df["drawbacks"] = [r[2] for r in results]

    top3 = filtered_df.sort_values(by="score", ascending=False).head(3)

    st.subheader("🏆 Top Matches For You")

    for i, row in top3.iterrows():

        match_percent = min(100, int(row["score"]))

        st.markdown(f"## 🏠 {row.get('pg_name','PG')} — {match_percent}% Match ✅")

        st.markdown("### Why this match?")
        for r in row["reasons"]:
            st.write(f"- {r}")

        st.markdown("### Why choose this PG?")
        st.write("- Good overall balance")
        st.write("- Matches most of your needs")

        if row["drawbacks"]:
            st.markdown("### Things to consider:")
            for d in row["drawbacks"]:
                st.write(f"- {d}")

        st.markdown(f"""
💰 Price: ₹{row['price']}  
📍 Location: {row.get('location','N/A')}  
👤 Gender: {row.get('gender','N/A')}  
👥 Sharing: {row['sharing']}  
🛏 Beds: {row['available_beds']}
""")

        if row["available_beds"] > 0:

            if st.button(f"Book {row.get('pg_name','PG')}", key=f"book_{i}"):

                new_beds = row["available_beds"] - 1

                new_json = {
                    "type": f"{row['sharing']} Sharing",
                    "price": row["price"],
                    "deposit": 2000,
                    "total_beds": row["total_beds"],
                    "available_beds": new_beds
                }

                room_sheet.update(
                    f"A{i+2}",
                    [[json.dumps([new_json])]]
                )

                booking_sheet.append_row([
                    name,
                    phone,
                    row.get("pg_name","PG"),
                    row["sharing"],
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                st.success("✅ Booking Confirmed")
                st.cache_data.clear()
                st.rerun()

        else:
            st.error("❌ Full")

        st.divider()

# =========================================================
# 📜 BOOKINGS
# =========================================================
st.subheader("📜 Booking History")

if not booking_df.empty:
    st.dataframe(booking_df)
else:
    st.info("No bookings yet")