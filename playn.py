from playwright.sync_api import sync_playwright
from datetime import datetime
from datetime import timedelta
import os
import sys

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
        # BUSINESS DATE LOGIC
        # =========================

        if len(sys.argv) > 1:
            date_str = sys.argv[1]
        else:
            now = datetime.now()
            if now.hour < 10:
                now = now - timedelta(days=1)
            date_str = now.strftime("%Y-%m-%d")

        print(f"📅 Using date: {date_str}")

        # =========================
        # SET DATE & TIME USING KEYBOARD WORKAROUND
        # =========================
        print("👉 Resetting focus to Search box...")
        search_box = page.locator('input[placeholder*="Search"]')
        search_box.click()
        page.wait_for_timeout(500)

        print("👉 Pressing Tab 10 times to reach 'From Date'...")
        for _ in range(8):  # Keeping your 8 from the script
            page.keyboard.press("Tab")
            page.wait_for_timeout(100)

        print(f"👉 Typing From Date: {date_str}")
        page.keyboard.type(date_str)

        print("👉 Pressing Tab to reach 'To Date'...")
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)

        print(f"👉 Typing To Date: {date_str}")
        page.keyboard.type(date_str)

        print("👉 Pressing Tab to reach 'From Time'...")
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)

        print("👉 Typing From Time: 00:00:00")
        page.keyboard.type("00:00:00")

        # 🔥 ADDED THE EXTRA TAB HERE
        print("👉 Pressing Tab TWICE to reach 'To Time'...")
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)

        print("👉 Typing To Time: 23:59:59")
        page.keyboard.type("23:59:59")

        print("✅ Date and Time set seamlessly via keyboard")

        # =========================
        # CLICK SHOW BUTTON (DIRECT)
        # =========================
        print("👉 Tabbing to the Show button...")
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
        page.keyboard.press("Tab")  # Usually takes 1 or 2 tabs from 'To Time'
        page.wait_for_timeout(100)

        print("👉 Pressing Enter to click Show...")
        page.keyboard.press("Enter")

        print("⏳ Waiting for data load...")
        page.wait_for_timeout(5000)   # minimum wait

        # Wait for the table body to render to ensure data loaded
        page.wait_for_selector("table tbody tr", timeout=15000)

        print("✅ Data loaded successfully")

        # # =========================
        # # SET DATE USING KEYBOARD WORKAROUND
        # # =========================
        # print("👉 Resetting focus to Search box...")
        # search_box = page.locator('input[placeholder*="Search"]')
        # search_box.click()
        # page.wait_for_timeout(500)

        # print("👉 Pressing Tab 10 times to reach 'From Date'...")
        # for _ in range(8):
        #     page.keyboard.press("Tab")
        #     page.wait_for_timeout(100)  # Tiny pause to let the browser catch up

        # print(f"👉 Typing From Date: {date_str}")
        # page.keyboard.type(date_str)

        # print("👉 Pressing Tab to reach 'To Date'...")
        # page.keyboard.press("Tab")
        # page.wait_for_timeout(100)

        # print(f"👉 Typing To Date: {date_str}")
        # page.keyboard.type(date_str)

        # print("✅ Dates set via keyboard workaround")

        # # # =========================
        # # # SET DATE FIELD
        # # # =========================
        # # try:
        # #     date_input = page.locator('input[type="date"]').first
        # #     date_input.click()
        # #     date_input.fill(date_str)
        # #     print("✅ Date set")
        # # except Exception as e:
        # #     print("⚠️ Date set failed:", e)

        # # =========================
        # # SET TIME PROPERLY
        # # =========================

        # # From Time
        # page.locator('input[type="time"]').nth(0).click()
        # page.keyboard.press("Control+A")
        # page.keyboard.type("00:00:00")

        # # To Time
        # page.locator('input[type="time"]').nth(1).click()
        # page.keyboard.press("Control+A")
        # page.keyboard.type("23:59:59")

        # print("✅ Time set correctly")

        # =========================
        # CLICK SHOW BUTTON (DIRECT)
        # =========================
        page.locator('button:has-text("Show")').click()

        print("⏳ Waiting for data load...")
        page.wait_for_timeout(5000)   # minimum

        # OR better (if table exists)
        page.wait_for_selector("table tbody tr", timeout=15000)

        print("👉 Clicked Show properly")

        # # =========================
        # # CLICK SHOW
        # # =========================
        # page.keyboard.press("Tab")
        # page.keyboard.press("Tab")
        # page.keyboard.press("Enter")

        # print("⏳ Waiting for data load...")
        # page.wait_for_timeout(15000)

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
            now = datetime.now()
            time_str = now.strftime('%H-%M-%S')

            new_name = os.path.join(
                DOWNLOAD_DIR,
                f"tray_status_{date_str}_{time_str}.xlsx"
            )
            time_str = now.strftime('%H-%M-%S')
            
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