import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import io
import base64
from database import db

class ChartGenerator:
    def __init__(self):
        self.colors = {
            'lesson': '#FF6B6B',
            'work': '#4ECDC4', 
            'sport': '#45B7D1',
            'personal': '#96CEB4',
            'exam': '#FFEAA7'
        }
    
    def generate_daily_chart(self, user_id, date):
        """تولید نمودار گانت روزانه"""
        
        tasks = db.session.query(db.Task).filter(
            db.Task.user_id == user_id,
            db.Task.scheduled_date == date
        ).all()
        
        if not tasks:
            return None
        
        # آماده‌سازی داده‌ها برای نمودار
        tasks_data = []
        for task in tasks:
            start_time = datetime.strptime(task.scheduled_time, '%H:%M')
            end_time = start_time + pd.Timedelta(minutes=task.duration or 60)
            
            tasks_data.append({
                'Task': task.title,
                'Start': start_time,
                'Finish': end_time,
                'Type': task.task_type,
                'Status': task.status,
                'Description': f"{task.title}\n{task.task_type}\nوضعیت: {task.status}"
            })
        
        df = pd.DataFrame(tasks_data)
        
        # ایجاد نمودار گانت
        fig = px.timeline(
            df, 
            x_start="Start", 
            x_end="Finish", 
            y="Task",
            color="Type",
            color_discrete_map=self.colors,
            title=f"برنامه روزانه - {date}",
            hover_data=["Description"]
        )
        
        fig.update_layout(
            title_x=0.5,
            title_font_size=20,
            font_family="Tahoma",
            font_size=12,
            xaxis_title="زمان",
            yaxis_title="کارها",
            height=400 + len(tasks) * 40
        )
        
        fig.update_xaxes(tickformat="%H:%M")
        fig.update_yaxes(autorange="reversed")
        
        # تبدیل به عکس
        img_bytes = fig.to_image(format="png", width=800, height=600)
        return img_bytes
    
    def generate_productivity_chart(self, user_id, days=7):
        """نمودار بهره‌وری هفتگی"""
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        
        summaries = db.session.query(db.DailySummary).filter(
            db.DailySummary.user_id == user_id,
            db.DailySummary.date >= start_date,
            db.DailySummary.date <= end_date
        ).all()
        
        if not summaries:
            return None
        
        dates = [summary.date for summary in summaries]
        scores = [summary.productivity_score for summary in summaries]
        completed = [summary.completed_tasks for summary in summaries]
        total = [summary.total_tasks for summary in summaries]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates, y=scores,
            mode='lines+markers',
            name='امتیاز بهره‌وری',
            line=dict(color='#4ECDC4', width=3)
        ))
        
        fig.add_trace(go.Bar(
            x=dates, y=completed,
            name='تسک‌های انجام شده',
            marker_color='#FF6B6B'
        ))
        
        fig.update_layout(
            title="نمودار بهره‌وری هفتگی",
            xaxis_title="تاریخ",
            yaxis_title="تعداد/امتیاز",
            barmode='group',
            height=500
        )
        
        img_bytes = fig.to_image(format="png", width=800, height=500)
        return img_bytes

chart_generator = ChartGenerator()
