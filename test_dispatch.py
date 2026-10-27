from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", timeout=30000)
    page.wait_for_selector(".main-title", timeout=20000)
    
    # Click dispatch selectbox
    selectboxes = page.locator("[data-testid='stSelectbox']")
    if selectboxes.count() > 1:
        selectboxes.nth(1).click()
        page.wait_for_timeout(600)
        page.locator("li").filter(has_text="Polatlı").first.click()
        page.wait_for_timeout(3500)
        page.screenshot(path="screenshot_polatli_dispatch.png")
        print("Captured Polatli dispatch screenshot!")
    browser.close()
