import json
import logging
import argparse
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# --- Configuration ---
class Config:
    """Configuration class for the scraper."""
    BASE_URL = "http://192.168.230.169/"
    SCRAPE_URLS = [
        '#/menu/MMM%2BABOT',
        '/#/dashboard', 
        # '#/status/Versions', '#/status/Fans', '#/status/Temperatures',
        # '#/status/System', '#/status/Lamp', '#/status/Lens',
        # '#/status/Network', '#/status/Interlocks', '#/status/Serial',
        # '#/status/Video', '#/status/Playback', '#/status/Scheduler',
        # '#/status/Automation', '#/status/ChristieNAS', '#/status/Debugging',
    ]
    OUTPUT_FILE = "status_data.json"
    WAIT_TIMEOUT = 20
    POLL_FREQUENCY = 0.5
    USERNAME = "service"
    PASSWORD = "service"


def setup_logging():
    """Sets up basic logging."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Sets up and returns a Chrome WebDriver instance."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    if headless:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
    prefs = {"profile.default_content_setting_values.media_stream_mic": 2}
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)


def login(driver: webdriver.Chrome):
    """Handles the login process."""
    try:
        # Check if already logged in by looking for the dashboard URL
        if "dashboard" in driver.current_url:
            logging.info("Already logged in.")
            return

        username_field = WebDriverWait(driver, Config.WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "login-username-text-input"))
        )
        password_field = driver.find_element(By.ID, "login-password-text-input")
        submit_button = driver.find_element(By.ID, "submit-button")

        username_field.clear()
        username_field.send_keys(Config.USERNAME)
        password_field.send_keys(Config.PASSWORD)
        submit_button.click()

        WebDriverWait(driver, Config.WAIT_TIMEOUT).until(
            EC.url_contains("dashboard"))
        logging.info("Login successful.")

        # Click Acknowledge button if it appears
        try:
            acknowledge_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Acknowledge')]"))
            )
            acknowledge_button.click()
            logging.info("Clicked 'Acknowledge' button to close dialog.")
        except TimeoutException:
            logging.info("'Acknowledge' button not found, continuing.")

    except TimeoutException:
        logging.error("Login elements not found or login failed.")
        raise
    except NoSuchElementException:
        logging.error("Could not find one of the login elements.")
        raise
    
def scrape_page_context(driver) -> Dict:
    """Extracts a page's full visible context for LLM use."""
    from bs4 import BeautifulSoup

    context = {"url": driver.current_url, "sections": []}
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Capture page title
    title = soup.find("h1") or soup.find("mat-card-title")
    if title:
        context["title"] = title.get_text(strip=True)

    # Use a set to track text content that has already been processed
    processed_text = set()
    if context.get("title"):
        processed_text.add(context["title"])

    # Strategy 1: Paired items with specific classes
    paired_selectors = [
        (".status-item-label", ".status-item-value"),
        ("span#info-name", "span#info-value"),
    ]
    for label_selector, value_selector in paired_selectors:
        labels = soup.select(label_selector)
        values = soup.select(value_selector)
        if len(labels) > 0 and len(labels) == len(values):
            for label, value in zip(labels, values):
                label_text = label.get_text(strip=True)
                value_text = value.get_text(strip=True)
                if label_text and value_text:
                    context["sections"].append({"name": label_text, "value": value_text})
                    processed_text.add(label_text)
                    processed_text.add(value_text)

    # Strategy 2: Tables
    for table in soup.find_all("table"):
        table_content = " ".join(table.stripped_strings)
        if table_content in processed_text:
            continue

        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows_data = []
        for row in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells:
                continue
            if headers and len(headers) == len(cells):
                rows_data.append(dict(zip(headers, cells)))
            else:
                rows_data.append(cells)
        
        if rows_data:
            context["sections"].append({"table": {"headers": headers, "rows": rows_data}})
            for s in table.stripped_strings:
                processed_text.add(s)

    # Strategy 3: Generic labels followed by a value
    for label in soup.find_all("label"):
        label_text = label.get_text(strip=True)
        if label_text in processed_text:
            continue
        
        next_el = label.find_next_sibling()
        if next_el:
            value_text = next_el.get_text(strip=True)
            if value_text:
                context["sections"].append({"name": label_text, "value": value_text})
                processed_text.add(label_text)
                processed_text.add(value_text)

    # Capture remaining headings and paragraphs
    for element in soup.find_all(["h2", "h3", "p"]):
        text = element.get_text(strip=True)
        if text and text not in processed_text:
            if element.name in ["h2", "h3"]:
                context["sections"].append({"heading": text})
            else:
                context["sections"].append({"text": text})
            processed_text.add(text)

    return context


