from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import database as db
import os
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

# =================================================================
# 🛠️ ส่วนแจกจ่ายไฟล์ HTML จากโฟลเดอร์ templates

@app.get("/")
def read_home(): return FileResponse(os.path.join("templates", "home.html"))

@app.get("/scan")
def read_index(): return FileResponse(os.path.join("templates", "index.html"))

@app.get("/data.html")
def read_data(): return FileResponse(os.path.join("templates", "data.html"))

@app.get("/add-homework")
def read_add_homework(): return FileResponse(os.path.join("templates", "add-homework.html"))

@app.get("/add-student")
def read_add_student(): return FileResponse(os.path.join("templates", "add-student.html"))

@app.get("/manage-students")
def read_manage_students(): return FileResponse(os.path.join("templates", "manage-students.html"))

@app.get("/student-dashboard")
def read_student_dashboard(): return FileResponse(os.path.join("templates", "student-dashboard.html"))

@app.get("/manage-homeworks")
def read_manage_homeworks(): return FileResponse(os.path.join("templates", "manage-homeworks.html"))

@app.get("/generate-qr-page")
def read_qr_page(): return FileResponse(os.path.join("templates", "generate-qr.html"))

# =================================================================
# 📥 API ระบบหลังบ้านและการดึงข้อมูลจาก Database

