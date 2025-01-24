import requests
import os
import time
import logging
import json
import random
from beautifultable import BeautifulTable
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')

class BrowserManager:
    def __init__(self, serial_number):
        self.serial_number = serial_number
        self.driver = None
    
    def check_browser_status(self):
        try:
            response = requests.get(
                'http://local.adspower.net:50325/api/v1/browser/active',
                params={'serial_number': self.serial_number}
            )
            data = response.json()
            if data['code'] == 0 and data['data']['status'] == 'Active':
                logging.info(f"Account {self.serial_number}: Browser is already active.")
                return True
            else:
                return False
        except Exception as e:
            logging.exception(f"Account {self.serial_number}: Exception in checking browser status: {str(e)}")
            return False

    def start_browser(self):
        try:
            if self.check_browser_status():
                logging.info(f"Account {self.serial_number}: Browser already open. Closing the existing browser.")
                self.close_browser()
                time.sleep(5)

            script_dir = os.path.dirname(os.path.abspath(__file__))
            requestly_extension_path = os.path.join(script_dir, 'blum_unlocker_extension')

            launch_args = json.dumps(["--headless=new", f"--load-extension={requestly_extension_path}"])

            request_url = (
                f'http://local.adspower.net:50325/api/v1/browser/start?'
                f'serial_number={self.serial_number}&ip_tab=1&headless=1&launch_args={launch_args}'
            )

            response = requests.get(request_url)
            data = response.json()
            if data['code'] == 0:
                selenium_address = data['data']['ws']['selenium']
                webdriver_path = data['data']['webdriver']
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", selenium_address)

                service = Service(executable_path=webdriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_window_size(600, 720)
                logging.info(f"Account {self.serial_number}: Browser started successfully.")
                return True
            else:
                logging.warning(f"Account {self.serial_number}: Failed to start the browser. Error: {data['msg']}")
                return False
        except Exception as e:
            logging.exception(f"Account {self.serial_number}: Exception in starting browser: {str(e)}")
            return False
        

    def close_browser(self):
        try:
            if self.driver:
                try:
                    self.driver.close()
                    self.driver.quit()
                    self.driver = None  
                    logging.info(f"Account {self.serial_number}: Browser closed successfully.")
                except WebDriverException as e:
                    logging.info(f"Account {self.serial_number}: exception, Browser should be closed now")
        except Exception as e:
            logging.exception(f"Account {self.serial_number}: General Exception occurred when trying to close the browser: {str(e)}")
        finally:
            try:
                response = requests.get(
                    'http://local.adspower.net:50325/api/v1/browser/stop',
                    params={'serial_number': self.serial_number}
                )
                data = response.json()
                if data['code'] == 0:
                    logging.info(f"Account {self.serial_number}: Browser closed successfully.")
                else:
                    logging.info(f"Account {self.serial_number}: exception, Browser should be closed now")
            except Exception as e:
                logging.exception(f"Account {self.serial_number}: Exception occurred when trying to close the browser: {str(e)}")

class TelegramBotAutomation:
    def __init__(self, serial_number):
        self.serial_number = serial_number
        self.browser_manager = BrowserManager(serial_number)
        logging.info(f"Initializing automation for account {serial_number}")
        self.browser_manager.start_browser()
        self.driver = self.browser_manager.driver


    def clear_browser_cache_and_reload(self):
        """
        Очищает кэш браузера, IndexedDB для https://web.telegram.org и перезагружает текущую страницу.
        """
        try:
            logging.debug(
                f"#{self.serial_number}: Attempting to clear browser cache and IndexedDB for https://web.telegram.org.")
            # Очистка кэша через CDP команду
            self.driver.execute_cdp_cmd("Network.clearBrowserCache", {})
            logging.debug(f"#{self.serial_number}: Browser cache successfully cleared.")
            # Очистка IndexedDB для https://web.telegram.org
            self.driver.execute_cdp_cmd("Storage.clearDataForOrigin", {
                "origin": "https://web.telegram.org",
                "storageTypes": "indexeddb"
            })
            logging.debug(
                f"#{self.serial_number}: IndexedDB successfully cleared for https://web.telegram.org.")
            # Перезагрузка текущей страницы
            logging.debug(f"#{self.serial_number}: Refreshing the page.")
            self.driver.refresh()
            logging.debug(f"#{self.serial_number}: Page successfully refreshed.")
        except WebDriverException as e:
            logging.warning(
                f"#{self.serial_number}: WebDriverException while clearing cache or reloading page: {str(e).splitlines()[0]}")
        except Exception as e:
            logging.error(
                f"#{self.serial_number}: Unexpected error during cache clearing or page reload: {str(e)}")




    def navigate_to_bot(self):
        try:
            # Переходим на страницу Telegram Web
            self.driver.get('https://web.telegram.org/k/')
            logging.info(f"Account {self.serial_number}: Navigated to Telegram web.")
            
            # Очистка кэша и IndexedDB, затем перезагрузка
            self.clear_browser_cache_and_reload()
            logging.info(f"Account {self.serial_number}: Browser cache cleared and page reloaded.")
        except Exception as e:
            logging.exception(f"Account {self.serial_number}: Exception in navigating to Telegram bot: {str(e)}")
            self.browser_manager.close_browser()

    

    def send_message(self, message):
        chat_input_area = self.wait_for_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div/div[1]/div[2]/input')
        chat_input_area.click()
        chat_input_area.send_keys(message)

        search_area = self.wait_for_element(By.XPATH, '/html/body/div[1]/div[1]/div[1]/div/div/div[3]/div[2]/div[2]/div[2]/div/div[1]/div/div[2]/ul/a/div[1]')
        search_area.click()
        logging.info(f"Account {self.serial_number}: Group searched.")

    def click_link(self):
        retries = 0
        while retries < 3:
            try:
                # Ищем ссылку
                link = self.wait_for_element(By.CSS_SELECTOR, "a[href*='https://t.me/TVerse?startapp']")
                if link:
                    # Прокручиваем к элементу и поднимаем его на передний план
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    self.driver.execute_script("arguments[0].style.zIndex = '1000';", link)
                    time.sleep(1)  # Короткая задержка после прокрутки

                    # Кликаем через JavaScript
                    self.driver.execute_script("arguments[0].click();", link)
                    logging.info(f"Account {self.serial_number}: Link clicked via JavaScript.")
                    time.sleep(2)  # Даем странице время для реакции

                    # Проверяем, что клик привел к появлению launch_button
                    launch_button = self.driver.find_elements(By.CSS_SELECTOR, "button.popup-button.btn.primary.rp")
                    if not launch_button:
                        # Пробуем альтернативный XPATH, если по CSS-селектору не найдено
                        launch_button = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'popup-button') and contains(@class, 'primary') and span[text()='Launch']]")

                    # Если кнопка найдена, прокручиваем к ней и кликаем
                    if launch_button:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", launch_button[0])
                        launch_button[0].click()
                        logging.info(f"Account {self.serial_number}: Launch button clicked.")
                    
                    # Задержка перед следующим действием
                    time.sleep(random.randint(15, 20))
                    return True  # Клик успешно выполнен, выходим из функции

            except WebDriverException as e:
                logging.warning(f"Account {self.serial_number}: Error clicking link (attempt {retries + 1}): {str(e)}")
                retries += 1
                time.sleep(5)  # Задержка перед повторной попыткой

        # Если после всех попыток клик не удался, возвращаем False
        return False

    def switch_to_iframe(self):
        self.driver.switch_to.default_content()
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            self.driver.switch_to.frame(iframes[0])
            logging.info(f"Account {self.serial_number}: Switched to iframe.")
            return True
        return False

    def click_button_in_iframe(self):
        try:
            self.switch_to_iframe()  # Переходим в iframe
                # Ищем ссылку с текстом "Begin your own journey"
            logging.info("Собираю звёзды")
            journey_link = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div[4]/a[2]"))
        )
            journey_link.click()
            logging.info("Готово звёзды у меня!")
            time.sleep(3)
            # Возвращаемся к основному содержимому  
            # Ищем кнопку с текстом "Begin Journey"
            logging.info("Улучшаю галактику")
            begin_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div/div[4]/a[1]"))
        )
            begin_button.click()
            time.sleep(3)
            begin_create = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[3]/div[2]/div/div[1]/div[3]/button"))
        )
            begin_create.click()
            time.sleep(3)
            logging.info("Вроде заебись чекай сука")
        except TimeoutException as e:
            logging.error(f"Timeout occurred while interacting with the elements: {e}")
        except Exception as e:
            logging.exception(f"An error occurred while clicking the link or button: {e}")
        except Exception as e:
            logging.exception(f"Account {self.serial_number}: Error clicking button inside iframe: {str(e)}")
            return False

    def wait_for_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def wait_for_elements(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_all_elements_located((by, value))
        )

