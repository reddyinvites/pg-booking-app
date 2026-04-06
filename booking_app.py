import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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

# ✅ SAFE CONNECTION
try:
    sh = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")
    sheet = sh.sheet1
except:
    st.error("❌ Unable to connect to Google Sheet")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=20)
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.lower().str.strip()
    return df

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df["available_beds"] > 0]
df[["area", "locality"]] = df["location"].str.split("-", expand=True)

# ---------------- SEARCH ----------------
st.subheader("🎯 Your Preferences")

search = st.text_input("🔍 Search Area / Locality")

if search:
    s = search.lower()
    df = df[
        df["area"].str.lower().str.contains(s) |
        df["locality"].str.lower().str.contains(s)
    ]

# ---------------- DROPDOWNS ----------------
pref_area = st.selectbox("📍 Area", sorted(df["area"].dropna().unique()))
pref_locality = st.selectbox("🏠 Locality", sorted(df["locality"].dropna().unique()))
pref_budget = st.number_input("💰 Budget", value=8000, step=500)
pref_sharing = st.selectbox("🛏 Sharing", ["1 Sharing","2 Sharing","3 Sharing","4 Sharing"])
pref_gender = st.selectbox("👤 Gender", ["Male","Female","Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg","Non Veg","Both"])
pref_room_type = st.selectbox("🧊 Room Type", ["AC","Non AC"])

# ---------------- FILTER ----------------
df = df[(df["area"] == pref_area) & (df["locality"] == pref_locality)]

def safe_float(val, default=5):
    try:
        return float(val)/2
    except:
        return default

# ---------------- SCORING ----------------
results = []
grouped = df.groupby(["pg_name","location"])

for (pg_name, location), group in grouped:

    row = group.iloc[0]

    try:
        price = int(str(row["price"]).replace("₹","").replace(",",""))
    except:
        continue

    score = 0
    reasons = []
    cons = []

    # Budget
    if price == pref_budget:
        score += 40
        reasons.append("Perfect budget match 🔥")
    elif price < pref_budget:
        score += 25
        reasons.append("Good value under budget")
    elif price <= pref_budget + 1000:
        score += 20
    else:
        continue

    # Location
    if row["area"] == pref_area:
        score += 20
    if row["locality"] == pref_locality:
        score += 20

    if row["sharing_type"] == pref_sharing:
        score += 10

    if str(row.get("food_type","")).lower() == pref_food.lower():
        score += 5

    if str(row.get("room_type","")).lower() == pref_room_type.lower():
        score += 5

    score = max(0, min(100, int(score)))

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "score": score
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for r in results[:3]:

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

    st.info(f"💰 ₹{r['price']}")

    # ---------------- ROOM DATA ----------------
    room_df = df[
        (df["pg_name"] == r["pg"]) &
        (df["location"] == r["location"]) &
        (df["available_beds"] > 0)
    ]

    if not room_df.empty:

        room_list = room_df["room_no"].astype(str).unique().tolist()

        selected_room = st.selectbox(
            f"🛏 Select Room - {r['pg']}",
            room_list,
            key=f"room_{r['pg']}"
        )

        selected_room_data = room_df[
            room_df["room_no"].astype(str) == selected_room
        ]

        beds_left = int(selected_room_data["available_beds"].values[0])
        st.info(f"🛏 Available Beds in Room {selected_room}: {beds_left}")

        # ---------------- BOOK FORM ----------------
        with st.form(f"book_form_{r['pg']}"):

            name = st.text_input("👤 Your Name")
            phone = st.text_input("📞 Phone Number")

            submit = st.form_submit_button("🚀 Confirm Booking")

            if submit:

                if not name or not phone:
                    st.error("Please fill all details ❌")

                else:
                    try:
                        booking_sheet = client.open_by_key(PG_APP_ID).worksheet("Bookings")

                        pg_id = str(selected_room_data["pg_id"].values[0])

                        booking_sheet.append_row([
                            pg_id,
                            name,
                            phone,
                            r["pg"],
                            selected_room,
                            pref_sharing
                        ])

                        # Reduce beds
                        all_rows = sheet.get_all_records()
                        headers = sheet.row_values(1)
                        bed_col = headers.index("available_beds") + 1

                        for i, row_data in enumerate(all_rows, start=2):
                            if (
                                row_data["pg_name"] == r["pg"] and
                                str(row_data["room_no"]) == selected_room
                            ):
                                beds = int(row_data["available_beds"])
                                if beds > 0:
                                    sheet.update_cell(i, bed_col, beds - 1)

                        st.success("🎉 Booking Confirmed!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error: {e}")

    else:
        st.warning("No rooms available ❌")

    st.divider()