from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def download_tray_status():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_options)

    driver.get("http://172.31.0.241:5006/user/home")
    time.sleep(3)

    # =========================
    # LOGIN
    # =========================
    if "login" in driver.current_url:
        print("Login page detected")

        wait = WebDriverWait(driver, 15)

        # wait for inputs
        username = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
        )
        password = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
        )

        username.send_keys("0246")
        password.send_keys("123")

        time.sleep(2)

        # get all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print("Buttons found:", [b.text for b in buttons])

        # click visible button
        for b in buttons:
            if b.is_displayed():
                print("Clicking:", b.text)
                b.click()
                break

        time.sleep(3)

        # retry if needed
        if "login" in driver.current_url:
            print("Retrying login...")

        # 🔥 re-find elements after refresh
        username = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
        )
        password = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
        )

        username.send_keys("0246")
        password.send_keys("123")

        driver.find_elements(By.TAG_NAME, "button")[0].click()

        time.sleep(3)
    # =========================
    # SEARCH Tray Status
    # =========================
    search = driver.find_element(By.XPATH, '//input[contains(@placeholder,"Search")]')
    search.click()
    search.send_keys("Tray Status")
    time.sleep(2)

    driver.find_element(By.XPATH, '//*[contains(text(),"Tray Status")]').click()
    time.sleep(5)

    # =========================
    # SET DATE & TIME (DIRECT)
    # =========================
    
    print("👉 Setting time fields directly")
    
    print("👉 Waiting for time fields...")

    time_inputs = WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, '//input[@type="time"]'))
    )
    
    # from time
    time_inputs[0].clear()
    time_inputs[0].send_keys("00:00:00")
    
    # to time
    time_inputs[1].clear()
    time_inputs[1].send_keys("23:59:59")
    
    # =========================
    # CLICK SHOW
    # =========================
    print("👉 Clicking Show")
    
    show_btn = driver.find_element(By.ID, "search")
    show_btn.click()
    
    print("⏳ Waiting for data load...")
    time.sleep(30)


    # =========================
    # CLICK EXPORT (REAL CLICK)
    # =========================
    print("👉 Clicking Export")
    
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for b in buttons:
        if "Export" in b.text:
            b.click()
            break
        
    time.sleep(2)
    
    print("👉 Clicking Excel")
    
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for b in buttons:
        if b.text.strip() == "Excel":
            b.click()
            break
        
    print("⏳ Waiting for download...")
    time.sleep(20)

    print("✅ Check Chrome downloads")

    time.sleep(10)
    driver.quit()


download_tray_status()