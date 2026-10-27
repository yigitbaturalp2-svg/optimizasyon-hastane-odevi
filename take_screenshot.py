from playwright.sync_api import sync_playwright
import sys

tab_name = sys.argv[1] if len(sys.argv) > 1 else ""
output_path = sys.argv[2] if len(sys.argv) > 2 else "screenshot_tab.png"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", timeout=30000)
    
    # Wait until main-title is visible
    page.wait_for_selector(".main-title", timeout=20000)
    page.wait_for_timeout(3000)
    
    if tab_name:
        tab_btn = page.get_by_role("tab", name=tab_name)
        if tab_btn.count() > 0:
            tab_btn.first.click()
            page.wait_for_timeout(3000)
            
    page.screenshot(path=output_path)
    browser.close()
    print(f"Captured {output_path}")
