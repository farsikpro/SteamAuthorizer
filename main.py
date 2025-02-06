import time
import json
import os
import base64
import hmac
import hashlib

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def generate_steam_guard_code(shared_secret: str) -> str:
    secret_bytes = base64.b64decode(shared_secret)
    time_buffer = int(time.time()) // 30
    time_bytes = time_buffer.to_bytes(8, byteorder='big')
    hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
    offset = hmac_hash[19] & 0x0F
    code_int = int.from_bytes(hmac_hash[offset:offset + 4], byteorder='big') & 0x7fffffff
    steam_chars = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''
    for _ in range(5):
        code += steam_chars[code_int % len(steam_chars)]
        code_int //= len(steam_chars)
    return code


def parse_steam_id64(profile_link: str) -> str:
    link_clean = profile_link.strip().rstrip('/')
    return link_clean.split('/')[-1]


def create_driver():
    options = uc.ChromeOptions()
    proxy_host = "ip:port" # ВВЕСТИ НУЖНЫЙ ip:port
    options.add_argument(f"--proxy-server=http://{proxy_host}")

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 800)
    return driver


def login_steam_account(driver, steam_login, steam_password, shared_secret):
    wait = WebDriverWait(driver, 20)
    steam_code = generate_steam_guard_code(shared_secret)
    print(f"Пытемся войти в акк: {steam_login}")

    try:
        driver.get("https://store.steampowered.com/login/")

        LOGIN_CSS = (
            "#responsive_page_template_content > div.page_content > div:nth-child(1) > div > "
            "div > div > div._3XCnc4SuTz8V8-jXVwkt_s > div > form > div:nth-child(1) > input"
        )
        login_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_CSS)))
        login_field.send_keys(steam_login)

        PASSWORD_CSS = (
            "#responsive_page_template_content > div.page_content > div:nth-child(1) > div > "
            "div > div > div._3XCnc4SuTz8V8-jXVwkt_s > div > form > div:nth-child(2) > input"
        )
        password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, PASSWORD_CSS)))
        password_field.send_keys(steam_password)

        SIGN_IN_BUTTON_CSS = (
            "#responsive_page_template_content > div.page_content > div:nth-child(1) > div > "
            "div > div > div._3XCnc4SuTz8V8-jXVwkt_s > div > form > div:nth-child(4) > button"
        )
        sign_in_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SIGN_IN_BUTTON_CSS)))
        sign_in_button.click()

        GUARD_TEMPLATE = (
            "#responsive_page_template_content > div.page_content > div:nth-child(1) > div > div > div > "
            "div._3XCnc4SuTz8V8-jXVwkt_s > form > div > "
            "div._3huyZ7Eoy2bX4PbCnH3p5w > div._1NOsG2PAO2rRBb8glCFM_6._2QHQ1DkwVuPafY7Yr1Df6w > div > "
            "input:nth-child({i})"
        )
        for i, digit in enumerate(steam_code, start=1):
            guard_css = GUARD_TEMPLATE.format(i=i)
            guard_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, guard_css)))
            guard_field.send_keys(digit)

        time.sleep(2)
        print(f"Успешно вошли в акк: {steam_login}")
        time.sleep(5)
        return True

    except Exception as e:
        print(f"[ERROR] login_steam_account() - ошибка входа для {steam_login}: {e}")
        return False


def accept_cookies_if_needed(driver, wait):
    try:
        COOKIES_ACCEPT_CSS = "#acceptAllButton"
        accept_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, COOKIES_ACCEPT_CSS)))
        accept_button.click()
        time.sleep(1)
        print("[INFO] Cookie consent accepted.")
    except Exception:
        pass


