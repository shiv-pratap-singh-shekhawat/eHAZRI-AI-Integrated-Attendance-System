import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import time

from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.components.header import header_dashboard, footer_dashboard
from src.components.subject_card import subject_card
from src.database.db import (
    check_teacher_exists,
    create_teacher,
    teacher_login,
    get_teacher_subjects,
    get_attendance_for_teacher,
)
from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog
from src.components.dialog_add_photo import add_photos_dialog
from src.pipelines.face_pipeline import predict_attendance
from src.components.dialog_attendance_results import attendance_result_dialog
from src.components.dialog_voice_attendance import voice_attendance_dialog
from src.database.config import supabase


def teacher_screen():
    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type == "login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"Welcome, {teacher_data.get('name', 'Teacher')}")
        if st.button("Logout", type='secondary', key='teacherlogoutbtn'):
            st.session_state['is_logged_in'] = False
            st.session_state.pop('teacher_data', None)
            st.session_state['login_type'] = None
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendance'

    tab1, tab2, tab3 = st.columns(3)

    with tab1:
        type1 = "primary" if st.session_state.current_teacher_tab == 'take_attendance' else "tertiary"
        if st.button('Take Attendance', type=type1, use_container_width=True, icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendance'
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_teacher_tab == 'manage_subjects' else "tertiary"
        if st.button('Manage Subjects', type=type2, use_container_width=True, icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subjects'
            st.rerun()

    with tab3:
        type3 = "primary" if st.session_state.current_teacher_tab == 'attendance_records' else "tertiary"
        if st.button('Attendance Records', type=type3, use_container_width=True, icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendance_records'
            st.rerun()

    st.divider()

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    elif st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    elif st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()

    footer_dashboard()


def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Take AI Attendance')

    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning("You haven't created any subjects yet! Please go to 'Manage Subjects' to create one first.")
        return

    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3, 1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', use_container_width=True):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4]:
                st.image(img, use_container_width=True, caption=f'Photo {idx+1}')

    has_photos = bool(st.session_state.attendance_images)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button('Clear all photos', use_container_width=True, type='tertiary', icon=':material/delete:', disabled=not has_photos):
            st.session_state.attendance_images = []
            st.rerun()

    with c2:
        if st.button('Run Face Analysis', use_container_width=True, type='secondary', icon=':material/analytics:', disabled=not has_photos):
            with st.spinner('Deep scanning classroom photos...'):
                all_detected_ids = {}

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert('RGB'))
                    detected, _, _ = predict_attendance(img_np)

                    if detected:
                        for sid in detected.keys():
                            student_id = int(sid)
                            all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

                enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id', selected_subject_id).execute()
                enrolled_students = enrolled_res.data or []

                if not enrolled_students:
                    st.warning('No students enrolled in this course yet.')
                else:
                    results, attendance_to_log = [], []
                    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    for node in enrolled_students:
                        student = node.get('students')
                        if not student:
                            continue
                        sid = int(student['student_id'])
                        sources = all_detected_ids.get(sid, [])
                        is_present = len(sources) > 0

                        results.append({
                            "Name": student.get('name', 'Unknown'),
                            "ID": sid,
                            "Source": ", ".join(sources) if is_present else "-",
                            "Status": "✅ Present" if is_present else "❌ Absent"
                        })

                        attendance_to_log.append({
                            'student_id': sid,
                            'subject_id': selected_subject_id,
                            'timestamp': current_timestamp,
                            'is_present': bool(is_present)
                        })

                    attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

    with c3:
        if st.button('Use Voice Attendance', type='primary', use_container_width=True, icon=':material/mic:'):
            voice_attendance_dialog(selected_subject_id)


def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects')

    with col2:
        if st.button('Create New Subject', use_container_width=True):
            create_subject_dialog(teacher_id)

    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🫂", "Students", sub.get('total_students', 0)),
                ("🕰️", "Classes", sub.get('total_classes', 0)),
            ]

            def make_share_btn(current_sub):
                def share_btn():
                    if st.button(f"Share Code: {current_sub['name']}", key=f"share_{current_sub['subject_code']}", icon=":material/share:", use_container_width=True):
                        share_subject_dialog(current_sub['name'], current_sub['subject_code'])
                return share_btn

            subject_card(
                name=sub['name'],
                code=sub['subject_code'],
                section=sub.get('section', 'A'),
                stats=stats,
                footer_callback=make_share_btn(sub)
            )
    else:
        st.info("No subjects found. Click 'Create New Subject' above to create one.")


def teacher_tab_attendance_records():
    st.header('Attendance Records')
    teacher_id = st.session_state.teacher_data['teacher_id']
    records = get_attendance_for_teacher(teacher_id)

    if not records:
        st.info("No attendance records found yet.")
        return

    data = []
    for r in records:
        ts = r.get('timestamp')
        sub_info = r.get('subjects') or {}

        time_str = "N/A"
        if ts:
            try:
                time_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p")
            except Exception:
                time_str = str(ts)

        data.append({
            "ts_group": ts.split(".")[0] if ts else "N/A",
            "Time": time_str,
            "Subject": sub_info.get('name', 'N/A'),
            "Subject Code": sub_info.get('subject_code', 'N/A'),
            "is_present": bool(r.get('is_present', False))
        })

    df = pd.DataFrame(data)

    if df.empty:
        st.info("No attendance records found yet.")
        return

    summary = (
        df.groupby(['ts_group', 'Time', 'Subject', 'Subject Code'])
        .agg(
            Present_Count=('is_present', 'sum'),
            Total_Count=('is_present', 'count')
        ).reset_index()
    )

    summary['Attendance Stats'] = (
        "✅ " + summary['Present_Count'].astype(str) + " / "
        + summary['Total_Count'].astype(str) + ' Students'
    )

    display_df = (
        summary.sort_values(by='ts_group', ascending=False)
        [['Time', 'Subject', 'Subject Code', 'Attendance Stats']]
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def login_teacher(username, password):
    if not username or not password:
        return False

    teacher = teacher_login(username, password)
    if teacher:
        st.session_state['user_role'] = 'teacher'
        st.session_state['teacher_data'] = teacher
        st.session_state['is_logged_in'] = True
        return True

    return False


def teacher_screen_login():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='teacherloginbackbtn'):
            st.session_state['login_type'] = None
            st.rerun()

    st.markdown("<h2 style='text-align:center;'>Teacher Login</h2>", unsafe_allow_html=True)
    st.space()

    teacher_username = st.text_input("Enter username", placeholder='rahulgupta')
    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    st.divider()
    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Login', icon=':material/passkey:', use_container_width=True):
            if login_teacher(teacher_username, teacher_pass):
                st.toast("Welcome back!", icon="👋")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with btnc2:
        if st.button('Register Instead', type="primary", icon=':material/passkey:', use_container_width=True):
            st.session_state.teacher_login_type = 'register'
            st.rerun()


def register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm):
    if not teacher_username or not teacher_name or not teacher_pass:
        return False, "All fields are required!"
    if check_teacher_exists(teacher_username):
        return False, "Username already taken."
    if teacher_pass != teacher_pass_confirm:
        return False, "Passwords do not match."

    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Profile created successfully! You can now log in."
    except Exception as e:
        return False, f"Unexpected Error: {e}"


def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='teacherregbackbtn'):
            st.session_state['login_type'] = None
            st.rerun()

    st.markdown("<h2 style='text-align:center;'>Register Teacher Profile</h2>", unsafe_allow_html=True)
    st.space()

    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')
    teacher_name = st.text_input("Enter name", placeholder='Ananya Roy')
    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")
    teacher_pass_confirm = st.text_input("Confirm your password", type='password', placeholder="Confirm password")

    st.divider()
    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now', icon=':material/passkey:', use_container_width=True):
            success, message = register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm)
            if success:
                st.success(message)
                time.sleep(1)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)

    with btnc2:
        if st.button('Login Instead', type="primary", icon=':material/passkey:', use_container_width=True):
            st.session_state.teacher_login_type = 'login'
            st.rerun()
