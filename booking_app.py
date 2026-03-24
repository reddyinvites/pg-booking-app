import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import urllib.parse

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

room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
booking_sheet = client.open_by_key(SHEET_ID).worksheet("Bookings")

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

# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name", key="name")
phone = st.text_input("Phone Number", key="phone")

# -------- LOAD DATA --------
room_data = room_sheet.get_all_records()
df = pd.DataFrame(room_data)

booking_data = booking_sheet.get_all_records()
booking_df = pd.DataFrame(booking_data)

# -------- FIND USER BOOKING --------
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

sharing_filter = st.selectbox("Sharing", ["All", 1, 2, 3, 4, 5, 6])

filtered = df[df["pg_name"] == selected_pg]

if sharing_filter != "All":
    filtered = filtered[filtered["sharing"] == sharing_filter]

# -------- WHATSAPP FUNCTION --------
def send_whatsapp_link(user_name, phone, pg, room_no):
    message = f"""
New PG Booking

Name: {user_name}
Phone: {phone}
PG: {pg}
Room: {room_no}
"""
    encoded_msg = urllib.parse.quote(message)
    owner_number = "919618557269"  # 👉 change to owner number
    return f"https://wa.me/{owner_number}?text={encoded_msg}"

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
                        st.error("❌ Room just got filled")
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

                    # 📲 WhatsApp button
                    wa_link = send_whatsapp_link(user_name, phone, pg, room_no)
                    st.markdown(f"📲 [Send WhatsApp to Owner]({wa_link})")

                    st.session_state.clear_form = True

                except Exception as e:
                    st.error(f"❌ Error: {e}")

        else:
            st.warning("🚫 Booking disabled (Already booked)")

    else:
        st.error("❌ Full")

# -------- HISTORY --------
st.markdown("---")
st.subheader("📜 Booking History")

if not booking_df.empty:

    for i, row in booking_df.iterrows():

        st.markdown(f"""
👤 {row['user_name']}  
📞 {row['phone']}  
🏠 {row['pg_name']}  
🏢 Room: {row['room_no']}  
👥 Sharing: {row['sharing']}  
🕒 {row['booked_at']}
""")

        if st.button(f"❌ Cancel Booking {i}", key=f"cancel_{i}"):

            try:
                for idx, r in df.iterrows():

                    if (
                        str(r["pg_name"]) == str(row["pg_name"]) and
                        str(r["room_no"]) == str(row["room_no"])
                    ):
                        new_beds = int(r["available_beds"]) + 1
                        sheet_row = idx + 2
                        room_sheet.update(f"E{sheet_row}", [[new_beds]])
                        break

                booking_sheet.delete_rows(i + 2)

                st.success("✅ Booking Cancelled")

            except Exception as e:
                st.error(f"❌ Error: {e}")

        st.divider()

else:
    st.info("No bookings yet")