def change_region_to_norway_and_activate_gift(driver, gift_code):
    wait = WebDriverWait(driver, 10)
    try:
        print("[DEBUG] Переходим на страницу пополнения баланса")
        driver.get("https://store.steampowered.com/steamaccount/addfunds")
        time.sleep(3)

        print("[DEBUG] Проверяем, есть ли куки-баннер")
        accept_cookies_if_needed(driver, wait)

        current_url = driver.current_url
        print(f"[DEBUG] current_url после загрузки: {current_url}")

        print("[DEBUG] Ищем кнопку смены региона...")
        REGION_BUTTON_CSS = "#usercountrycurrency_trigger"
        region_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, REGION_BUTTON_CSS)))
        print("[DEBUG] Нашли кнопку смены региона, кликаем...")
        region_btn.click()
        time.sleep(1)

        print("[DEBUG] Ищем элемент #NO для выбора Норвегии...")
        NORWAY_OPTION_CSS = "#NO"
        norway_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, NORWAY_OPTION_CSS)))
        print("[DEBUG] Нашли #NO, кликаем...")
        norway_option.click()
        time.sleep(2)
        print("[DEBUG] Норвегия выбрана.")

        print("[DEBUG] Ищем кнопку подтверждения...")
        # Ставим короткий таймаут = 2 секунды
        NORWAY_CONFIRM_CSS = (
            "#currency_change_confirm_dialog > div.currency_have_options > "
            "div > div:nth-child(2) > div > span > div.country"
        )
        try:
            # Используем короткий WebDriverWait
            short_wait = WebDriverWait(driver, 2)
            confirm_norway_btn = short_wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, NORWAY_CONFIRM_CSS))
            )
            print("[DEBUG] Нашли кнопку подтверждения, кликаем...")
            confirm_norway_btn.click()
            time.sleep(2)
            print("[DEBUG] Подтверждение смены региона нажато.")
        except TimeoutException:
            print("[DEBUG] Кнопка подтверждения не появилась за 2 секунды. Пропускаем этот шаг.")

        print("[DEBUG] Ищем кнопку 'Активировать gift-код'...")
        GIFT_ACTIVATE_CSS = (
            "#responsive_page_template_content > div.page_content_ctn > div > "
            "div.rightcol > div > div.block_content.block_content_inner > "
            "div.wallent_actions_ctn > a:nth-child(2)"
        )
        gift_activate_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, GIFT_ACTIVATE_CSS)))
        print("[DEBUG] Нашли 'Активировать gift-код', кликаем...")
        gift_activate_link.click()
        time.sleep(1)

        print("[DEBUG] Ищем поле gift-кода...")
        GIFT_INPUT_CSS = "#wallet_code"
        gift_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, GIFT_INPUT_CSS)))
        gift_input.send_keys(gift_code)
        time.sleep(1)
        print(f"[DEBUG] Gift-код введён: {gift_code}")

        print("[DEBUG] Ищем кнопку 'Продолжить'...")
        VALIDATE_BUTTON_CSS = "#validate_btn > span"
        validate_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, VALIDATE_BUTTON_CSS)))
        print("[DEBUG] Нашли кнопку 'Продолжить', кликаем...")
        validate_button.click()
        time.sleep(2)

        print("[INFO] Gift-код введён и подтверждён.")

    except Exception as e:
        print(f"[ERROR] change_region_to_norway_and_activate_gift() - ошибка: {e}")
        with open("error_change_region.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)


def logout_steam(driver):
    try:
        driver.execute_script("Logout();")
        time.sleep(3)
        print("Выполнили выход из аккаунта.")
    except Exception as e:
        print(f"[ERROR] logout_steam(): {e}")


def main():
    accounts_file = "accounts.txt"
    if not os.path.exists(accounts_file):
        print(f"[ERROR] Не найден файл {accounts_file}!")
        return

    driver = create_driver()

    with open(accounts_file, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if "ready" in line:
            continue

        parts = line.split(':')
        if len(parts) == 8:
            steam_login   = parts[0]
            steam_pass    = parts[1]
            mail_login    = parts[2]
            mail_pass     = parts[3]
            profile_link  = parts[4] + ':' + parts[5]
            restore_code  = parts[6]
            gift_code     = parts[7]
        elif len(parts) == 7:
            steam_login   = parts[0]
            steam_pass    = parts[1]
            mail_login    = parts[2]
            mail_pass     = parts[3]
            profile_link  = parts[4]
            restore_code  = parts[5]
            gift_code     = parts[6]
        else:
            print(f"[WARNING] Строка не подходит: {line}")
            continue

        steam_id64 = parse_steam_id64(profile_link)
        mafile_path = os.path.join("maFiles", f"{steam_id64}.maFile")
        if not os.path.exists(mafile_path):
            print(f"[ERROR] maFile не найден: {mafile_path}")
            continue

        with open(mafile_path, "r", encoding="utf-8") as mf:
            ma_data = json.load(mf)
        shared_secret = ma_data.get("shared_secret")
        if not shared_secret:
            print(f"[ERROR] Нет shared_secret в {mafile_path}")
            continue

        # Логинимся
        success = login_steam_account(driver, steam_login, steam_pass, shared_secret)
        if not success:
            continue

        # Смена региона + активация
        change_region_to_norway_and_activate_gift(driver, gift_code)

        # Выход
        logout_steam(driver)

        # Помечаем ready
        lines[i] = line + ":ready"

        # Перезаписываем файл
        with open(accounts_file, "w", encoding="utf-8") as fw:
            for ln in lines:
                fw.write(ln + "\n")

        print(f"[INFO] Аккаунт {steam_login} отмечен как ready.")

    driver.quit()
    print("[INFO] Скрипт завершён.")


if __name__ == "__main__":
    main()