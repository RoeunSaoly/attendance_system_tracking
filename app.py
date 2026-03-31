import base64
import os
import sqlite3
from datetime import datetime, time

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = "data/db/attendance.db"
STUDENT_DIR = "data/student_images"
RECOGNITION_THRESHOLD = 0.70

# Attendance time rules
ON_TIME_START = time(8, 0)
ON_TIME_END = time(8, 0)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id       TEXT PRIMARY KEY,
                name     TEXT NOT NULL,
                class    TEXT,
                photo    TEXT,
                encoding BLOB,
                created  TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                name       TEXT,
                class      TEXT,
                date       TEXT,
                time       TEXT,
                status     TEXT,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
            """
        )
        migrate_attendance_schema(conn)
        conn.commit()


def migrate_attendance_schema(conn):
    """Keep old DB files compatible with the current API shape."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(attendance)")
    columns = {row[1] for row in c.fetchall()}

    if "status" not in columns:
        c.execute("ALTER TABLE attendance ADD COLUMN status TEXT")

    if "late" in columns:
        c.execute(
            """
            UPDATE attendance
            SET status = CASE
                WHEN COALESCE(status, '') <> '' THEN status
                WHEN late = 1 THEN 'LATE'
                ELSE 'ON TIME'
            END
            """
        )

    c.execute("UPDATE attendance SET status='ON TIME' WHERE COALESCE(status, '') = ''")


init_db()

# Face detectors (frontal + profile for angled faces)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
face_cascade_alt = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


