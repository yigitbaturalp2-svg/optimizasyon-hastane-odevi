import os
from playwright.sync_api import sync_playwright

os.makedirs("docs/screens", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    print("Navigating to http://localhost:8501...")
    page.goto("http://localhost:8501", timeout=30000)
    page.wait_for_selector(".main-title", timeout=20000)
    page.wait_for_timeout(4000)
    
    # 1. Map Dashboard
    page.screenshot(path="docs/screens/01_map_dashboard.png")
    print("Captured 01_map_dashboard.png")
    
    # 2. Scenario Comparison Tab
    tab_cmp = page.get_by_role("tab", name="MEVCUT DURUM VS YENİ YATIRIMLAR")
    if tab_cmp.count() > 0:
        tab_cmp.first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="docs/screens/02_scenario_comparison.png")
        print("Captured 02_scenario_comparison.png")
        
    # 3. Data Transparency Tab
    tab_data = page.get_by_role("tab", name="VERİ ŞEFFAFLIĞI VE PROVENANCE")
    if tab_data.count() > 0:
        tab_data.first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="docs/screens/03_data_transparency.png")
        print("Captured 03_data_transparency.png")
        
    browser.close()
    print("Screenshots captured successfully.")
