import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Booking", layout="centered")
st.title("🏠 PG Booking")

# ================= GOOGLE SHEETS =================

@st.cache_resource
def connect():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp"], scope
    )

    return gspread.authorize(creds)


@st.cache_data(ttl=10)
def load_data():
    try:
        client = connect()

        SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

        room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
        booking_sheet = client.open_by_key(SHEET_ID).worksheet("Bookings")

        room_df = pd.DataFrame(room_sheet.get_all_records())
        booking_df = pd.DataFrame(booking_sheet.get_all_records())

        # 🔥 FIX COLUMN ISSUES
        room_df.columns = room_df.columns.str.strip().str.lower()
        booking_df.columns = booking_df.columns.str.strip().str.lower()

        return room_sheet, booking_sheet, room_df, booking_df

    except:
        st.error("❌ Sheet connection error")
        st.stop()


room_sheet, booking_sheet, room_df, booking_df = load_data()

# ================= SESSION =================

if "name" not in st.session_state:
    st.session_state.name = ""

if "phone" not in st.session_state:
    st.session_state.phone = ""

# ================= USER DETAILS =================

st.subheader("👤 Your Details")

name = st.text_input("Your Name", key="name")
phone = st.text_input("Phone Number", key="phone")

# ================= FILTER =================

st.subheader("🔍 Filter")

pg_list = room_df["pg_name"].unique() if not room_df.empty else []
selected_pg = st.selectbox("Select PG", pg_list)

# ================= AVAILABLE ROOMS =================

st.subheader("🛏 Available Rooms")

if not room_df.empty:

    filtered = room_df[room_df["pg_name"] == selected_pg]

    for i, row in filtered.iterrows():

        st.markdown("---")

        st.write(f"🏠 {row['pg_name']}")
        st.write(f"🛏 Room: {row['room_no']}")
        st.write(f"👥 Sharing: {row['sharing']}")
        st.write(f"🛌 Beds: {row['available_beds']}")
        st.write(f"🏢 Floor: {row['floor']}")

        if int(row["available_beds"]) > 0:

            if st.button(f"Book Room {row['room_no']}", key=f"book_{i}"):

                if name and phone:

                    booking_sheet.append_row([
                        name,   # this goes into user_name column
                        phone,
                        row["pg_name"],
                        row["room_no"],
                        row["sharing"],
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    ])

                    st.success("✅ Room Booked")

                    # CLEAR FORM
                    st.session_state.name = ""
                    st.session_state.phone = ""

                    st.cache_data.clear()
                    st.rerun()

                else:
                    st.error("Enter Name & Phone")

        else:
            st.error("❌ Full")

# ================= BOOKING HISTORY =================

st.subheader("📜 Booking History")

if not booking_df.empty:

    for i, row in booking_df.iterrows():

        st.markdown("---")

        col1, col2 = st.columns([3,1])

        # LEFT SIDE
        with col1:
            st.write(f"👤 {row.get('user_name','-')}")
            st.write(f"📞 {row.get('phone','-')}")
            st.write(f"🏠 {row.get('pg_name','-')}")
            st.write(f"🛏 Room: {row.get('room_no','-')}")
            st.write(f"👥 Sharing: {row.get('sharing','-')}")

        # RIGHT SIDE BUTTONS
        with col2:

            if st.button("📲 WhatsApp", key=f"wa_{i}"):
                wa_url = f"https://wa.me/{row.get('phone','')}"
                st.markdown(f"[Open WhatsApp]({wa_url})")

            if st.button("❌ Cancel", key=f"cancel_{i}"):

                booking_sheet.delete_rows(i + 2)

                st.success("Cancelled")

                st.cache_data.clear()
                st.rerun()

else:
    st.info("No bookings yet")