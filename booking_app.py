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

    def get_sharing(x):
        try:
            return int(str(x.get("type", "0")).split()[0])
        except:
            return 0

    room_df["sharing"] = room_df["parsed"].apply(get_sharing)
    room_df["price"] = room_df["parsed"].apply(lambda x: int(x.get("price", 0)))
    room_df["available_beds"] = room_df["parsed"].apply(lambda x: int(x.get("available_beds", 0)))
    room_df["total_beds"] = room_df["parsed"].apply(lambda x: int(x.get("total_beds", 0)))

# =========================================================
# 👤 USER DETAILS
# =========================================================
st.subheader("👤 Your Details")

name = st.text_input("Name")
phone = st.text_input("Phone")

# =========================================================
# 🎯 USER PREFERENCES
# =========================================================
st.subheader("🎯 Your Preferences")

budget = st.number_input("Budget (₹)", value=6000)
location = st.text_input("Preferred Location")
sharing_pref = st.selectbox("Sharing", [1, 2, 3, 4])
food_required = st.selectbox("Food Required", ["Yes", "No"])
cleanliness = st.selectbox("Cleanliness", ["Low", "Medium", "High"])

# =========================================================
# 🔥 MATCH ENGINE
# =========================================================
def calculate_score(row):
    score = 0

    # Budget (30%)
    if row["price"] <= budget:
        score += 30
    else:
        diff = abs(row["price"] - budget)
        score += max(0, 30 - diff/100)

    # Location (25%)
    if location.lower() in str(row.get("location", "")).lower():
        score += 25

    # Sharing (10%)
    if row["sharing"] == sharing_pref:
        score += 10

    # Beds (20%)
    if row["available_beds"] > 0:
        score += 20

    # Cleanliness (15%)
    if cleanliness == "High":
        score += 15
    elif cleanliness == "Medium":
        score += 10
    else:
        score += 5

    return score

# =========================================================
# 🔍 FIND PGs
# =========================================================
if st.button("🔍 Find Best PGs"):

    if room_df.empty:
        st.error("No PG data available")
        st.stop()

    room_df["score"] = room_df.apply(calculate_score, axis=1)

    top = room_df.sort_values(by="score", ascending=False).head(3)

    st.subheader("🏆 Top Matches")

    for i, row in top.iterrows():

        st.markdown(f"""
### 🏠 {row.get('pg_name','PG')} — {int(row['score'])}% Match

💰 Price: ₹{row['price']}  
📍 Location: {row.get('location','N/A')}  
👥 Sharing: {row['sharing']}  
🛏 Beds Available: {row['available_beds']}
""")

        st.info("Why this match?")
        st.write("✔ Budget compatible")
        st.write("✔ Location relevance")
        st.write("✔ Beds available")

        # ---------------- BOOK ----------------
        if row["available_beds"] > 0:

            if st.button(f"Book {row.get('pg_name','PG')}", key=i):

                if name.strip()=="" or phone.strip()=="":
                    st.error("Enter name & phone")
                    st.stop()

                new_beds = row["available_beds"] - 1

                new_json = {
                    "type": f"{row['sharing']} Sharing",
                    "price": row["price"],
                    "deposit": 2000,
                    "total_beds": row["total_beds"],
                    "available_beds": new_beds
                }

                # 🔥 UPDATE JSON BACK
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