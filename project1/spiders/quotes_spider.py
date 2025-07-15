from pathlib import Path
from urllib import response
import scrapy
import json
import re

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output' 

class QuotesSpider(scrapy.Spider):
    name = "quotes_spider"
    extracted_data = []

    def __init__(self, start_url=None, depth=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [start_url] if start_url else ['http://quotes.toscrape.com/page/1/']
        self.depth_limit = int(depth) if depth else 1
        self.scraped_urls = set()

    def start_requests(self):
        for url in self.start_urls:
            self.scraped_urls.add(url)
            yield scrapy.Request(url=url, callback=self.process_links, meta={'depth': 0})

    def process_links(self, response):
        current_depth = response.meta.get('depth', 0)
        self.parse(response)

        if current_depth < self.depth_limit:
            base_domain = response.url.split('/')[2]
            found_links = response.css('a::attr(href)').getall()

            for link in found_links:
                link_url = response.urljoin(link)
                if link_url not in self.scraped_urls and base_domain in link_url:
                    self.scraped_urls.add(link_url)
                    yield scrapy.Request(url=link_url, callback=self.process_links, meta={'depth': current_depth + 1})

    def parse(self, response):
        paragraphs = self.extract_text(response)
        self.extracted_data.append({"extracted_data": self.format_text(paragraphs)})

    def extract_text(self, response):
        paragraphs = []
        elements = response.xpath('//p | //ul | //ol | //h1 | //h2 | //h3 | //h4 | //h5 | //h6')
        
        for element in elements:
            tag = element.root.tag
            if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                ""
            elif tag in ['ul', 'ol']:
                " "


        
        return paragraphs

    def format_text(self, paragraph_list):
        cleaned = []
        for item in paragraph_list:
            if isinstance(item, list):
                cleaned_bullets = [re.sub(r"\*\*(.*?)\*\*", r"\1", bullet) for bullet in item]
                cleaned.append(cleaned_bullets)
            else:
                cleaned.append(re.sub(r"\*\*(.*?)\*\*", r"\1", item))
        return cleaned

    def closed(self, reason):
        self.store_json(self.extracted_data)

    def store_json(self, extracted_data):
        output_file = Path('output', 'data.json')
        with output_file.open('w', encoding='utf-8') as f:
            json.dump({"data": extracted_data}, f, ensure_ascii=False, indent=4)