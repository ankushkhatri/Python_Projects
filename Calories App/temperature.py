from selectorlib import Extractor
import requests

class Temperature:
    headers = {"Content-Type":"text"}
    base_url = 'https://www.timeanddate.com/weather/'
    yml_path = 'temperature.yaml'

    def __init__(self, country, city):
        self.country = country.replace(" ","-")
        self.city = city.replace(" ","-")

    def _build_url(self):
        return self.base_url + self.country + "/" + self.city
    
    def _scrape(self):
        url = self._build_url()
        extractor = Extractor.from_yaml_file(self.yml_path)
        r = requests.get(url, headers=self.headers)
        full_context = r.text
        raw_content = extractor.extract(full_context)
        return raw_content

    def get(self):
        scraped_content = self._scrape()
        return float(scraped_content['temp'].replace("°C", "").strip())

