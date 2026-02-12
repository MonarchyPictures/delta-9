import logging
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)
  
class WhatsAppPublicGroupScraper(BaseScraper): 
    source = "whatsapp" 
 
    GROUPS = [ 
        "https://chat.whatsapp.com/exampleKENYA1", 
        "https://chat.whatsapp.com/exampleKENYA2" 
    ] 
 
    def scrape(self, query: str, time_window_hours: int): 
        import time
        # Simulate very fast runtime for speed boost testing
        time.sleep(0.5) 
        
        logger.info(f"WHATSAPP_PUBLIC: Checking groups for {query} (Window: {time_window_hours}h)")
        results = [] 
 
        # Simulate finding more leads in wider windows
        num_leads = 2 if time_window_hours <= 2 else 4
        
        for i in range(num_leads): 
            # Use a more realistic mock message that doesn't just echo the expanded query
            mock_phone = f"071234567{i}"
            messages = [
                f"Anyone selling a clean {query}? My budget is around 1.5M. Contact me at {mock_phone} ASAP",
                f"I need a {query} for a client urgently today. Nairobi area. Call {mock_phone} if you have one.",
                f"Looking for {query}, must be in good condition. Need it now. {mock_phone}",
                f"Who has {query} for sale? Ready to buy today. Budget 1.2M. {mock_phone}"
            ]
            text = messages[i % len(messages)]
            group = self.GROUPS[i % len(self.GROUPS)]
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=text,
                author=f"WhatsApp User {i}",
                contact=self.extract_contact_info(f"{text} {group}"),
                location="Kenya",
                url=f"{group}?id={i}",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results
