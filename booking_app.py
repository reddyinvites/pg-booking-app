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

# ---------------- CONNECT ----------------
try:
    sh = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")
    sheet = sh.worksheet("rooms")
except Exception as e:
    st.error(f"❌ {e}")
    st.stop()

# ---------------- LOAD ----------------
@st.cache_data(ttl=20)
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.lower().str.strip()

    df["sharing_type"] = (
        df["sharing_type"]
        .astype(str)
        .str.replace("Sharing", "")
        .str.strip()
    )

    return df

df = load_data()
df = df[df["available_beds"] > 0]

# ---------------- LOCATION SPLIT ----------------
loc = df["location"].astype(str).str.split("-", n=1, expand=True)
df["area"] = loc[0].fillna("").str.strip()
df["locality"] = loc[1].fillna("").str.strip()

# ---------------- FILTER UI ----------------
st.subheader("🎯 Your Preferences")

pref_area = st.selectbox("📍 Area", sorted(df["area"].unique()))
pref_locality = st.selectbox("🏠 Locality", sorted(df["locality"].unique()))
pref_budget = st.number_input("💰 Budget", value=8000)

pref_sharing = st.selectbox("🛏 Sharing",
    ["1 Sharing","2 Sharing","3 Sharing","4 Sharing"])

pref_gender = st.selectbox("👤 Gender", ["Male","Female","Co-Living"])
pref_food = st.selectbox("🍽 Food", ["Veg","Non Veg","Both"])
pref_room_type = st.selectbox("🧊 Room Type", ["AC","Non AC"])

# ---------------- FILTER ----------------
df = df[(df["area"] == pref_area) & (df["locality"] == pref_locality)]

# STRICT SHARING FILTER
df = df[df["sharing_type"] == pref_sharing.split()[0]]

# ---------------- SAFE FLOAT ----------------
def safe(v):
    try:
        return float(v)/2
    except:
        return 3

# ---------------- SCORING ----------------
results = []

for (pg_id, pg_name, loc), g in df.groupby(["pg_id","pg_name","location"]):

    row = g.iloc[0]

    try:
        price = int(str(row["price"]).replace("₹","").replace(",",""))
    except:
        continue

    score = 0
    reasons = []
    cons = []

    # PRICE
    if price == pref_budget:
        score += 40
        reasons.append("Perfect budget match 🔥")
    elif price < pref_budget:
        score += 30
        reasons.append("Under your budget")
    elif price <= pref_budget+1000:
        score += 20
        cons.append("Slightly above budget")
    else:
        continue

    # MATCH
    score += 20; reasons.append("Area match")
    score += 20; reasons.append("Locality match")
    score += 10; reasons.append("Sharing matched")

    # RATINGS
    food = safe(row.get("food_rating"))
    clean = safe(row.get("cleanliness"))
    safety = safe(row.get("safety"))
    maint = safe(row.get("maintenance_score"))

    noise_map = {"low":5,"medium":3.5,"high":1.5}
    noise = noise_map.get(str(row.get("noise_level")).lower(),3.5)

    rating = round((food+clean+safety+maint+noise)/5,1)

    score += int(rating*2)

    if int(row["available_beds"]) == 1:
        cons.append("Only 1 bed left 🔥")

    results.append({
        "pg": pg_name,
        "id": pg_id,
        "loc": loc,
        "price": price,
        "beds": int(g["available_beds"].sum()),
        "score": min(score,100),
        "reasons": reasons,
        "cons": cons,
        "rating": rating,
        "food": food,
        "clean": clean,
        "safety": safety,
        "maint": maint
    })

results = sorted(results, key=lambda x: x["score"], reverse=True)

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

for i,r in enumerate(results[:3]):

    with st.container():
        st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")

        # PRICE STYLE
        if r["price"] == pref_budget:
            st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
        else:
            st.info(f"💰 ₹{r['price']}")

        st.write(f"🛏 {r['beds']} Beds Available")

        # WHY
        st.markdown("### ✅ Why this PG?")
        for x in r["reasons"]:
            st.write(f"✔️ {x}")

        # CONS
        if r["cons"]:
            st.markdown("### ⚠️ Things to consider")
            for c in r["cons"]:
                st.write(f"⚠️ {c}")

        # RATINGS
        st.markdown("### ⭐ Ratings")
        st.write(f"🍛 Food: {r['food']}/5")
        st.write(f"🧹 Clean: {r['clean']}/5")
        st.write(f"🛡 Safety: {r['safety']}/5")
        st.write(f"🔧 Maintenance: {r['maint']}/5")

        st.progress(r["rating"]/5)
        st.caption(f"Overall Score: {r['rating']}/5")

        # BOOKING
        with st.form(f"book_{i}"):

            name = st.text_input("👤 Name")
            phone = st.text_input("📞 Phone")
            date = st.date_input("📅 Move Date")

            if st.form_submit_button("🚀 Book Now"):

                phone = phone.replace("+91","").strip()

                if not(phone.isdigit() and len(phone)==10):
                    st.error("Invalid phone ❌")
                else:
                    sheet_b = client.open_by_key(PG_APP_ID).worksheet("Bookings")
                    sheet_b.append_row([
                        r["id"],r["pg"],r["loc"],r["price"],
                        name,phone,str(date),"CONFIRMED"
                    ])

                    st.success("🎉 Booked!")
                    st.rerun()

        st.divider()