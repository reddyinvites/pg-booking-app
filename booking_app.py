st.subheader("🛏 Available Rooms")

if filtered.empty:
    st.info("No rooms available")

else:
    for i, row in filtered.iterrows():

        # -------- CLEAN DATA --------
        room_no = str(row.get("room_no", "")).strip()
        sharing = row.get("sharing", "")
        floor = row.get("floor", "")
        beds = int(row.get("available_beds", 0))
        pg = row.get("pg_name", "")

        # ❌ Skip invalid rows
        if room_no == "" or sharing == "" or floor == "":
            continue

        # -------- DISPLAY --------
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
                    latest_data = sheet.get_all_records()
                    latest_df = pd.DataFrame(latest_data)

                    latest_row = latest_df.iloc[i]
                    current_beds = int(latest_row["available_beds"])

                    if current_beds <= 0:
                        st.error("❌ Already Full")
                        st.stop()

                    new_beds = current_beds - 1
                    row_index = i + 2

                    sheet.update(f"E{row_index}", [[new_beds]])

                    st.success("✅ Booking Successful")
                    st.rerun()

                except:
                    st.error("❌ Try again")

        else:
            st.error("❌ Full")