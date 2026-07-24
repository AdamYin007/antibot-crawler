"""Content extraction utilities - HTML to Markdown, link/image extraction, structured data."""
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract structured content from HTML pages."""
    
    @staticmethod
    def html_to_markdown(html: str) -> str:
        """Convert HTML to clean markdown using basic parser (no external deps)."""
        try:
            from html.parser import HTMLParser
            
            class MarkdownConverter(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.result = []
                    self.in_heading = 0
                    self.in_bold = False
                    self.in_italic = False
                    self.in_link = False
                    self.link_text = ""
                    self.link_url = ""
                    self.in_list = False
                    self.list_char = ""
                    self.in_paragraph = False
                    
                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    tag = tag.lower()
                    
                    if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                        self.in_heading = int(tag[1])
                        self.result.append(f'\n{"#" * self.in_heading} ')
                    elif tag in ('strong', 'b'):
                        self.in_bold = True
                    elif tag in ('em', 'i'):
                        self.in_italic = True
                    elif tag == 'a':
                        self.in_link = True
                        self.link_url = attrs_dict.get('href', '')
                        self.link_text = ""
                    elif tag in ('ul', 'ol'):
                        self.in_list = True
                        self.list_char = '-' if tag == 'ul' else '1.'
                    elif tag == 'li':
                        self.result.append(f'\n{self.list_char} ')
                    elif tag == 'br':
                        self.result.append('\n')
                    elif tag == 'p':
                        if self.in_paragraph:
                            self.result.append('\n\n')
                        self.in_paragraph = True
                    elif tag == 'div':
                        if self.in_paragraph:
                            self.result.append('\n')
                    
                def handle_endtag(self, tag):
                    tag = tag.lower()
                    if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                        self.in_heading = 0
                        self.result.append('\n')
                    elif tag in ('strong', 'b'):
                        self.in_bold = False
                    elif tag in ('em', 'i'):
                        self.in_italic = False
                    elif tag == 'a':
                        if self.link_url:
                            self.result.append(f'[{self.link_text}]({self.link_url})')
                        else:
                            self.result.append(self.link_text)
                        self.in_link = False
                    elif tag in ('ul', 'ol'):
                        self.in_list = False
                    elif tag == 'p':
                        self.in_paragraph = False
                        self.result.append('\n\n')
                
                def handle_data(self, data):
                    if self.in_bold:
                        data = f'**{data}**'
                    if self.in_italic:
                        data = f'*{data}*'
                    if self.in_link:
                        self.link_text += data
                    else:
                        self.result.append(data)
            
            converter = MarkdownConverter()
            converter.feed(html)
            text = ''.join(converter.result)
            
            # Clean up whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'[ \t]+', ' ', text)
            return text.strip()
            
        except ImportError:
            # Fallback: basic conversion
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\n+', '\n', text)
            return text.strip()
    
    @staticmethod
    def extract_links(html: str, base_url: str) -> List[str]:
        """Extract all links from HTML."""
        try:
            from html.parser import HTMLParser
        except ImportError:
            return []
        
        class LinkExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
                
            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    for name, value in attrs:
                        if name == 'href' and value:
                            self.links.append(urljoin(base_url, value))
        
        extractor = LinkExtractor()
        extractor.feed(html)
        return list(set(extractor.links))
    
    @staticmethod
    def extract_images(html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract image URLs from HTML."""
        try:
            from html.parser import HTMLParser
        except ImportError:
            return []
        
        class ImageExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images = []
                
            def handle_starttag(self, tag, attrs):
                if tag == 'img':
                    src = None
                    alt = None
                    for name, value in attrs:
                        if name == 'src' and value:
                            src = urljoin(base_url, value)
                        elif name == 'alt':
                            alt = value
                    if src:
                        self.images.append({"url": src, "alt": alt or ""})
        
        extractor = ImageExtractor()
        extractor.feed(html)
        return extractor.images
    
    @staticmethod
    def extract_structured_data(html: str, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract structured data using CSS selectors and XPath patterns."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available for structured extraction")
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        if schema:
            for key, selector_info in schema.items():
                selector = selector_info.get("selector", "")
                attr = selector_info.get("attr", "text")
                multiple = selector_info.get("multiple", False)
                
                elements = soup.select(selector)
                if multiple:
                    result[key] = [
                        el.get_text(strip=True) if attr == "text" 
                        else el.get(attr, "") 
                        for el in elements
                    ]
                elif elements:
                    el = elements[0]
                    result[key] = el.get_text(strip=True) if attr == "text" else el.get(attr, "")
        else:
            # Default extraction
            result["title"] = soup.title.string if soup.title else None
            desc_tag = soup.find("meta", attrs={"name": "description"})
            result["description"] = desc_tag.get("content", "") if desc_tag else None
            
            headings = []
            for h in soup.find_all(re.compile(r'^h[1-6]$')):
                headings.append({"level": h.name, "text": h.get_text(strip=True)})
            result["headings"] = headings
            
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
            result["paragraphs"] = paragraphs[:50]
        
        return result
