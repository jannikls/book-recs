from apscheduler.schedulers.background import BackgroundScheduler
from app.api_reading_lists import fetch_reading_list
from app import models, db

def schedule_reading_list_refresh():
    scheduler = BackgroundScheduler()
    session = next(db.get_db())
    lists = session.query(models.ReadingList).all()
    for rl in lists:
        scheduler.add_job(fetch_reading_list, 'interval', hours=24, args=[rl.id])
    scheduler.start()
    return scheduler
