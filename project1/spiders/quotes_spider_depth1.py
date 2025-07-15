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
        raw_content = self.extract_text(response)
        cleaned_content = self.format_text(raw_content)
        self.extracted_data_list.append({"extracted_data": cleaned_content})

    def extract_text(self, response):
        elements = response.xpath('//*[self::h1 or self::h2 or self::h3 or self::p or self::ul or self::ol][not(ancestor::header or ancestor::footer or ancestor::nav or ancestor::aside)]')
        content_tree = []

        current_h1 = current_h2 = current_h3 = None
        current_list = None
        inside_list = False

        for element in elements:
            tag = element.root.tag
            text = ' '.join(element.css('::text').getall()).strip()
            
            if not text:
                continue

            match tag:
                case "h1":
                    current_h1 = {
                        "h1": {
                            "title": text,
                            "content": []
                        }
                    }
                    content_tree.append(current_h1)
                    current_h2 = current_h3 = None

                case "h2":
                    if not current_h1:
                        continue
                    current_h2 = {
                        "h2": {
                            "title": text,
                            "content": []
                        }
                    }
                    current_h1["h1"]["content"].append(current_h2)
                    current_h3 = None

                case "h3":
                    if not current_h2:
                        continue
                    current_h3 = {
                        "h3": {
                            "title": text,
                            "content": []
                        }
                    }
                    current_h2["h2"]["content"].append(current_h3)

                case "p":
                    paragraph = re.sub(r'\s+', ' ', text).strip()

                    if inside_list and current_list is not None:
                        current_list[-1]["content"].append(paragraph)   # Dentro de una lista
                    elif current_h3:
                        current_h3["h3"]["content"].append(paragraph)   # Dentro de h3
                    elif current_h2:
                        current_h2["h2"]["content"].append(paragraph)   # Dentro de h2
                    elif current_h1:
                        current_h1["h1"]["content"].append(paragraph)   # Dentro de h1
                    else:
                        content_tree.append(paragraph)                  # Por separado

                case "ul" | "ol":
                    list_items = []
                    counter = 1

                    # Procesado de lista
                    for li in element.css('li'):
                        li_text = ' '.join(li.css('::text').getall()).strip()
                        if not li_text:
                            continue
                        bullet = f"- {li_text}" if tag == 'ul' else f"{counter}. {li_text}"
                        counter += 1 if tag == 'ol' else 0

                        clean_bullet = re.sub(r'\s+', ' ', bullet).strip()
                        list_items.append({"content": [clean_bullet]})

                    if current_h3:
                        current_h3["h3"]["content"].append({ "list": list_items })  # Dentro de h3
                    elif current_h2:
                        current_h2["h2"]["content"].append({ "list": list_items })  # Dentro de h2
                    elif current_h1:
                        current_h1["h1"]["content"].append({ "list": list_items })  # Dentro de h1
                    else:
                        content_tree.append({ "list": list_items })                 # Por separado

                    # Guardar referencia para insertar futuros <p> dentro del último <li>
                    current_list = list_items
                    inside_list = True

            # Si no es lista, salir del estado de "estoy dentro de lista"
            if tag not in ("ul", "ol", "p"):
                inside_list = False
                current_list = None

        return content_tree

    def add_list(self, element, elements, tag, bigger_list, i):
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

            if links_text:
                bullet += f" {links_text}"

            clean_bullet = re.sub(r'\s+', ' ', bullet).strip()
            if clean_bullet:
                list_content.append(clean_bullet)

        # Convert list to tuple for uniqueness check
        list_content_tuple = tuple(list_content)
        
        # Check for uniqueness before appending
        if list_content_tuple and list_content_tuple not in self.unique_list_contents:
            self.unique_list_contents.add(list_content_tuple)
            if i > 0 and elements[i-1].root.tag == 'p' and \
                bigger_list and isinstance(bigger_list[-1], str):
                last_paragraph = bigger_list.pop() # Get the string paragraph
                bigger_list.append({"content": [last_paragraph] + list_content}) # Create a new list combining
            else:
                bigger_list.append({"content": list_content})
    
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
        def clean_text(text):
            t = re.sub(r"\*\*(.*?)\*\*", r"\1", text)           # Negrita
            t = re.sub(r"\*(.*?)\*", r"\1", t)                  # Cursiva
            t = re.sub(r"__(.*?)__", r"\1", t)                  # Subrayado
            t = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", t)         # Enlaces Markdown
            t = re.sub(r"^\d+\.\s*", "", t)                     # Números enumerados
            t = re.sub(r"^- ", "", t)                           # Guiones de listas
            return t.strip()

        def recurse_format(node):
            if isinstance(node, str):
                return clean_text(node)

            elif isinstance(node, list):
                return [recurse_format(item) for item in node]

            elif isinstance(node, dict):
                new_node = {}
                for key, value in node.items():
                    if key in ["h1", "h2", "h3"] and isinstance(value, dict):
                        new_node[key] = {
                            "title": clean_text(value.get("title", "")),
                            "content": recurse_format(value.get("content", []))
                        }
                    elif key == "list":
                        # Aplanar la lista
                        cleaned_list = []
                        for item in value:
                            if isinstance(item, dict) and "content" in item:
                                for subitem in item["content"]:
                                    cleaned_list.append(clean_text(subitem))
                            elif isinstance(item, str):
                                cleaned_list.append(clean_text(item))
                            elif isinstance(item, list):
                                cleaned_list.extend([clean_text(i) for i in item])
                        new_node["list"] = cleaned_list
                    else:
                        new_node[key] = recurse_format(value)
                return new_node

            return node  # fallback

        return recurse_format(content_tree)

