import os
import random
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

# initialize faker
fake = Faker()

# create data folder
os.makedirs("data", exist_ok=True)

# --- 1. Students Data ---
students = []
classes = ["Grade 9", "Grade 10", "Grade 11", "Grade 12"]

for sid in range(1, 101):
    students.append({
        "student_id": sid,
        "name": fake.name(),
        "class": random.choice(classes)
    })

df_students = pd.DataFrame(students)
df_students.to_csv("data/students.csv", index=False)

# --- 2. Attendance Data ---
attendance = []
start_date = datetime(2025, 1, 1)

for sid in range(1, 101):
    for week in range(12):  # 12 weeks of data
        date = start_date + timedelta(weeks=week)
        attendance.append({
            "student_id": sid,
            "date": date.strftime("%Y-%m-%d"),
            "attendance_percentage": random.randint(60, 100)
        })

df_attendance = pd.DataFrame(attendance)
df_attendance.to_csv("data/attendance.csv", index=False)

# --- 3. Tests Data ---
tests = []

for sid in range(1, 101):
    for test_num in range(5):  # 5 test scores each
        date = start_date + timedelta(days=test_num * 10)
        tests.append({
            "student_id": sid,
            "date": date.strftime("%Y-%m-%d"),
            "score": random.randint(40, 100)
        })

df_tests = pd.DataFrame(tests)
df_tests.to_csv("data/tests.csv", index=False)

# --- 4. Attempts Data ---
subjects = ["Math", "Science", "English", "History"]

attempts = []
for sid in range(1, 101):
    for subj in subjects:
        attempts.append({
            "student_id": sid,
            "subject": subj,
            "attempts": random.randint(1, 5)
        })

df_attempts = pd.DataFrame(attempts)
df_attempts.to_csv("data/attempts.csv", index=False)

# --- 5. Fees Data ---
fees = []
for sid in range(1, 101):
    fees.append({
        "student_id": sid,
        "pending_amount": random.choice([0, 0, 0, 500, 1000, 2000])  # more likely to have 0
    })

df_fees = pd.DataFrame(fees)
df_fees.to_csv("data/fees.csv", index=False)

print("✅ Sample CSVs generated in 'data/' folder with 100 students.")
