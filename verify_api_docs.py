import os
import re
import glob
import logging
import argparse
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_info_from_html(html_file):
    """
    从HTML文件中提取API信息

    Returns:
        dict: 包含API信息的字典
    """
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取API方法和路径
        method_elem = soup.select_one("div.http-method")
        path_elem = soup.select_one("div.path")

        if not method_elem or not path_elem:
            logger.warning(f"{html_file} 未找到API方法或路径")
            return None

        method = method_elem.text.strip()
        path = path_elem.text.strip()

        # 提取API描述
        desc_elem = soup.select_one("h2.title")
        description = desc_elem.text.strip() if desc_elem else ""

        # 提取所有h3标题和它们后面的内容
        sections = {}
        h3_elems = soup.select("h3.title")

        for i, h3 in enumerate(h3_elems):
            title = h3.text.strip()
            content = []

            # 获取当前h3和下一个h3之间的所有内容
            next_elem = h3.next_sibling
            while next_elem and (i == len(h3_elems) - 1 or next_elem != h3_elems[i+1]):
                if next_elem.name == 'table':
                    # 如果是表格，提取表格内容
                    rows = next_elem.select('tr')
                    table_content = []
                    for row in rows:
                        cols = row.select('td, th')
                        if cols:
                            table_content.append([col.text.strip() for col in cols])
                    content.append(('table', table_content))
                elif next_elem.name == 'pre':
                    # 如果是代码块，提取代码内容
                    content.append(('pre', next_elem.text.strip()))
                elif next_elem.name == 'code' and next_elem.parent and next_elem.parent.name == 'pre':
                    # 如果是嵌套在pre中的code元素
                    content.append(('pre', next_elem.text.strip()))

                next_elem = next_elem.next_sibling
                if not next_elem:
                    break

            # 如果没有找到内容，尝试使用XPath直接定位
            if not content and ('请求示例' in title or '响应示例' in title):
                # 尝试找到该标题后面的pre元素
                pre_elems = soup.select(f"h3:contains('{title}') ~ pre")
                if pre_elems:
                    content.append(('pre', pre_elems[0].text.strip()))

            sections[title] = content

        return {
            'method': method,
            'path': path,
            'description': description,
            'sections': sections
        }
    except Exception as e:
        logger.error(f"解析HTML文件 {html_file} 时出错: {str(e)}")
        return None

def extract_info_from_markdown(md_file):
    """
    从Markdown文件中提取API信息

    Returns:
        dict: 包含API信息的字典
    """
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 提取API方法和路径
        m = re.search(r'###\s+(\w+)\s+([^\n]+)', md_content)
        if not m:
            logger.warning(f"{md_file} 未找到API方法或路径")
            return None

        method = m.group(1)
        path = m.group(2).strip()

        # 提取API描述
        desc_match = re.search(r'###\s+\w+\s+[^\n]+\n+([^\n#]+)', md_content)
        description = desc_match.group(1).strip() if desc_match else ""

        # 提取所有section
        sections = {}
        section_matches = re.finditer(r'####\s+([^\n]+)\s*\n([\s\S]+?)(?=\n####|\Z)', md_content)

        for match in section_matches:
            title = match.group(1).strip()
            content = match.group(2).strip()

            # 检查内容类型
            if '```' in content:
                # 代码块
                code_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', content)
                if code_match:
                    sections[title] = [('pre', code_match.group(1).strip())]
            elif '|' in content:
                # 表格
                lines = [line.strip() for line in content.splitlines() if '|' in line]
                table_content = []
                for line in lines:
                    if '---' in line:  # 跳过分隔行
                        continue
                    cols = [col.strip() for col in line.split('|')[1:-1]]
                    if cols:
                        table_content.append(cols)
                sections[title] = [('table', table_content)]

        return {
            'method': method,
            'path': path,
            'description': description,
            'sections': sections
        }
    except Exception as e:
        logger.error(f"解析Markdown文件 {md_file} 时出错: {str(e)}")
        return None

