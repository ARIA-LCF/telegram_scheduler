from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import database as db
import gemini_processor as gemini
import chart_generator as chart_gen
from scheduler import TaskScheduler
import config
from datetime import datetime
import os
import io

# ایجاد دایرکتوری برای فایل‌های موقت
os.makedirs('temp', exist_ok=True)

class TelegramSchedulerBot:
    def __init__(self):
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        self.scheduler = TaskScheduler(config.BOT_TOKEN)
        self.setup_handlers()
    
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        
        # دستورات
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("today", self.show_today_tasks))
        self.application.add_handler(CommandHandler("schedule", self.show_schedule))
        self.application.add_handler(CommandHandler("summary", self.show_weekly_summary))
        self.application.add_handler(CommandHandler("add", self.add_task_command))
        
        # پیام‌ها
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        
        # callback queries برای دکمه‌ها
        self.application.add_handler(CallbackQueryHandler(self.handle_button_click))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        db.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = (
            "🤖 **به ربات برنامه‌ریزی هوشمند خوش آمدید!**\n\n"
            "**قابلیت‌های اصلی:**\n"
            "✅ تنظیم برنامه درسی، کاری و ورزشی\n"
            "🔔 یادآوری خودکار با Google Gemini AI\n"
            "🎯 درک ویس‌های فارسی و تنظیم برنامه\n"
            "📊 گزارش روزانه با نمودارهای زیبا\n"
            "⏰ برنامه پیش‌فرض هوشمند\n"
            "📈 تحلیل بهره‌وری هفتگی\n\n"
            "**دستورات سریع:**\n"
            "/today - برنامه امروز\n"
            "/schedule - برنامه‌های آینده\n"
            "/summary - نمودار بهره‌وری\n"
            "/add - اضافه کردن تسک جدید\n\n"
            "می‌تونید متن بفرستید یا ویس ضبط کنید!"
        )
        
        keyboard = [
            [KeyboardButton("📅 برنامه امروز"), KeyboardButton("➕ اضافه کردن تسک")],
            [KeyboardButton("🎯 برنامه پیش‌فرض"), KeyboardButton("📊 گزارش هفتگی")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /add برای اضافه کردن تسک"""
        await update.message.reply_text(
            "لطفاً تسک خود را به صورت متن یا ویس ارسال کنید. مثال‌ها:\n\n"
            "• \"فردا ساعت ۱۰ جلسه ریاضی\"\n"
            "• \"پس‌فردا امتحان فیزیک دارم\"\n"
            "• \"هر روز ساعت ۱۸ باشگاه\"\n"
            "• \"شنبه ساعت ۱۴ جلسه کاری\""
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام متنی"""
        user_text = update.message.text
        user_id = update.effective_user.id
        
        # پردازش دکمه‌های کیبورد
        if user_text == "📅 برنامه امروز":
            await self.show_today_tasks(update, context)
        elif user_text == "➕ اضافه کردن تسک":
            await self.add_task_command(update, context)
        elif user_text == "🎯 برنامه پیش‌فرض":
            await self.show_default_schedule(update, context)
        elif user_text == "📊 گزارش هفتگی":
            await self.show_weekly_summary(update, context)
        else:
            # پردازش با Gemini AI
            await update.message.reply_text("🔄 در حال پردازش درخواست شما با Gemini AI...")
            
            task_data = gemini.gemini_processor.parse_schedule_request(user_text)
            
            if task_data and task_data.get('confidence', 0) > 0.3:
                task = db.db.add_task(user_id, task_data)
                self.scheduler.schedule_task_reminder(task)
                
                response_text = (
                    f"✅ **تسک با Gemini AI ثبت شد!**\n\n"
                    f"📝 **عنوان:** {task_data['task_title']}\n"
                    f"🎯 **نوع:** {task_data['task_type']}\n"
                    f"📅 **تاریخ:** {task_data['scheduled_date']}\n"
                    f"⏰ **زمان:** {task_data['scheduled_time']}\n"
                    f"🔔 **یادآوری:** {task_data['reminder_before']} دقیقه قبل\n"
                    f"⏱ **مدت:** {task_data['duration']} دقیقه\n"
                    f"📋 **توضیحات:** {task_data.get('notes', 'بدون توضیح')}\n\n"
                    f"اعتماد: {task_data.get('confidence', 0)*100:.1f}%"
                )
                
                await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    "❌ متوجه درخواست شما نشدم. لطفاً واضح‌تر بیان کنید.\n\n"
                    "**مثال‌های صحیح:**\n"
                    "• \"فردا ساعت ۱۰ جلسه ریاضی\"\n"
                    "• \"پس‌فردا امتحان فیزیک دارم\"\n"
                    "• \"شنبه ساعت ۱۴ جلسه کاری\"\n"
                    "• \"هر روز ساعت ۱۸ باشگاه برم\""
                )
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام ویس"""
        await update.message.reply_text("🔊 در حال پردازش ویس شما با Whisper و Gemini...")
        
        voice_file = await update.message.voice.get_file()
        file_path = f"temp/voice_{update.effective_user.id}.ogg"
        await voice_file.download_to_drive(file_path)
        
        # تبدیل ویس به متن با Whisper
        transcribed_text = gemini.gemini_processor.transcribe_audio(file_path)
        
        if transcribed_text:
            await update.message.reply_text(f"📝 **متن استخراج شده:**\n{transcribed_text}")
            
            # پردازش متن با Gemini
            task_data = gemini.gemini_processor.parse_schedule_request(transcribed_text)
            
            if task_data and task_data.get('confidence', 0) > 0.3:
                task = db.db.add_task(update.effective_user.id, task_data)
                self.scheduler.schedule_task_reminder(task)
                
                response_text = (
                    f"✅ **تسک از ویس شما ثبت شد!**\n\n"
                    f"📝 {task_data['task_title']}\n"
                    f"🎯 نوع: {task_data['task_type']}\n"
                    f"📅 تاریخ: {task_data['scheduled_date']}\n"
                    f"⏰ زمان: {task_data['scheduled_time']}\n"
                    f"🔔 یادآوری: {task_data['reminder_before']} دقیقه قبل"
                )
                
                await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    "❌ متوجه محتوای ویس نشدم. لطفاً دوباره تلاش کنید.\n\n"
                    "**مثال‌های صحیح:**\n"
                    "\"فردا ساعت ده جلسه ریاضی دارم\"\n"
                    "\"پس فردا امتحان فیزیک دارم\"\n"
                    "\"شنبه ساعت دوازده جلسه کاری دارم\""
                )
        else:
            await update.message.reply_text("❌ خطا در پردازش ویس. لطفاً دوباره تلاش کنید.")
        
        # حذف فایل موقت
        try:
            os.remove(file_path)
        except:
            pass
    
    async def show_today_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش تسک‌های امروز"""
        user_id = update.effective_user.id
        today = datetime.now().strftime('%Y-%m-%d')
        tasks = db.db.get_today_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text(
                "📭 هیچ تسکی برای امروز ثبت نشده است.\n\n"
                "می‌توانید با دستور /add یا ارسال ویس تسک جدید اضافه کنید."
            )
            return
        
        tasks_text = "📅 **برنامه امروز شما:**\n\n"
        completed_count = 0
        
        for i, task in enumerate(tasks, 1):
            status_icon = "✅" if task.status == 'completed' else "⏳" if task.status == 'pending' else "❌"
            if task.status == 'completed':
                completed_count += 1
                
            tasks_text += (
                f"{i}. {status_icon} **{task.title}**\n"
                f"   ⏰ {task.scheduled_time} | 🎯 {task.task_type} | ⏱ {task.duration} دقیقه\n"
                f"   📝 {task.notes or 'بدون توضیح'}\n\n"
            )
        
        tasks_text += f"📊 **پیشرفت:** {completed_count}/{len(tasks)} تکمیل شده"
        
        # ارسال نمودار
        chart_img = chart_gen.chart_generator.generate_daily_chart(user_id, today)
        if chart_img:
            await update.message.reply_photo(
                photo=chart_img,
                caption=tasks_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(tasks_text, parse_mode='Markdown')
    
    async def show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش برنامه‌های آینده"""
        user_id = update.effective_user.id
        upcoming_tasks = db.db.get_upcoming_tasks(user_id, hours=72)  # 3 روز آینده
        
        if not upcoming_tasks:
            await update.message.reply_text(
                "📭 هیچ برنامه آینده‌ای ثبت نشده است.\n\n"
                "می‌توانید با دستور /add یا ارسال ویس تسک جدید اضافه کنید."
            )
            return
        
        schedule_text = "📋 **برنامه‌های آینده شما (۳ روز آینده):**\n\n"
        
        # گروه‌بندی بر اساس تاریخ
        tasks_by_date = {}
        for task in upcoming_tasks:
            if task.scheduled_date not in tasks_by_date:
                tasks_by_date[task.scheduled_date] = []
            tasks_by_date[task.scheduled_date].append(task)
        
        for date in sorted(tasks_by_date.keys()):
            schedule_text += f"📅 **{date}**\n"
            for task in tasks_by_date[date]:
                schedule_text += (
                    f"  ⏰ {task.scheduled_time} - {task.title} ({task.task_type})\n"
                )
            schedule_text += "\n"
        
        await update.message.reply_text(schedule_text, parse_mode='Markdown')
    
    async def show_weekly_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش نمودار بهره‌وری هفتگی"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("📈 در حال تولید نمودار بهره‌وری هفتگی...")
        
        chart_img = chart_gen.chart_generator.generate_productivity_chart(user_id)
        
        if chart_img:
            await update.message.reply_photo(
                photo=chart_img,
                caption="📊 **نمودار بهره‌وری هفتگی شما**\n\n"
                       "این نمودار عملکرد شما را در ۷ روز گذشته نشان می‌دهد."
            )
        else:
            await update.message.reply_text(
                "📊 داده کافی برای تولید نمودار وجود ندارد.\n"
                "حداقل ۲ روز فعالیت نیاز است."
            )
    
    async def show_default_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش برنامه پیش‌فرض"""
        schedule_text = "⏰ **برنامه پیش‌فرض هوشمند:**\n\n"
        
        for time, activity in config.DEFAULT_SCHEDULE.items():
            schedule_text += f"🕒 **{time}** - {activity}\n"
        
        schedule_text += (
            "\n💡 **نکته:** اگر برنامه خاصی ثبت نکنید، این زمان‌بندی به صورت خودکار اجرا می‌شود "
            "و یادآوری دریافت خواهید کرد."
        )
        
        await update.message.reply_text(schedule_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = (
            "🤖 **راهنمای ربات برنامه‌ریزی هوشمند**\n\n"
            "**دستورات اصلی:**\n"
            "/start - شروع کار با ربات\n"
            "/today - نمایش برنامه امروز\n"
            "/schedule - برنامه‌های آینده\n"
            "/summary - نمودار بهره‌وری\n"
            "/add - اضافه کردن تسک جدید\n"
            "/help - این راهنما\n\n"
            "**نحوه استفاده:**\n"
            "• متن بفرستید: \"فردا ساعت ۱۰ جلسه دارم\"\n"
            "• ویس ضبط کنید: همین متن را بگویید\n"
            "• از دکمه‌های کیبورد استفاده کنید\n\n"
            "**فناوری‌های استفاده شده:**\n"
            "🤖 Google Gemini AI - پردازش هوشمند\n"
            "🔊 OpenAI Whisper - تبدیل ویس به متن\n"
            "📊 Plotly - نمودارهای زیبا\n"
            "⏰ APScheduler - زمان‌بندی پیشرفته"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کلیک روی دکمه‌ها"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text="این قابلیت به زودی اضافه خواهد شد!")
    
    def run(self):
        """اجرای ربات"""
        print("🤖 ربات برنامه‌ریزی هوشمند با Gemini AI در حال اجرا...")
        print("🔧 فناوری‌ها: Google Gemini + Whisper + Plotly")
        self.application.run_polling()

if __name__ == "__main__":
    bot = TelegramSchedulerBot()
    bot.run()
