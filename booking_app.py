import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="PG Booking", layout="centered")

st.title("🏠 PG Booking")

import time

st.caption("🔄 Auto refreshing every 5 seconds...")

# -------- AUTO REFRESH --------
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# refresh every 5 seconds
if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()

# -------- SESSION --------
if "name" not in st.session_state:
    st.session_state.name = ""

if "phone" not in st.session_state:
    st.session_state.phone = ""

if "clear_form" not in st.session_state:
    st.session_state.clear_form = False

if "show_whatsapp" not in st.session_state:
    st.session_state.show_whatsapp = False

if "wa_link" not in st.session_state:
    st.session_state.wa_link = ""

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

# ✅ CORRECT SHEET NAMES
room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
booking_sheet = client.open_by_key(SHEET_ID).worksheet("Bookings")

# -------- LOAD DATA --------
try:
    room_data = room_sheet.get_all_records()
    df = pd.DataFrame(room_data)
except:
    df = pd.DataFrame()

try:
    booking_data = booking_sheet.get_all_records()
    booking_df = pd.DataFrame(booking_data) if booking_data else pd.DataFrame()
except:
    booking_df = pd.DataFrame()

# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name", key="name")
phone = st.text_input("Phone Number", key="phone")

# -------- CHECK USER BOOKING --------
user_booking = None

if not booking_df.empty and phone:
    user_rows = booking_df[booking_df["phone"].astype(str) == phone]
    if not user_rows.empty:
        user_booking = user_rows.iloc[0]

if user_booking is not None:
    st.warning("⚠️ You already booked. Cancel to rebook.")

# -------- FILTER --------
st.subheader("🔍 Filter")

pg_list = df["pg_name"].dropna().unique() if not df.empty else []
selected_pg = st.selectbox("Select PG", pg_list)

sharing_filter = st.selectbox("Sharing", ["All", 1, 2, 3, 4, 5, 6])

filtered = df[df["pg_name"] == selected_pg] if not df.empty else pd.DataFrame()

if sharing_filter != "All" and not filtered.empty:
    filtered = filtered[filtered["sharing"] == sharing_filter]

# -------- WHATSAPP FUNCTION --------
def send_whatsapp_link(user_name, phone, pg, room_no):
    message = f"""New PG Booking

Name: {user_name}
Phone: {phone}
PG: {pg}
Room: {room_no}"""

    encoded = urllib.parse.quote(message)
    owner_number = "919618557269"  # ✅ your number

    return f"https://api.whatsapp.com/send?phone={owner_number}&text={encoded}"

# -------- ROOMS --------
st.subheader("🛏 Available Rooms")

if filtered.empty:
    st.info("No rooms available")

else:
    for i, row in filtered.iterrows():

        room_no = str(row.get("room_no", ""))
        sharing = int(row.get("sharing", 0))
        floor = int(row.get("floor", 0))
        beds = int(row.get("available_beds", 0))
        pg = row.get("pg_name", "")

        st.markdown(f"""
### 🏠 {pg}
🏢 Room: {room_no}  
👥 Sharing: {sharing}  
🛏 Available Beds: {beds}  
🏢 Floor: {floor}
""")

        if beds > 0:

            if user_booking is None:

                if st.button(f"Book Room {room_no}", key=f"book_{i}"):

                    if user_name.strip() == "" or phone.strip() == "":
                        st.error("Enter name & phone")
                        st.stop()

                    if not phone.isdigit() or len(phone) != 10:
                        st.error("Invalid phone")
                        st.stop()

                    try:
                        latest_data = room_sheet.get_all_records()
                        latest_df = pd.DataFrame(latest_data)

                        latest_row = latest_df.iloc[i]
                        current_beds = int(latest_row["available_beds"])

                        if current_beds <= 0:
                            st.error("❌ Room just filled")
                            st.stop()

                        new_beds = current_beds - 1
                        row_index = i + 2

                        room_sheet.update(f"E{row_index}", [[new_beds]])

                        booking_sheet.append_row([
                            user_name,
                            phone,
                            pg,
                            room_no,
                            sharing,
                            datetime.now().strftime("%Y-%m-%d %H:%M")
                        ])

                        st.success("✅ Booking Confirmed 🎉")

                        # ✅ WhatsApp trigger
                        st.session_state.wa_link = send_whatsapp_link(user_name, phone, pg, room_no)
                        st.session_state.show_whatsapp = True
                        st.session_state.clear_form = True

                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            else:
                st.warning("🚫 Booking disabled")

        else:
            st.error("❌ Full")

st.subheader("📜 Booking History")

history = booking_sheet.get_all_records()
history_df = pd.DataFrame(history)

if not history_df.empty:

    # 👉 latest booking index
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

        # ======================
        # ❌ CANCEL BUTTON
        # ======================
        with col1:
            if st.button("❌ Cancel", key=f"cancel_{i}"):

                try:
                    room_data = room_sheet.get_all_records()
                    room_df = pd.DataFrame(room_data)

                    match = room_df[
                        (room_df["pg_name"].astype(str) == str(row["pg_name"])) &
                        (room_df["room_no"].astype(str) == str(row["room_no"]))
                    ]

                    if not match.empty:
                        idx = match.index[0]
                        current_beds = int(match.iloc[0]["available_beds"])
                        new_beds = current_beds + 1
                        sheet_row = idx + 2

                        room_sheet.update(f"E{sheet_row}", [[new_beds]])

                    # delete booking row
                    booking_sheet.delete_rows(i + 2)

                    st.success("✅ Booking Cancelled")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")

        # ======================
        # 📲 WHATSAPP BUTTON
        # ======================
        with col2:

            if i == latest_index:
                import urllib.parse

                message = f"""
New Booking Alert!

Name: {row['user_name']}
Phone: {row['phone']}
PG: {row['pg_name']}
Room: {row['room_no']}
Sharing: {row['sharing']}
"""

                encoded = urllib.parse.quote(message)

                owner_number = "919618557269"  # 👈 your number

                wa_link = f"https://wa.me/{owner_number}?text={encoded}"

                st.link_button("📲 WhatsApp", wa_link)

            else:
                st.button("📲 WhatsApp", disabled=True)

        st.divider()

else:
    st.info("No bookings yet")