def preprocess_for_detection(gray_img):
    """Enhance image for better face detection in low-light and uneven lighting."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_img)

    mean_brightness = np.mean(enhanced)
    if mean_brightness < 80:
        gamma = 0.6
        table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype("uint8")
        enhanced = cv2.LUT(enhanced, table)
        enhanced = clahe.apply(enhanced)

    enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
    return enhanced


def _overlaps_any(rect, rect_list, threshold=0.4):
    """Check if rect overlaps significantly with any rect in list."""
    rx, ry, rw, rh = rect
    for ex, ey, ew, eh in rect_list:
        ix1 = max(rx, ex)
        iy1 = max(ry, ey)
        ix2 = min(rx + rw, ex + ew)
        iy2 = min(ry + rh, ey + eh)
        if ix2 > ix1 and iy2 > iy1:
            inter_area = (ix2 - ix1) * (iy2 - iy1)
            min_area = min(rw * rh, ew * eh)
            if min_area > 0 and inter_area / min_area > threshold:
                return True
    return False


def detect_faces(gray_img):
    """Detect faces using multiple cascades for frontal + angled faces."""
    enhanced = preprocess_for_detection(gray_img)

    faces = face_cascade.detectMultiScale(
        enhanced,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(50, 50),
    )
    found = list(faces) if len(faces) > 0 else []

    if len(found) == 0:
        faces_alt = face_cascade_alt.detectMultiScale(
            enhanced,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(50, 50),
        )
        if len(faces_alt) > 0:
            found = list(faces_alt)

    try:
        profiles_left = profile_cascade.detectMultiScale(
            enhanced,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(50, 50),
        )
        if len(profiles_left) > 0:
            for pf in profiles_left:
                if not _overlaps_any(pf, found):
                    found.append(pf)
    except cv2.error:
        pass

    try:
        flipped = cv2.flip(enhanced, 1)
        profiles_right = profile_cascade.detectMultiScale(
            flipped,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(50, 50),
        )
        if len(profiles_right) > 0:
            img_w = enhanced.shape[1]
            for pf in profiles_right:
                mirrored = (img_w - pf[0] - pf[2], pf[1], pf[2], pf[3])
                if not _overlaps_any(mirrored, found):
                    found.append(mirrored)
    except cv2.error:
        pass

    if len(found) == 0:
        try:
            faces_loose = face_cascade_alt.detectMultiScale(
                enhanced,
                scaleFactor=1.08,
                minNeighbors=2,
                minSize=(40, 40),
            )
            if len(faces_loose) > 0:
                found = list(faces_loose)
        except cv2.error:
            pass

    return found


def extract_face_region(img_bgr, face_rect, size=(128, 128)):
    x, y, w, h = face_rect
    pad = int(0.25 * max(w, h))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img_bgr.shape[1], x + w + pad)
    y2 = min(img_bgr.shape[0], y + h + pad)
    face = img_bgr[y1:y2, x1:x2]
    return cv2.resize(face, size)


def preprocess_face_for_encoding(face_bgr):
    """Normalize face image for consistent encoding regardless of lighting."""
    face_bgr = cv2.fastNlMeansDenoisingColored(face_bgr, None, 6, 6, 7, 21)

    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge([l_channel, a_channel, b_channel])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def compute_encoding(face_bgr):
    """
    Compute a lighting-robust, angle-tolerant face encoding.
    Uses CLAHE-normalized grayscale histograms + color histograms.
    """
    face_bgr = preprocess_face_for_encoding(face_bgr)

    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    features = []
    height, width = gray.shape
    block_h, block_w = height // 4, width // 4

    for i in range(4):
        for j in range(4):
            block = gray[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
            hist = cv2.calcHist([block], [0], None, [32], [0, 256])
            features.extend(hist.flatten())

    ycrcb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2YCrCb)
    for channel in range(1, 3):
        hist = cv2.calcHist([ycrcb], [channel], None, [16], [0, 256])
        features.extend(hist.flatten())

    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(sobelx, sobely)
    for i in range(4):
        for j in range(4):
            block = magnitude[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
            hist = cv2.calcHist([block.astype(np.uint8)], [0], None, [16], [0, 256])
            features.extend(hist.flatten())

    encoding = np.array(features, dtype=np.float32)
    norm = np.linalg.norm(encoding)
    if norm > 0:
        encoding = encoding / norm
    return encoding


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def decode_image(b64_str):
    if not isinstance(b64_str, str) or not b64_str.strip():
        return None

    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        return cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


ENCODING_DIM = 800  # 512 gray + 32 color + 256 gradient


def _safe_status(status_value):
    status = (status_value or "").strip().upper()
    if status not in {"EARLY", "ON TIME", "LATE"}:
        status = "ON TIME"
    return status


def load_all_encodings():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, class, photo, encoding FROM students WHERE encoding IS NOT NULL")
        rows = c.fetchall()

    students = []
    for sid, name, cls, photo, enc_blob in rows:
        if not enc_blob:
            continue

        enc = np.frombuffer(enc_blob, dtype=np.float32)

        # Re-encode if stored encoding has old dimension
        if len(enc) != ENCODING_DIM:
            if photo and os.path.exists(photo):
                img = cv2.imread(photo)
                if img is None:
                    continue
                enc = compute_encoding(img)
                with sqlite3.connect(DB_PATH) as update_conn:
                    update_conn.execute(
                        "UPDATE students SET encoding=? WHERE id=?",
                        (enc.tobytes(), sid),
                    )
                    update_conn.commit()
            else:
                continue

        students.append({"id": sid, "name": name, "class": cls, "encoding": enc})

    return students


def get_attendance_status(now_time=None):
    now_time = now_time or datetime.now().time()
    if ON_TIME_START <= now_time <= ON_TIME_END:
        return "ON TIME"
    if now_time > ON_TIME_END:
        return "LATE"
    return "EARLY"


def parse_request_json():
    return request.get_json(silent=True) or {}


def _parse_date(value):
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_time(value):
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return datetime.strptime(raw, "%H:%M:%S").time()
    except ValueError:
        return None


def resolve_client_clock(payload=None):
    """
    Use browser-provided local date/time when available; otherwise fallback
    to server clock.
    """
    payload = payload or {}
    now = datetime.now()

    client_date = _parse_date(payload.get("client_date"))
    client_time = _parse_time(payload.get("client_time"))

    date_text = client_date.strftime("%Y-%m-%d") if client_date else now.strftime("%Y-%m-%d")
    time_text = client_time.strftime("%H:%M:%S") if client_time else now.strftime("%H:%M:%S")
    status_time = client_time if client_time else now.time()

    return date_text, time_text, status_time


@app.route("/")
def index():
    return jsonify(
        {
            "name": "FaceAttend API",
            "status": "ok",
            "version": "1.0",
        }
    )


@app.route("/api/register", methods=["POST"])
def register_student():
    data = parse_request_json()
    student_id = str(data.get("id", "")).strip()
    name = str(data.get("name", "")).strip()
    cls = str(data.get("class", "")).strip()
    photos = data.get("photos", [])

    if not photos and data.get("photo"):
        photos = [data["photo"]]

    if not isinstance(photos, list):
        photos = []

    if not student_id or not name or not photos:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "ID, name and at least one photo are required.",
                }
            ),
            400,
        )

    all_encodings = []
    first_face_region = None

    for i, photo_b64 in enumerate(photos, start=1):
        img = decode_image(photo_b64)
        if img is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Invalid image data in photo {i}.",
                    }
                ),
                400,
            )

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = detect_faces(gray)

        if len(faces) == 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"No face detected in photo {i}. Please use a clear face photo.",
                    }
                ),
                400,
            )

        largest = max(faces, key=lambda f: f[2] * f[3])
        face_region = extract_face_region(img, largest)
        encoding = compute_encoding(face_region)
        all_encodings.append(encoding)

        if first_face_region is None:
            first_face_region = face_region

    avg_encoding = np.mean(all_encodings, axis=0).astype(np.float32)
    norm = np.linalg.norm(avg_encoding)
    if norm > 0:
        avg_encoding = avg_encoding / norm

    os.makedirs(STUDENT_DIR, exist_ok=True)
    photo_path = os.path.join(STUDENT_DIR, f"{student_id}.jpg")
    cv2.imwrite(photo_path, first_face_region)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        exists = c.fetchone() is not None

        if exists:
            c.execute(
                """
                UPDATE students
                SET name=?, class=?, photo=?, encoding=?, created=?
                WHERE id=?
                """,
                (
                    name,
                    cls,
                    photo_path,
                    avg_encoding.tobytes(),
                    datetime.now().isoformat(),
                    student_id,
                ),
            )
            message = f"Student '{name}' updated with {len(photos)} photo(s)."
        else:
            c.execute(
                """
                INSERT INTO students (id, name, class, photo, encoding, created)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    name,
                    cls,
                    photo_path,
                    avg_encoding.tobytes(),
                    datetime.now().isoformat(),
                ),
            )
            message = f"Student '{name}' registered with {len(photos)} photo(s)."

        conn.commit()

    return jsonify({"success": True, "message": message})


