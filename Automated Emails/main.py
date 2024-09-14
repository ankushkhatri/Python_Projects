import yagmail
import pandas
import datetime
import time
from news import NewsFeed

# while True:
#     if datetime.datetime.now().hour == 15 and datetime.datetime.now().minute == 45:
df = pandas.read_excel('D:\Python_Projects\Automated Emails\people.xlsx')

for index, row in df.iterrows():
    news_feed = NewsFeed(interest = row['interest'], 
                        from_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'), 
                        to_date = datetime.datetime.now().strftime('%Y-%m-%d'), 
                        language = 'en')
    
    email = yagmail.SMTP(user="ankushkhatri.k@gmail.com", password="xqme tjiv oolc xxdd")
    email.send(to=row['email'], 
            subject=f"Your {row['interest']} news for today!",
            contents=f"Hi {row['name']}\n See what's on about {row['interest']} today. \n\n {news_feed.get()} \n Ash Mafia")
        
    # time.sleep(60)