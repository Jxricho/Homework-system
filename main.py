from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import database as db
import os
from fastapi.responses import StreamingResponse
import qrcode
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

@app.on_event("startup")
def setup_dummy_data():
    session = db.SessionLocal()
    if session.query(db.Student).count() == 0:
        student1 = db.Student(id="STD001", name="สมชาย ใจดี", grade="ม.1/1", no="1")
        student2 = db.Student(id="STD002", name="สมหญิง รักเรียน", grade="ม.1/1", no="2")
        
        hw1 = db.Homework(id="HW01", subject="คณิตศาสตร์", title="การบวกเศษส่วน", due_date=datetime(2026, 6, 21).date())
        hw2 = db.Homework(id="HW02", subject="วิทยาศาสตร์", title="ระบบสุริยะ", due_date=datetime(2026, 6, 25).date())
        
        session.add_all([student1, student2, hw1, hw2])
        session.commit()
    session.close()

@app.get("/generate-qr-page")
def read_qr_page():
    return FileResponse(os.path.join("templates", "generate-qr.html"))

# 2. API สำหรับเปลี่ยนรหัสนักเรียนเป็นรูปภาพ QR Code ส่งไปแสดงบนหน้าเว็บ
@app.get("/api/get-qr/{student_id}")
def get_student_qr(student_id: str):
    # สร้าง QR Code โดยฝังแค่รหัสนักเรียนลงไปตรงๆ 
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=12,
        border=6,
    )
    qr.add_data(student_id)
    qr.make(fit=True)

    # เปลี่ยนภาพ QR Code ให้เป็นข้อมูลสำหรับส่งผ่านเว็บ (Image Byte Stream)
    img = qr.make_image(fill_color="#000000", back_color="#ffffff") # ใช้สีน้ำตาลเข้มให้เข้ากับธีมเว็บ
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")
# =================================================================
# 🛠️ ส่วนแจกจ่ายไฟล์ HTML จากโฟลเดอร์ templates

@app.get("/")
def read_home():
    return FileResponse(os.path.join("templates", "home.html"))

@app.get("/scan")
def read_index():
    return FileResponse(os.path.join("templates", "index.html"))

@app.get("/data.html")
def read_data():
    return FileResponse(os.path.join("templates", "data.html"))

@app.get("/add-homework")
def read_add_homework():
    return FileResponse(os.path.join("templates", "add-homework.html"))

@app.get("/add-student")
def read_add_student():
    return FileResponse(os.path.join("templates", "add-student.html"))

@app.get("/manage-students")
def read_manage_students():
    return FileResponse(os.path.join("templates", "manage-students.html"))

@app.get("/student-dashboard")
def read_student_dashboard():
    return FileResponse(os.path.join("templates", "student-dashboard.html"))

@app.get("/manage-homeworks")
def read_manage_homeworks():
    return FileResponse(os.path.join("templates", "manage-homeworks.html"))

# =================================================================
# 📥 API ระบบหลังบ้านและการดึงข้อมูลจาก Database

class StudentRequest(BaseModel):
    student_id: str

