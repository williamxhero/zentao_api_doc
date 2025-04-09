import os
import re
import yaml
import glob
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_markdown_file(filepath):
    """
    解析单个Markdown文件，提取接口信息
    Returns:
        dict: {'path': str, 'method': str, 'description': str, 'parameters': list, 'responses': dict, 'response_example': str}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配接口标题
    m = re.search(r'###\s+(\w+)\s+([^\n]+)', content)
    if not m:
        logger.warning(f"{filepath} 未找到接口标题")
        return None
    method = m.group(1).lower()
    path = m.group(2).strip()

    # 描述
    desc_match = re.search(r'###\s+\w+\s+[^\n]+\n+([^\n#]+)', content)
    description = desc_match.group(1).strip() if desc_match else ""

    # 请求参数表格
    req_params = []
    req_table_match = re.search(r'####\s*请求头\s*\n([\s\S]+?)\n\n', content)
    if req_table_match:
        table = req_table_match.group(1)
        lines = [line.strip() for line in table.splitlines() if '|' in line]
        if len(lines) >= 2:
            headers = [h.strip() for h in lines[0].split('|')[1:-1]]
            for line in lines[2:]:
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) != len(headers):
                    continue
                param = dict(zip(headers, cols))
                req_params.append({
                    'name': param.get('名称', ''),
                    'in': 'query',
                    'required': param.get('必填', '') == '是',
                    'description': param.get('描述', ''),
                    'schema': {'type': 'string'}  # 默认string，未来可改进
                })

    # 响应参数表格（暂不细分，未来可扩展）
    responses = {
        '200': {
            'description': '成功响应',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object'
                    }
                }
            }
        }
    }

    # 响应示例
    resp_example_match = re.search(r'####\s*响应示例\s*\n```json\n([\s\S]+?)\n```', content)
    if resp_example_match:
        example_json = resp_example_match.group(1).strip()
        responses['200']['content']['application/json']['example'] = example_json

    return {
        'path': path,
        'method': method,
        'description': description,
        'parameters': req_params,
        'responses': responses
    }


def parse_info_md(info_path):
    """
    解析info.md，返回字典
    """
    info = {
        "version": "",
        "time": "",
        "url": "",
        "account": ""
    }
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"禅道版本:\s*(.+)", content)
        if m:
            info["version"] = m.group(1).strip()
        m = re.search(r"爬取时间:\s*(.+)", content)
        if m:
            info["time"] = m.group(1).strip()
        m = re.search(r"API文档URL:\s*(.+)", content)
        if m:
            info["url"] = m.group(1).strip()
        m = re.search(r"账号:\s*(.+)", content)
        if m:
            info["account"] = m.group(1).strip()
    except Exception as e:
        logger.warning(f"读取info.md失败: {str(e)}")
    return info


def build_openapi_spec(api_list):
    """
    根据接口信息构建OpenAPI字典
    """
    info_md_path = os.path.join("api_doc", "info.md")
    info_data = parse_info_md(info_md_path)

    openapi = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Zentao API',
            'version': info_data.get('version', 'unknown'),
            'description': f"禅道版本: {info_data.get('version', '')}\n"
                           f"爬取时间: {info_data.get('time', '')}\n"
                           f"API文档URL: {info_data.get('url', '')}\n"
                           f"账号: {info_data.get('account', '')}"
        },
        'servers': [
            {'url': info_data.get('url', 'http://192.168.0.72/zentao')}
        ],
        'paths': {}
    }

    for api in api_list:
        if not api:
            continue
        path = api['path']
        method = api['method']
        if path not in openapi['paths']:
            openapi['paths'][path] = {}
        openapi['paths'][path][method] = {
            'summary': api['description'],
            'parameters': api['parameters'],
            'responses': api['responses']
        }

    return openapi


def main():
    api_dir = 'api_doc'
    md_files = glob.glob(os.path.join(api_dir, '*.md'))
    logger.info(f"发现 {len(md_files)} 个Markdown文件")

    api_list = []
    for md_file in md_files:
        api = parse_markdown_file(md_file)
        if api:
            api_list.append(api)

    openapi_spec = build_openapi_spec(api_list)

    output_file = os.path.join('api_doc', 'openapi_generated.yaml')
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(openapi_spec, f, allow_unicode=True, sort_keys=False)

    logger.info(f"已生成OpenAPI文件: {output_file}")


if __name__ == '__main__':
    main()
