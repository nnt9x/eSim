import random
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


class AutoBase:
    def __init__(self, wait_timeout=30):
        options = webdriver.FirefoxOptions()
        options.set_preference("dom.webnotifications.enabled", True)
        options.set_preference("dom.popup_allowed_events", "click dblclick mousedown mouseup")
        options.set_preference("dom.allow_scripts_to_close_windows", True)
        self.driver = webdriver.Firefox(options=options)
        self.WAIT_TIMEOUT = wait_timeout

    def _set_field(self, value: str, pattern: str) -> None:
        field = WebDriverWait(self.driver, self.WAIT_TIMEOUT).until(
            ec.presence_of_element_located((By.XPATH, pattern))
        )
        field.send_keys(value)
        field.send_keys(Keys.TAB)

    def _get_field(self, pattern: str, by=By.XPATH) -> object:
        return WebDriverWait(self.driver, self.WAIT_TIMEOUT).until(
            ec.presence_of_element_located((by, pattern))
        )

    def _get_fields(self, pattern: str, by=By.NAME) -> list:
        return WebDriverWait(self.driver, self.WAIT_TIMEOUT).until(
            ec.presence_of_all_elements_located((by, pattern))
        )

    def _load_url(self, url) -> bool:
        self.driver.get(url)
        self.driver.maximize_window()
        try:
            WebDriverWait(self.driver, self.WAIT_TIMEOUT).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            print("Đã tải trang:", url)
            return True
        except TimeoutError as e:
            print("Quá thời gian!")
            return False
        except Exception as e:
            print("Lỗi khi tải trang:", e)
            return False

    def wait_for_url_change(self) -> bool:
        try:
            WebDriverWait(self.driver, self.WAIT_TIMEOUT).until(ec.url_changes(self.driver.current_url))
            print("URL đã thay đổi. URL mới:", self.driver.current_url)
            return True
        except TimeoutError as e:
            print("Quá thời gian!")
            return False
        except Exception as e:
            print("Có lỗi xảy ra:", e)
            return False

    def scroll_to_bottom(self) -> None:
        actions = ActionChains(self.driver)
        for _ in range(5):
            actions.send_keys(Keys.END).perform()
            time.sleep(1)

    def close(self):
        self.driver.close()

    def quit(self):
        self.driver.quit()


class AutoActivateSubscription(AutoBase):

    def login(self, email: str, password: str, url="https://bcss-uat.vnsky.vn/login") -> None:
        self._load_url(url)
        self._set_field(email, "//input[@placeholder='Nhập địa chỉ email']")
        self._set_field(password, "//input[@placeholder='Nhập mật khẩu']")
        self._get_field("//button[@type='submit']").click()

    def activate_subscription(self, url="https://bcss-uat.vnsky.vn/#/activate-subscription") -> None:
        self._load_url(url)

    def fill_basic_info(self, phone: str, serial: str, front_image: str, rear_image: str, portrait: str) -> None:
        self._set_field(phone, "//input[@placeholder='Số thuê bao']")
        self._set_field(serial, "//input[@placeholder='Số serial sim']")
        images = self._get_fields("file")[1:4]
        images[0].send_keys(front_image)
        images[1].send_keys(rear_image)
        images[2].send_keys(portrait)

    def create_signature_link(self) -> None:
        btn = self._get_field("//button/span[text()='Tạo link ký']")
        btn.click()

    def fake_signature(self, canvas) -> None:
        actions = ActionChains(self.driver)
        x_start, y_start = random.randint(10, 30), random.randint(10, 30)
        actions.move_to_element_with_offset(canvas, x_start, y_start).click_and_hold()
        for _ in range(random.randint(8, 10)):
            x_offset, y_offset = random.randint(10, 30), random.randint(10, 30)
            if random.choice([True, False]): x_offset *= -1
            if random.choice([True, False]): y_offset *= -1
            actions.move_by_offset(x_offset, y_offset)
        actions.release().perform()

    def sign_document(self) -> None:
        current_window = self.driver.current_window_handle
        all_windows = self.driver.window_handles
        self.driver.switch_to.window(all_windows[-1])
        canvas = self._get_field("sigCanvas", By.CLASS_NAME)
        self.fake_signature(canvas)
        btn = self._get_field("//button/span[text()='Xác nhận ký']")
        btn.click()
        time.sleep(5)  # Wait for the signature to be saved
        self.driver.close()
        self.driver.switch_to.window(current_window)

    def active_subscription(self):
        btn = self._get_field("//button/span[text()='Kích hoạt']")
        # btn.click() # Test only


class SkyBotAuto:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.bot = AutoActivateSubscription()

    def activate_subscription(self, phone: str, serial: str, front_image: str, rear_image: str, portrait: str) -> bool:
        result = False
        try:
            # Step 1: Login
            print("*Step 1: Logging in")
            self.bot.login(self.email, self.password, "https://bcss-uat.vnsky.vn/login")
            self.bot.wait_for_url_change()

            # Step 2: Redirect to activate subscription page
            print("*Step 2: Redirecting to activate subscription page")
            self.bot.activate_subscription()

            # Step 3: Fill basic information
            print("*Step 3: Filling basic information")
            self.bot.fill_basic_info(phone, serial, front_image, rear_image, portrait)
            WebDriverWait(self.bot.driver, 20).until(
                ec.presence_of_element_located((By.XPATH, "//button/span[text()='Tạo link ký']"))
            )
            self.bot.scroll_to_bottom()
            print("Basic information filled!")

            # Step 4: Create signature link
            print("*Step 4: Creating signature link")
            self.bot.create_signature_link()
            WebDriverWait(self.bot.driver, self.bot.WAIT_TIMEOUT).until(
                lambda driver: len(driver.window_handles) > 1
            )

            # Step 5: Sign document
            print("*Step 5: Signing document")
            self.bot.sign_document()

            # Step 6: Activate subscription
            time.sleep(8)
            print("*Step 6: Activating subscription")
            self.bot.active_subscription()
            print("Subscription activated successfully!")
            result = True
        except Exception as e:
            print("Activation failed!", e)
            result = False
        finally:
            time.sleep(5)
            self.bot.quit()
            return result
