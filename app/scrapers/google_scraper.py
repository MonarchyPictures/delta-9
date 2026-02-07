import logging
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GoogleScraper(BaseScraper):
    def scrape(self, query: str, time_window_hours: int):
        tbs = "qdr:h"
        if time_window_hours > 1 and time_window_hours <= 24:
            tbs = f"qdr:h{time_window_hours}"
            if time_window_hours == 24: tbs = "qdr:d"
        elif time_window_hours > 24:
            days = time_window_hours // 24
            if days >= 7:
                tbs = "qdr:w"
            else:
                tbs = f"qdr:d{days}"
            
        url = f"https://www.google.com/search?q={query}&tbs={tbs}&gl=ke&hl=en&gws_rd=cr"
        logger.info(f"OUTBOUND CALL: Google Scrape for {query} (Window: {time_window_hours}h, TBS: {tbs})")
        
        content = self.get_page_content(url)
        if not content: 
            logger.warning(f"Google Scrape: No content returned for {query}")
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        search_results = soup.select('div.g') or soup.select('div[data-ved]') or soup.select('div.MjjYud') or soup.select('div.tF2Cxc')
        
        for g in search_results:
            try:
                link_tag = g.select_one('a')
                if not link_tag: continue
                
                title_tag = g.select_one('h3') or g.select_one('div[role="heading"]') or g.select_one('div.vv77sc')
                snippet_tag = g.select_one('div.VwiC3b') or g.select_one('div.kb0u9b') or g.select_one('div.st') or g.select_one('span.aCOp7e')
                
                link = link_tag['href'] if link_tag.has_attr('href') else ""
                title = title_tag.text if title_tag else ""
                snippet = snippet_tag.text if snippet_tag else ""
                
                if link.startswith('/url?q='):
                    link = link.split('/url?q=')[1].split('&')[0]
                elif link.startswith('/'):
                    continue
                    
                if link and title and not any(x in link for x in ['accounts.google.com', 'google.com/search', 'maps.google.com']):
                    results.append({
                        "intent_text": f"{title} {snippet}",
                        "link": link,
                        "source": "Google",
                        "product": query,
                        "location": "Kenya",
                        "contact_method": f"Web: {link}",
                        "confidence_score": 0.7
                    })
            except Exception as e:
                logger.error(f"Error parsing Google result: {e}")
                continue
        
        return results
