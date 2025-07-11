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
URL = "http://localhost:4200/#/status/Lens"
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
    # options.add_argument("--headless")  # Uncomment for headless execution
    return webdriver.Chrome(service=service, options=options)


def login(driver: webdriver.Chrome):
    """Handles the login process."""
    try:
        # Wait for the login elements to be present
        username_field = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "login-username-text-input"))
        )
        password_field = driver.find_element(By.ID, "login-password-text-input")
        submit_button = driver.find_element(By.ID, "submit-button")

        # Enter credentials and login
        username_field.clear()
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        submit_button.click()

    except TimeoutException:
        print("Login elements not found within the timeout period.")
        raise
    except NoSuchElementException:
        print("Could not find one of the login elements.")
        raise


def scrape_status_items(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """
    Navigates to the specified URL and scrapes status items.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of dictionaries, where each dictionary represents a scraped item
        with "label" and "value" keys.
    """
    driver.get(URL)
    
    # Perform login
    login(driver)
    
    results = []
    try:
        # Wait for the status items to be present after login
        WebDriverWait(driver, WAIT_TIMEOUT, poll_frequency=POLL_FREQUENCY).until(
            EC.presence_of_element_located((By.CLASS_NAME, "status-item"))
        )
        # Optional sleep to allow for dynamic content loading
        time.sleep(2)

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
        print(f"Timed out waiting for page elements to load at {URL}")
    return results


def save_results(results: List[Dict[str, str]]):
    """Saves the scraped results to a JSON file and prints them to the console."""
    if not results:
        print("No data was scraped.")
        return

    # Output to console
    for r in results:
        print(f"{r['label']}: {r['value']}")

    # Save to JSON
    try:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved to {OUTPUT_FILE}")
    except IOError as e:
        print(f"Error saving data to {OUTPUT_FILE}: {e}")


def main():
    """Main function to run the scraper."""
    driver = setup_driver()
    try:
        scraped_data = scrape_status_items(driver)
        save_results(scraped_data)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
