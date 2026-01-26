import scrapy
from scrapy_playwright.page import PageMethod

class ClassifiedsSpider(scrapy.Spider):
    name = "classifieds"
    
    def __init__(self, query=None, *args, **kwargs):
        super(ClassifiedsSpider, self).__init__(*args, **kwargs)
        self.query = query

    def start_requests(self):
        # Example for a classifieds site like Gumtree or OLX
        urls = [
            f"https://www.gumtree.com/search?search_query={self.query}",
        ]
        for url in urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div.user-ad-collection"),
                    ],
                },
            )

    def parse(self, response):
        for ad in response.css("div.user-ad-collection li"):
            yield {
                "link": response.urljoin(ad.css("a::attr(href)").get()),
                "text": ad.css("h2::text").get().strip(),
                "source": "Gumtree Classifieds",
            }