@app.post("/api/scan-student")
def scan_student(request: StudentRequest, session: Session = Depends(get_db)):
    student = session.query(db.Student).filter(db.Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักเรียนในระบบ")
        
    today = datetime.now().date()
    all_homeworks = session.query(db.Homework).all()
    active_homeworks = []
    
    for hw in all_homeworks:
        max_allow_date = hw.due_date + timedelta(days=2)
        if hw.due_date <= today <= max_allow_date:
            active_homeworks.append({
                "id": hw.id,
                "subject": hw.subject,
                "title": hw.title
            })
            
    return {
        "student": {"name": student.name, "grade": student.grade, "no": student.no},
        "student_id": student.id,
        "available_homeworks": active_homeworks
    }

class SubmitRequest(BaseModel):
    student_id: str
    homework_id: str

@app.post("/api/submit-homework")
def submit_homework(request: SubmitRequest, session: Session = Depends(get_db)):
    hw = session.query(db.Homework).filter(db.Homework.id == request.homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการบ้าน")
        
    today = datetime.now().date()
    max_allow_date = hw.due_date + timedelta(days=2)
    
    if not (hw.due_date <= today <= max_allow_date):
        return {"status": "ignored", "message": "หมดเขตส่งและผ่อนผันแล้ว ไม่บันทึกข้อมูล"}
        
    submission_id = f"{request.student_id}_{request.homework_id}"
    
    existing = session.query(db.Submission).filter(db.Submission.id == submission_id).first()
    if existing:
        return {"status": "success", "message": f"นักเรียนเคยส่งงานวิชา {hw.subject} นี้ไปแล้วครับ"}

    new_submission = db.Submission(
        id=submission_id,
        student_id=request.student_id,
        homework_id=request.homework_id,
        scanned_at=today
    )
    session.add(new_submission)
    session.commit()
    
    return {
        "status": "success",
        "message": f"ติ๊กถูกส่งงานวิชา {hw.subject} ลงฐานข้อมูลสำเร็จเรียบร้อยแล้ว!"
    }

class HomeworkAddRequest(BaseModel):
    id: str
    subject: str
    title: str
    due_date: str

@app.post("/api/add-homework")
def add_homework(request: HomeworkAddRequest, session: Session = Depends(get_db)):
    date_obj = datetime.strptime(request.due_date, "%Y-%m-%d").date()
    existing = session.query(db.Homework).filter(db.Homework.id == request.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="รหัสการบ้านนี้มีอยู่ในระบบแล้ว")
        
    new_hw = db.Homework(id=request.id, subject=request.subject, title=request.title, due_date=date_obj)
    session.add(new_hw)
    session.commit()
    return {"status": "success", "message": f"เพิ่มการบ้านวิชา {request.subject} สำเร็จ"}

# 🌟 เพิ่มเติม: โค้ดรับข้อมูลสำหรับลงทะเบียนนักเรียนใหม่ (จุดที่คุณครูขาดไป)
class StudentAddRequest(BaseModel):
    id: str
    name: str
    grade: str
    no: str

@app.post("/api/add-student")
def add_student(request: StudentAddRequest, session: Session = Depends(get_db)):
    # 1. เช็กความซ้ำซ้อนในตารางอย่างแม่นยำ
    existing = session.query(db.Student).filter(db.Student.id == request.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="รหัสนักเรียนนี้มีอยู่ในระบบแล้วจริง ๆ")
        
    try:
        # 2. บันทึกข้อมูลเข้าตารางฐานข้อมูลจริง (homework.db)
        new_student = db.Student(
            id=str(request.id),
            name=request.name,
            grade=request.grade,
            no=str(request.no)
        )
        session.add(new_student)
        session.commit()
        return {"status": "success", "message": f"เพิ่มข้อมูล {request.name} เข้าฐานข้อมูลสำเร็จ"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดภายในระบบ: {str(e)}")
@app.get("/api/students")
def get_all_students(session: Session = Depends(get_db)):
    students = session.query(db.Student).all()
    return [{"id": s.id, "name": s.name, "grade": s.grade, "no": s.no} for s in students]
@app.delete("/api/delete-student/{student_id}")
def delete_student(student_id: str, session: Session = Depends(get_db)):
    student = session.query(db.Student).filter(db.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักเรียน")
    try:
        # ลบประวัติงานเก่าก่อนเพื่อป้องกันตารางเออเร่อพัวพันกัน
        session.query(db.Submission).filter(db.Submission.student_id == student_id).delete()
        # ลบตัวตนนักเรียนออกจากฐานข้อมูลจริง
        session.delete(student)
        session.commit()
        return {"status": "success", "message": f"ลบข้อมูลของ {student.name} เรียบร้อยแล้ว"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/student-dashboard/{student_id}")
def get_student_dashboard_data(student_id: str, session: Session = Depends(get_db)):
    # 1. ตรวจสอบข้อมูลเด็กนักเรียน
    student = session.query(db.Student).filter(db.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักเรียน")
        
    # 2. ดึงงานที่ส่งแล้วทั้งหมดของเด็กคนนี้
    submissions = session.query(db.Submission).filter(db.Submission.student_id == student_id).all()
    
    submitted_list = []
    submitted_hw_ids = set() # เก็บไอดีงานที่ส่งแล้วไว้เช็กงานค้าง
    
    for sub in submissions:
        hw = session.query(db.Homework).filter(db.Homework.id == sub.homework_id).first()
        if hw:
            submitted_hw_ids.add(hw.id)
            submitted_list.append({
                "submission_id": sub.id,
                "subject": hw.subject,
                "title": hw.title,
                "scanned_at": str(sub.scanned_at)
            })
            
    # 3. ดึงงานทั้งหมดในระบบเพื่อมาหักลบหางานที่ค้างส่ง
    all_homeworks = session.query(db.Homework).all()
    pending_list = []
    
    for hw in all_homeworks:
        if hw.id not in submitted_hw_ids:
            pending_list.append({
                "id": hw.id,
                "subject": hw.subject,
                "title": hw.title,
                "due_date": str(hw.due_date)
            })
            
    return {
        "student": {"id": student.id, "name": student.name, "grade": student.grade, "no": student.no},
        "submitted_homeworks": submitted_list,
        "pending_homeworks": pending_list
    }
@app.delete("/api/cancel-submission/{submission_id}")
def cancel_submission(submission_id: str, session: Session = Depends(get_db)):
    submission = session.query(db.Submission).filter(db.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="ไม่พบประวัติการส่งงานนี้")
    try:
        session.delete(submission)
        session.commit()
        return {"status": "success", "message": "ยกเลิกบันทึกการส่งงานเรียบร้อย สถานะกลับเป็นค้างส่งแล้วครับ"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/homeworks")
def get_all_homeworks(session: Session = Depends(get_db)):
    homeworks = session.query(db.Homework).all()
    return [{"id": h.id, "subject": h.subject, "title": h.title, "due_date": str(h.due_date)} for h in homeworks]
@app.delete("/api/delete-homework/{homework_id}")
def delete_homework(homework_id: str, session: Session = Depends(get_db)):
    hw = session.query(db.Homework).filter(db.Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการบ้านที่ต้องการลบ")
    try:
        # 1. เคลียร์ประวัติเด็กทุกคนที่เคยส่งงานชิ้นนี้ก่อน เพื่อไม่ให้ฐานข้อมูลติด Error (Foreign Key Constraint)
        session.query(db.Submission).filter(db.Submission.homework_id == homework_id).delete()
        # 2. ลบตัวหัวข้อการบ้านชิ้นนี้ออกจากตารางหลัก
        session.delete(hw)
        session.commit()
        return {"status": "success", "message": f"ลบรายการการบ้านวิชา {hw.subject} ออกจากตารางฐานข้อมูลเรียบร้อย"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))