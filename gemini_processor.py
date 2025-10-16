import google.generativeai as genai
import whisper
import json
import re
from datetime import datetime, timedelta
import config

class GeminiProcessor:
    def __init__(self):
        # تنظیم API Key برای Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # تنظیم مدل Gemini
        self.model = genai.GenerativeModel('gemini-pro')
        
        # مدل Whisper برای تبدیل صوت به متن (رایگان)
        self.whisper_model = whisper.load_model("base")
    
    def transcribe_audio(self, audio_path):
        """تبدیل ویس به متن با Whisper"""
        try:
            result = self.whisper_model.transcribe(audio_path, language="fa")
            return result["text"]
        except Exception as e:
            print(f"Error in transcription: {e}")
            return None
    
    def parse_schedule_request(self, text):
        """پردازش متن و استخراج اطلاعات برنامه با Gemini"""
        
        prompt = f"""
        شما یک دستیار برنامه‌ریزی هوشمند فارسی هستید. متن کاربر را تحلیل کرده و اطلاعات مربوط به برنامه‌ریزی را استخراج کنید.
        
        قوانین مهم:
        - اگر تاریخ ذکر نشده، امروز ({datetime.now().strftime('%Y-%m-%d')}) در نظر گرفته شود
        - اگر زمان ذکر نشده، بر اساس上下文 زمان مناسب پیشنهاد دهید
        - نوع تسک را تشخیص دهید: lesson, work, sport, personal, exam
        - مدت زمان پیش‌فرض 60 دقیقه است مگر اینکه کاربر مشخص کند
        - یادآوری پیش‌فرض 15 دقیقه قبل است
        
        متن کاربر: "{text}"
        
        لطفاً خروجی را فقط و فقط به صورت JSON برگردانید بدون هیچ متن اضافی:
        {{
            "task_title": "عنوان تسک به فارسی",
            "task_type": "lesson/work/sport/personal/exam",
            "scheduled_date": "YYYY-MM-DD",
            "scheduled_time": "HH:MM",
            "duration": عدد به دقیقه,
            "reminder_before": عدد به دقیقه,
            "notes": "توضیحات اضافی به فارسی",
            "confidence": میزان اطمینان از 0 تا 1
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # تمیز کردن خروجی - حذف markdown blocks اگر وجود دارد
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # پارس کردن JSON
            task_data = json.loads(result_text)
            
            # اعتبارسنجی داده‌ها
            if not self.validate_task_data(task_data):
                return self.fallback_parsing(text)
                
            return task_data
            
        except Exception as e:
            print(f"Error in Gemini parsing: {e}")
            # Fallback به روش ساده‌تر
            return self.fallback_parsing(text)
    
    def validate_task_data(self, task_data):
        """اعتبارسنجی داده‌های استخراج شده"""
        required_fields = ['task_title', 'task_type', 'scheduled_date', 'scheduled_time']
        
        for field in required_fields:
            if field not in task_data or not task_data[field]:
                return False
        
        # اعتبارسنجی تاریخ
        try:
            datetime.strptime(task_data['scheduled_date'], '%Y-%m-%d')
            datetime.strptime(task_data['scheduled_time'], '%H:%M')
        except:
            return False
            
        return True
    
    def fallback_parsing(self, text):
        """روش جایگزین برای زمانی که Gemini失败 می‌شود"""
        # تشخیص نوع تسک
        task_types = {
            "درس": ["درس", "مدرسه", "کلاس", "امتحان", "تحصیل", "دانشگاه", "کالج"],
            "کار": ["کار", "پروژه", "جلسه", "اداری", "شرکت", "دفتر", "کاری"],
            "ورزش": ["ورزش", "باشگاه", "بدنسازی", "دویدن", "تمرین", " fitness", " gym"],
            "امتحان": ["امتحان", "تست", "آزمون", "کوئیز", " آزمون"],
            "شخصی": ["ملاقات", "دکتر", "استراحت", "ناهار", "شام", "صبحانه", "خواب"]
        }
        
        detected_type = "personal"
        for task_type, keywords in task_types.items():
            if any(keyword in text for keyword in keywords):
                detected_type = task_type
                break
        
        # استخراج زمان
        time_str = self.extract_time(text)
        
        # استخراج تاریخ
        date_str = self.extract_date(text)
        
        return {
            "task_title": self.extract_title(text),
            "task_type": detected_type,
            "scheduled_date": date_str,
            "scheduled_time": time_str,
            "duration": 60,
            "reminder_before": 15,
            "notes": "ثبت شده با پردازش متن",
            "confidence": 0.7
        }
    
    def extract_time(self, text):
        """استخراج زمان از متن"""
        patterns = [
            r'ساعت\s*(\d+)[:]?(\d*)',
            r'(\d+)[:]?(\d*)\s*بعدازظهر',
            r'(\d+)[:]?(\d*)\s*عصر',
            r'(\d+)[:]?(\d*)\s*صبح',
            r'(\d+)[:]?(\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                hour = int(match.group(1))
                minute = match.group(2) if match.group(2) else "00"
                
                # تبدیل به فرمت 24 ساعته
                if ("بعدازظهر" in text or "عصر" in text) and hour < 12:
                    hour += 12
                elif "صبح" in text and hour == 12:
                    hour = 0
                
                return f"{hour:02d}:{minute}"
        
        return "10:00"  # زمان پیش‌فرض
    
    def extract_date(self, text):
        """استخراج تاریخ از متن"""
        today = datetime.now()
        
        if "فردا" in text:
            date = today + timedelta(days=1)
        elif "پس فردا" in text:
            date = today + timedelta(days=2)
        elif "هفته آینده" in text:
            date = today + timedelta(days=7)
        elif "هفته بعد" in text:
            date = today + timedelta(days=7)
        else:
            date = today
        
        return date.strftime("%Y-%m-%d")
    
    def extract_title(self, text):
        """استخراج عنوان از متن"""
        # حذف کلمات اضافی
        stop_words = ["می‌خواهم", "می‌خوام", "باید", "لطفا", "برای", "یک", "یه"]
        words = text.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        return " ".join(filtered_words[:8])  # حداکثر 8 کلمه اول
    
    def generate_daily_summary(self, tasks, completed_tasks):
        """تولید خلاصه روزانه با Gemini"""
        
        task_list = "\n".join([f"- {task.title} ({task.status})" for task in tasks])
        
        prompt = f"""
        شما یک مربی انگیزشی فارسی هستید. بر اساس عملکرد کاربر امروز، یک خلاصه کوتاه و انگیزشی بنویسید.
        
        تسک‌های امروز:
        {task_list}
        
        تسک‌های انجام شده: {len(completed_tasks)} از {len(tasks)}
        
        لطفاً یک خلاصه کوتاه و انرژی‌بخش به فارسی بنویسید (حداکثر 80 کلمه). روی نقاط قوت و پیشرفت کاربر تمرکز کنید.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error in summary generation: {e}")
            return "امروز روز خوبی بود! ادامه بده 💪"

# ایجاد نمونه Gemini Processor
gemini_processor = GeminiProcessor()
