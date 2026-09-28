import streamlit as st
import time
from src.database.db import enroll_student_to_subject
from src.database.config import supabase


@st.dialog("Enroll in Subject")
def enroll_dialog():
    st.write('Enter the subject code provided by your teacher to enroll:')
    join_code = st.text_input('Subject Code', placeholder='E.g. CS101')

    if st.button('Enroll now', type='primary', use_container_width=True):
        if join_code.strip():
            res = supabase.table('subjects').select('subject_id, name, subject_code').eq('subject_code', join_code.strip()).execute()
            if res.data:
                subject = res.data[0]
                student_data = st.session_state.get('student_data')
                if not student_data:
                    st.error("Please log in as a student to enroll.")
                    return
                student_id = student_data['student_id']

                check = supabase.table('subject_students').select('*').eq('subject_id', subject['subject_id']).eq('student_id', student_id).execute()
                if check.data:
                    st.warning('You are already enrolled in this course.')
                else:
                    enroll_student_to_subject(student_id, subject['subject_id'])
                    st.success(f"Successfully enrolled in {subject['name']}!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("No course found with that subject code.")
        else:
            st.warning('Please enter a subject code.')