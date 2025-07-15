from pathlib import Path
from urllib import response
import scrapy
import json
import re

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output' 

class QuotesSpider(scrapy.Spider):
    name = "quotes_spider"
    scrapedUrls = []
    paragraphs = []

    def __init__(self, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        else:
            self.start_urls = ['http://quotes.toscrape.com/page/1/']

    def start_requests(self):
        for url in self.start_urls:
            if not url.startswith("http"):
                raise ValueError(f"URL inválida: {url}")
            
            self.scrapedUrls.append(url)
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # Extracción de contenido. Formateo y almacenamiento.
        paragraph_list = self.extract_text(response)

        formatted_paragraphs = self.format_text(paragraph_list)

        self.paragraphs.append({"extracted_data":formatted_paragraphs})
        self.paragraphs.append({"scraped_urls":self.scrapedUrls})
        
        self.store_json()

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
                    paragraphs_list.append(content_to_append)

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

                    list_content.append(bullet)

                # Si el anterior es un párrafo, se guarda junto
                if i > 0 and elements[i-1].root.tag == 'p' and paragraphs_list:
                    last_paragraph = paragraphs_list[-1]
                    if list_content:
                        combined_content = [last_paragraph] + list_content
                        paragraphs_list[-1] = combined_content
                else:
                    if list_content not in paragraphs_list:
                        print("- List content: ", list_content)
                        print("- Paragraph list: ", paragraphs_list)
                        print("\n")
                        paragraphs_list.append(list_content)

        return paragraphs_list

    def store_json(self):
        output_file = Path('output', 'data.json')

        with output_file.open('w', encoding='utf-8') as f:
            json.dump(self.paragraphs, f, ensure_ascii=False, indent=4)


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