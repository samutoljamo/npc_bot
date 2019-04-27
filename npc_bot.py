from selenium import webdriver
from selenium.webdriver.chrome.options import Options as coptions
from selenium.webdriver.firefox.options import Options as foptions
from selenium.common.exceptions import NoSuchElementException
import re
import configparser
import time


class NpcBot:

    def __init__(self):
        self.config = None  # dictionary consisting of the values in the config file
        self.username = None  # travian username
        self.password = None  # travian password
        self.visible = None  # True: user sees the browser False: use headless mode
        self.driver = None # webdriver
        self.server_url = None # url of the travian server
        self.villages = None
        self.browser = None
        self.marketplace_url = None


    def string_to_boolean(self, string):
        if string.lower() == "true":
            return True
        elif string.lower() == "false":
            return False
        return None


    def get_driver_path(self):
        if self.browser == 'chrome':
            return "chromedriver.exe"
        elif self.browser == 'firefox':
            return 'geckodriver.exe'
        raise ValueError("'browser' must either chrome or firefox. Fix the config file")


    def read_config_file(self):
        config = configparser.ConfigParser()
        config.read('npc_bot.ini')
        self.config = config['general']
        self.username = self.config['username']
        self.password = self.config['password']
        visible = self.string_to_boolean(self.config['visible'])
        if visible is None: raise ValueError("'visible' must either true or false. Fix the config file")
        self.visible = visible
        self.browser = self.config['browser'].lower()
        self.villages = self.config['villages'].split(",")
        self.server_url = self.config['server_url']
        if not self.username:raise ValueError("'username' is not valid")
        if not self.password:raise ValueError("'password' is not valid")
        if not self.villages[0]:raise ValueError("'villages' is not valid")
        if not self.server_url:raise ValueError("'server_url' is not valid")


    def run(self):
        self.read_config_file()
        self.driver_path = self.get_driver_path()
        self.marketplace_url = f"{self.server_url}/build.php?gid=17"
        print(self.driver_path)
        if self.browser == 'chrome':
            options = coptions()
            if self.visible is False:
                options.add_argument("--headless")
            self.driver = webdriver.Chrome(self.driver_path, chrome_options=options)
        else:
            options = foptions()
            if self.visible is False:
                options.add_argument("--headless")
            self.driver = webdriver.Firefox(executable_path=self.driver_path, firefox_options=options)
        self.login()
        try:
            self.get_amount_of_gold()
        except:
            raise ValueError("Bad credentials")
        self.npc()
        while True:
            if self.get_amount_of_gold() >= 3:
                t1 = self.main()
                time.sleep(120 if t1 > 120 else t1 - 20 if t1 - 20 >= 0 else 5)
            else:
                raise ValueError("You need at least 3 gold coins to trade resources")

    def login(self):
        self.driver.get(f"{self.server_url}/login.php")
        username_field = self.driver.find_element_by_name("name")
        password_field = self.driver.find_element_by_name("password")
        username_field.send_keys(self.username)
        password_field.send_keys(self.password)
        self.driver.find_element_by_id("s1").click()


    def get_amount_of_gold(self):
        if self.driver.current_url != f"{self.server_url}/dorf1.php":
            self.driver.get(f"{self.server_url}/dorf1.php")
        return self.remove_extra_chars(self.driver.find_element_by_class_name("ajaxReplaceableGoldAmount").text)


    def main(self):
        times = []
        for i in self.villages:
            t = self.check(self.village_link_by_name(i))
            if t is not None:
                times.append(t)
        try:
            return min(times)
        except ValueError:
            return 120


    def check(self, village_url):
        self.driver.get(village_url)
        t = self.time_until_full()
        if t < 10:
            self.npc()
            return None
        else:
            return t


    def npc(self):
        ware_space = self.ware_total_space()
        print(ware_space)
        url = self.marketplace_url
        if self.driver.current_url != self.marketplace_url:
            self.driver.get(url)
        for i in self.driver.find_elements_by_tag_name('button'):
            if i.text.lower() == "exchange resources":
                i.click()
                break
        time.sleep(3)
        inputs = self.driver.find_elements_by_class_name('text')
        for i in range(4):
            inputs[i].clear()
            if i == 3:
                inputs[i].send_keys(str(0))
                break
            inputs[i].send_keys(ware_space)
        time.sleep(0.3)
        for i in range(4):
            if i == 3:
                if int(inputs[3].get_attribute("value")) != 0:
                    print("Errored")
                break
            if int(inputs[i].get_attribute("value")) != ware_space:
                print("Errored")
        for i in self.driver.find_elements_by_tag_name('button'):
            if i.get_attribute("value").lower() == "distribute remaining resources.":
                i.click()
                break
        time.sleep(0.3)
        self.driver.find_element_by_id("npc_market_button").click()
        time.sleep(0.3)


    def time_until_full(self):
        return (self.granary_total_space() - self.crop_amount()) / self.production_per_second()


    def village_link_by_name(self, name):
        villages = self.driver.find_elements_by_css_selector(".innerBox.content")[5].find_elements_by_tag_name("a")
        for i in villages:
            if i.find_element_by_class_name("name").text == name:
                return i.get_attribute("href")
        if name[0] == " ":
            name = name[1:]
            for i in villages:
                if i.find_element_by_class_name("name").text == name:
                    return i.get_attribute("href")
        raise ValueError("Village was not found")


    def granary_total_space(self):
        if self.driver.current_url != f"{self.server_url}/dorf1.php":
            self.driver.get(f"{self.server_url}/dorf1.php")
        return self.remove_extra_chars(self.driver.find_element_by_id("stockBarGranary").text)


    def ware_total_space(self):
        if self.driver.current_url != f"{self.server_url}/dorf1.php":
            self.driver.get(f"{self.server_url}/dorf1.php")
        return self.remove_extra_chars(self.driver.find_element_by_id("stockBarWarehouse").text)


    def crop_amount(self):
        if self.driver.current_url != f"{self.server_url}/dorf1.php":
            self.driver.get(f"{self.server_url}/dorf1.php")
        div = self.driver.find_element_by_id("stockBarResource4")
        return self.remove_extra_chars(div.find_element_by_class_name("value").text)


    def production_per_second(self):
        if self.driver.current_url != f"{self.server_url}/dorf1.php":
            self.driver.get(f"{self.server_url}/dorf1.php")
        return self.remove_extra_chars(self.driver.find_elements_by_class_name("num")[3].text) / 3600


    @staticmethod
    def remove_extra_chars(somestr):
        return int(re.sub('[^0-9-]', '', somestr))


if __name__ == "__main__":
    d = NpcBot()
    d.run()
    input('Press enter to exit')
