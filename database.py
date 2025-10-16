from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    created_at = Column(DateTime, default=datetime.now())

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    task_type = Column(String)  # lesson, work, sport, personal, exam
    scheduled_date = Column(String)  # YYYY-MM-DD
    scheduled_time = Column(String)  # HH:MM
    duration = Column(Integer)  # minutes
    reminder_before = Column(Integer, default=15)  # minutes
    status = Column(String, default='pending')  # pending, completed, missed
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now())

class DailySummary(Base):
    __tablename__ = 'daily_summaries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date = Column(String)  # YYYY-MM-DD
    completed_tasks = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    productivity_score = Column(Integer, default=0)
    notes = Column(Text)
    chart_image_path = Column(String)
    created_at = Column(DateTime, default=datetime.now())

class Database:
    def __init__(self):
        self.engine = create_engine('sqlite:///scheduler.db')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_user(self, telegram_id, username, first_name):
        user = self.session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            self.session.add(user)
            self.session.commit()
        return user

    def add_task(self, user_id, task_data):
        task = Task(
            user_id=user_id,
            title=task_data['task_title'],
            task_type=task_data['task_type'],
            scheduled_date=task_data['scheduled_date'],
            scheduled_time=task_data['scheduled_time'],
            duration=task_data.get('duration', 60),
            reminder_before=task_data.get('reminder_before', 15),
            notes=task_data.get('notes', '')
        )
        self.session.add(task)
        self.session.commit()
        return task

    def get_today_tasks(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        return self.session.query(Task).filter(
            Task.user_id == user_id,
            Task.scheduled_date == today
        ).all()

    def get_upcoming_tasks(self, user_id, hours=24):
        now = datetime.now()
        future = now + timedelta(hours=hours)
        
        tasks = self.session.query(Task).filter(
            Task.user_id == user_id,
            Task.status == 'pending'
        ).all()
        
        upcoming = []
        for task in tasks:
            task_datetime = datetime.strptime(
                f"{task.scheduled_date} {task.scheduled_time}", 
                '%Y-%m-%d %H:%M'
            )
            if now <= task_datetime <= future:
                upcoming.append(task)
        
        return upcoming

    def update_task_status(self, task_id, status, notes=None):
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            if notes:
                task.notes = notes
            self.session.commit()
        return task

db = Database()
