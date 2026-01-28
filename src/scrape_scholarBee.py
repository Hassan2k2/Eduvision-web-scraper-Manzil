from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import os

# =========================
# CONFIG
# =========================
URL = "https://www.hec.gov.pk/english/scholarshipsgrants/pages/default.aspx"
CSV_FILE = "Scholarships/hec_bs_scholarships.csv"
JSON_FILE = "Scholarships/hec_bs_scholarships.json"

os.makedirs("Scholarships", exist_ok=True)

print("Starting HEC Undergraduate (BS) Scholarships Scraping")
print("=" * 60)

# =========================
# DRIVER SETUP
# =========================
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.get(URL)
time.sleep(6)  # allow page to fully load

# =========================
# SCRAPE DATA
# =========================
elements = driver.find_elements(By.XPATH, "//h3")
print(f"Scholarships found on page: {len(elements)}")

data = []  # ✅ create FIRST

for el in elements:
    title = el.text.strip()
    if not title:
        continue

    data.append({
        "Scholarship Name": title,
        "Degree Level": "Bachelors",
        "Scholarship Type": "National",
        "Opening Date": "Not Announced",
        "Deadline": "Not Announced",
        "Source": "HEC Pakistan"
    })

    print("Added:", title)

driver.quit()

# =========================
# SAVE DATA (AFTER SCRAPING)
# =========================
df = pd.DataFrame(data)

df.to_csv(CSV_FILE, index=False, encoding="utf-8")
df.to_json(JSON_FILE, orient="records", indent=2)

print("=" * 60)
print(f"Total BS scholarships scraped: {len(df)}")
print(f"Saved CSV to: {CSV_FILE}")
print(f"Saved JSON to: {JSON_FILE}")
print("=" * 60)
