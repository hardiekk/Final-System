from flask import Flask, render_template, request, jsonify
import face_recognition
import numpy as np
import cv2
import base64
import os
import pandas as pd
from datetime import datetime, time

app = Flask(__name__, template_folder='templates')

dataset_path = 'dataset'
attendance_file = 'attendance.csv'
known_face_encodings = []
known_face_names = []

print("Loading faces")
for student_folder in os.listdir(dataset_path):
    folder_path = os.path.join(dataset_path, student_folder)
    if os.path.isdir(folder_path):
        for img_name in os.listdir(folder_path):
            try:
                image = face_recognition.load_image_file(os.path.join(folder_path, img_name))
                encodings = face_recognition.face_encodings(image)
                if len(encodings) == 1:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(student_folder)
                else:
                    print(f"Skipping {img_name}, multiple faces")
            except Exception as e:
                print(f"Error loading {img_name}: {e}")
print(f"Loaded faces for {len(set(known_face_names))} students.")

# CSV check/create
if not os.path.exists(attendance_file):
    df = pd.DataFrame(columns=['RollNo_Name', 'Time', 'Subject'])
    df.to_csv(attendance_file, index=False)
else:
    df = pd.read_csv(attendance_file)
    if 'Subject' not in df.columns:
        df['Subject'] = ''
        df.to_csv(attendance_file, index=False)

def mark_attendance(name, subject):
    df = pd.read_csv(attendance_file)
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    already_marked = ((df['RollNo_Name'] == name) & (df['Subject'] == subject) & (df['Time'].str.startswith(date_str))).any()
    if not already_marked:
        new_row = pd.DataFrame({'RollNo_Name': [name], 'Time': [f"{date_str} {time_str}"], 'Subject': [subject]})
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(attendance_file, index=False)
        print(f"Marked attendance: {name}, Subject: {subject}")
        return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/attendance')
def attendance():
    df = pd.read_csv(attendance_file)
    total_students = set(known_face_names)
    present_students = set(df['RollNo_Name'].values)
    absent_students = total_students - present_students
    records = df.to_dict(orient='records')
    stats = {
        'total_students': len(total_students),
        'present_students': len(present_students),
        'absent_students': len(absent_students),
        'absent_list': sorted(list(absent_students))
    }
    return render_template('attendance.html', records=records, stats=stats)

@app.route('/recognize', methods=['POST'])
def recognize():
    data = request.get_json(force=True)
    subject = data.get('subject')
    img_data = data.get('image')

    if not subject or not img_data:
        return jsonify({'error': 'Subject and image required'}), 400

    if not (time(10, 0) <= datetime.now().time() <= time(10, 30)):
        return jsonify({'error': 'Attendance allowed only 14:00-14:30'}), 403

    try:
        encoded = img_data.split(',')[1]
        img = base64.b64decode(encoded)
        npimg = np.frombuffer(img, np.uint8)
        img_cv = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    except Exception as e:
        return jsonify({'error': f'Image decode failed: {e}'}), 500

    face_locations = face_recognition.face_locations(rgb_img)
    encodings = face_recognition.face_encodings(rgb_img, face_locations)
    recognized = []

    for enc in encodings:
        matches = face_recognition.compare_faces(known_face_encodings, enc)
        distances = face_recognition.face_distance(known_face_encodings, enc)
        if len(distances) == 0:
            continue
        best_match = np.argmin(distances)
        if matches[best_match]:
            name = known_face_names[best_match]
            if mark_attendance(name, subject):
                recognized.append(name)

    return jsonify({'names': recognized})

@app.route('/delete_attendance', methods=['POST'])
def delete_attendance():
    data = request.get_json(force=True)
    index = data.get('index')
    print(f"Delete request for index: {index}")
    df = pd.read_csv(attendance_file)
    if index is not None and 0 <= index < len(df):
        df = df.drop(index).reset_index(drop=True)
        df.to_csv(attendance_file, index=False)
        print(f"Deleted row {index}")
        return jsonify({'success': True})
    print("Delete failed: Invalid index")
    return jsonify({'success': False})

if __name__ == '__main__':
    app.run(debug=True)