@app.route("/api/detect", methods=["POST"])
def detect_only():
    data = parse_request_json()
    photo_b64 = data.get("frame", "")
    if not photo_b64:
        return jsonify({"success": False, "faces": []})

    img = decode_image(photo_b64)
    if img is None:
        return jsonify({"success": False, "faces": []})

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detect_faces(gray)
    if len(faces) == 0:
        return jsonify({"success": True, "faces": []})

    students = load_all_encodings()
    results = []
    today, _, _ = resolve_client_clock(data)

    for face_rect in faces:
        x, y, w, h = [int(v) for v in face_rect]
        face_region = extract_face_region(img, face_rect)
        query_enc = compute_encoding(face_region)

        best_score = -1
        best_student = None

        for student in students:
            score = cosine_similarity(query_enc, student["encoding"])
            if score > best_score:
                best_score = score
                best_student = student

        if best_score >= RECOGNITION_THRESHOLD and best_student:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id FROM attendance WHERE student_id=? AND date=?",
                    (best_student["id"], today),
                )
                already = c.fetchone() is not None

            results.append(
                {
                    "recognized": True,
                    "name": best_student["name"],
                    "student_id": best_student["id"],
                    "class": best_student["class"],
                    "score": round(best_score, 3),
                    "already_marked": already,
                    "bbox": [x, y, w, h],
                }
            )
        else:
            results.append(
                {
                    "recognized": False,
                    "name": "Unknown",
                    "bbox": [x, y, w, h],
                    "score": round(best_score, 3) if best_score >= 0 else 0,
                }
            )

    return jsonify({"success": True, "faces": results})


