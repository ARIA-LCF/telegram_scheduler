from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import database as db
import chart_generator as chart_gen
from telegram import Bot
import config

class TaskScheduler:
    def __init__(self, bot_token):
        self.bot = Bot(token=bot_token)
        self.scheduler = BackgroundScheduler()
        self.setup_schedulers()
    
    def setup_schedulers(self):
        """تنظیم زمان‌بندها"""
        
        # خلاصه روزانه هر شب ساعت 22:00
        self.scheduler.add_job(
            self.send_daily_summary,
            trigger=CronTrigger(hour=22, minute=0),
            id='daily_summary'
        )
        
        # چک کردن تسک‌های پیش‌فرض هر 30 دقیقه
        self.scheduler.add_job(
            self.check_default_schedule,
            trigger='interval',
            minutes=30,
            id='default_schedule_check'
        )
        
        # شروع زمان‌بند
        self.scheduler.start()
    
    async def send_daily_summary(self):
        """ارسال خلاصه روزانه برای همه کاربران"""
        users = db.db.session.query(db.User).all()
        
        for user in users:
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                
                # تولید نمودار
                chart_img = chart_gen.chart_generator.generate_daily_chart(user.telegram_id, today)
                
                if chart_img:
                    # ارسال عکس
                    await self.bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=chart_img,
                        caption="📊 خلاصه برنامه امروز شما"
                    )
                
                # ارسال خلاصه متنی
                tasks = db.db.get_today_tasks(user.telegram_id)
                completed_tasks = [t for t in tasks if t.status == 'completed']
                
                summary_text = (
                    f"📅 گزارش روزانه\n\n"
                    f"✅ تسک‌های انجام شده: {len(completed_tasks)}/{len(tasks)}\n"
                    f"📈 میزان بهره‌وری: {int((len(completed_tasks)/len(tasks))*100) if tasks else 0}%\n\n"
                    f"فردا رو هم با انرژی شروع کن! 💪"
                )
                
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=summary_text
                )
                
            except Exception as e:
                print(f"Error sending summary to user {user.telegram_id}: {e}")
    
    async def check_default_schedule(self):
        """چک کردن و اجرای برنامه پیش‌فرض"""
        users = db.db.session.query(db.User).all()
        current_time = datetime.now().strftime('%H:%M')
        
        for user in users:
            try:
                # چک کن اگر کاربر برای زمان فعلی تسکی ثبت نکرده باشد
                today_tasks = db.db.get_today_tasks(user.telegram_id)
                current_hour = datetime.now().strftime('%H:%M')
                
                has_task_now = any(
                    task.scheduled_time <= current_hour <= 
                    (datetime.strptime(task.scheduled_time, '%H:%M') + 
                     timedelta(minutes=task.duration or 60)).strftime('%H:%M')
                    for task in today_tasks
                )
                
                if not has_task_now and current_time in config.DEFAULT_SCHEDULE:
                    default_task = config.DEFAULT_SCHEDULE[current_time]
                    
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"⏰ طبق برنامه پیش‌فرض، الان وقت {default_task} هست!\n"
                             f"آماده‌اید؟"
                    )
                    
            except Exception as e:
                print(f"Error in default schedule for user {user.telegram_id}: {e}")
    
    def schedule_task_reminder(self, task):
        """زمان‌بندی یادآوری برای یک تسک"""
        task_time = datetime.strptime(
            f"{task.scheduled_date} {task.scheduled_time}", 
            '%Y-%m-%d %H:%M'
        )
        reminder_time = task_time - timedelta(minutes=task.reminder_before)
        
        if reminder_time > datetime.now():
            self.scheduler.add_job(
                self.send_task_reminder,
                'date',
                run_date=reminder_time,
                args=[task.id],
                id=f"reminder_{task.id}"
            )
    
    async def send_task_reminder(self, task_id):
        """ارسال یادآوری تسک"""
        task = db.db.session.query(db.Task).filter_by(id=task_id).first()
        if task and task.status == 'pending':
            user = db.db.session.query(db.User).filter_by(telegram_id=task.user_id).first()
            
            if user:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"🔔 یادآوری!\n\n"
                         f"📝 {task.title}\n"
                         f"⏰ ساعت: {task.scheduled_time}\n"
                         f"📅 تاریخ: {task.scheduled_date}\n"
                         f"🎯 نوع: {task.task_type}\n\n"
                         f"آماده باشید!"
                )
