import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import random

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp"],
    scopes=scope
)

client = gspread.authorize(creds)

# ---------------- CONNECT BOTH SHEETS ----------------
try:
    sh = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")

    sheet_pg = sh.sheet1
    sheet_rooms = sh.worksheet("rooms")

except:
    st.error("❌ Unable to connect to Google Sheet")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    try:
        df_pg = pd.DataFrame(sheet_pg.get_all_records())
        df_rooms = pd.DataFrame(sheet_rooms.get_all_records())

        if not df_pg.empty:
            df_pg.columns = df_pg.columns.str.lower().str.strip()

        if not df_rooms.empty:
            df_rooms.columns = df_rooms.columns.str.lower().str.strip()

        # FIX sharing format
        df_rooms["sharing_type"] = (
            df_rooms["sharing_type"]
            .astype(str)
            .str.replace("Sharing", "")
            .str.strip()
        )

        # MERGE BOTH
        df = pd.merge(
            df_rooms,
            df_pg,
            on=["pg_id", "pg_name"],
            how="left"
        )

        return df

    except Exception as e:
        st.error(e)
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]

location_split = df["location"].astype(str).str.split("-", n=1, expand=True)
df["area"] = location_split[0].fillna("").str.strip()
df["locality"] = location_split[1].fillna("").str.strip()

# ---------------- SEARCH ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s, na=False) |
        df["locality"].str.lower().str.contains(s, na=False)
    ]

# ---------------- DROPDOWNS ----------------
all_areas = sorted(df["area"].dropna().unique())
all_localities = sorted(df["locality"].dropna().unique())

pref_area = st.selectbox("📍 Area", all_areas)
pref_locality = st.selectbox("🏠 Locality", all_localities)

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox(
    "🛏 Sharing",
    ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"]
)

pref_gender = st.selectbox("👤 Gender", ["Male", "Female", "Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg", "Non Veg", "Both"])
pref_room_type = st.selectbox("🧊 Room Type", ["AC", "Non AC"])

# ---------------- FILTER ----------------
df = df[(df["area"] == pref_area) & (df["locality"] == pref_locality)]

# ---------------- SCORING ----------------
results = []
grouped = df.groupby(["pg_id", "pg_name", "location"])

for (pg_id, pg_name, location), group in grouped:

    row = group.iloc[0]

    price_str = str(row["price"]).replace("₹", "").replace(",", "").strip()
    if not price_str.isdigit():
        continue

    price = int(price_str)

    score = 0

    if price == pref_budget:
        score += 40
    elif price < pref_budget:
        score += 30
    elif price <= pref_budget + 1000:
        score += 20
    else:
        continue

    if str(row["sharing_type"]) == pref_sharing.split()[0]:
        score += 10

    results.append({
        "pg_id": pg_id,
        "pg": pg_name,
        "location": location,
        "price": price,
        "beds": int(group["available_beds"].sum()),
        "score": score
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for r in results[:3]:

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
    st.write(f"💰 ₹{r['price']}")
    st.write(f"🛏 {r['beds']} Beds Available")

    # ROOM FILTER
    room_df = df[
        (df["pg_id"] == r["pg_id"]) &
        (df["location"] == r["location"]) &
        (df["available_beds"] > 0) &
        (df["sharing_type"] == pref_sharing.split()[0])
    ]

    if room_df.empty:
        st.warning("No rooms available for selected sharing ❌")
        continue

    room_list = room_df["room_no"].astype(str).unique().tolist()

    selected_room = st.selectbox(
        f"🛏 Select Room - {r['pg']}",
        room_list,
        key=f"room_{r['pg_id']}"
    )

    selected_room_data = room_df[
        room_df["room_no"].astype(str) == selected_room
    ]

    beds_left = int(selected_room_data["available_beds"].values[0])
    st.info(f"🛏 Available Beds in Room {selected_room}: {beds_left}")

    # BOOKING
    with st.form(f"book_form_{r['pg_id']}"):

        name = st.text_input("👤 Your Name")
        phone = st.text_input("📞 Phone Number")
        move_date = st.date_input("📅 Move-in Date")

        submit = st.form_submit_button("🚀 Confirm Booking")

        if submit:
            try:
                booking_sheet = client.open_by_key(PG_APP_ID).worksheet("Bookings")

                booking_sheet.append_row([
                    r["pg_id"], r["pg"], selected_room, r["location"],
                    r["price"], name, phone, str(move_date), "CONFIRMED"
                ])

                # UPDATE BEDS IN ROOMS SHEET
                all_rows = sheet_rooms.get_all_records()
                headers = [h.strip().lower() for h in sheet_rooms.row_values(1)]
                bed_col_index = headers.index("available_beds") + 1

                for i, row_data in enumerate(all_rows, start=2):
                    if (
                        str(row_data["pg_id"]) == str(r["pg_id"]) and
                        str(row_data["room_no"]) == str(selected_room)
                    ):
                        current_beds = int(row_data["available_beds"])
                        if current_beds > 0:
                            sheet_rooms.update_cell(i, bed_col_index, current_beds - 1)

                st.success("🎉 Booking Confirmed!")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(e)

    st.divider()