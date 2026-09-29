import streamlit as st
import numpy as np
from PIL import Image
import time

from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.components.header import header_dashboard, footer_dashboard
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding
from src.database.db import (
    get_all_students,
    create_student,
    get_student_subjects,
    get_student_attendance,
    unenroll_student_to_subject,
)
from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card


def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']

    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"Welcome, {student_data.get('name', 'Student')}")
        if st.button("Logout", type='secondary', key='studentlogoutbtn'):
            st.session_state['is_logged_in'] = False
            st.session_state.pop('student_data', None)
            st.session_state['login_type'] = None
            st.rerun()

    st.space()

    c1, c2 = st.columns(2)
    with c1:
        st.header('Your Enrolled Subjects')
    with c2:
        if st.button('Enroll in Subject', type='primary', use_container_width=True):
            enroll_dialog()

    st.divider()

    with st.spinner('Loading your enrolled subjects...'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}
    for log in logs:
        sid = log.get('subject_id')
        if sid not in stats_map:
            stats_map[sid] = {"total": 0, "attended": 0}

        stats_map[sid]['total'] += 1
        if log.get('is_present'):
            stats_map[sid]['attended'] += 1

    if not subjects:
        st.info("You haven't enrolled in any subjects yet. Click 'Enroll in Subject' above to join with a subject code.")
    else:
        cols = st.columns(2)
        for i, sub_node in enumerate(subjects):
            sub = sub_node.get('subjects')
            if not sub:
                continue
            sid = sub.get('subject_id')
            stats = stats_map.get(sid, {"total": 0, "attended": 0})

            def make_unenroll_button(current_sid, current_name):
                def unenroll_button():
                    if st.button("Unenroll from this course", type='tertiary', use_container_width=True, icon=':material/delete_forever:', key=f"unenroll_{current_sid}"):
                        unenroll_student_to_subject(student_id, current_sid)
                        st.toast(f"Unenrolled from {current_name} successfully!")
                        st.rerun()
                return unenroll_button

            with cols[i % 2]:
                subject_card(
                    name=sub.get('name', 'Untitled'),
                    code=sub.get('subject_code', '-'),
                    section=sub.get('section', 'A'),
                    stats=[
                        ('📅', 'Total', stats['total']),
                        ('✅', 'Attended', stats['attended']),
                    ],
                    footer_callback=make_unenroll_button(sid, sub.get('name', 'Course'))
                )

    footer_dashboard()


def student_screen():
    style_background_dashboard()
    style_base_layout()

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='studenthomebackbtn'):
            st.session_state['login_type'] = None
            st.rerun()

    st.markdown("<h2 style='text-align:center;'>Login using FaceID</h2>", unsafe_allow_html=True)
    st.space()

    show_registration = False
    photo_source = st.camera_input("Position your face in the center")

    if photo_source:
        img = np.array(Image.open(photo_source).convert('RGB'))

        with st.spinner('AI is scanning...'):
            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('No face detected! Please ensure your face is clearly visible in the frame.')
            elif num_faces > 1:
                st.warning('Multiple faces detected! Please ensure only one person is in front of the camera.')
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    all_students = get_all_students()
                    student = next((s for s in all_students if s.get('student_id') == student_id), None)

                    if student:
                        st.session_state['is_logged_in'] = True
                        st.session_state['user_role'] = 'student'
                        st.session_state['student_data'] = student
                        st.toast(f"Welcome back, {student.get('name', 'Student')}!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info('Face not recognized! You might be a new student. Please register your profile below.')
                    show_registration = True

    if show_registration and photo_source:
        with st.container(border=True):
            st.header('Register New Profile')
            new_name = st.text_input("Enter your name", placeholder='E.g. Shiv Pratap')

            st.subheader('Optional : Voice Enrollment')
            st.info("Enroll your voice for voice-only attendance verification.")

            audio_data = None
            try:
                audio_data = st.audio_input('Record a short phrase like "I am present, my name is Shiv."')
            except Exception:
                st.error('Audio capture not available in this browser.')

            if st.button('Create Account', type='primary', use_container_width=True):
                if new_name.strip():
                    with st.spinner('Creating profile...'):
                        img = np.array(Image.open(photo_source).convert('RGB'))
                        encodings = get_face_embeddings(img)
                        if encodings:
                            face_emb = encodings[0].tolist()

                            voice_emb = None
                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(new_name.strip(), face_embedding=face_emb, voice_embedding=voice_emb)

                            if response_data:
                                train_classifier()
                                st.session_state['is_logged_in'] = True
                                st.session_state['user_role'] = 'student'
                                st.session_state['student_data'] = response_data[0]
                                st.toast(f"Profile created! Welcome, {new_name}!")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("Could not capture your facial features. Please ensure good lighting and face the camera directly.")
                else:
                    st.warning('Please enter your name!')
