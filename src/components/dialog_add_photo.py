import streamlit as st
from PIL import Image


@st.dialog("Capture or upload photos")
def add_photos_dialog():
    st.write('Add classroom photos to scan for attendance.')

    if 'photo_tab' not in st.session_state:
        st.session_state.photo_tab = 'camera'

    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    if 'processed_uploads' not in st.session_state:
        st.session_state.processed_uploads = set()

    t1, t2 = st.columns(2)

    with t1:
        type_camera = "primary" if st.session_state.photo_tab == 'camera' else 'tertiary'
        if st.button('Camera', type=type_camera, use_container_width=True):
            st.session_state.photo_tab = 'camera'
            st.rerun()

    with t2:
        type_upload = "primary" if st.session_state.photo_tab == 'upload' else 'tertiary'
        if st.button('Upload photos', type=type_upload, use_container_width=True):
            st.session_state.photo_tab = 'upload'
            st.rerun()

    if st.session_state.photo_tab == 'camera':
        cam_photo = st.camera_input('Take Snapshot', key='dialog_cam')
        if cam_photo:
            photo_id = f"cam_{cam_photo.size}_{cam_photo.name}"
            if photo_id not in st.session_state.processed_uploads:
                st.session_state.attendance_images.append(Image.open(cam_photo).convert('RGB'))
                st.session_state.processed_uploads.add(photo_id)
                st.toast('Photo Captured')

    if st.session_state.photo_tab == 'upload':
        uploaded_files = st.file_uploader(
            'Choose image files',
            type=['jpg', 'png', 'jpeg'],
            accept_multiple_files=True,
            key='dialog_upload'
        )

        if uploaded_files:
            new_added = 0
            for f in uploaded_files:
                file_id = f"file_{f.name}_{f.size}"
                if file_id not in st.session_state.processed_uploads:
                    st.session_state.attendance_images.append(Image.open(f).convert('RGB'))
                    st.session_state.processed_uploads.add(file_id)
                    new_added += 1

            if new_added > 0:
                st.toast(f'{new_added} Photo(s) Added Successfully')

    st.write(f"Total photos currently added: **{len(st.session_state.attendance_images)}**")
    st.divider()
    if st.button('Done', type='primary', use_container_width=True):
        st.rerun()