from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import glob
import time

DOWNLOAD_DIR = r"C:\Users\SSSPLCOM-391\Downloads"

def wait_for_download(download_dir, timeout=90):
    print("⏳ Watching Downloads folder...")

    before = set(os.listdir(download_dir))  # 🔥 capture initial state
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(2)

        after = set(os.listdir(download_dir))
        new_files = after - before   # 🔥 only NEW files

        # ignore temp downloads
        new_files = [f for f in new_files if not f.endswith(".crdownload")]

        if new_files:
            latest = max(
                [os.path.join(download_dir, f) for f in new_files],
                key=os.path.getctime
            )

            print(f"✅ NEW Download detected: {latest}")
            return latest

    print("❌ No NEW download detected")
    return None


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
        page.wait_for_timeout(3000)

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
        page.wait_for_timeout(30000)

        # =========================
        # EXPORT USING KEYBOARD FLOW
        # =========================
        print("👉 Reset focus via search")
        search_box.click()
        page.wait_for_timeout(2000)

        print("👉 TAB navigation to Export...")
        for i in range(21):
            page.keyboard.press("Tab")
            print(f"   🔹 Tab {i+1}/21")
            page.wait_for_timeout(500)

        print("👉 Opening Export dropdown")
        page.keyboard.press("Enter")

        page.wait_for_timeout(2000)

        print("👉 Selecting Excel")
        page.keyboard.press("Enter")

        # 🔥 IMPORTANT: wait longer for server
        print("⏳ Waiting for server to generate file...")
        page.wait_for_timeout(25000)

        # =========================
        # DOWNLOAD DETECTION (FIXED)
        # =========================
        print("📂 Files in folder BEFORE detection:")
        print(os.listdir(DOWNLOAD_DIR))

        downloaded_file = wait_for_download(DOWNLOAD_DIR)

        print("📂 Files in folder AFTER detection:")
        print(os.listdir(DOWNLOAD_DIR))

        if not downloaded_file:
            print("❌ Download failed or blocked")
            return

        new_name = os.path.join(
            DOWNLOAD_DIR,
            f"tray_status_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        )

        os.rename(downloaded_file, new_name)

        print("🎉 SUCCESS:", new_name)

        browser.close()


download_tray_status()