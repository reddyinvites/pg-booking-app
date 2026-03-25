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

# -------- RESET FORM --------
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

# -------- LOAD DATA --------
room_df = pd.DataFrame(room_sheet.get_all_records())
booking_df = pd.DataFrame(booking_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name", key="name")
phone = st.text_input("Phone Number", key="phone")

# -------- FILTER --------
st.subheader("🔍 Filter")

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

                # trigger clear form
                st.session_state.clear_form = True

                st.rerun()
    else:
        st.error("❌ Full")

# -------- BOOKING HISTORY --------
st.subheader("📜 Booking History")

history = booking_sheet.get_all_records()
history_df = pd.DataFrame(history)

if not history_df.empty:

    for i, row in history_df.iterrows():

        # DETAILS
        st.markdown(f"""
👤 {row['user_name']}  
📞 {row['phone']}  
🏠 {row['pg_name']}  
🏢 Room: {row['room_no']}  
👥 Sharing: {row['sharing']}  
🕒 {row['booked_at']}
""")

        col1, col2 = st.columns(2)

        # 📲 WHATSAPP
        with col1:

            message = f"""
New Booking

Name: {row['user_name']}
Phone: {row['phone']}
PG: {row['pg_name']}
Room: {row['room_no']}
Sharing: {row['sharing']}
"""

            encoded = urllib.parse.quote(message)

            owner_row = owner_df[
                owner_df["pg_name"].astype(str).str.strip() ==
                str(row["pg_name"]).strip()
            ]

            if not owner_row.empty:
                owner_phone = str(owner_row.iloc[0]["phone"])
                wa_link = f"https://wa.me/{owner_phone}?text={encoded}"
                st.link_button("📲 WhatsApp", wa_link)
            else:
                st.button("📲 WhatsApp", disabled=True)

        # ❌ CANCEL
        with col2:
            if st.button("❌ Cancel", key=f"cancel_{i}_{row['room_no']}"):

                room_data = room_sheet.get_all_records()
                room_df2 = pd.DataFrame(room_data)

                match = room_df2[
                    (room_df2["pg_name"].astype(str) == str(row["pg_name"])) &
                    (room_df2["room_no"].astype(str) == str(row["room_no"]))
                ]

                if not match.empty:
                    idx = match.index[0]
                    beds = int(match.iloc[0]["available_beds"]) + 1
                    room_sheet.update(f"E{idx+2}", [[beds]])

                booking_sheet.delete_rows(i + 2)

                st.success("Cancelled")
                st.rerun()

        st.divider()

else:
    st.info("No bookings yet")