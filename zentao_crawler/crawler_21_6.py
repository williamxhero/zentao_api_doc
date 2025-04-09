from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
import re

# 获取日志记录器
logger = logging.getLogger(__name__)

# 导入基类
from .base_crawler import BaseWebCrawler

class WebCrawler_21_6(BaseWebCrawler):
    """
    禅道21.6版本的爬虫实现
    """

    def detect_version(self):
        """
        检测禅道版本

        Returns:
            str: 版本号文本
        """
        try:
            version_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div[2]/a/span"))
            )
            version_text = version_element.text.strip()
            logger.info(f"检测到禅道版本: {version_text}")
            return version_text
        except Exception:
            logger.warning("未能检测到禅道版本信息")
            return None

    def version_supported(self, ver_str):
        """
        判断版本号是否满足条件

        Args:
            ver_str: 版本号字符串

        Returns:
            bool: 是否支持该版本
        """
        if not ver_str:
            return False
        # 简单判断，未来可扩展为更复杂的版本比较
        try:
            # 只提取数字部分
            match = re.search(r'(\d+\.\d+)', ver_str)
            if not match:
                return False
            major_minor = match.group(1)
            major, minor = map(float, major_minor.split('.'))
            # 版本大于等于21.6
            return (major > 21) or (major == 21 and minor >= 6)
        except Exception as e:
            logger.error(f"版本号解析失败: {str(e)}")
            return False

    def parse_table_recursive(self, table_elem):
        """
        递归解析表格，生成嵌套的markdown表格

        Args:
            table_elem: 表格元素

        Returns:
            str: markdown格式的表格
        """
        try:
            rows = table_elem.find_elements(By.TAG_NAME, "tr")
            param_list = []
            for row in rows[1:]:  # 跳过表头
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4:
                    continue
                raw_name = cols[0].text.strip()
                indent_level = 0
                name_clean = raw_name
                indent_match = re.match(r'^(∟+)', raw_name)
                if indent_match:
                    indent_level = len(indent_match.group(1))
                    name_clean = raw_name[indent_level:].strip()
                param = {
                    "name": name_clean,
                    "type": cols[1].text.strip(),
                    "required": cols[2].text.strip(),
                    "description": cols[3].text.strip(),
                    "children": [],
                    "indent": indent_level
                }
                param_list.append(param)

            # 构建树
            root = []
            stack = []
            for param in param_list:
                while stack and stack[-1]["indent"] >= param["indent"]:
                    stack.pop()
                if stack:
                    stack[-1]["children"].append(param)
                else:
                    root.append(param)
                stack.append(param)

            # 递归生成markdown
            def gen_md(params, title=None):
                md = ""
                if title:
                    md += f"**{title}**\n\n"
                md += "| 名称 | 类型 | 必填 | 描述 |\n"
                md += "| --- | --- | --- | --- |\n"
                for p in params:
                    md += f"| {p['name']} | {p['type']} | {p['required']} | {p['description']} |\n"
                md += "\n"
                for p in params:
                    if p["children"]:
                        child_title = f"{p['name']} 对象" if p["type"] == "object" else f"{p['name']} 数组元素"
                        md += gen_md(p["children"], child_title)
                return md

            return gen_md(root)
        except Exception as e:
            logger.error(f"解析表格失败: {str(e)}")
            return ""

    def crawl(self):
        """
        爬取API文档
        """
        try:
            # 确保已登录
            if not self.driver:
                self.setup_driver()
                if not self.login():
                    logger.error("登录失败，无法继续爬取")
                    return False

            logger.info("访问API文档页面...")
            self.driver.get(self.api_doc_url)

            # 等待页面加载
            time.sleep(2)
            logger.info(f"当前页面标题: {self.driver.title}")
            logger.info(f"当前URL: {self.driver.current_url}")

            # 检测禅道版本
            version_text = self.detect_version()
            if not self.version_supported(version_text):
                logger.error(f"当前版本 {version_text} 不支持，需要21.6及以上版本")
                return ""

            logger.info("版本满足条件，开始提取API菜单链接")
            try:
                # 切换到appIframe-admin
                self.driver.switch_to.default_content()
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "appIframe-admin"))
                )
                self.driver.switch_to.frame(iframe)
                logger.info("已切换到iframe #appIframe-admin")

                # 展开所有菜单
                top_menus = self.driver.find_elements(By.XPATH, "//menu/li/div/div")
                logger.info(f"发现 {len(top_menus)} 个一级菜单，尝试依次点击展开")
                for idx, menu in enumerate(top_menus):
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", menu)
                        menu.click()
                        time.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"点击第{idx+1}个一级菜单失败: {str(e)}")

                # 查找所有API菜单项链接
                all_links = self.driver.find_elements(By.XPATH, "//menu//a")
                api_links = []
                for link in all_links:
                    href = link.get_attribute("href")
                    if href and re.search(r"dev-api-restapi-\d+\.html", href):
                        api_links.append(link)
                logger.info(f"共识别出 {len(api_links)} 个API菜单项")

                # 确保输出目录存在
                if not os.path.exists(self.output_dir):
                    os.makedirs(self.output_dir)

                logger.info("开始逐个提取API详情")
                for idx, api_link in enumerate(api_links):
                    try:
                        title = api_link.text.strip()
                        href = api_link.get_attribute("href")
                        logger.info(f"[{idx+1}/{len(api_links)}] 处理API: {title} ({href})")

                        # 点击菜单项
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", api_link)
                        api_link.click()
                        time.sleep(1)  # 等待详情加载

                        # 提取请求方法
                        try:
                            method_elem = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[1]")
                            method = method_elem.text.strip()
                        except:
                            method = ""

                        # 提取API URL
                        try:
                            url_elem = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[2]")
                            api_url = url_elem.text.strip()
                        except:
                            api_url = ""

                        # 提取描述
                        try:
                            desc_elem = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/h2")
                            description = desc_elem.text.strip()
                        except:
                            description = ""

                        # 请求头表格
                        req_md = ""
                        try:
                            req_table_elem = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/table[1]")
                            req_md = self.parse_table_recursive(req_table_elem)
                        except:
                            pass

                        # 响应参数表格
                        resp_md = ""
                        try:
                            resp_table_elem = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/table[2]")
                            resp_md = self.parse_table_recursive(resp_table_elem)
                        except:
                            pass

                        # 响应示例
                        resp_example = ""
                        try:
                            resp_pre = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/pre")
                            resp_example = resp_pre.text.strip()
                        except:
                            pass

                        # 生成简洁markdown内容
                        md = f"### {method} {api_url}\n\n"
                        md += f"{description}\n\n"

                        if req_md:
                            md += "#### 请求头\n\n"
                            md += req_md + "\n\n"

                        if resp_md:
                            md += "#### 响应参数\n\n"
                            md += resp_md + "\n\n"

                        if resp_example:
                            md += "#### 响应示例\n\n"
                            md += f"```json\n{resp_example}\n```\n"

                        # 生成英文文件名
                        if api_url:
                            safe_name = api_url.strip().replace("/", "_").replace(":", "_").strip("_")
                            safe_name = re.sub(r'[\\/*?:"<>|]', "_", safe_name)
                            if not safe_name:
                                safe_name = f"api_{idx+1}"
                        else:
                            safe_name = f"api_{idx+1}"

                        filename = os.path.join(self.output_dir, f"{safe_name}.md")
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(md)
                        logger.info(f"已保存: {filename}")

                    except Exception as e:
                        logger.error(f"处理第{idx+1}个API时出错: {str(e)}")

                # 调用基类方法生成info.md
                self.save_info_md(version_text)

                return version_text

            except Exception as e:
                logger.error(f"查找API菜单链接时发生异常: {str(e)}")
                return ""

        except Exception as e:
            logger.error(f"爬取过程中发生异常: {str(e)}")
            return ""
