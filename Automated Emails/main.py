import yagmail
import pandas
from news import NewsFeed

df = pandas.read_excel('people.xlsx')

for index, row in df.iterrows():
    news_feed = NewsFeed(interest=row['interest'], from_date='2024-08-20', to_date='2024-08-20', language='en')
    email = yagmail.SMTP(user="ankushkhatri.k@gmail.com", password="xqme tjiv oolc xxdd")
    email.send(to=row['email'], 
            subject=f"Your {row['interest']} news for today!",
            contents=f"Hi {row['name']}\n See what's on about {row['interest']} today. \n {news_feed.get()} \n Ash Mafia")