import streamlit as st
import time
from src.database.db import create_subject


@st.dialog("Create New Subject")
def create_subject_dialog(teacher_id):
    st.write("Enter the details of the new subject:")
    sub_id = st.text_input("Subject Code", placeholder="CS101")
    sub_name = st.text_input("Subject Name", placeholder="Introduction to Computer Science")
    sub_section = st.text_input("Section", placeholder="A", value="A")

    if st.button("Create Subject Now", type='primary', use_container_width=True):
        if sub_id.strip() and sub_name.strip():
            try:
                create_subject(sub_id.strip(), sub_name.strip(), sub_section.strip(), teacher_id)
                st.toast("Subject Created Successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error creating subject: {str(e)}")
        else:
            st.warning("Please fill in Subject Code and Subject Name.")