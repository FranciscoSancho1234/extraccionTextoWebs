from pathlib import Path
from urllib.parse import urlparse
import scrapy
import json
import re
import os 

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output' 

class QuotesSpiderDepth1(scrapy.Spider):
    name = "quotes_spider"

    extracted_data_list = []
    handle_httpstatus_list = [404]

    def __init__(self, start_url=None, depth=None, target_path_prefix=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Comprobar valores de los parámetros
        print("Introduced variables")
        print("- Start url: ", start_url)
        print("- Depth: ", depth)
        print("- Target path: ", target_path_prefix)

        # Url de inicio
        if start_url:
            self.start_urls = [start_url]        
        else:
            self.start_urls = ['http://quotes.toscrape.com/page/1/']

        # Profundidad de exploración de páginas web
        if depth:
            self.depth_limit = int(depth)
            if self.depth_limit < 0:
                self.depth_limit = 10
        else:
            self.depth_limit = 10

        # Prefijo de página web
        if target_path_prefix:
            self.target_path_prefix = target_path_prefix
        else:
            self.target_path_prefix = '/'

        self.scrapedUrls = set()            # Inicializar como una instancia
        self.unique_list_contents = set()   # Almacenar contenidos de listas
        
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.process_links, meta={'depth': 0})

    def is_target_path(self, path):

        # Normalizar la ruta (remover barras finales para comparación consistente)
        normalized_path = path.rstrip('/')
        normalized_prefix = self.target_path_prefix.rstrip('/')
        
        return normalized_path.startswith(normalized_prefix)

    def process_links(self, response):
        
        current_depth = response.meta.get('depth', 0)

        # Parse the current page for content
        if response.status == 200:
            self.parse(response)

        if current_depth < self.depth_limit:
            base_domain = urlparse(self.start_urls[0]).netloc
            found_links = response.css('a::attr(href)').getall()
            
            for link in found_links:
                link_url = response.urljoin(link)
                parsed_link = urlparse(link_url)
                
                # Verificar si el link es del mismo dominio y no ha sido procesado
                if (parsed_link.netloc == base_domain and 
                    link_url not in self.scrapedUrls and 
                    self.is_target_path(parsed_link.path)):
                    
                    
                    yield scrapy.Request(url=link_url, callback=self.process_links, meta={'depth': current_depth + 1})
                
    def parse(self, response):
        
        mod_target_path_prefix = str(self.target_path_prefix)
        mod_response = str(response.url)

        if mod_target_path_prefix in mod_response:
            self.scrapedUrls.add(response.url)
            raw_content = self.extract_text(response)
            cleaned_content = self.format_text(raw_content)
            self.extracted_data_list.append({"extracted_data": cleaned_content})

    def extract_text(self, response):
        elements = response.xpath('//*[self::h1 or self::h2 or self::h3 or self::p or self::ul or self::ol][not(ancestor::header or ancestor::footer or ancestor::nav or ancestor::aside)]')
        content_tree = []

        for element in elements:
            text = ' '.join(element.css('::text').getall()).strip()
            less_spaces = re.sub(r'\s+', ' ', text).strip()
            text = less_spaces

            if text:
                content_tree.append(text)

        return content_tree
    
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

    def format_text(self, content_tree):
        array_to_store = []

        for element in content_tree:
            t = re.sub(r"\*\*(.*?)\*\*", r"\1", element)        # Negrita
            t = re.sub(r"\*(.*?)\*", r"\1", t)                  # Cursiva
            t = re.sub(r"__(.*?)__", r"\1", t)                  # Subrayado
            t = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", t)         # Enlaces Markdown
            t = re.sub(r"^\d+\.\s*", "", t)                     # Números enumerados
            t = re.sub(r"^- ", "", t)                           # Guiones de listas
            array_to_store.append(t)

        return array_to_store