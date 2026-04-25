from playwright.sync_api import sync_playwright
from datetime import datetime
import os

DOWNLOAD_DIR = r"D:\current tray"

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

        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("http://172.31.0.241:5006/user/home")
        page.wait_for_timeout(5000)

        # =========================
        # LOGIN
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
        # KEYBOARD NAVIGATION TO TIME
        # =========================
        page.click("body")

        for _ in range(7):
            page.keyboard.press("Tab")
            page.wait_for_timeout(200)

        # =========================
        # SET TIME = 23:59:59
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

        print("⏳ Waiting for data load...")
        page.wait_for_timeout(15000)

        # =========================
        # EXPORT USING KEYBOARD FLOW
        # =========================
        print("👉 Reset focus via search")
        search_box.click()
        page.wait_for_timeout(1000)

        print("👉 TAB navigation to Export...")
        for i in range(21):
            page.keyboard.press("Tab")
            # print(f"   🔹 Tab {i+1}/21")
            # page.wait_for_timeout(500)

        print("👉 Opening Export dropdown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        print("👉 Selecting Excel and waiting for download...")

        # =========================
        # DOWNLOAD DETECTION (FIXED)
        # =========================
        try:
            with page.expect_download(timeout=90000) as download_info:
                page.keyboard.press("Enter")
            
            download = download_info.value
            
            # --- CUSTOM BUSINESS DAY LOGIC ---
            from datetime import timedelta
            now = datetime.now()
            
            # If it is before 9:00 AM, count it as the previous calendar day
            if now.hour < 9:
                business_date = now - timedelta(days=1)
            else:
                business_date = now

            # Format the string using the calculated business date (but keep the actual time for tracking)
            date_str = business_date.strftime('%Y-%m-%d')
            time_str = now.strftime('%H-%M')
            
            # Create your final file path
            new_name = os.path.join(
                DOWNLOAD_DIR,
                f"tray_status_{date_str}_{time_str}.xlsx"
            )
            # ---------------------------------

            # Save the file
            download.save_as(new_name)
            print(f"🎉 SUCCESS: {new_name}")

        except Exception as e:
            print(f"❌ Download failed or timed out: {e}")

        finally:
            browser.close()

# Run the script
if __name__ == "__main__":
    download_tray_status()