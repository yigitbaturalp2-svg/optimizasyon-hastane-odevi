import os
import time
from playwright.sync_api import sync_playwright

os.makedirs("docs/screens", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    print("Navigating to http://localhost:8501...")
    page.goto("http://localhost:8501", timeout=30000)
    page.wait_for_selector(".main-title", timeout=20000)
    time.sleep(6)  # Wait for full rendering of Folium map
    
    # 1. Main Map Dashboard
    page.screenshot(path="docs/screens/01_map_dashboard.png")
    print("Captured 01_map_dashboard.png")
    
    tabs = page.get_by_role("tab").all()
    print(f"Found {len(tabs)} tabs.")

    if len(tabs) >= 2:
        tabs[1].click()
        time.sleep(3)
        page.screenshot(path="docs/screens/02_scenario_comparison.png")
        print("Captured 02_scenario_comparison.png")
        
    if len(tabs) >= 3:
        tabs[2].click()
        time.sleep(3)
        page.screenshot(path="docs/screens/03_data_transparency.png")
        print("Captured 03_data_transparency.png")

    browser.close()
    print("Screenshots captured successfully.")
