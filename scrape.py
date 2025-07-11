from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
from typing import List, Dict

# --- Configuration ---
BASE_URL = "http://localhost:4200/"
SCRAPE_URLS = ['#/status/Versions',
               '#/status/Fans',
               '#/status/Temperatures',
               '#/status/System',
               '#/status/Lamp',
               '#/status/Lens',
               '#/status/Network',
               '#/status/Interlocks',
               '#/status/Serial',
               '#/status/Video',
               '#/status/Playback',
               '#/status/Scheduler',
               '#/status/Automation',
               '#/status/ChristieNAS',
               '#/status/Debugging']
OUTPUT_FILE = "status_data.json"
CHROME_DRIVER_PATH = './chromedriver.exe'
WAIT_TIMEOUT = 10
POLL_FREQUENCY = 0.5
USERNAME = "service"
PASSWORD = "service"


def setup_driver() -> webdriver.Chrome:
    """Sets up and returns a Chrome WebDriver instance."""
    service = Service(CHROME_DRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Disable microphone access to prevent voice transcription errors
    prefs = {"profile.default_content_setting_values.media_stream_mic": 2}
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless")  # Uncomment for headless execution
    return webdriver.Chrome(service=service, options=options)


def login(driver: webdriver.Chrome):
    """Handles the login process."""
    try:
        username_field = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "login-username-text-input"))
        )
        password_field = driver.find_element(By.ID, "login-password-text-input")
        submit_button = driver.find_element(By.ID, "submit-button")

        username_field.clear()
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        submit_button.click()
        
        # Wait for login to complete by checking for the dashboard URL
        WebDriverWait(driver, WAIT_TIMEOUT).until(EC.url_contains("dashboard"))
        print("Login successful.")

    except TimeoutException:
        print("Login elements not found or login failed within the timeout period.")
        raise
    except NoSuchElementException:
        print("Could not find one of the login elements.")
        raise


def scrape_status_items(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """
    Scrapes status items from the current page.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of dictionaries, where each dictionary represents a scraped item.
    """
    items = []
    current_url = driver.current_url

    try:
        if "/status" in current_url:
            print("📄 Scraping using status-item-label/status-item-value pattern")

            # Wait for at least one status item to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "status-item-label"))
            )

            labels = driver.find_elements(By.CLASS_NAME, "status-item-label")
            values = driver.find_elements(By.CLASS_NAME, "status-item-value")

            for label_el, value_el in zip(labels, values):
                items.append({
                    "name": label_el.text.strip(),
                    "value": value_el.text.strip()
                })

        else:
            print("📄 Scraping using info-name/info-value pattern")

            # Wait until info-name and info-value are present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "info-name"))
            )

            name_el = driver.find_element(By.ID, "info-name")
            value_el = driver.find_element(By.ID, "info-value")

            items.append({
                "name": name_el.text.strip(),
                "value": value_el.text.strip()
            })

    except Exception as e:
        print(f"⚠️ Failed to scrape on {current_url}: {e}")

    return items


def save_results(results: List[Dict[str, str]]):
    """Saves the scraped results to a JSON file and prints them to the console."""
    if not results:
        print("No data was scraped.")
        return

    for r in results:
        print(f"{r['label']}: {r['value']}")

    try:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved to {OUTPUT_FILE}")
    except IOError as e:
        print(f"Error saving data to {OUTPUT_FILE}: {e}")


def main():
    """Main function to run the scraper for multiple hash URLs."""
    driver = setup_driver()
    try:
        # Navigate to the base site and log in once
        driver.get(BASE_URL)
        login(driver)
        print('131')
        all_data = []

        for idx, hash_url in enumerate(SCRAPE_URLS, start=1):
            try:
                print(f"\n[{idx}/{len(SCRAPE_URLS)}] Navigating to: {hash_url}")
                driver.execute_script(f"window.location.hash = '{hash_url}';")
                

                # Optional: wait for the route to load
                WebDriverWait(driver, 10).until(
                    lambda d: hash_url.strip("#") in d.current_url
                )

                # Scrape this view
                scraped_data = scrape_status_items(driver)

                # Tag or store per route
                all_data.extend(scraped_data)

            except Exception as scrape_err:
                print(f"⚠️ Failed to scrape {hash_url}: {scrape_err}")

        # Save final combined results
        save_results(all_data)

    except Exception as e:
        print(f"❌ Critical error occurred: {e}")

    finally:
        driver.quit()
        print("✅ Scraper finished and browser closed.")
if __name__ == "__main__":
    main()
