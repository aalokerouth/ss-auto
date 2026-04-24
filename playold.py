from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import glob
import time

DOWNLOAD_DIR = r"D:\tray_downloads"

def download_tray_status():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            accept_downloads=True
        )

        page = context.new_page()

        page.goto("http://172.31.0.241:5006/user/home")
        page.wait_for_timeout(3000)

        # =========================
        # LOGIN (ROBUST)
        # =========================
        def do_login():
            page.fill('input[type="text"]', "0246")
            page.fill('input[type="password"]', "123")
            page.click('button:has-text("SIGN IN")')

        if "login" in page.url:
            print("Login page detected")

            do_login()
            page.wait_for_timeout(2000)

            if "login" in page.url:
                print("Retrying login...")
                do_login()
                page.wait_for_timeout(3000)

        # =========================
        # SEARCH Tray Status
        # =========================
        search_box = page.locator('input[placeholder*="Search"]')

        search_box.click()
        search_box.fill("Tray Status")

        dropdown_item = page.locator("text=Tray Status").first
        dropdown_item.wait_for(timeout=5000)
        dropdown_item.click()

        # =========================
        # WAIT FOR PAGE
        # =========================
        page.wait_for_url("**/reports/**", timeout=15000)
        page.wait_for_timeout(3000)

        # =========================
        # KEYBOARD NAVIGATION
        # =========================
        page.click("body")

        for _ in range(7):
            page.keyboard.press("Tab")
            page.wait_for_timeout(200)

        # =========================
        # SET TIME
        # =========================
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.keyboard.type("235959")

        # =========================
        # CLICK SHOW
        # =========================
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")

        # wait for data
        page.wait_for_timeout(15000)

        # =========================
        # EXPORT USING PURE KEYBOARD FLOW (VISIBLE + DEBUG)
        # =========================

        print("⏳ Waiting after Show...")
        page.wait_for_timeout(20000)

        # 🔥 Click search box to reset focus
        print("👉 Clicking search box to reset focus")
        search_box = page.locator('input[placeholder*="Search"]').first
        search_box.click()
        page.wait_for_timeout(2000)

        # 🔥 TAB 17 TIMES (with delay + logs)
        print("👉 Starting TAB navigation...")
        for i in range(21):
            page.keyboard.press("Tab")
            print(f"   🔹 Tab {i+1}/21")
            page.wait_for_timeout(1000)   # 👀 visible movement

        print("✅ Reached target (hopefully Export)")

        # 🔥 ENTER → open Export dropdown
        print("👉 Pressing ENTER (open Export)")
        page.keyboard.press("Enter")

        page.wait_for_timeout(1000)

        # 🔥 ENTER again → select Excel
        print("👉 Pressing ENTER again (select Excel)")
        page.keyboard.press("Enter")

        print("⏳ Waiting for download...")
        page.wait_for_timeout(8000)

        

        # # click Excel
        # page.evaluate("""
        # () => {
        #     let buttons = Array.from(document.querySelectorAll('button'));

        #     let excelButtons = buttons.filter(b =>
        #         b.innerText &&
        #         b.innerText.includes('Excel') &&
        #         b.offsetParent !== null
        #     );

        #     if (excelButtons.length > 0) {
        #         excelButtons[0].scrollIntoView();
        #         excelButtons[0].click();
        #     }
        # }
        # """)

        # =========================
        # HANDLE DOWNLOAD FILE
        # =========================
        timeout = 15
        start = time.time()

        latest_file = None

        while time.time() - start < timeout:
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
            if files:
                latest_file = max(files, key=os.path.getctime)
                break
            time.sleep(1)

        if not latest_file:
            print("❌ No file found in download folder")
            return

        latest_file = max(files, key=os.path.getctime)

        new_name = os.path.join(
            DOWNLOAD_DIR,
            f"tray_status_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        )

        os.rename(latest_file, new_name)

        print("✅ Downloaded:", new_name)

        browser.close()


download_tray_status()