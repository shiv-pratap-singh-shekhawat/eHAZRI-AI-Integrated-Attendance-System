from src.database.config import supabase
import bcrypt


def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def check_teacher_exists(username):
    # Check for unique username, returns true when username is already taken
    response = supabase.table("teachers").select("usernane").eq("usernane", username).execute()
    return len(response.data) > 0


def create_teacher(username, password, name):
    data = {"usernane": username, "password": hash_pass(password), "name": name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    response = supabase.table("teachers").select("*").eq("usernane", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


def get_all_students():
    response = supabase.table('students').select("*").execute()
    return response.data or []


def create_student(new_name, face_embedding=None, voice_embedding=None):
    data = {'name': new_name, 'face_embedding': face_embedding, 'voice_embedding': voice_embedding}
    response = supabase.table('students').insert(data).execute()
    return response.data


def create_subject(subject_code, name, section, teacher_id):
    data = {"subject_code": subject_code, "name": name, "teacher_id": teacher_id}
    if section:
        data["section"] = section
    try:
        response = supabase.table("subjects").insert(data).execute()
        return response.data
    except Exception as e:
        if "section" in str(e):
            data.pop("section", None)
            response = supabase.table("subjects").insert(data).execute()
            return response.data
        raise e


def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select("*, subject_students(count), attendance_logs(timestamp)").eq("teacher_id", teacher_id).execute()
    subjects = response.data or []

    for sub in subjects:
        sub['total_students'] = sub.get("subject_students", [{}])[0].get('count', 0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
        sub['total_classes'] = unique_sessions
        sub.setdefault('section', 'A')

        sub.pop('subject_students', None)
        sub.pop('subject_student', None)
        sub.pop('attendance_logs', None)

    return subjects


def enroll_student_to_subject(student_id, subject_id):
    # Check if already enrolled
    existing = supabase.table('subject_students').select('*').eq('student_id', student_id).eq('subject_id', subject_id).execute()
    if existing.data:
        return existing.data
    data = {'student_id': student_id, "subject_id": subject_id}
    response = supabase.table('subject_students').insert(data).execute()
    return response.data


def unenroll_student_to_subject(student_id, subject_id):
    response = supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data


def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
    data = response.data or []
    for item in data:
        if item.get('subjects'):
            item['subjects'].setdefault('section', 'A')
    return data


def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data or []


def create_attendance(logs):
    if not logs:
        return []
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data


def get_attendance_for_teacher(teacher_id):
    response = supabase.table('attendance_logs').select("*, subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
    return response.data or []