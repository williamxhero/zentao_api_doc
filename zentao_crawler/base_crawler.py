from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
import sys
import glob
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_chrome_executable():
    """
    自动搜索Chrome浏览器可执行文件路径

    Returns:
        str: Chrome浏览器可执行文件路径，如果未找到则返回None
    """
    # 常见的Chrome安装路径
    possible_paths = [
        # Windows路径
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),

        # Linux路径
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",

        # macOS路径
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    ]

    # 先检查常见路径
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"在常见路径中找到Chrome: {path}")
            return path

    # 如果常见路径中未找到，尝试使用glob模式搜索
    if sys.platform.startswith('win'):
        # Windows上的搜索模式
        search_patterns = [
            r"C:\Program Files\Google\Chrome*\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome*\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome*\Application\chrome.exe"),
        ]

        for pattern in search_patterns:
            matches = glob.glob(pattern)
            if matches:
                logger.info(f"通过搜索模式找到Chrome: {matches[0]}")
                return matches[0]

    # 如果仍然未找到，返回None
    logger.warning("未能自动找到Chrome浏览器路径")
    return None


class BaseWebCrawler(ABC):
    """
    爬虫基类，定义爬虫的通用接口
    """

    def __init__(self, login_url, api_doc_url, username, password, output_dir="api_doc"):
        """
        初始化爬虫

        Args:
            login_url: 登录页面URL
            api_doc_url: API文档页面URL
            username: 用户名
            password: 密码
            output_dir: 输出目录
        """
        self.login_url = login_url
        self.api_doc_url = api_doc_url
        self.username = username
        self.password = password
        self.output_dir = output_dir
        self.driver = None

    def setup_driver(self):
        """
        初始化Chrome浏览器驱动，伪装无头模式，避免被检测。

        Returns:
            WebDriver实例
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 自动搜索Chrome浏览器路径
            chrome_path = find_chrome_executable()
            if chrome_path:
                chrome_options.binary_location = chrome_path

            driver = webdriver.Chrome(options=chrome_options)

            # 伪装webdriver特征
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })

            self.driver = driver
            return driver
        except Exception as e:
            logger.error(f"初始化Chrome驱动失败: {str(e)}")
            raise

    def login(self):
        """
        登录禅道系统

        注意：这是一个基本的登录方法，适用于大多数禅道版本。
        如果特定版本的登录流程有变化，子类可以重写这个方法。

        Returns:
            bool: 登录是否成功
        """
        try:
            logger.info("访问禅道登录页...")
            self.driver.get(self.login_url)

            # 等待用户名输入框出现
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "account"))
            )

            # 输入用户名
            user_input = self.driver.find_element(By.NAME, "account")
            user_input.clear()
            user_input.send_keys(self.username)

            # 输入密码
            pwd_input = self.driver.find_element(By.NAME, "password")
            pwd_input.clear()
            pwd_input.send_keys(self.password)

            # 点击登录按钮
            submit_btn = self.driver.find_element(By.ID, "submit")
            submit_btn.click()

            # 等待跳转，判断是否登录成功
            time.sleep(2)
            current_url = self.driver.current_url
            if "user-login" in current_url:
                logger.error("登录失败，请检查用户名和密码")
                return False
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录禅道时发生异常: {str(e)}")
            return False

    def close(self):
        """
        关闭浏览器
        """
        if self.driver:
            logger.info("关闭浏览器")
            self.driver.quit()
            self.driver = None

    def save_info_md(self, version_text):
        """
        生成api_doc/info.md，记录禅道版本、时间、API URL、账号等信息

        Args:
            version_text (str): 禅道版本号
        """
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            info_path = os.path.join(self.output_dir, "info.md")
            with open(info_path, "w", encoding="utf-8") as f:
                f.write("# 爬虫信息\n\n")
                f.write(f"- 禅道版本: {version_text}\n")
                f.write(f"- 爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- API文档URL: {self.api_doc_url}\n")
                f.write(f"- 账号: {self.username}\n")
            logger.info(f"已生成info.md: {info_path}")
        except Exception as e:
            logger.warning(f"生成info.md失败: {str(e)}")

    def run_crawl(self):
        """
        模板方法：执行爬虫，自动保存info.md

        子类必须实现crawl()，并返回禅道版本号字符串

        调用此方法后，将自动生成api_doc/info.md
        """
        version_text = self.crawl()
        self.save_info_md(version_text)

    @abstractmethod
    def crawl(self):
        """
        爬取API文档，生成符合规范的Markdown接口文档。

        生成的每个Markdown文件应遵循以下格式：

        ### METHOD /path

        接口的简要描述。

        #### 请求头

        | 名称 | 类型 | 必填 | 描述 |
        | --- | --- | --- | --- |
        | param1 | string | 是 | 参数1描述 |
        | param2 | int | 否 | 参数2描述 |

        #### 响应参数

        | 名称 | 类型 | 必填 | 描述 |
        | --- | --- | --- | --- |
        | total | int | 是 | 版本总数 |
        | builds | array | 是 | 版本列表 |

        **builds 数组元素**

        | 名称 | 类型 | 必填 | 描述 |
        | --- | --- | --- | --- |
        | id | int | 是 | 版本ID |
        | project | int | 是 | 所属项目 |
        | product | int | 是 | 所属产品 |
        | branch | int | 是 | 所属分支 |
        | execution | int | 是 | 所属执行 |
        | name | string | 是 | 版本名称 |
        | scmPath | string | 否 | 源代码地址 |
        | filePath | string | 否 | 下载地址 |
        | date | date | 是 | 打包日期 |
        | builder | user | 是 | 构建者 |
        | desc | string | 是 | 版本描述 |

        **嵌套规则：**
        - 对象类型字段，使用 "**字段名 对象**" 作为新表格标题
        - 数组类型字段，使用 "**字段名 数组元素**" 作为新表格标题
        - 支持多层嵌套，递归展开

        #### 响应示例

        ```json
        {
            "total": 1,
            "builds": [
                {
                    "id": 123,
                    "project": 1,
                    "product": 2,
                    "branch": 3,
                    "execution": 4,
                    "name": "版本名称",
                    "scmPath": "http://repo",
                    "filePath": "http://download",
                    "date": "2024-01-01",
                    "builder": "admin",
                    "desc": "描述信息"
                }
            ]
        }
        ```

        其他版本的爬虫实现此方法时，必须生成符合上述规范的Markdown文档，
        以便后续自动转换为OpenAPI规范。
        """
        pass
