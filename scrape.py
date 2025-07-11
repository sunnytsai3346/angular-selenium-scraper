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
SCRAPE_URLS = ["#/status/Lens",
               '#/status/Versions',
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
    results = []
    try:
        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=POLL_FREQUENCY).until(
            EC.presence_of_element_located((By.CLASS_NAME, "status-item"))
        )
        time.sleep(2)  # Optional sleep for dynamic content

        items = driver.find_elements(By.CLASS_NAME, "status-item")
        for item in items:
            try:
                label = item.find_element(By.CLASS_NAME, "status-item-label").text.strip()
                value = item.find_element(By.CLASS_NAME, "status-item-value").text.strip()
                if label and value:
                    results.append({"label": label, "value": value})
            except NoSuchElementException:
                print("⚠️ Could not find label or value for an item.")
                continue
    except TimeoutException:
        print(f"Timed out waiting for status items to load on the page.")
    return results


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
