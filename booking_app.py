import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="PG Match Engine", layout="centered")
st.title("🏠 PG Match Engine (Smart Recommendation)")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp"],
    scopes=scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1

# ---------------- LOAD ----------------
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

# ---------------- USER INPUT ----------------
st.subheader("🎯 Your Preferences")

col1, col2, col3 = st.columns(3)

pref_location = col1.selectbox("Area", df["location"].dropna().unique())
pref_budget = col2.number_input("Budget", value=8000)
pref_sharing = col3.selectbox("Sharing", ["1 Sharing", "2 Sharing", "3 Sharing", "4 Sharing"])

# ---------------- FILTER ----------------
df = df[df["available_beds"] > 0]

# ---------------- SCORING ----------------
results = []

for _, row in df.iterrows():

    try:
        price = int(float(row["price"]))
    except:
        continue

    score = 0
    reasons = []
    pros = []
    cons = []

    # 🔥 PRIORITY BUDGET LOGIC
    if price == pref_budget:
        score += 100
        reasons.append("Perfect budget match 🔥")

    elif price < pref_budget:
        diff = pref_budget - price
        score += 80 - diff / 100

        if diff <= 500:
            reasons.append("Very close to your budget")
        else:
            reasons.append("Good value under budget")
            pros.append("Saves money 💰")

    elif price <= pref_budget + 1000:
        diff = price - pref_budget
        score += 60 - diff / 100
        cons.append("Slightly above budget")

    else:
        continue

    # LOCATION
    if pref_location.lower() in str(row["location"]).lower():
        score += 30
        reasons.append("Exact location match")

    # SHARING
    if row["sharing_type"] == pref_sharing:
        score += 20
        reasons.append("Preferred sharing matched")

    results.append({
        "pg": row["pg_name"],
        "location": row["location"],
        "price": price,
        "beds": int(row["available_beds"]),
        "phone": row["owner_number"],
        "score": int(score),
        "reasons": reasons,
        "pros": pros,
        "cons": cons
    })

# ---------------- SORT ----------------
results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

# ---------------- DISPLAY ----------------
st.subheader("🏆 Best PGs For You")

if not results:
    st.error("No matching PGs found ❌")

for i, r in enumerate(results):

    # 🥇🥈🥉 BADGES
    if i == 0:
        badge = "🥇 Best Match"
    elif i == 1:
        badge = "🥈 Great Option"
    else:
        badge = "🥉 Value Pick"

    st.markdown(f"## 🏠 {r['pg']} — {r['score']}% Match")
    st.markdown(f"### {badge}")

    st.markdown(f"📍 {r['location']}")

    # 💰 PRICE DISPLAY
    if r["price"] == pref_budget:
        st.success(f"💰 ₹{r['price']} (Perfect match 🔥)")
    elif r["price"] < pref_budget:
        st.info(f"💰 ₹{r['price']} (₹{pref_budget - r['price']} cheaper)")
    else:
        st.warning(f"💰 ₹{r['price']} (above budget)")

    st.markdown(f"🛏 {r['beds']} Beds Available")

    # ⚡ URGENCY
    if r["beds"] <= 2:
        st.warning("⚡ Only few beds left!")

    # 📞 CONTACT
    st.markdown(f"📞 {r['phone']}")
    st.link_button("📲 WhatsApp Now", f"https://wa.me/{r['phone']}")

    # WHY
    st.markdown("### 💡 Why this PG?")
    for reason in r["reasons"]:
        st.write("•", reason)

    # PROS
    if r["pros"]:
        st.markdown("### 👍 Pros")
        for p in r["pros"]:
            st.write("✓", p)

    # CONS
    if r["cons"]:
        st.markdown("### ⚠️ Consider")
        for c in r["cons"]:
            st.write("•", c)

    st.divider()