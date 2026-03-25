import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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

try:
    sheet = client.open_by_key(SHEET_ID)
    room_sheet = sheet.worksheet("Sheet1")
    booking_sheet = sheet.worksheet("Bookings")
    st.success("✅ Connected to Google Sheet")
except Exception as e:
    st.error(f"❌ ERROR: {e}")
    st.stop()

# -------- CACHE --------
@st.cache_data(ttl=30)
def load_data():
    room_df = pd.DataFrame(room_sheet.get_all_records())
    booking_df = pd.DataFrame(booking_sheet.get_all_records())
    return room_df, booking_df

room_df, booking_df = load_data()

# -------- REFRESH --------
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# ================= ROOMS =================
st.header("🏠 Available Rooms")

if not room_df.empty:

    for idx, row in room_df.iterrows():

        st.markdown(f"### 🏠 {row['pg_name']}")
        st.write(f"🛏 Room: {row['room_no']}")
        st.write(f"👥 Sharing: {row['sharing']}")
        st.write(f"🛌 Beds Available: {row['available_beds']}")
        st.write(f"🏢 Floor: {row['floor']}")

        if row["available_beds"] > 0:

            if st.button(f"Book Room {row['room_no']}", key=f"book_{idx}"):

                # ✅ Add booking
                booking_sheet.append_row([
                    "user",   # replace with login user if needed
                    "9999999999",
                    row["pg_name"],
                    row["room_no"],
                    row["sharing"],
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                # ✅ Reduce beds
                new_beds = int(row["available_beds"]) - 1
                room_sheet.update_cell(idx + 2, 5, new_beds)

                st.success("✅ Room Booked")
                st.cache_data.clear()
                st.rerun()

        st.divider()

else:
    st.info("No rooms available")

# ================= BOOKING HISTORY =================
st.header("📜 Booking History")

if not booking_df.empty:

    for idx in range(len(booking_df)):

        row = booking_df.iloc[idx]

        col1, col2 = st.columns([4,1])

        with col1:
            st.write(f"👤 {row['name']}")
            st.write(f"📞 {row['phone']}")
            st.write(f"🏠 {row['pg_name']}")
            st.write(f"🛏 Room: {row['room_no']}")
            st.write(f"👥 Sharing: {row['sharing']}")

        with col2:
            if st.button("❌ Cancel", key=f"cancel_{idx}"):

                try:
                    # ✅ Restore bed
                    room_rows = room_sheet.get_all_records()

                    for r_idx, r in enumerate(room_rows):
                        if str(r["room_no"]) == str(row["room_no"]):
                            new_beds = int(r["available_beds"]) + 1
                            room_sheet.update_cell(r_idx + 2, 5, new_beds)
                            break

                    # ✅ Delete booking (FIXED)
                    booking_sheet.delete_rows(idx + 2)

                    st.success("Booking Cancelled")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()

else:
    st.info("No bookings yet")