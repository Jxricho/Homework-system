from sqlalchemy import create_engine, Column, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🌟 แก้ไขตรงนี้: เอาลิงก์ URI ที่ก๊อบปี้มาจาก Supabase ในส่วนที่ 1 มาวางทับตรงนี้ได้เลยครับครู
# (อย่าลืมเปลี่ยนตรงรหัสผ่านให้ถูกต้องนะครับ)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.hlxkyxzomfvwwvcmbyxj:Jxricho130768@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# ปรับการตั้งค่า Engine ให้รองรับการเชื่อมต่อผ่านระบบคลาวด์ออนไลน์
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)  
    grade = Column(String, nullable=False)    
    no = Column(String, nullable=False)
    
class Homework(Base):
    __tablename__ = "homeworks"
    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(Date, nullable=False) 

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(String, primary_key=True, index=True) 
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    homework_id = Column(String, ForeignKey("homeworks.id"), nullable=False)
    scanned_at = Column(Date, nullable=False)
    status = Column(String, default="ส่งแล้ว")

def init_db():
    Base.metadata.create_all(bind=engine)
