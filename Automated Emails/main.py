# 691d6b11568940c0bc7724c97756be37
import requests
from pprint import pprint

class NewsFeed:
    base_url = "https://newsapi.org/v2/everything"
    api_key = "691d6b11568940c0bc7724c97756be37"
    
    def __init__(self, interest, from_date, to_date, language):
        self.interest = interest
        self.from_date = from_date
        self.to_date = to_date
        self.language = language

    def get(self):
        url = f"{self.base_url}?qInTitle={self.interest}&from={self.from_date}&to={self.to_date}&language={self.language}&apiKey={self.api_key}"
        print(url)
        
        res = requests.get(url)
        content = res.json()
        articles = content['articles']

        email_body = ''
        for article in articles:
            email_body += article['title'] + '\n' + article['url'] + '\n\n'

        return email_body
    
news_feed = NewsFeed(interest='aviation', from_date='2024-08-12', to_date='2024-08-12', language='en')
print(news_feed.get())
    