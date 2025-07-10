from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

# Setup Chrome WebDriver
service = Service('./chromedriver')  # adjust path if needed
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=service, options=options)

try:
    # Step 1: Go to Angular app page
    url = "http://localhost:4200/#/menu/MMM%2BSTAT"
    driver.get(url)

    # Step 2: Wait for Angular to render '.status-item' components
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "status-item"))
    )

    # Optional: Wait longer if content is still loading
    time.sleep(2)

    # Step 3: Scrape each label-value pair
    items = driver.find_elements(By.CLASS_NAME, "status-item")
    results = []

    for item in items:
        try:
            label = item.find_element(By.CLASS_NAME, "status-item-label").text.strip()
            value = item.find_element(By.CLASS_NAME, "status-item-value").text.strip()
            results.append({"label": label, "value": value})
        except Exception as e:
            print("⚠️ Failed to extract item:", e)

    # Step 4: Output to console
    for r in results:
        print(f"{r['label']}: {r['value']}")

    # Step 5: Save to JSON
    with open("status_data.json", "w", encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("✅ Saved to status_data.json")

finally:
    driver.quit()