def compare_api_info(html_info, md_info):
    """
    比较HTML和Markdown中提取的API信息

    Returns:
        dict: 包含比较结果的字典
    """
    if not html_info or not md_info:
        return {'match': False, 'reason': '无法提取信息'}

    result = {
        'match': True,
        'differences': []
    }

    # 比较方法
    if html_info['method'].lower() != md_info['method'].lower():
        result['match'] = False
        result['differences'].append(f"方法不匹配: HTML={html_info['method']}, MD={md_info['method']}")

    # 比较路径
    # 将Markdown中的路径转换为与HTML相同的格式（例如，将 /users/{id} 转换为 /users/:id）
    md_path = re.sub(r'{([^{}]+)}', r':\1', md_info['path'])
    if html_info['path'] != md_path:
        result['match'] = False
        result['differences'].append(f"路径不匹配: HTML={html_info['path']}, MD={md_path}")

    # 比较描述（允许一些差异）
    if not similar_text(html_info['description'], md_info['description']):
        result['match'] = False
        result['differences'].append(f"描述不匹配: HTML={html_info['description']}, MD={md_info['description']}")

    # 比较各个部分
    html_sections = set(html_info['sections'].keys())
    md_sections = set(md_info['sections'].keys())

    # 检查缺失的部分
    missing_in_md = html_sections - md_sections
    if missing_in_md:
        result['match'] = False
        result['differences'].append(f"Markdown中缺少以下部分: {', '.join(missing_in_md)}")

    # 比较共有部分的内容
    for section in html_sections & md_sections:
        html_content = html_info['sections'][section]
        md_content = md_info['sections'][section]

        # 简单比较内容类型和数量
        if len(html_content) != len(md_content):
            result['match'] = False
            result['differences'].append(f"部分 '{section}' 的内容数量不匹配")
            continue

        # 比较每个内容项
        for i, (html_type, html_data) in enumerate(html_content):
            if i >= len(md_content):
                break

            md_type, md_data = md_content[i]

            if html_type != md_type:
                result['match'] = False
                result['differences'].append(f"部分 '{section}' 的内容类型不匹配: HTML={html_type}, MD={md_type}")
                continue

            # 根据类型比较内容
            if html_type == 'pre':
                # 对于代码块，比较文本内容（允许一些差异）
                if not similar_text(html_data, md_data):
                    result['match'] = False
                    result['differences'].append(f"部分 '{section}' 的代码块内容不匹配")
            elif html_type == 'table':
                # 对于表格，比较行数和列数
                if len(html_data) != len(md_data):
                    result['match'] = False
                    result['differences'].append(f"部分 '{section}' 的表格行数不匹配: HTML={len(html_data)}, MD={len(md_data)}")
                    continue

                # 比较每一行
                for j, html_row in enumerate(html_data):
                    if j >= len(md_data):
                        break

                    md_row = md_data[j]

                    if len(html_row) != len(md_row):
                        result['match'] = False
                        result['differences'].append(f"部分 '{section}' 的表格第{j+1}行列数不匹配: HTML={len(html_row)}, MD={len(md_row)}")
                        continue

    return result

def similar_text(a, b, threshold=0.8):
    """
    检查两个文本是否相似

    Args:
        a: 第一个文本
        b: 第二个文本
        threshold: 相似度阈值

    Returns:
        bool: 如果相似度大于阈值，则返回True
    """
    if not a and not b:
        return True
    if not a or not b:
        return False

    return SequenceMatcher(None, a, b).ratio() >= threshold

