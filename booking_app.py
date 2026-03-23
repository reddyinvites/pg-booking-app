import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
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

# MAIN ROOM SHEET
room_sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Sheet1")

# BOOKING SHEET
booking_sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Bookings")


# -------- USER INPUT --------
st.subheader("👤 Your Details")

user_name = st.text_input("Your Name")
phone = st.text_input("Phone Number")

# -------- LOAD DATA --------
data = room_sheet.get_all_records()
df = pd.DataFrame(data)

if df.empty:
    st.warning("No rooms available")
    st.stop()

# CLEAN
df = df[
    (df["room_no"].astype(str).str.strip() != "") &
    (df["sharing"].notna()) &
    (df["floor"].notna())
]

# -------- FILTER --------
st.subheader("🔍 Filter")

pg_list = df["pg_name"].dropna().unique()
selected_pg = st.selectbox("Select PG", pg_list)

sharing_filter = st.selectbox("Sharing", ["All", 1, 2, 3, 4, 5, 6])

filtered = df[df["pg_name"] == selected_pg]

if sharing_filter != "All":
    filtered = filtered[filtered["sharing"] == sharing_filter]

# -------- SHOW ROOMS --------
st.subheader("🛏 Available Rooms")

for i, row in filtered.iterrows():

    room_no = str(row["room_no"]).strip()
    sharing = int(row["sharing"])
    floor = int(row["floor"])
    beds = int(row["available_beds"])
    pg = row["pg_name"]

    if room_no == "":
        continue

    st.markdown(f"""
    ### 🏠 {pg}
    🏢 Room: {room_no}  
    👥 Sharing: {sharing}  
    🛏 Available Beds: {beds}  
    🏢 Floor: {floor}
    """)

    if beds > 0:

        if st.button(f"Book Room {room_no}", key=i):

            # VALIDATION
            if user_name.strip() == "" or phone.strip() == "":
                st.error("⚠️ Enter name & phone")
                st.stop()

            if not phone.isdigit() or len(phone) != 10:
                st.error("⚠️ Invalid phone number")
                st.stop()

            try:
                # 🔁 Reload latest
                latest_data = room_sheet.get_all_records()
                latest_df = pd.DataFrame(latest_data)

                latest_row = latest_df.iloc[i]
                current_beds = int(latest_row["available_beds"])

                if current_beds <= 0:
                    st.error("❌ Already Full")
                    st.stop()

                new_beds = current_beds - 1
                row_index = i + 2

                # UPDATE BEDS
                room_sheet.update(f"E{row_index}", [[new_beds]])

                # SAVE BOOKING HISTORY
                booking_sheet.append_row([
                    user_name,
                    phone,
                    pg,
                    room_no,
                    sharing,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])

                st.success("✅ Booking Confirmed 🎉")
                st.rerun()

            except:
                st.error("❌ Try again")

    else:
        st.error("❌ Full")


# -------- SHOW HISTORY --------
st.subheader("📜 Booking History")

history = booking_sheet.get_all_records()
history_df = pd.DataFrame(history)

if not history_df.empty:
    st.dataframe(history_df, use_container_width=True)
else:
    st.info("No bookings yet")