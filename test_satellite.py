from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", timeout=20000)
    page.wait_for_timeout(3000)
    
    # Click selectbox
    selectbox = page.locator("[data-testid='stSelectbox']")
    if selectbox.count() > 0:
        selectbox.first.click()
        page.wait_for_timeout(800)
        page.locator("li").filter(has_text="Uydu").click()
        page.wait_for_timeout(4000)
        page.screenshot(path="screenshot_satellite.png")
        print("Satellite screenshot saved!")
    browser.close()