def find_matching_md_file(html_file, md_files):
    """
    根据HTML文件找到对应的Markdown文件

    Args:
        html_file: HTML文件路径
        md_files: Markdown文件列表

    Returns:
        str: 匹配的Markdown文件路径，如果没有找到则返回None
    """
    # 从HTML文件中提取API信息
    html_info = extract_info_from_html(html_file)
    if not html_info:
        return None

    # 构造可能的文件名模式
    method = html_info['method'].lower()
    path = html_info['path'].strip('/')
    path = re.sub(r':([^/]+)', r'_\1', path)  # 将 :id 转换为 _id
    path = path.replace('/', '_')

    possible_patterns = [
        f"{method}_{path}.md",
        f"{method}{path}.md"
    ]

    # 尝试直接匹配文件名
    for pattern in possible_patterns:
        for md_file in md_files:
            if os.path.basename(md_file).lower() == pattern.lower():
                return md_file

    # 如果没有直接匹配，则尝试提取每个Markdown文件的信息进行比较
    for md_file in md_files:
        md_info = extract_info_from_markdown(md_file)
        if not md_info:
            continue

        if md_info['method'].lower() == method.lower():
            # 将Markdown中的路径转换为与HTML相同的格式
            md_path = re.sub(r'{([^{}]+)}', r':\1', md_info['path'])
            if md_path == html_info['path']:
                return md_file

    return None

def verify_api_docs(html_dir, md_dir, report_file=None):
    """
    验证API文档的一致性

    Args:
        html_dir: HTML文件目录
        md_dir: Markdown文件目录
        report_file: 报告文件路径

    Returns:
        dict: 包含验证结果的字典
    """
    # 获取所有HTML和Markdown文件
    html_files = glob.glob(os.path.join(html_dir, '*.html'))
    md_files = glob.glob(os.path.join(md_dir, '*.md'))

    # 过滤掉info.md
    md_files = [f for f in md_files if os.path.basename(f) != 'info.md']

    logger.info(f"发现 {len(html_files)} 个HTML文件和 {len(md_files)} 个Markdown文件")

    results = []

    # 对每个HTML文件，找到对应的Markdown文件并比较
    for html_file in html_files:
        md_file = find_matching_md_file(html_file, md_files)

        if not md_file:
            logger.warning(f"未找到与 {html_file} 匹配的Markdown文件")
            results.append({
                'html_file': html_file,
                'md_file': None,
                'match': False,
                'reason': '未找到匹配的Markdown文件'
            })
            continue

        html_info = extract_info_from_html(html_file)
        md_info = extract_info_from_markdown(md_file)

        comparison = compare_api_info(html_info, md_info)

        results.append({
            'html_file': html_file,
            'md_file': md_file,
            'match': comparison['match'],
            'differences': comparison.get('differences', [])
        })

        if comparison['match']:
            logger.info(f"{os.path.basename(html_file)} 与 {os.path.basename(md_file)} 匹配")
        else:
            logger.warning(f"{os.path.basename(html_file)} 与 {os.path.basename(md_file)} 不匹配: {', '.join(comparison.get('differences', []))}")

    # 生成报告
    if report_file:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# API文档验证报告\n\n")

            # 总体统计
            match_count = sum(1 for r in results if r['match'])
            f.write(f"## 总体统计\n\n")
            f.write(f"- 总计: {len(results)} 个API\n")
            f.write(f"- 匹配: {match_count} 个API\n")
            f.write(f"- 不匹配: {len(results) - match_count} 个API\n\n")

            # 不匹配的详细信息
            if len(results) - match_count > 0:
                f.write(f"## 不匹配的API\n\n")
                for r in results:
                    if not r['match']:
                        f.write(f"### {os.path.basename(r['html_file'])}\n\n")
                        f.write(f"- Markdown文件: {os.path.basename(r['md_file']) if r['md_file'] else '未找到'}\n")
                        f.write(f"- 差异:\n")
                        for diff in r.get('differences', []):
                            f.write(f"  - {diff}\n")
                        f.write("\n")

        logger.info(f"验证报告已保存到 {report_file}")

    return {
        'total': len(results),
        'match': sum(1 for r in results if r['match']),
        'mismatch': len(results) - sum(1 for r in results if r['match']),
        'results': results
    }

def main():
    parser = argparse.ArgumentParser(description='验证API文档的一致性')
    parser.add_argument('--html-dir', default='api_doc/html', help='HTML文件目录')
    parser.add_argument('--md-dir', default='api_doc', help='Markdown文件目录')
    parser.add_argument('--report', default='api_doc/verification_report.md', help='报告文件路径')

    args = parser.parse_args()

    verify_api_docs(args.html_dir, args.md_dir, args.report)

if __name__ == '__main__':
    main()
