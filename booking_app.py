import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="PG Booking", layout="centered")

st.title("🏠 PG Booking")

# -------- GOOGLE SHEETS CONNECT --------
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

# -------- CLEAN DATA --------
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

# -------- APPLY FILTER --------
filtered = df[df["pg_name"] == selected_pg]

if sharing_filter != "All":
    filtered = filtered[filtered["sharing"] == sharing_filter]

# -------- SHOW ROOMS --------
st.subheader("🛏 Available Rooms")

if filtered.empty:
    st.info("No rooms available")

else:
    for i, row in filtered.iterrows():

        room_no = str(row["room_no"]).strip()
        sharing = int(row["sharing"])
        floor = int(row["floor"])
        beds = int(row["available_beds"])
        pg = row["pg_name"]

        # Skip bad rows
        if room_no == "":
            continue

        st.markdown(f"""
        ### 🏠 {pg}
        🏢 Room: {room_no}  
        👥 Sharing: {sharing}  
        🛏 Available Beds: {beds}  
        🏢 Floor: {floor}
        """)

        # -------- BOOK --------
        if beds > 0:

            if st.button(f"Book Room {room_no}", key=f"{i}"):

                try:
                    # 🔁 Reload latest data (avoid mismatch)
                    latest_data = sheet.get_all_records()
                    latest_df = pd.DataFrame(latest_data)

                    latest_row = latest_df.iloc[i]
                    current_beds = int(latest_row["available_beds"])

                    if current_beds <= 0:
                        st.error("❌ Already Full")
                        st.stop()

                    new_beds = current_beds - 1
                    row_index = i + 2  # header offset

                    # ✅ Correct update format
                    sheet.update(f"E{row_index}", [[new_beds]])

                    st.success("✅ Booking Successful")
                    st.rerun()

                except Exception as e:
                    st.error("❌ Booking failed. Try again")

        else:
            st.error("❌ Full")