def scrape_page(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """
    Scrapes status items from the current page using different strategies.
    Handles stale element references by re-fetching elements.
    """
    items = []
    strategies = [
        (By.CLASS_NAME, "status-item-label", By.CLASS_NAME, "status-item-value"),
        (By.CSS_SELECTOR, "span#info-name", By.CSS_SELECTOR, "span#info-value")
    ]

    for label_by, label_locator, value_by, value_locator in strategies:
        try:
            # Wait for at least one label to be present
            WebDriverWait(driver, Config.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((label_by, label_locator))
            )
            
            # Get the initial count of labels
            num_labels = len(driver.find_elements(label_by, label_locator))
            if num_labels == 0:
                continue

            logging.info(f"Scraping {num_labels} items using {label_by.upper()}: {label_locator}")
            
            for i in range(num_labels):
                try:
                    # Re-find the elements in each iteration to avoid stale references
                    labels = driver.find_elements(label_by, label_locator)
                    values = driver.find_elements(value_by, value_locator)
                    
                    if i < len(labels) and i < len(values):
                        items.append({
                            "name": labels[i].text.strip(),
                            "value": values[i].text.strip()
                        })
                except NoSuchElementException:
                    logging.warning(f"Could not find element at index {i}, page might have changed.")
                    continue # Skip to the next item
            
            # If we found items with this strategy, we can break
            if items:
                return items
                
        except TimeoutException:
            # This strategy didn't find any elements, try the next one
            continue
    
    logging.warning(f"No scrapeable elements found on {driver.current_url}")
    return items


def save_results(results: List[Dict[str, str]], output_file: str):
    """Saves the scraped results to a JSON file."""
    if not results:
        logging.info("No data was scraped.")
        return

    logging.info(f"Scraped {len(results)} items.")

    # Load EN.json to create a name -> url map
    try:
        with open('EN.json', 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        name_to_url = {item['name']: item.get('url') for item in en_data}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Could not load or parse EN.json: {e}")
        name_to_url = {}

    # Restructure the results to match the desired format
    structured_results = []
    for item in results:
        name = item.get("name", "").strip()
        if not name:
            continue
            
        relative_url = name_to_url.get(name)
        # Prepend BASE_URL if a relative URL exists
        full_url = f"{Config.BASE_URL.rstrip('/')}/{relative_url.lstrip('/')}" if relative_url else None

        structured_results.append({
            "name": name,
            "value": item.get("value", "").strip(),
            "url": full_url
        })

    try:
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(structured_results, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ Saved to {output_file}")
    except IOError as e:
        logging.error(f"Error saving data to {output_file}: {e}")


def main(output_file: Optional[str] = None, headless: bool = False, scrape_context: bool = False):
    """Main function to run the scraper."""
    setup_logging()
    output_file = output_file or Config.OUTPUT_FILE
    
    driver = setup_driver(headless=headless)
    all_data = []
    all_context_data = []

    try:
        driver.get(Config.BASE_URL)
        login(driver)

        for idx, hash_url in enumerate(Config.SCRAPE_URLS, start=1):
            full_url = f"{Config.BASE_URL}{hash_url}"
            logging.info(f"[{idx}/{len(Config.SCRAPE_URLS)}] Navigating to: {full_url}")
            try:
                driver.get(full_url)
                WebDriverWait(driver, Config.WAIT_TIMEOUT).until(
                    EC.url_contains(hash_url.strip("#"))
                )

                if scrape_context:
                    context_data = scrape_page_context(driver)
                    all_context_data.append(context_data)
                else:
                    scraped_data = scrape_page(driver)
                    if scraped_data:
                        all_data.extend(scraped_data)

            except TimeoutException:
                logging.warning(f"Failed to load page for {hash_url}")
            except Exception as scrape_err:
                logging.error(f"Failed to scrape {hash_url}: {scrape_err}")

        if scrape_context:
            save_results(all_context_data, "status_context.json")
        else:
            save_results(all_data, output_file)

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")

    finally:
        driver.quit()
        logging.info("✅ Scraper finished and browser closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape status data from a web page.")
    parser.add_argument("-o", "--output", help=f"Output file name (default: {Config.OUTPUT_FILE})")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode.")
    parser.add_argument("--context", action="store_true", help="Scrape full page context instead of specific data.")
    args = parser.parse_args()
    
    main(output_file=args.output, headless=args.headless, scrape_context=args.context)

