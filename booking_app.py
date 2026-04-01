import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Verified PGs", layout="wide")
st.cache_data.clear()

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
# SHEET
# -----------------------
sheet = client.open("verified_pg")
pg_sheet = sheet.sheet1

# -----------------------
# SESSION
# -----------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

# -----------------------
# HOME
# -----------------------
if st.session_state.page == "home":

    st.title("🏠 Verified PGs")

    data = pg_sheet.get_all_values()
    rows = data[1:] if len(data) > 1 else []

    for i, row in enumerate(rows):

        if len(row) < 2:
            continue

        name = row[0].strip()
        location = row[1].strip()

        if not name:
            continue

        st.subheader(f"🏠 {name}")
        st.write(f"📍 {location}")

        if st.button(f"View {name}", key=f"view_{i}"):
            st.session_state.pg = row
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

    pg = st.session_state.pg

    name = pg[0] if len(pg) > 0 else ""
    location = pg[1] if len(pg) > 1 else ""
    verified = pg[2] if len(pg) > 2 else ""
    images = pg[3] if len(pg) > 3 else ""
    videos = pg[4] if len(pg) > 4 else ""

    st.title(name)
    st.write(f"📍 {location}")

    if verified == "Yes":
        st.success("✅ Verified by Us")

    # -----------------------
    # IMAGE GALLERY
    # -----------------------
    sections = images.split("|")
    sections += [""] * (6 - len(sections))

    titles = ["🏠 Room", "🚿 Bathroom", "🍛 Food", "🍽️ Dining", "🧳 Storage", "📍 Outside"]

    for idx, sec in enumerate(sections):

        img_list = [img for img in sec.split(",") if img.strip()]

        if img_list:
            st.subheader(titles[idx])

            cols = st.columns(2)

            for i, img in enumerate(img_list):
                if img.startswith("http"):
                    cols[i % 2].image(img, use_container_width=True)

    # -----------------------
    # VIDEO GALLERY
    # -----------------------
    video_list = [v for v in videos.split(",") if v.strip()]

    if video_list:
        st.subheader("🎥 Videos")

        for vid in video_list:
            if vid.startswith("http"):
                st.video(vid)

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

    if st.button("Logout"):
        st.session_state.clear()
        st.session_state.page = "home"
        st.rerun()

    # -----------------------
    # ADD PG
    # -----------------------
    st.subheader("Add PG")

    name = st.text_input("Name")
    location = st.text_input("Location")
    verified = st.selectbox("Verified", ["Yes", "No"])

    def uploader(key):
        return st.file_uploader(key, accept_multiple_files=True, key=key)

    room = uploader("room")
    bath = uploader("bath")
    food = uploader("food")
    dining = uploader("dining")
    storage = uploader("storage")
    outside = uploader("outside")
    videos = st.file_uploader("videos", accept_multiple_files=True)

    if st.button("Save PG"):

        if not name.strip() or not location.strip():
            st.error("Enter name & location")
            st.stop()

        def upload(files, video=False):
            urls = []
            if files:
                for f in files:
                    try:
                        res = cloudinary.uploader.upload(
                            f, resource_type="video" if video else "image"
                        )
                        urls.append(res["secure_url"])
                    except Exception as e:
                        st.error(e)
            return ",".join(urls)

        image_string = "|".join([
            upload(room),
            upload(bath),
            upload(food),
            upload(dining),
            upload(storage),
            upload(outside)
        ])

        video_string = upload(videos, True)

        pg_sheet.append_row([
            name.strip(),
            location.strip(),
            verified,
            image_string,
            video_string
        ])

        st.success("✅ Saved Successfully!")
        st.rerun()

    # -----------------------
    # MANAGE PGs
    # -----------------------
    st.subheader("📋 Manage PGs")

    data = pg_sheet.get_all_values()
    rows = data[1:] if len(data) > 1 else []

    for i, row in enumerate(rows):

        if len(row) < 3 or not row[0].strip():
            continue

        name = row[0]
        location = row[1]
        verified = row[2]

        st.markdown(f"### 🏠 {name}")
        st.write(f"📍 {location}")

        if verified == "Yes":
            st.success("✅ Verified")
        else:
            st.warning("❌ Not Verified")

        col1, col2 = st.columns(2)

        # DELETE
        if col1.button("❌ Delete", key=f"d{i}"):
            pg_sheet.delete_rows(i + 2)
            st.rerun()

        # 🔒 TOGGLE DISABLED AFTER VERIFIED
        if verified == "No":
            if col2.button("🔄 Verify Now", key=f"t{i}"):

                pg_sheet.update_cell(i + 2, 3, "Yes")

                st.success("PG Verified ✅")
                st.rerun()
        else:
            col2.write("🔒 Locked (Verified)")

        st.divider()