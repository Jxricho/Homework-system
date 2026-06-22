from sqlalchemy import create_engine, Column, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. ตั้งชื่อไฟล์ฐานข้อมูล (มันจะสร้างไฟล์ชื่อ homework.db ขึ้นมาให้เองในเครื่อง)
SQLALCHEMY_DATABASE_URL = "sqlite:///./homework.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. สร้างโครงสร้างตารางนักเรียน
class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, index=True) # รหัสนักเรียน (ที่ใช้อ่านจาก QR)
    name = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    no = Column(String, nullable=False)

# 3. สร้างโครงสร้างตารางการบ้าน
class Homework(Base):
    __tablename__ = "homeworks"
    
    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(Date, nullable=False) # วันกำหนดส่งสุดท้าย

# 4. สร้างโครงสร้างตารางบันทึกการตรวจงาน (เมื่อครูกดส่ง)
class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(String, primary_key=True, index=True, autoincrement=False) # เช่น STD001_HW01
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    homework_id = Column(String, ForeignKey("homeworks.id"), nullable=False)
    scanned_at = Column(Date, nullable=False)
    status = Column(String, default="ส่งแล้ว")

# ฟังก์ชันสำหรับสั่งสร้างตารางจริงในคอมพิวเตอร์
def init_db():
    Base.metadata.create_all(bind=engine)