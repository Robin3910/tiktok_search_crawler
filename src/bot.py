# -*- coding:utf-8 -*-
import _thread
import json
import logging
import re
from random import randint
from time import time, sleep, localtime

import openpyxl
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager as CM

DEFAULT_IMPLICIT_WAIT = 1


class Bot(object):

    def __init__(self, headless=False, profileDir=None):
        f = open('infos/config.json', )
        botConfig = json.load(f)

        self.fetchTopic = botConfig["topic"]
        self.fetchNums = botConfig["fetch_nums"]
        self.fetchInterval = botConfig["fetch_interval"]
        self.kickFirst = True
        self.selectors = {
            'username': "//*[@data-e2e='challenge-item-username']",
            'fans': "//*[@data-e2e='followers-count']",
            'user_bio': "//*[@data-e2e='user-bio']",
            "btn_next": "//button[@class='btn-next']",
            "contact_link": "//*[@data-e2e='user-bio']/../div[2]/a/span"
        }
        self.curUserMap = {}
        self.ttUserHeaders = {
            'authority': 'www.tiktok.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        }
        self.data = [
            ["username", "contact_link", "fans", "brief", "tt_link"]
        ]
        self.nameList = []

        # Selenium config
        options = webdriver.ChromeOptions()

        # browser log
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

        # capabilities['loggingPrefs'] = {'browser': 'ALL'}

        options.add_argument(
            f'cookie=""')

        if profileDir:
            options.add_argument("user-data-dir=profiles/" + profileDir)

        if headless:
            options.add_argument("--headless")

        options.add_argument("--log-level=3")

        self.driver = webdriver.Chrome(
            executable_path=CM().install(), options=options, desired_capabilities=capabilities)
        self.driver.set_window_position(0, 0)
        self.driver.maximize_window()

        try:
            self.driver.get(f'https://www.tiktok.com/tag/{self.fetchTopic}?lang=en')

            _thread.start_new_thread(self.__waiting_for_stop_bot, ())
            self.__get_name_list()
            self.__fetch_info()
            self.__save_excel()

            self.__random_sleep__(3600, 3740)

            exit(0)

        except Exception as e:
            print(str(e))
            self.__save_excel()
            exit(0)

    def typeMessage(self, user, message):
        # Go to page and type message
        if self.__wait_for_element__(self.selectors['next_button'], "xpath"):
            self.__get_element__(
                self.selectors['next_button'], "xpath").click()
            self.__random_sleep__()

        for msg in message:
            if self.__wait_for_element__(self.selectors['textarea'], "xpath"):
                self.__type_slow__(self.selectors['textarea'], "xpath", msg)
                self.__random_sleep__()

            if self.__wait_for_element__(self.selectors['send'], "xpath"):
                self.__get_element__(self.selectors['send'], "xpath").click()
                self.__random_sleep__(3, 5)
                print('Message sent successfully')

    def __get_element__(self, element_tag, locator):
        """Wait for element and then return when it is available"""
        try:
            locator = locator.upper()
            dr = self.driver
            if locator == 'ID' and self.is_element_present(By.ID, element_tag):
                return WebDriverWait(dr, 15).until(lambda d: dr.find_element_by_id(element_tag))
            elif locator == 'NAME' and self.is_element_present(By.NAME, element_tag):
                return WebDriverWait(dr, 15).until(lambda d: dr.find_element_by_name(element_tag))
            elif locator == 'XPATH' and self.is_element_present(By.XPATH, element_tag):
                return WebDriverWait(dr, 15).until(lambda d: dr.find_element_by_xpath(element_tag))
            elif locator == 'CSS' and self.is_element_present(By.CSS_SELECTOR, element_tag):
                return WebDriverWait(dr, 15).until(lambda d: dr.find_element_by_css_selector(element_tag))
            else:
                logging.info(f"Error: Incorrect locator = {locator}")
        except Exception as e:
            logging.error(e)
        logging.info(f"Element not found with {locator} : {element_tag}")
        return None

    def is_element_present(self, how, what):
        """Check if an element is present"""
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def __wait_for_element__(self, element_tag, locator, timeout=30):
        """Wait till element present. Max 30 seconds"""
        result = False
        self.driver.implicitly_wait(0)
        locator = locator.upper()
        for i in range(timeout):
            initTime = time()
            try:
                if locator == 'ID' and self.is_element_present(By.ID, element_tag):
                    result = True
                    break
                elif locator == 'NAME' and self.is_element_present(By.NAME, element_tag):
                    result = True
                    break
                elif locator == 'XPATH' and self.is_element_present(By.XPATH, element_tag):
                    result = True
                    break
                elif locator == 'CSS' and self.is_element_present(By.CSS_SELECTORS, element_tag):
                    result = True
                    break
                else:
                    logging.info(f"Error: Incorrect locator = {locator}")
            except Exception as e:
                logging.error(e)
                print(f"Exception when __wait_for_element__ : {e}")

            sleep(1 - (time() - initTime))
        else:
            print(
                f"Timed out. Element not found with {locator} : {element_tag}")
        self.driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)
        return result

    def __type_slow__(self, element_tag, locator, input_text=''):
        """Type the given input text"""
        try:
            self.__wait_for_element__(element_tag, locator, 5)
            self.__wait_for_element__(element_tag, locator, 5)
            element = self.__get_element__(element_tag, locator)
            actions = ActionChains(self.driver)
            actions.click(element).perform()
            # element.send_keys(input_text)
            for s in input_text:
                element.send_keys(s)
                # sleep(uniform(0.005, 0.02))

        except Exception as e:
            logging.error(e)
            print(f'Exception when __typeSlow__ : {e}')

    def __random_sleep__(self, minimum=2, maximum=7):
        t = randint(minimum, maximum)
        logging.info(f'Wait {t} seconds')
        sleep(t)

    def __scrolldown__(self):
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

    def teardown(self):
        self.driver.close()
        self.driver.quit()

    def extract_cookies(self, cookie=""):
        """从浏览器或者request headers中拿到cookie字符串，提取为字典格式的cookies"""
        cookies = {i.split("=")[0]: i.split("=")[1] for i in cookie.split("; ")}
        return cookies

    def __find_element_and_click(self, name, locator):
        if self.__wait_for_element__(name, locator):
            self.__get_element__(
                name, locator).click()
            self.__random_sleep__()

    def __save_excel(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        for row in self.data:
            sheet.append(row)
        workbook.save('userinfo_' + str(time()) + '.xlsx')
        print("get userinfo task finish, save into excel")

    def __fetch_info(self):
        for username in self.nameList:
            ttUserLink = f'https://www.tiktok.com/@{username}?lang=en'
            desc = ""
            contactLink = ""
            fans = ""
            # open new tab for fetch info
            newWindow = f'window.open("{ttUserLink}")'
            self.driver.execute_script(newWindow)
            handles = self.driver.window_handles
            self.driver.switch_to.window(handles[len(handles) - 1])
            self.__random_sleep__(5, 10)
            try:
                userBio = self.__get_element__(self.selectors["user_bio"], "xpath")
                if userBio is not None:
                    desc = userBio.text
                contactNode = self.__get_element__(self.selectors["contact_link"], "xpath")
                if contactNode is not None:
                    contactLink = contactNode.text

                fansNode = self.__get_element__(self.selectors["fans"], "xpath")
                if fansNode is not None:
                    fans = fansNode.text

                self.data.append(
                    [username, fans, contactLink, desc, ttUserLink])
                print(
                    f'-------------------fetch success|username:{username}|cur num: {len(self.data) - 1}----------------------')
                self.driver.close()
                self.driver.switch_to.window(handles[0])
                if len(self.data) - 1 >= self.fetchNums:
                    return
                self.__random_sleep__(self.fetchInterval, self.fetchInterval)

            except Exception as e:
                print(
                    f'-------------------fetch error|error info: {e}|username:{username}|cur num: {len(self.data) - 1}----------------------')

    def __run_crawler(self):
        print("fetch info start...")
        self.__fetch_info()
        while len(self.data) < self.fetchNums:
            print("cur process: " + str(len(self.data) - 1) + "|target nums: " + str(self.fetchNums))
            self.__scrolldown__()
            self.__random_sleep__()
            self.__find_element_and_click(self.selectors["btn_next"], "xpath")
            self.__random_sleep__(10, 10)
            self.__fetch_info()

        self.__save_excel()
        exit(0)

    def __waiting_for_stop_bot(self):
        cmd = input()
        if cmd == "stop":
            self.__save_excel()
            print("stop the bot!")
            exit(0)

    def __get_name_list(self):
        usernamesEles = self.driver.find_elements_by_xpath(self.selectors["username"])
        while len(usernamesEles) < self.fetchNums:
            self.__scrolldown__()
            self.__random_sleep__(5, 10)
            usernamesEles = self.driver.find_elements_by_xpath(self.selectors["username"])

        for usernamesEle in usernamesEles:
            self.nameList.append(usernamesEle.text)
