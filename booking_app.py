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

sheet = client.open_by_key(SHEET_ID)
room_sheet = sheet.worksheet("Sheet1")
booking_sheet = sheet.worksheet("Bookings")
owner_sheet = sheet.worksheet("Owners")

# -------- CACHE --------
@st.cache_data(ttl=20)
def load_data():
    rooms = pd.DataFrame(room_sheet.get_all_records())
    bookings = pd.DataFrame(booking_sheet.get_all_records())
    owners = pd.DataFrame(owner_sheet.get_all_records())
    return rooms, bookings, owners

room_df, booking_df, owner_df = load_data()

# -------- REFRESH --------
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# =========================================================
# 👤 USER DETAILS
# =========================================================
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name")
phone = st.text_input("Phone Number")

# =========================================================
# 🔍 FILTER (AFTER DETAILS ✅)
# =========================================================
st.subheader("🔍 Filter")

pg_list = room_df["pg_name"].dropna().unique()
selected_pg = st.selectbox("Select PG", pg_list)

sharing_filter = st.selectbox("Sharing", ["All", 1, 2, 3, 4, 5])

filtered = room_df[room_df["pg_name"] == selected_pg]

if sharing_filter != "All":
    filtered = filtered[filtered["sharing"] == sharing_filter]

# =========================================================
# 🛏 ROOMS LIST (AFTER FILTER ✅)
# =========================================================
st.subheader("🛏 Available Rooms")

for i, row in filtered.iterrows():

    room_no = str(row["room_no"])
    sharing = int(row["sharing"])
    beds = int(row["available_beds"])
    floor = row["floor"]
    pg = row["pg_name"]

    st.markdown(f"""
### 🏠 {pg}
🏢 Room: {room_no}  
👥 Sharing: {sharing}  
🛏 Beds Available: {beds}  
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
                room_sheet.update(f"E{idx+2}", [[beds - 1]])

            booking_sheet.append_row([
                user_name,
                phone,
                pg,
                room_no,
                sharing,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("✅ Booking Confirmed")
            st.cache_data.clear()
            st.rerun()

    else:
        st.error("❌ Full")

    st.divider()

# =========================================================
# 📜 BOOKING HISTORY (LAST ✅)
# =========================================================
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

        col1, col2 = st.columns(2)

        # 📲 WHATSAPP
        with col1:
            owner_row = owner_df[
                owner_df["pg_name"].astype(str).str.strip() ==
                str(row["pg_name"]).strip()
            ]

            if not owner_row.empty:
                owner_phone = str(owner_row.iloc[0]["phone"])

                message = f"""
New Booking

Name: {row['user_name']}
Phone: {row['phone']}
PG: {row['pg_name']}
Room: {row['room_no']}
"""

                link = f"https://wa.me/{owner_phone}?text={urllib.parse.quote(message)}"
                st.link_button("📲 WhatsApp", link)
            else:
                st.button("📲 WhatsApp", disabled=True)

        # ❌ CANCEL (BESIDE WHATSAPP ✅)
        with col2:
            if st.button("❌ Cancel", key=f"cancel_{i}"):

                room_data = room_sheet.get_all_records()
                room_df2 = pd.DataFrame(room_data)

                match = room_df2[
                    (room_df2["pg_name"].astype(str) == str(row["pg_name"])) &
                    (room_df2["room_no"].astype(str) == str(row["room_no"]))
                ]

                if not match.empty:
                    idx = match.index[0]
                    new_beds = int(match.iloc[0]["available_beds"]) + 1
                    room_sheet.update(f"E{idx+2}", [[new_beds]])

                booking_sheet.delete_rows(i + 2)

                st.success("Cancelled")
                st.cache_data.clear()
                st.rerun()

        st.divider()

else:
    st.info("No bookings yet")