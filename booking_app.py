import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

st.set_page_config(page_title="PG App", layout="wide")

# -----------------------
# CONFIG
# -----------------------
cloudinary.config(
    cloud_name=st.secrets["cloudinary"]["cloud_name"],
    api_key=st.secrets["cloudinary"]["api_key"],
    api_secret=st.secrets["cloudinary"]["api_secret"]
)

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

gcp_info = dict(st.secrets["gcp_service_account"])
gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(gcp_info, scopes=scope)
client = gspread.authorize(creds)

# -----------------------
# SHEET (ONLY ONE)
# -----------------------
sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q")
pg_sheet = sheet.sheet1   # only Sheet1

# -----------------------
# SESSION
# -----------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

# -----------------------
# HOME
# -----------------------
if st.session_state.page == "home":

    st.title("🏠 PG List")

    data = pg_sheet.get_all_values()
    rows = data[1:]

    for i, row in enumerate(rows):

        if len(row) < 3:
            continue

        name = row[1]
        location = row[2]
        verified = row[3] if len(row) > 3 else "No"

        st.subheader(f"🏠 {name}")
        st.write(f"📍 {location}")

        if verified == "Yes":
            st.success("✅ Verified")

        if st.button(f"View {name}", key=f"view{i}"):
            st.session_state.pg_index = i + 2
            st.session_state.page = "detail"
            st.rerun()

        st.divider()

    if st.button("👨‍💼 Admin"):
        st.session_state.page = "admin"
        st.rerun()

# -----------------------
# DETAIL
# -----------------------
elif st.session_state.page == "detail":

    row = pg_sheet.row_values(st.session_state.pg_index)

    st.title(row[1])
    st.write(f"📍 {row[2]}")

    images = row[4].split("|") if len(row) > 4 else []

    st.subheader("📸 Images")
    for img in images:
        if img.startswith("http"):
            st.image(img)

    videos = row[5].split("|") if len(row) > 5 else []

    st.subheader("🎥 Videos")
    for v in videos:
        if v.startswith("http"):
            st.video(v)

    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()

# -----------------------
# ADMIN
# -----------------------
elif st.session_state.page == "admin":

    st.title("👨‍💼 Admin")

    if st.text_input("Password", type="password") != "1234":
        st.stop()

    st.success("Logged in")

    data = pg_sheet.get_all_values()
    rows = data[1:]

    options = []

    for i, row in enumerate(rows):
        if len(row) >= 3:
            options.append(f"{i+2} | {row[1]} | {row[2]}")

    selected = st.selectbox("Select PG", options)

    index = int(selected.split(" | ")[0])

    verified = st.selectbox("Verified", ["Yes", "No"])

    image_files = st.file_uploader("Upload Images", accept_multiple_files=True)
    video_files = st.file_uploader("Upload Videos", accept_multiple_files=True)

    image_urls = []
    video_urls = []

    if image_files:
        for f in image_files:
            res = cloudinary.uploader.upload(f)
            image_urls.append(res["secure_url"])

    if video_files:
        for f in video_files:
            res = cloudinary.uploader.upload(f, resource_type="video")
            video_urls.append(res["secure_url"])

    if st.button("Save"):

        if image_urls:
            pg_sheet.update_cell(index, 5, "|".join(image_urls))

        if video_urls:
            pg_sheet.update_cell(index, 6, "|".join(video_urls))

        pg_sheet.update_cell(index, 4, verified)

        st.success("Updated ✅")
        st.rerun()