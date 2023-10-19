"""
MIT License

Copyright (c) 2022-2023 iDev
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import shutil
import tempfile
from glob import glob
from dotenv import load_dotenv

from .features import *
import undetected_chromedriver as uc

load_dotenv()
IS_DEBUG = os.environ.get("IS_DEBUG")
PROFILE_PATH = os.environ.get("PROFILE_PATH")
WEBRTC = os.path.join('extension', 'webrtc_control.zip')
ACTIVE = os.path.join('extension', 'always_active.zip')
FINGERPRINT = os.path.join('extension', 'fingerprint_defender.zip')
TIMEZONE = os.path.join('extension', 'spoof_timezone.zip')
CUSTOM_EXTENSIONS = glob(os.path.join('extension', 'custom_extension', '*.zip')) + \
    glob(os.path.join('extension', 'custom_extension', '*.crx'))

class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    def __del__(self):
        shutil.rmtree(self._dir)


def get_driver(background, viewports, agent, auth_required, patched_driver, proxy_link, profile):
    options = None
    driver = None

    if profile:
        options = uc.ChromeOptions()
    else:
        options = webdriver.ChromeOptions()

    options.headless = background
    if viewports:
        options.add_argument(f"--window-size={choice(viewports)}")
    options.add_argument("--log-level=3")
    if not profile:
        options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"intl.accept_languages": 'en_US,en',
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2,
                "download_restrictions": 3}
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option('extensionLoadTimeout', 120000)
        options.add_argument(f"user-agent={agent}")
    options.add_argument("--mute-audio")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-features=UserAgentClientHint')
    options.add_argument("--disable-web-security")
    webdriver.DesiredCapabilities.CHROME['loggingPrefs'] = {
        'driver': 'OFF', 'server': 'OFF', 'browser': 'OFF'}

    if not background:
        options.add_extension(WEBRTC)
        options.add_extension(FINGERPRINT)
        options.add_extension(TIMEZONE)
        options.add_extension(ACTIVE)

        if CUSTOM_EXTENSIONS:
            for extension in CUSTOM_EXTENSIONS:
                options.add_extension(extension)

    if int(IS_DEBUG) == 0:

        if auth_required:

            proxy = proxy_link.replace('@', ':')
            splited_proxy = proxy.split(":")
            proxy = (splited_proxy[2], splited_proxy[-1], splited_proxy[0], splited_proxy[1])
            proxy_extension = ProxyExtension(*proxy)
            options.add_argument(f"--load-extension={proxy_extension.directory}")
        else:
            options.add_argument(f'--proxy-server={proxy_link}')

    service = Service(executable_path=patched_driver)

    if profile:
        profile_path = PROFILE_PATH + profile
        print(profile_path)
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument(f'--profile-directory={profile}')

        # driver = uc.Chrome(options=options, user_data_dir=profile_path)
        driver = uc.Chrome(options=options)
    else:
        
        service = Service(executable_path=patched_driver)
        driver = webdriver.Chrome(options=options, service=service)
    

    return driver


def play_video(driver):
    try:
        driver.find_element(By.CSS_SELECTOR, '[title^="Pause (k)"]')
    except WebDriverException:
        try:
            driver.find_element(
                By.CSS_SELECTOR, 'button.ytp-large-play-button.ytp-button').send_keys(Keys.ENTER)
        except WebDriverException:
            try:
                driver.find_element(
                    By.CSS_SELECTOR, '[title^="Play (k)"]').click()
            except WebDriverException:
                try:
                    driver.execute_script(
                        "document.querySelector('button.ytp-play-button.ytp-button').click()")
                except WebDriverException:
                    pass

    skip_again(driver)


def play_music(driver):
    try:
        driver.find_element(
            By.XPATH, '//*[@id="play-pause-button" and @title="Pause"]')
    except WebDriverException:
        try:
            driver.find_element(
                By.XPATH, '//*[@id="play-pause-button" and @title="Play"]').click()
        except WebDriverException:
            driver.execute_script(
                'document.querySelector("#play-pause-button").click()')

    skip_again(driver)


def type_keyword(driver, keyword, retry=False):
    if retry:
        for _ in range(30):
            try:
                driver.find_element(By.CSS_SELECTOR, 'input#search').click()
                break
            except WebDriverException:
                sleep(3)

    input_keyword = driver.find_element(By.CSS_SELECTOR, 'input#search')
    input_keyword.clear()
    for letter in keyword:
        input_keyword.send_keys(letter)
        sleep(uniform(.1, .4))

    method = randint(1, 2)
    if method == 1:
        input_keyword.send_keys(Keys.ENTER)
    else:
        icon = driver.find_element(
            By.XPATH, '//button[@id="search-icon-legacy"]')
        ensure_click(driver, icon)


def scroll_search(driver, video_title):
    msg = None
    for i in range(1, 11):
        try:
            section = WebDriverWait(driver, 60).until(EC.visibility_of_element_located(
                (By.XPATH, f'//ytd-item-section-renderer[{i}]')))
            if driver.find_element(By.XPATH, f'//ytd-item-section-renderer[{i}]').text == 'No more results':
                msg = 'failed'
                break
            find_video = section.find_element(
                By.XPATH, f'//a[@id="video-title"][@title="{video_title}"]')
            driver.execute_script(
                "arguments[0].scrollIntoViewIfNeeded();", find_video)
            sleep(1)
            bypass_popup(driver)
            ensure_click(driver, find_video)
            msg = 'success'
            break
        except NoSuchElementException:
            sleep(randint(2, 5))
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located(
                (By.TAG_NAME, 'body'))).send_keys(Keys.CONTROL, Keys.END)

    if i == 10:
        msg = 'failed'

    return msg


def filter_datetime(driver, filter_by):
    # Start Selector Section
    filters_selector = "//ytd-toggle-button-renderer/yt-button-shape/button"
    filters_last_hour_selector = "//ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[1]/a"
    filters_today_selector = "//ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[2]/a"
    filters_week_selector = "//ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[3]/a"
    filters_month_selector = "//ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[4]/a"
    filters_year_selector = "//ytd-search-filter-group-renderer[1]/ytd-search-filter-renderer[5]/a"
    selected_filter = ""
    if filter_by == "LAST_HOUR":
        selected_filter = filters_last_hour_selector
    elif filter_by == "TODAY":
        selected_filter = filters_today_selector
    elif filter_by == "THIS_WEEK":
        selected_filter = filters_week_selector
    elif filter_by == "THIS_MONTH":
        selected_filter = filters_month_selector
    elif filter_by == "THIS_YEAR":
        selected_filter = filters_year_selector
    # End Selector Section
    WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, filters_selector)))
    filters_action = driver.find_element(By.XPATH, filters_selector)
    ensure_click(driver, filters_action)

    sleep(uniform(1, 2))

    WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, selected_filter)))
    selected_filter_action = driver.find_element(By.XPATH, selected_filter)
    ensure_click(driver, selected_filter_action)


def search_video(driver, keyword, video_title, filter_by):
    try:
        type_keyword(driver, keyword)
        if filter_by != '':
            filter_datetime(driver, filter_by)
    except WebDriverException:
        try:
            bypass_popup(driver)
            type_keyword(driver, keyword, retry=True)
            if filter_by != '':
                filter_datetime(driver, filter_by)
        except WebDriverException:
            raise Exception(
                "Slow internet speed or Stuck at recaptcha! Can't perfrom search keyword")

    msg = scroll_search(driver, video_title)

    if msg == 'failed':
        bypass_popup(driver)

        filters = driver.find_element(By.CSS_SELECTOR, '#filter-menu a')
        driver.execute_script('arguments[0].scrollIntoViewIfNeeded()', filters)
        sleep(randint(1, 3))
        ensure_click(driver, filters)

        sleep(randint(1, 3))
        sort = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(
            (By.XPATH, '//div[@title="Sort by upload date"]')))
        ensure_click(driver, sort)

        msg = scroll_search(driver, video_title)

    return msg

def type_email(driver, email):
    WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.NAME, 'identifier'))
    )
    sleep(uniform(1, 3))
    input_keyword = driver.find_element(By.NAME, 'identifier')
    input_keyword.clear()
    for letter in email:
        input_keyword.send_keys(letter)
        sleep(uniform(.1, .2))

    method = randint(1, 2)
    if method == 1:
        input_keyword.send_keys(Keys.ENTER)
    else:
        icon = driver.find_element(
            By.ID, 'identifierNext')
        ensure_click(driver, icon)


def type_password(driver, password):
    WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.NAME, 'Passwd'))
    )
    sleep(uniform(1, 3))
    input_keyword = driver.find_element(By.NAME, 'Passwd')
    input_keyword.clear()
    for letter in password:
        input_keyword.send_keys(letter)
        sleep(uniform(.1, .2))

    method = randint(1, 2)
    if method == 1:
        input_keyword.send_keys(Keys.ENTER)
    else:
        icon = driver.find_element(
            By.ID, 'passwordNext')
        ensure_click(driver, icon)


def login_email(driver, email, password):
    driver.get("https://accounts.google.com/signin/v2/identifier")
    sleep(uniform(1, 3))
    type_email(driver, email)
    sleep(uniform(1, 3))
    type_password(driver, password)
    sleep(uniform(10, 15))

    # try:
    #     if driver.find_element(By.XPATH, f'//h1[text()="ยืนยันตัวตนของคุณ"]') or driver.find_element(By.XPATH, f'//span[text()="ยืนยันว่าเป็นคุณ"]'):
    #         return "failed"
    # except WebDriverException:
    return "success"