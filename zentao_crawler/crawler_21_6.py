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
    禅道21.6版本的爬虫实现，
    未来版本的爬虫类应该继承自该类，而不是BaseWebCrawler
    """

    def login(self):
        """
        登录21.6版本的禅道系统

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

    def save_api_html(self, html_filename):
        """
        保存API页面的HTML内容

        Args:
            html_filename: HTML文件保存路径

        Returns:
            bool: 保存是否成功
        """
        try:
            # 创建html目录
            html_dir = os.path.dirname(html_filename)
            if not os.path.exists(html_dir):
                os.makedirs(html_dir)

            # 只保存<div class="bg-white p-3 panel">里的内容
            panel_elem = self.driver.find_element(By.CSS_SELECTOR, "div.bg-white.p-3.panel")
            if panel_elem:
                panel_html = panel_elem.get_attribute('outerHTML')
                with open(html_filename, "w", encoding="utf-8") as f:
                    f.write(panel_html)
                logger.info(f"已保存面板内容: {html_filename}")
                return True
            else:
                logger.warning(f"未找到面板元素")
                return False
        except Exception as e:
            logger.warning(f"保存HTML内容失败: {str(e)}")
            return False

    def parse_api_info(self):
        """
        解析API基本信息，包括方法、URL和描述

        Returns:
            dict: 包含API信息的字典
        """
        result = {
            'method': '',
            'url': '',
            'description': ''
        }

        # 提取API方法
        try:
            method_elem = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[1]"))
            )
            result['method'] = method_elem.text.strip()
            logger.info(f"检测到API方法: {result['method']}")
        except Exception as e:
            logger.warning(f"未能检测到API方法: {str(e)}")

        # 提取API URL
        try:
            url_elem = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[2]"))
            )
            result['url'] = url_elem.text.strip()
            logger.info(f"检测到API URL: {result['url']}")
        except Exception as e:
            logger.warning(f"未能检测到API URL: {str(e)}")

        # 提取API描述
        try:
            desc_elem = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/h2"))
            )
            result['description'] = desc_elem.text.strip()
            logger.info(f"检测到API描述: {result['description']}")
        except Exception as e:
            logger.warning(f"未能检测到API描述: {str(e)}")

        return result

    def parse_api_sections(self):
        """
        解析API页面的各个部分，包括表格和示例

        本方法会根据标题内容动态判断表格类型，而不是固定的表格顺序。
        对于请求体表格，会提取字段名称、类型、是否必填、描述等信息。
        对于请求示例和响应示例，会从 pre 元素中提取，而不是表格。
        如果主要方法失败，会尝试使用备用方法提取示例。

        Returns:
            dict: 包含各部分内容的字典，包括：
                - req_md: 请求头表格的Markdown内容
                - req_body_md: 请求体表格的Markdown内容
                - resp_md: 响应参数表格的Markdown内容
                - req_example: 请求示例的JSON字符串
                - resp_example: 响应示例的JSON字符串
        """
        result = {
            'req_md': '',
            'req_body_md': '',
            'resp_md': '',
            'req_example': '',
            'resp_example': ''
        }

        try:
            # 使用显式等待，等待页面内容加载
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]"))
            )

            # 获取所有h3标题
            h3_elems = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/h3")
            # 获取所有表格
            tables = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/table")

            # 对每个h3标题，找到其后面的表格
            for i, h3 in enumerate(h3_elems):
                title_text = h3.text.strip()
                logger.info(f"发现标题: {title_text}")

                # 获取当前标题的位置
                h3_location = h3.location

                # 获取下一个标题的位置（如果有）
                next_h3_location = None
                if i < len(h3_elems) - 1:
                    next_h3_location = h3_elems[i+1].location

                # 如果是表格标题，尝试找到其后面的表格
                if any(keyword in title_text for keyword in ["请求头", "请求体", "请求响应", "响应参数", "返回参数", "响应字段"]):
                    # 找到该标题后面的第一个表格
                    table_found = False
                    for table in tables:
                        # 如果表格在标题之后
                        if table.location['y'] > h3_location['y']:
                            # 如果这个标题后面还有其他标题，则表格应该在这两个标题之间
                            if next_h3_location and table.location['y'] > next_h3_location['y']:
                                continue

                            # 根据标题内容判断表格类型
                            if "请求头" in title_text:
                                result['req_md'] = self.parse_table_recursive(table)
                                logger.info("成功解析请求头表格")
                            elif "请求体" in title_text:
                                result['req_body_md'] = self.parse_table_recursive(table)
                                logger.info("成功解析请求体表格")
                            elif "请求响应" in title_text or "响应参数" in title_text or "返回参数" in title_text or "响应字段" in title_text:
                                result['resp_md'] = self.parse_table_recursive(table)
                                logger.info("成功解析响应参数表格")

                            table_found = True
                            break

                    if not table_found:
                        logger.warning(f"标题 '{title_text}' 后面没有找到表格")

                # 如果是示例标题，尝试找到其后面的pre元素
                elif any(keyword in title_text for keyword in ["请求示例", "响应示例", "返回示例"]):
                    # 使用XPath直接定位当前标题后面的pre元素
                    xpath = f"//h3[contains(text(), '{title_text}')]/following-sibling::pre[1]"
                    try:
                        pre_elem = self.driver.find_element(By.XPATH, xpath)

                        # 确保pre元素在当前标题和下一个标题之间
                        if next_h3_location is None or pre_elem.location['y'] < next_h3_location['y']:
                            pre_text = pre_elem.text.strip()

                            if "请求示例" in title_text:
                                result['req_example'] = pre_text
                                logger.info(f"成功提取请求示例: {pre_text[:50]}...")
                            elif "响应示例" in title_text or "返回示例" in title_text:
                                result['resp_example'] = pre_text
                                logger.info(f"成功提取响应示例: {pre_text[:50]}...")
                    except Exception as e:
                        logger.warning(f"未能找到标题 '{title_text}' 后面的pre元素: {str(e)}")

                        # 尝试使用更通用的方法
                        try:
                            # 获取所有pre元素
                            pre_elems = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/div[2]/pre")

                            # 找到当前标题后面的第一个pre元素
                            for pre in pre_elems:
                                if pre.location['y'] > h3_location['y']:
                                    if next_h3_location is None or pre.location['y'] < next_h3_location['y']:
                                        pre_text = pre.text.strip()

                                        if "请求示例" in title_text:
                                            result['req_example'] = pre_text
                                            logger.info(f"成功提取请求示例(备用方法): {pre_text[:50]}...")
                                        elif "响应示例" in title_text or "返回示例" in title_text:
                                            result['resp_example'] = pre_text
                                            logger.info(f"成功提取响应示例(备用方法): {pre_text[:50]}...")
                                        break
                        except Exception as e2:
                            logger.warning(f"备用方法也未能提取示例: {str(e2)}")
        except Exception as e:
            logger.error(f"解析API部分时发生错误: {str(e)}")

        return result

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

        本方法实现了完整的爬取流程，包括：
        1. 登录禅道系统
        2. 访问API文档页面
        3. 检测禅道版本
        4. 展开所有API菜单
        5. 逐个点击API链接并提取信息
        6. 保存HTML内容到api_doc/html目录，只保存<div class="bg-white p-3 panel">里的内容
        7. 解析API信息，包括方法、URL、描述等
        8. 根据标题内容动态判断表格类型，而不是固定的表格顺序
        9. 正确提取请求体表格，包含字段名称、类型、是否必填、描述等信息
        10. 从 pre 元素中提取请求示例和响应示例，而不是表格
        11. 处理复杂的请求示例，包括嵌套对象、数组等结构
        12. 生成符合规范的Markdown文档

        未来版本的爬虫类应该继承自本类，而不是 BaseWebCrawler。
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

                        # 增加等待时间，确保页面完全加载
                        time.sleep(3)  # 增加等待时间

                        # 保存HTML内容
                        html_filename = os.path.join(self.output_dir, "html", f"{idx+1:03d}_{href.split('/')[-1]}")
                        self.save_api_html(html_filename)

                        # 解析API信息
                        api_info = self.parse_api_info()
                        method = api_info['method']
                        api_url = api_info['url']
                        description = api_info['description']

                        # 解析表格和示例
                        sections = self.parse_api_sections()
                        req_md = sections.get('req_md', '')
                        req_body_md = sections.get('req_body_md', '')
                        resp_md = sections.get('resp_md', '')
                        req_example = sections.get('req_example', '')
                        resp_example = sections.get('resp_example', '')


                        # 验证是否获取到有效内容
                        if not method or not api_url:
                            logger.warning(f"未能获取到有效的API方法或URL，尝试重新加载页面")
                            # 尝试重新加载页面
                            api_link.click()
                            time.sleep(5)  # 等待更长时间

                            # 重新获取方法
                            try:
                                method_elem = WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[1]"))
                                )
                                method = method_elem.text.strip()
                                logger.info(f"重试后检测到API方法: {method}")
                            except Exception as e:
                                logger.warning(f"重试后仍未能检测到API方法: {str(e)}")

                            # 重新获取URL
                            try:
                                url_elem = WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/div[2]"))
                                )
                                api_url = url_elem.text.strip()
                                logger.info(f"重试后检测到API URL: {api_url}")
                            except Exception as e:
                                logger.warning(f"重试后仍未能检测到API URL: {str(e)}")

                        # 生成简洁markdown内容
                        md = f"### {method} {api_url}\n\n"
                        md += f"{description}\n\n"

                        if req_md:
                            md += "#### 请求头\n\n"
                            md += req_md + "\n\n"

                        if req_body_md:
                            md += "#### 请求体\n\n"
                            md += req_body_md + "\n\n"

                        if req_example:
                            md += "#### 请求示例\n\n"
                            md += f"```json\n{req_example}\n```\n\n"

                        if resp_md:
                            md += "#### 响应参数\n\n"
                            md += resp_md + "\n\n"

                        if resp_example:
                            md += "#### 响应示例\n\n"
                            md += f"```json\n{resp_example}\n```\n"

                        # 生成英文文件名，包含HTTP方法
                        if api_url:
                            # 将URL转换为安全的文件名
                            safe_name = api_url.strip().replace("/", "_").replace(":", "_").strip("_")
                            safe_name = re.sub(r'[\\/*?:"<>|]', "_", safe_name)

                            # 添加HTTP方法到文件名中，避免不同方法的同一URL覆盖
                            if method:
                                safe_name = f"{method.lower()}_{safe_name}"

                            if not safe_name:
                                safe_name = f"api_{idx+1}"
                        else:
                            safe_name = f"api_{idx+1}"

                        filename = os.path.join(self.output_dir, f"{safe_name}.md")
                        logger.info(f"生成文件名: {filename}")
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
