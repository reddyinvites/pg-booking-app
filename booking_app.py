import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="PG Booking")

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

sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Sheet1")


# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)

if df.empty:
    st.warning("No rooms available")
    st.stop()

# -------- FILTERS --------
st.subheader("🔍 Filter")

pg_list = df["pg_name"].unique()
selected_pg = st.selectbox("Select PG", pg_list)

sharing_filter = st.selectbox("Sharing", ["All", 1,2,3,4,5,6])

# -------- FILTER LOGIC --------
filtered = df[df["pg_name"] == selected_pg]

if sharing_filter != "All":
    filtered = filtered[filtered["sharing"] == sharing_filter]

# -------- SHOW ROOMS --------
st.subheader("🛏 Available Rooms")

if filtered.empty:
    st.info("No rooms available")
else:
    for i, row in filtered.iterrows():

        st.write(f"""
        🏢 Room: {row['room_no']}  
        🧍 Sharing: {row['sharing']}  
        🛏 Available Beds: {row['available_beds']}  
        🏢 Floor: {row['floor']}
        """)

        if row["available_beds"] > 0:

            if st.button(f"Book Room {row['room_no']}", key=i):

                new_beds = row["available_beds"] - 1

                # UPDATE SHEET
                sheet.update(f"E{i+2}", new_beds)

                st.success("✅ Booking Successful")

                st.rerun()
        else:
            st.error("❌ Full")