@app.route("/api/scan", methods=["POST"])
def scan_face():
    data = parse_request_json()
    photo_b64 = data.get("frame", "")

    if not photo_b64:
        return jsonify({"success": False, "message": "No frame provided."}), 400

    img = decode_image(photo_b64)
    if img is None:
        return jsonify({"success": False, "message": "Invalid image."}), 400

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detect_faces(gray)
    if len(faces) == 0:
        return jsonify({"success": False, "message": "No face detected.", "faces": []})

    students = load_all_encodings()
    if not students:
        return jsonify({"success": False, "message": "No students registered yet.", "faces": []})

    today, mark_time, status_time = resolve_client_clock(data)
    current_status = get_attendance_status(status_time)

    results = []
    for face_rect in faces:
        x, y, w, h = [int(v) for v in face_rect]
        face_region = extract_face_region(img, face_rect)
        query_enc = compute_encoding(face_region)

        best_score = -1
        best_student = None
        for student in students:
            score = cosine_similarity(query_enc, student["encoding"])
            if score > best_score:
                best_score = score
                best_student = student

        if best_score >= RECOGNITION_THRESHOLD and best_student:
            sid = best_student["id"]
            sname = best_student["name"]
            scls = best_student["class"]

            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT time, status FROM attendance WHERE student_id=? AND date=?",
                    (sid, today),
                )
                already = c.fetchone()

                if already:
                    saved_time, saved_status = already
                    final_status = _safe_status(saved_status)
                    already_marked = True
                else:
                    final_status = _safe_status(current_status)
                    c.execute(
                        """
                        INSERT INTO attendance (student_id, name, class, date, time, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (sid, sname, scls, today, mark_time, final_status),
                    )
                    conn.commit()
                    saved_time = mark_time
                    already_marked = False

            results.append(
                {
                    "recognized": True,
                    "already_marked": already_marked,
                    "student_id": sid,
                    "name": sname,
                    "class": scls,
                    "score": round(best_score, 3),
                    "bbox": [x, y, w, h],
                    "time": saved_time,
                    "status": final_status,
                    "late": final_status == "LATE",
                }
            )
        else:
            results.append(
                {
                    "recognized": False,
                    "name": "Unknown",
                    "message": "Unknown student",
                    "bbox": [x, y, w, h],
                    "score": round(best_score, 3) if best_score >= 0 else 0,
                }
            )

    return jsonify({"success": True, "faces": results})


@app.route("/api/records", methods=["GET"])
def get_records():
    date_filter = request.args.get("date", "")
    name_filter = request.args.get("name", "")
    cls_filter = request.args.get("class", "")

    query = "SELECT student_id, name, class, date, time, status FROM attendance WHERE 1=1"
    params = []

    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)
    if name_filter:
        query += " AND name LIKE ?"
        params.append(f"%{name_filter}%")
    if cls_filter:
        query += " AND class = ?"
        params.append(cls_filter)

    query += " ORDER BY date DESC, time DESC"

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()

    records = [
        {
            "student_id": row[0],
            "name": row[1],
            "class": row[2],
            "date": row[3],
            "time": row[4],
            "status": _safe_status(row[5]),
        }
        for row in rows
    ]

    return jsonify({"success": True, "records": records})


@app.route("/api/records", methods=["DELETE"])
def clear_records():
    return _clear_attendance_records()


@app.route("/api/records/clear", methods=["POST"])
def clear_records_fallback():
    return _clear_attendance_records()


def _clear_attendance_records():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM attendance")
        deleted_count = c.fetchone()[0]
        c.execute("DELETE FROM attendance")
        conn.commit()

    return jsonify(
        {
            "success": True,
            "deleted": deleted_count,
            "message": f"Cleared {deleted_count} attendance record(s).",
        }
    )


@app.route("/api/students", methods=["GET"])
def get_students():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, class, created FROM students ORDER BY name")
        rows = c.fetchall()

    students = [
        {"id": row[0], "name": row[1], "class": row[2], "created": row[3]}
        for row in rows
    ]
    return jsonify({"success": True, "students": students})


@app.route("/api/students/<sid>", methods=["DELETE"])
def delete_student(sid):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE id=?", (sid,))
        c.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
        conn.commit()

    photo = os.path.join(STUDENT_DIR, f"{sid}.jpg")
    if os.path.exists(photo):
        os.remove(photo)

    return jsonify({"success": True, "message": "Student deleted."})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    requested_date = str(request.args.get("date", "")).strip()
    parsed_date = _parse_date(requested_date)
    today = parsed_date.strftime("%Y-%m-%d") if parsed_date else datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM students")
        total_students = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,))
        today_total = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM attendance WHERE date=? AND status IN ('ON TIME', 'EARLY')",
            (today,),
        )
        today_ontime = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='LATE'", (today,))
        today_late = c.fetchone()[0]

    return jsonify(
        {
            "total_students": total_students,
            "today_total": today_total,
            "today_ontime": today_ontime,
            "today_late": today_late,
            "today": today,
        }
    )


@app.route("/student_images/<filename>")
def student_image(filename):
    return send_from_directory(STUDENT_DIR, filename)


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "9090")),
    )
