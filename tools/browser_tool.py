import logging
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)

@tool
def browse_website(url: str) -> str:
    """Visits a web page, extracts its visible text content, and returns it."""
    try:
        from playwright.sync_api import sync_playwright
        
        logger.info(f"Browsing website: {url} using Playwright...")
        with sync_playwright() as p:
            # We use chromium headless
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            # Wait for content to load
            page.wait_for_load_state("networkidle")
            # Get text content of body
            text = page.locator("body").inner_text()
            browser.close()
            return text[:8000] # Limit to 8k characters
            
    except Exception as e:
        logger.warning(f"Playwright failed to browse {url}: {e}. Falling back to requests/urllib.")
        
        # Fallback to requests/urllib
        try:
            import urllib.request
            from bs4 import BeautifulSoup
            
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read()
                soup = BeautifulSoup(html, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text()
                # break into lines and remove leading and trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text[:5000]
        except Exception as e2:
            logger.error(f"Fallback HTTP request also failed: {e2}")
            return f"Error: Failed to fetch {url}. Details: {e2}"