def read_accounts_from_file():
    with open('accounts.txt', 'r') as file:
        return [line.strip() for line in file.readlines()]

def write_accounts_to_file(accounts):
    with open('accounts.txt', 'w') as file:
        for account in accounts:
            file.write(f"{account}\n")


def process_accounts():
    while True:
        accounts = read_accounts_from_file()
        random.shuffle(accounts)
        write_accounts_to_file(accounts)

        for account in accounts:
            retry_count = 0
            success = False

            while retry_count < 3 and not success:
                bot = TelegramBotAutomation(account)
                try:
                    bot.navigate_to_bot()
                    bot.send_message("https://t.me/re_searchdegen")
                    bot.click_link()
                    bot.click_button_in_iframe()
                    logging.info(f"Account {account}: Processing completed successfully.")
                    success = True  
                except Exception as e:
                    logging.warning(f"Account {account}: Error occurred on attempt {retry_count + 1}: {e}")
                    retry_count += 1  
                finally:
                    logging.info("-------------END-----------")
                    bot.browser_manager.close_browser()
                    sleep_time = random.randint(5, 15)
                    logging.info(f"Sleeping for {sleep_time} seconds.")
                    time.sleep(sleep_time)

                if retry_count >= 3:
                    logging.warning(f"Account {account}: Failed after 3 attempts.")

        logging.info("All accounts processed. Restarting in 3 hours.")
        time.sleep(3 * 60)

if __name__ == "__main__":
    process_accounts()
