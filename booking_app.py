import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="PG Booking", layout="centered")
st.title("🏠 PG Booking")

# -------- SESSION --------
if "name" not in st.session_state:
    st.session_state.name = ""

if "phone" not in st.session_state:
    st.session_state.phone = ""

if "clear_form" not in st.session_state:
    st.session_state.clear_form = False

if st.session_state.clear_form:
    st.session_state.name = ""
    st.session_state.phone = ""
    st.session_state.clear_form = False

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

# -------- CACHE (FIX API ERROR) --------
@st.cache_data(ttl=30)
def load_data():
    room_df = pd.DataFrame(room_sheet.get_all_records())
    booking_df = pd.DataFrame(booking_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())
    return room_df, booking_df, owner_df

room_df, booking_df, owner_df = load_data()

# -------- REFRESH --------
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name", key="name")
phone = st.text_input("Phone Number", key="phone")

# -------- FILTER --------
st.subheader("🔍 Select PG")

pg_list = room_df["pg_name"].dropna().unique()
selected_pg = st.selectbox("Select PG", pg_list)

filtered = room_df[room_df["pg_name"] == selected_pg]

# -------- ROOMS --------
st.subheader("🛏 Available Rooms")

for i, row in filtered.iterrows():

    room_no = str(row["room_no"])
    sharing = row["sharing"]
    beds = int(row["available_beds"])
    floor = row["floor"]
    pg = row["pg_name"]

    st.markdown(f"""
### 🏠 {pg}
🏢 Room: {room_no}  
👥 Sharing: {sharing}  
🛏 Beds: {beds}  
🏢 Floor: {floor}
""")

    if beds > 0:
        if st.button(f"Book Room {room_no}", key=f"book_{pg}_{room_no}"):

            if user_name.strip() == "" or phone.strip() == "":
                st.error("Enter name & phone")
                st.stop()

            match = room_df[
                (room_df["pg_name"] == pg) &
                (room_df["room_no"].astype(str) == room_no)
            ]

            if not match.empty:
                idx = match.index[0]

                # update beds
                room_sheet.update(f"E{idx+2}", [[beds - 1]])

                # save booking
                booking_sheet.append_row([
                    user_name,
                    phone,
                    pg,
                    room_no,
                    sharing,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                st.success("✅ Booking Confirmed")

                st.session_state.clear_form = True
                st.cache_data.clear()
                st.rerun()
    else:
        st.error("❌ Full")

    st.divider()

# -------- BOOKING HISTORY --------
st.subheader("📜 Booking History")

history_df = booking_df

if not history_df.empty:

    for i, row in history_df.iterrows():

        st.markdown(f"""
👤 {row['name']}  
📞 {row['phone']}  
🏠 {row['pg_name']}  
🏢 Room: {row['room_no']}  
👥 Sharing: {row['sharing']}  
🕒 {row['booked