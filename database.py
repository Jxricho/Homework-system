from sqlalchemy import create_engine, Column, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./homework.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)  # 🌟 เพิ่มคอลัมน์ชื่อเล่นนักเรียน
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
    
    id = Column(String, primary_key=True, index=True, autoincrement=False) 
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    homework_id = Column(String, ForeignKey("homeworks.id"), nullable=False)
    scanned_at = Column(Date, nullable=False)
    status = Column(String, default="ส่งแล้ว")

def init_db():
    Base.metadata.create_all(bind=engine)
