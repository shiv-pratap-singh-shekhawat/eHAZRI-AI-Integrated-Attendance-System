import dlib
import numpy as np
import face_recognition_models
import streamlit as st

from src.database.db import get_all_students

# Optional SVM support if sklearn is available
try:
    from sklearn.svm import SVC
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector()

    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec


def get_face_embeddings(image_np):
    if image_np is None:
        return []

    # Ensure 8-bit RGB contiguous array for dlib
    if len(image_np.shape) == 3 and image_np.shape[2] == 4:
        image_np = image_np[:, :, :3]
    image_np = np.ascontiguousarray(image_np, dtype=np.uint8)

    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)

    encodings = []
    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)
        encodings.append(np.array(face_descriptor))
    return encodings


@st.cache_resource
def get_trained_model():
    X = []
    y = []

    student_db = get_all_students()
    if not student_db:
        return None

    for student in student_db:
        embedding = student.get('face_embedding')
        sid = student.get('student_id')
        if embedding and sid is not None:
            X.append(np.array(embedding, dtype=np.float64))
            y.append(sid)

    if len(X) == 0:
        return None

    clf = None
    if SKLEARN_AVAILABLE and len(set(y)) >= 2:
        try:
            clf = SVC(kernel='linear', probability=True, class_weight='balanced')
            clf.fit(X, y)
        except Exception:
            clf = None

    return {'clf': clf, 'X': X, 'y': y}


def train_classifier():
    st.cache_resource.clear()
    model_data = get_trained_model()
    return bool(model_data)


def predict_attendance(class_image_np):
    encodings = get_face_embeddings(class_image_np)
    detected_student = {}

    model_data = get_trained_model()
    if not model_data or not model_data.get('X'):
        return detected_student, [], len(encodings)

    clf = model_data.get('clf')
    X_train = np.array(model_data['X'])
    y_train = model_data['y']

    all_students = sorted(list(set(y_train)))
    resemblance_threshold = 0.6

    for encoding in encodings:
        enc_np = np.array(encoding, dtype=np.float64)
        predicted_id = None

        if clf is not None and len(all_students) >= 2:
            try:
                predicted_id = int(clf.predict([enc_np])[0])
            except Exception:
                predicted_id = None

        # Distance-based nearest neighbor verification (standard dlib face recognition)
        distances = np.linalg.norm(X_train - enc_np, axis=1)
        min_idx = int(np.argmin(distances))
        best_dist = distances[min_idx]

        if predicted_id is None:
            predicted_id = int(y_train[min_idx])

        # Verify against enrolled embedding threshold
        student_embedding = X_train[y_train.index(predicted_id)]
        match_score = np.linalg.norm(student_embedding - enc_np)

        if match_score <= resemblance_threshold or best_dist <= resemblance_threshold:
            detected_student[predicted_id] = True

    return detected_student, all_students, len(encodings)
