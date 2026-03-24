import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="PG Booking", layout="centered")

st.title("🏠 PG Booking")
st.caption("⚡ Fast mode (No API limits)")

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

room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
booking_sheet = client.open_by_key(SHEET_ID).worksheet("Bookings")
owner_sheet = client.open_by_key(SHEET_ID).worksheet("Owners")

# -------- SESSION CACHE (MAIN FIX) --------
if "data_loaded" not in st.session_state:

    try:
        room_data = room_sheet.get_all_records()
        booking_data = booking_sheet.get_all_records()
        owner_data = owner_sheet.get_all_records()

        st.session_state.room_data = room_data
        st.session_state.booking_data = booking_data
        st.session_state.owner_data = owner_data

        st.session_state.data_loaded = True

    except Exception as e:
        st.error("❌ API limit reached. Wait 1 minute and refresh.")
        st.stop()

room_data = st.session_state.room_data
booking_data = st.session_state.booking_data
owner_data = st.session_state.owner_data

df = pd.DataFrame(room_data)
booking_df = pd.DataFrame(booking_data)
owner_df = pd.DataFrame(owner_data)

# -------- REFRESH BUTTON --------
if st.button("🔄 Refresh Data"):
    st.session_state.data_loaded = False
    st.rerun()

# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name")
phone = st.text_input("Phone Number")

# -------- CHECK EXISTING BOOKING --------
user_booking = None

if not booking_df.empty and phone:
    user_rows = booking_df[booking_df["phone"].astype(str) == phone]
    if not user_rows.empty:
        user_booking = user_rows.iloc[0]

if user_booking is not None:
    st.warning("⚠️ You already booked. Cancel to rebook.")

# -------- FILTER --------
st.subheader("🔍 Filter")

pg_list = df["pg_name"].dropna().unique()
selected_pg = st.selectbox("Select PG", pg_list)

filtered = df[df["pg_name"] == selected_pg]

# -------- WHATSAPP FUNCTION --------
def send_whatsapp_link(user_name, phone, pg, room_no, owner_phone):

    message = f"""New PG Booking

Name: {user_name}
Phone: {phone}
PG: {pg}
Room: {room_no}"""

    encoded = urllib.parse.quote(message)

    return f"https://wa.me/{owner_phone}?text={encoded}"

# -------- ROOMS --------
st.subheader("🛏 Available Rooms")

for i, row in filtered.iterrows():

    room_no = str(row["room_no"])
    sharing = int(row["sharing"])
    floor = int(row["floor"])
    beds = int(row["available_beds"])
    pg = row["pg_name"]

    st.markdown(f"""
### 🏠 {pg}
🏢 Room: {room_no}  
👥 Sharing: {sharing}  
🛏 Beds: {beds}  
🏢 Floor: {floor}
""")

    if beds > 0:

        if user_booking is None:

            if st.button(f"Book Room {room_no}", key=f"book_{i}"):

                if user_name.strip() == "" or phone.strip() == "":
                    st.error("Enter name & phone")
                    st.stop()

                owner_row = owner_df[owner_df["pg_name"] == pg]

                if owner_row.empty:
                    st.error("Owner not found")
                    st.stop()

                owner_phone = str(owner_row.iloc[0]["phone"])

                new_beds = beds - 1
                room_sheet.update(f"E{i+2}", [[new_beds]])

                booking_sheet.append_row([
                    user_name,
                    phone,
                    pg,
                    room_no,
                    sharing,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                st.success("✅ Booking Confirmed")

                wa_link = send_whatsapp_link(
                    user_name, phone, pg, room_no, owner_phone
                )

                st.link_button("📲 WhatsApp Owner", wa_link)

                st.session_state.data_loaded = False
                st.rerun()

        else:
            st.warning("🚫 Booking disabled")

    else:
        st.error("❌ Full")

# -------- BOOKING HISTORY --------
st.subheader("📜 Booking History")

history_df = pd.DataFrame(booking_data)

if not history_df.empty:

    latest_index = history_df.index[-1]

    for i, row in history_df.iterrows():

        st.markdown(f"""
👤 {row['user_name']}  
📞 {row['phone']}  
🏠 {row['pg_name']}  
🏢 Room: {row['room_no']}  
👥 Sharing: {row['sharing']}  
🕒 {row['booked_at']}
""")

        col1, col2 = st.columns(2)

        # -------- CANCEL --------
        with col1:
            if st.button("❌ Cancel", key=f"cancel_{i}"):

                room_df = pd.DataFrame(room_data)

                match = room_df[
                    (room_df["pg_name"] == row["pg_name"]) &
                    (room_df["room_no"] == row["room_no"])
                ]

                if not match.empty:
                    idx = match.index[0]
                    beds = int(match.iloc[0]["available_beds"]) + 1
                    room_sheet.update(f"E{idx+2}", [[beds]])

                booking_sheet.delete_rows(i + 2)

                st.success("Cancelled")

                st.session_state.data_loaded = False
                st.rerun()

        # -------- WHATSAPP --------
        with col2:

            if i == latest_index:

                owner_row = owner_df[owner_df["pg_name"] == row["pg_name"]]

                if not owner_row.empty:
                    owner_phone = str(owner_row.iloc[0]["phone"])

                    message = f"""New Booking

Name: {row['user_name']}
Phone: {row['phone']}
PG: {row['pg_name']}
Room: {row['room_no']}
"""

                    encoded = urllib.parse.quote(message)

                    wa_link = f"https://wa.me/{owner_phone}?text={encoded}"

                    st.link_button("📲 WhatsApp", wa_link)

                else:
                    st.button("📲 WhatsApp", disabled=True, key=f"wa_disabled_{i}")

            else:
                st.button("📲 WhatsApp", disabled=True, key=f"wa_disabled_{i}")

        st.divider()

else:
    st.info("No bookings yet")