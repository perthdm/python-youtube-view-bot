from time import sleep
from random import uniform, randint
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def ensure_click(driver, element):
    try:
        element.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", element)

def type_email(driver, email):
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.NAME, 'identifier'))
    )
    sleep(uniform(1, 3))
    input_keyword = driver.find_element(By.NAME, 'identifier')
    input_keyword.clear()
    for letter in email:
        input_keyword.send_keys(letter)
        sleep(uniform(.1, .4))

    method = randint(1, 2)
    if method == 1:
        input_keyword.send_keys(Keys.ENTER)
    else:
        icon = driver.find_element(
            By.ID, 'identifierNext')
        ensure_click(driver, icon)


def type_password(driver, password):
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.NAME, 'Passwd'))
    )
    sleep(uniform(1, 3))
    input_keyword = driver.find_element(By.NAME, 'Passwd')
    input_keyword.clear()
    for letter in password:
        input_keyword.send_keys(letter)
        sleep(uniform(.1, .4))

    method = randint(1, 2)
    if method == 1:
        input_keyword.send_keys(Keys.ENTER)
    else:
        icon = driver.find_element(
            By.ID, 'passwordNext')
        ensure_click(driver, icon)


def subscribe_channel(driver, channel):
    driver.get(channel)
    subscribe_button_xpath = "//div[@id=\"subscribe-button\"]/ytd-subscribe-button-renderer/tp-yt-paper-button"
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, subscribe_button_xpath))
    )
    subscribe_button = driver.find_element(By.XPATH, subscribe_button_xpath)
    subscribe_button.click()
    ensure_click(driver, subscribe_button)