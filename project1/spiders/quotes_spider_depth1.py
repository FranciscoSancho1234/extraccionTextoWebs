from pathlib import Path
from urllib.parse import urlparse
import scrapy
import json
import re
import os 

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output' 

class QuotesSpiderDepth1(scrapy.Spider):
    name = "quotes_spider_depth1"

    extracted_data_list = []

    def __init__(self, start_url=None, depth=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_url and depth:
            self.start_urls = [start_url]
            self.depth_limit = int(depth)
        else:
            self.start_urls = ['http://quotes.toscrape.com/page/1/']
            self.depth_limit = 1
        # Initialize scrapedUrls as an instance variable
        self.scrapedUrls = set()
        # Initialize a set to store unique list contents as tuples
        self.unique_list_contents = set()

    def start_requests(self):
        for url in self.start_urls:
            self.scrapedUrls.add(url)
            yield scrapy.Request(url=url, callback=self.process_links, meta={'depth': 0})

    def process_links(self, response):
        
        current_depth = response.meta.get('depth', 0)
        
        # Parse the current page for content
        self.parse(response)
        
        if current_depth < self.depth_limit:
            base_domain = urlparse(self.start_urls[0]).netloc
            found_links = response.css('a::attr(href)').getall()
            for link in found_links:
                link_url = response.urljoin(link)
                if urlparse(link_url).netloc == base_domain and link_url not in self.scrapedUrls:
                    self.scrapedUrls.add(link_url) # Add to set
                    yield scrapy.Request(url=link_url, callback=self.process_links, meta={'depth': current_depth + 1})
                
    def parse(self, response):
        paragraph_list = self.extract_text(response)
        formatted_paragraphs = self.format_text(paragraph_list)
        self.extracted_data_list.append({"extracted_data":formatted_paragraphs})

    def extract_text(self, response):
        paragraphs_list = []
        content_to_append = ""
        elements = response.xpath('//p | //ul | //ol | //h1 | //h2 | //h3 | //h4 | //h5 | //h6')
    
        for i, element in enumerate(elements):
            tag = element.root.tag
            if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                text_content = element.css('::text').getall()

                if text_content:
                    content_to_append = ' '.join(text_content).strip()
                    clean_content = re.sub(r'\s+', ' ', content_to_append).strip()
                    paragraphs_list.append(clean_content)

            elif tag in ['ul', 'ol']:
                contador = 0
                list_content = []

                for li in element.css('li'):
                    element_text = li.css('::text').getall()
                    element_links = li.css('a::attr(title)').getall()

                    full_text = ' '.join(element_text).strip()
                    links_text = ' '.join(element_links).strip()

                    if tag == 'ul':
                        bullet = f"- {full_text}"
                    elif tag == 'ol':
                        contador += 1
                        bullet = f"{contador}. {full_text}"

                    # Añadir los enlaces si existen, al final
                    if links_text:
                        bullet += f" {links_text}"

                    clean_bullet = re.sub(r'\s+', ' ', bullet).strip()
                    if clean_bullet and clean_bullet not in list_content:
                        list_content.append(clean_bullet)

                # Convert list_content to a tuple for set comparison
                list_content_tuple = tuple(list_content)

                if i > 0 and elements[i-1].root.tag == 'p' and paragraphs_list:
                    last_paragraph = paragraphs_list[-1]
                    if list_content:
                        if list_content_tuple not in self.unique_list_contents:
                            self.unique_list_contents.add(list_content_tuple)
                            combined_content = [last_paragraph] + list_content
                            paragraphs_list[-1] = combined_content
                else:
                    if list_content and list_content_tuple not in self.unique_list_contents:
                        self.unique_list_contents.add(list_content_tuple)
                        paragraphs_list.append(list_content)

        return paragraphs_list
    
    # Esta función se ejecuta cuando todo termina
    def closed(self, reason):
        self.store_json(self.extracted_data_list, list(self.scrapedUrls))

    def store_json(self, extracted_data, scraped_urls_list):
        output_file = Path('output', 'data.json')
        
        # Formateo de datos para almacenarlos de una forma más eficiente
        data_to_store = []
        for element in extracted_data:
            data_to_store.append(element["extracted_data"])
        
        final_output = {
            "data": data_to_store,
            "scraped_urls": scraped_urls_list
        }

        with output_file.open('w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)

    def format_text(self, paragraph_list):
        cleaned = []
        for item in paragraph_list:
            if isinstance(item, list):
                cleaned_bullets = []
                for bullet in item:
                    # Aplicar limpieza a cada bullet
                    t = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet)           # Negrita
                    t = re.sub(r"\*(.*?)\*", r"\1", t)                    # Cursiva
                    t = re.sub(r"__(.*?)__", r"\1", t)                    # Subrayado
                    t = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", t)           # Enlaces
                    t = re.sub(r"^\d+\.", "", t, flags=re.MULTILINE)      # Enumeraciones
                    t = re.sub(r"^\* ", "", t, flags=re.MULTILINE)        # Bullets
                    cleaned_bullets.append(t.strip())

                cleaned.append(cleaned_bullets)
            else:
                t = re.sub(r"\*\*(.*?)\*\*", r"\1", item)           # Negrita
                t = re.sub(r"\*(.*?)\*", r"\1", t)                  # Cursiva
                t = re.sub(r"__(.*?)__", r"\1", t)                  # Subrayado
                t = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", t)         # Enlaces
                t = re.sub(r"^\d+\.", "", t, flags=re.MULTILINE)    # Enumeraciones
                t = re.sub(r"^\* ", "", t, flags=re.MULTILINE)      # Bullets

                cleaned.append(t.strip())
        return cleaned