@app.get("/api/get-qr/{student_id}")
def get_student_qr(student_id: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=12, border=6)
    qr.add_data(student_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

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
            active_homeworks.append({"id": hw.id, "subject": hw.subject, "title": hw.title})
            
    return {
        "student": {"name": student.name, "nickname": student.nickname if student.nickname else "", "grade": student.grade, "no": student.no},
        "student_id": student.id,
        "available_homeworks": active_homeworks
    }

class SubmitRequest(BaseModel):
    student_id: str
    homework_id: str

@app.post("/api/submit-homework")
def submit_homework(request: SubmitRequest, session: Session = Depends(get_db)):
    hw = session.query(db.Homework).filter(db.Homework.id == request.homework_id).first()
    if not hw: raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการบ้าน")
        
    today = datetime.now().date()
    max_allow_date = hw.due_date + timedelta(days=2)
    if not (hw.due_date <= today <= max_allow_date):
        return {"status": "ignored", "message": "หมดเขตส่งและผ่อนผันแล้ว ไม่บันทึกข้อมูล"}
        
    submission_id = f"{request.student_id}_{request.homework_id}"
    existing = session.query(db.Submission).filter(db.Submission.id == submission_id).first()
    if existing: return {"status": "success", "message": f"นักเรียนเคยส่งงานวิชา {hw.subject} นี้ไปแล้วครับ"}

    new_submission = db.Submission(id=submission_id, student_id=request.student_id, homework_id=request.homework_id, scanned_at=today)
    session.add(new_submission)
    session.commit()
    return {"status": "success", "message": f"บันทึกการส่งงานสำเร็จเรียบร้อยแล้ว!"}

class HomeworkAddRequest(BaseModel):
    id: str
    subject: str
    title: str
    due_date: str

@app.post("/api/add-homework")
def add_homework(request: HomeworkAddRequest, session: Session = Depends(get_db)):
    date_obj = datetime.strptime(request.due_date, "%Y-%m-%d").date()
    existing = session.query(db.Homework).filter(db.Homework.id == request.id).first()
    if existing: raise HTTPException(status_code=400, detail="รหัสการบ้านนี้มีอยู่ในระบบแล้ว")
        
    new_hw = db.Homework(id=request.id, subject=request.subject, title=request.title, due_date=date_obj)
    session.add(new_hw)
    session.commit()
    return {"status": "success", "message": f"เพิ่มการบ้านวิชา {request.subject} สำเร็จ"}

# 🌟 API สำหรับแก้ไขข้อมูลการบ้าน (เพิ่มเข้ามาใหม่ตามเช็กลิสต์)
@app.put("/api/update-homework/{homework_id}")
def update_homework(homework_id: str, request: HomeworkAddRequest, session: Session = Depends(get_db)):
    hw = session.query(db.Homework).filter(db.Homework.id == homework_id).first()
    if not hw: raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการบ้าน")
    try:
        hw.subject = request.subject
        hw.title = request.title
        hw.due_date = datetime.strptime(request.due_date, "%Y-%m-%d").date()
        session.commit()
        return {"status": "success", "message": "แก้ไขข้อมูลการบ้านเรียบร้อยแล้ว"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class StudentAddRequest(BaseModel):
    id: str
    name: str
    nickname: str  # 🌟 เพิ่มช่องรับชื่อเล่น
    grade: str
    no: str

@app.post("/api/add-student")
def add_student(request: StudentAddRequest, session: Session = Depends(get_db)):
    existing = session.query(db.Student).filter(db.Student.id == request.id).first()
    if existing: raise HTTPException(status_code=400, detail="รหัสนักเรียนนี้มีอยู่ในระบบแล้ว")
    try:
        new_student = db.Student(
            id=str(request.id),
            name=request.name,
            nickname=request.nickname,  # 🌟 บันทึกชื่อเล่น
            grade=request.grade,
            no=str(request.no)
        )
        session.add(new_student)
        session.commit()
        return {"status": "success", "message": f"เพิ่มข้อมูล {request.name} สำเร็จ"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/students")
def get_all_students(session: Session = Depends(get_db)):
    students = session.query(db.Student).all()
    # 🌟 ส่งฟิลด์ nickname กลับไปแสดงหน้าเว็บด้วย
    return [{"id": s.id, "name": s.name, "nickname": s.nickname if s.nickname else "", "grade": s.grade, "no": s.no} for s in students]

@app.delete("/api/delete-student/{student_id}")
def delete_student(student_id: str, session: Session = Depends(get_db)):
    student = session.query(db.Student).filter(db.Student.id == student_id).first()
    if not student: raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักเรียน")
    try:
        session.query(db.Submission).filter(db.Submission.student_id == student_id).delete()
        session.delete(student)
        session.commit()
        return {"status": "success", "message": f"ลบข้อมูลของ {student.name} เรียบร้อยแล้ว"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/student-dashboard/{student_id}")
def get_student_dashboard_data(student_id: str, session: Session = Depends(get_db)):
    student = session.query(db.Student).filter(db.Student.id == student_id).first()
    if not student: raise HTTPException(status_code=404, detail="ไม่พบข้อมูลนักเรียน")
        
    submissions = session.query(db.Submission).filter(db.Submission.student_id == student_id).all()
    submitted_list = []
    submitted_hw_ids = set()
    
    for sub in submissions:
        hw = session.query(db.Homework).filter(db.Homework.id == sub.homework_id).first()
        if hw:
            submitted_hw_ids.add(hw.id)
            submitted_list.append({"submission_id": sub.id, "subject": hw.subject, "title": hw.title, "scanned_at": str(sub.scanned_at)})
            
    all_homeworks = session.query(db.Homework).all()
    pending_list = []
    for hw in all_homeworks:
        if hw.id not in submitted_hw_ids:
            pending_list.append({"id": hw.id, "subject": hw.subject, "title": hw.title, "due_date": str(hw.due_date)})
            
    return {
        "student": {"id": student.id, "name": student.name, "nickname": student.nickname if student.nickname else "", "grade": student.grade, "no": student.no},
        "submitted_homeworks": submitted_list,
        "pending_homeworks": pending_list
    }

@app.delete("/api/cancel-submission/{submission_id}")
def cancel_submission(submission_id: str, session: Session = Depends(get_db)):
    submission = session.query(db.Submission).filter(db.Submission.id == submission_id).first()
    if not submission: raise HTTPException(status_code=404, detail="ไม่พบประวัติการส่งงานนี้")
    try:
        session.delete(submission)
        session.commit()
        return {"status": "success", "message": "ยกเลิกบันทึกการส่งงานเรียบร้อย"}
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
    if not hw: raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการบ้านที่ต้องการลบ")
    try:
        session.query(db.Submission).filter(db.Submission.homework_id == homework_id).delete()
        session.delete(hw)
        session.commit()
        return {"status": "success", "message": f"ลบรายการการบ้านเรียบร้อย"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
