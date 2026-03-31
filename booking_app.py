import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import urllib.parse
import ast

st.set_page_config(page_title="PG Booking", layout="centered")
st.title("🏠 PG Booking")

# -------- GOOGLE SHEETS --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

sheet = client.open_by_key(SHEET_ID)
room_sheet = sheet.worksheet("Sheet1")
booking_sheet = sheet.worksheet("Bookings")
owner_sheet = sheet.worksheet("Owners")

# -------- LOAD DATA --------
@st.cache_data(ttl=20)
def load_data():
    rooms = pd.DataFrame(room_sheet.get_all_records())
    bookings = pd.DataFrame(booking_sheet.get_all_records())
    owners = pd.DataFrame(owner_sheet.get_all_records())
    return rooms, bookings, owners

room_df, booking_df, owner_df = load_data()

# -------- PARSE JSON --------
def parse_sharing(row):
    try:
        return ast.literal_eval(row["sharing_json"])
    except:
        return []

# -------- REFRESH --------
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# =========================================================
# 👤 USER DETAILS (STEP 1)
# =========================================================
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name")
phone = st.text_input("Phone Number")

# =========================================================
# 🧾 USER NEEDS (STEP 2)
# =========================================================
st.subheader("🧾 Your Requirements")

budget = st.number_input("Budget ₹", value=6000)
location = st.text_input("Preferred Location")
sharing_pref = st.selectbox("Sharing", [1,2,3,4])
food_pref = st.selectbox("Food", ["Any","Veg","Non-Veg"])

# =========================================================
# 🤖 MATCH ENGINE (STEP 3)
# =========================================================
if st.button("🔍 Find Best PG"):

    if user_name.strip() == "" or phone.strip() == "":
        st.error("Enter Name & Phone ❌")
        st.stop()

    results = []

    for i, row in room_df.iterrows():

        sharing_data = parse_sharing(row)

        for s in sharing_data:

            if int(s["available_beds"]) <= 0:
                continue

            if int(s["type"]) != sharing_pref:
                continue

            score = 0

            # Budget
            diff = abs(int(s["price"]) - budget)
            if diff <= 500:
                score += 30
            elif diff <= 1000:
                score += 20

            # Location
            if location.lower() in str(row["location"]).lower():
                score += 25

            # Food
            if food_pref != "Any":
                if food_pref.lower() in str(row["food_type"]).lower():
                    score += 15

            # Availability
            score += int(s["available_beds"]) * 5

            results.append((score, row, s))

    results = sorted(results, key=lambda x: x[0], reverse=True)[:3]

    st.subheader("🏆 Best Matches")

    for score, row, s in results:

        st.markdown(f"""
### 🏠 {row['pg_name']} — {score}% Match

📍 {row['location']}  
💰 ₹{s['price']}  
👥 {s['type']} Sharing  
🛏 {s['available_beds']} Beds  

🍛 {row['food_type']}
📞 {row['owner_number']}
""")

        # BOOK BUTTON FROM MATCH
        if st.button(f"Book {row['pg_name']} Room", key=f"{row['pg_name']}_{s['type']}"):

            # reduce beds
            new_beds = int(s["available_beds"]) - 1

            # update full JSON
            sharing_data_updated = parse_sharing(row)

            for item in sharing_data_updated:
                if item["type"] == s["type"]:
                    item["available_beds"] = new_beds

            room_sheet.update(
                f"E{i+2}",
                [[str(sharing_data_updated)]]
            )

            # save booking
            booking_sheet.append_row([
                user_name,
                phone,
                row["pg_name"],
                s["type"],
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("✅ Booking Confirmed")
            st.cache_data.clear()
            st.rerun()

        st.divider()

# =========================================================
# 📜 BOOKING HISTORY (STEP 4)
# =========================================================
st.subheader("📜 Booking History")

if not booking_df.empty:

    for i, row in booking_df.iterrows():

        st.markdown(f"""
👤 {row['user_name']}  
📞 {row['phone']}  
🏠 {row['pg_name']}  
👥 Sharing: {row['sharing']}  
🕒 {row['booked_at']}
""")

        st.divider()

else:
    st.info("No bookings yet")