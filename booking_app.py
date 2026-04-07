import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
MAIN_SHEET_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------- AUTH ----------------
try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp"],
        scopes=scope
    )
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ Auth Error: {e}")
    st.stop()

# ---------------- CONNECT ----------------
try:
    sh = client.open_by_key(MAIN_SHEET_ID)
    sheet_pg = sh.sheet1
except Exception as e:
    st.error(f"❌ Sheet Error: {e}")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.DataFrame(sheet_pg.get_all_records())

        if df.empty:
            return pd.DataFrame()

        df.columns = df.columns.str.lower().str.strip()
        return df

    except Exception as e:
        st.error(f"❌ Data Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No PG data available")
    st.stop()

# ---------------- CLEAN ----------------
df = df[df.get("available_beds", 0) > 0]

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

# ---------------- FILTERS ----------------
all_areas = sorted(df["area"].dropna().unique())
all_localities = sorted(df["locality"].dropna().unique())

pref_area = st.selectbox("📍 Area", all_areas)
pref_locality = st.selectbox("🏠 Locality", all_localities)

pref_budget = st.number_input("💰 Budget", value=8000, step=500)

pref_sharing = st.selectbox(
    "🛏 Sharing",
    ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"]
)

# ---------------- FILTER ----------------
df = df[(df["area"] == pref_area) & (df["locality"] == pref_locality)]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    try:
        price = int(str(row["price"]).replace("₹", "").replace(",", "").strip())
    except:
        continue

    score = 0

    if price == pref_budget:
        score += 40
    elif price < pref_budget:
        score += 30
    elif price <= pref_budget + 1000:
        score += 20
    else:
        continue

    if str(row.get("sharing_type", "")) == pref_sharing.split()[0]:
        score += 10

    results.append({
        "pg_id": row.get("pg_id"),
        "pg": row.get("pg_name"),
        "location": row.get("location"),
        "price": price,
        "beds": row.get("available_beds", 0),
        "score": score
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for i, r in enumerate(results[:3]):  # ✅ FIXED HERE

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
    st.write(f"📍 {r['location']}")
    st.write(f"💰 ₹{r['price']}")
    st.write(f"🛏 Beds Available: {r['beds']}")

    # ---------------- BOOKING ----------------
    with st.form(f"book_form_{i}"):  # ✅ UNIQUE KEY

        name = st.text_input("👤 Your Name")
        phone = st.text_input("📞 Phone Number")
        move_date = st.date_input("📅 Move-in Date")

        submit = st.form_submit_button("🚀 Confirm Booking")

        if submit:

            if not (phone.isdigit() and len(phone) == 10):
                st.error("Invalid phone number ❌")
                st.stop()

            try:
                booking_sheet = client.open_by_key(PG_APP_ID).worksheet("Bookings")

                booking_sheet.append_row([
                    r["pg_id"], r["pg"],
                    r["location"], r["price"],
                    name, phone, str(move_date), "CONFIRMED"
                ])

                st.success("🎉 Booking Confirmed!")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Booking Error: {e}")

    st.divider()