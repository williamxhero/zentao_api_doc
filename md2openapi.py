import os
import re
import yaml
import glob
import json
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_markdown_file(filepath):
    """
    解析单个Markdown文件，提取接口信息
    Returns:
        dict: {'path': str, 'method': str, 'description': str, 'parameters': list, 'request_body': dict, 'responses': dict, 'response_schema': dict}
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

    # 将路径中的冒号格式转换为OpenAPI的花括号格式
    # 例如，将 /users/:id 转换为 /users/{id}
    path = re.sub(r':([^/]+)', r'{\1}', path)
    # 处理可能出现的多余冒号，如 /users/{id}:
    path = path.rstrip(':')

    # 描述
    desc_match = re.search(r'###\s+\w+\s+[^\n]+\n+([^\n#]+)', content)
    description = desc_match.group(1).strip() if desc_match else ""

    # 提取路径参数
    req_params = []
    path_params = re.findall(r'{([^{}]+)}', path)
    for param_name in path_params:
        req_params.append({
            'name': param_name,
            'in': 'path',
            'required': True,  # 路径参数始终是必填的
            'description': f'路径参数 {param_name}',
            'schema': {
                'type': 'string'
            }
        })

    # 请求参数表格
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
                param_name = param.get('名称', '')
                param_type = param.get('类型', '').lower()
                param_required = param.get('必填', '') == '是'
                param_desc = param.get('描述', '')

                # 确定参数位置
                # 默认情况下，请求头中的参数都视为header参数
                param_in = 'header'

                # 确定参数位置
                # 默认全部请求头字段都作为header参数

                # 确定参数类型和格式
                schema = determine_schema_type(param_type, param_desc)

                if param_in != 'body':
                    req_params.append({
                        'name': param_name,
                        'in': param_in,
                        'required': param_required,
                        'description': param_desc,
                        'schema': schema
                    })

    # 解析响应参数表格，构建响应模型
    response_schema = parse_response_schema(content)

    # 不再构建请求体模型，所有请求头字段都作为header参数
    request_body = None

    # 构建响应对象
    responses = {
        '200': {
            'description': '成功响应',
            'content': {
                'application/json': {
                    'schema': response_schema or {'type': 'object'},
                }
            }
        },
        '400': {
            'description': '请求错误',
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': '#/components/schemas/Error'
                    }
                }
            }
        },
        '401': {
            'description': '未授权',
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': '#/components/schemas/Error'
                    }
                }
            }
        },
        '500': {
            'description': '服务器错误',
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': '#/components/schemas/Error'
                    }
                }
            }
        }
    }

    # # 添加示例（如果有）
    # if example_json:
    #     responses['200']['content']['application/json']['example'] = example_json

    # 如果没有Token参数，自动添加一个Token header参数
    has_token = any(p.get('name', '').lower() == 'token' and p.get('in') == 'header' for p in req_params)
    if not has_token:
        req_params.append({
            'name': 'Token',
            'in': 'header',
            'required': False,
            'description': '认证Token',
            'schema': {'type': 'string'}
        })

    return {
        'path': path,
        'method': method,
        'description': description,
        'parameters': req_params,
        'request_body': request_body,
        'responses': responses,
        'response_schema': response_schema
    }


def determine_schema_type(param_type, param_desc, param_name=''):
    """
    根据参数类型和描述确定OpenAPI schema类型
    """
    param_type = param_type.lower()
    schema = {'type': 'string'}

    # 基本类型映射
    type_mapping = {
        'string': 'string',
        'str': 'string',
        'int': 'integer',
        'integer': 'integer',
        'float': 'number',
        'double': 'number',
        'number': 'number',
        'bool': 'boolean',
        'boolean': 'boolean',
        'array': 'array',
        'object': 'object',
        'date': 'string',
        'datetime': 'string',
        'time': 'string',
        'user': 'object',  # 特殊类型，处理为dict/字典
    }

    # 不再对 'desc' 字段进行特殊处理
    # if param_name.lower() == 'desc':
    #     return {'type': 'string'}

    # 设置基本类型
    if param_type in type_mapping:
        schema['type'] = type_mapping[param_type]

    # 特殊格式处理
    if param_type == 'date':
        schema['format'] = 'date'
    elif param_type == 'datetime':
        schema['format'] = 'date-time'
    elif param_type == 'time':
        schema['format'] = 'time'
    elif param_type == 'email':
        schema['format'] = 'email'
    elif param_type == 'uri' or param_type == 'url':
        schema['format'] = 'uri'

    # 从描述中提取枚举值
    enum_match = re.search(r'\((.+?)\)', param_desc)
    if enum_match:
        enum_str = enum_match.group(1)
        # 检查是否包含枚举格式的描述 (value1 desc1 | value2 desc2)
        enum_values = [v.split(' ')[0] for v in enum_str.split('|')]
        if len(enum_values) > 1:
            schema['enum'] = enum_values
            # 提取枚举描述作为x-enum-descriptions
            enum_descriptions = [' '.join(v.split(' ')[1:]).strip() for v in enum_str.split('|')]
            if any(enum_descriptions):
                schema['x-enum-descriptions'] = enum_descriptions

    return schema


def parse_response_schema(content):
    """
    解析响应参数表格，构建响应模型
    """
    resp_table_match = re.search(r'####\s*响应参数\s*\n([\s\S]+?)\n\n', content)
    if not resp_table_match:
        return None

    # 提取所有表格和它们的标题
    tables = []
    table_pattern = r'(\*\*([^*]+)\*\*\s*\n\s*\|[^\n]+\|\s*\n\s*\|[^\n]+\|\s*\n((?:\s*\|[^\n]+\|\s*\n)*))|(?:####\s*响应参数\s*\n\s*\|[^\n]+\|\s*\n\s*\|[^\n]+\|\s*\n((?:\s*\|[^\n]+\|\s*\n)*))'
    for m in re.finditer(table_pattern, content):
        if m.group(4):  # 主表格
            tables.append({
                'title': 'root',
                'content': m.group(4)
            })
        else:  # 子表格
            tables.append({
                'title': m.group(2),
                'content': m.group(3)
            })

    if not tables:
        return None

    # 解析表格内容为属性
    parsed_tables = {}
    for table in tables:
        properties = []
        lines = [line.strip() for line in table['content'].splitlines() if '|' in line]
        for line in lines:
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) < 3:
                continue

            # 假设列顺序为：名称、类型、必填、描述
            if len(cols) >= 4:
                prop = {
                    'name': cols[0],
                    'type': cols[1].lower(),
                    'required': cols[2] == '是',
                    'description': cols[3] if len(cols) > 3 else ''
                }
                properties.append(prop)

        parsed_tables[table['title']] = properties

    # 构建schema
    root_schema = {
        'type': 'object',
        'properties': {},
        'required': []
    }

    # 处理根表格
    if 'root' in parsed_tables:
        for prop in parsed_tables['root']:
            prop_schema = determine_schema_type(prop['type'], prop['description'], prop['name'])
            root_schema['properties'][prop['name']] = prop_schema
            if prop['required']:
                root_schema['required'].append(prop['name'])

    # 处理子表格（嵌套对象和数组）
    for title, properties in parsed_tables.items():
        if title == 'root':
            continue

        # 解析标题，确定父属性和类型
        title_parts = title.split(' ')
        if len(title_parts) < 2:
            continue

        parent_name = title_parts[0]
        obj_type = ' '.join(title_parts[1:]).lower()

        # 创建子schema
        child_schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }

        for prop in properties:
            prop_schema = determine_schema_type(prop['type'], prop['description'], prop['name'])
            child_schema['properties'][prop['name']] = prop_schema
            if prop['required']:
                child_schema['required'].append(prop['name'])

        # 如果没有必填字段，删除required数组
        if not child_schema['required']:
            del child_schema['required']

        # 将子schema添加到父属性
        if parent_name in root_schema['properties']:
            if '数组' in obj_type or 'array' in obj_type:
                root_schema['properties'][parent_name]['items'] = child_schema
            else:
                root_schema['properties'][parent_name] = child_schema

    # 如果没有必填字段，删除required数组
    if not root_schema['required']:
        del root_schema['required']

    return root_schema




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


def generate_schema_name(path, method, is_response=True):
    """
    生成schema名称，使用 operationId + Response 的格式
    例如：
    - GET /products -> getProductsResponse 或 listProductsResponse
    - GET /products/{id} -> getProductsIdResponse
    """
    # 生成 operationId
    operation_id = generate_operation_id(path, method)

    # 根据是响应还是请求添加相应的后缀
    if is_response:
        return operation_id + 'Response'
    else:
        return operation_id + 'Request'


def extract_schemas_from_apis(api_list):
    """
    从API列表中提取所有schema定义
    """
    schemas = {
        # 添加通用错误响应模型
        'Error': {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'integer',
                    'description': '错误代码'
                },
                'message': {
                    'type': 'string',
                    'description': '错误信息'
                }
            },
            'required': ['code', 'message']
        }
    }

    # 收集所有响应和请求模型
    for api in api_list:
        if not api:
            continue

        path = api['path']
        method = api['method']

        # 处理响应模型
        if api.get('response_schema'):
            schema_name = generate_schema_name(path, method, is_response=True)
            schemas[schema_name] = api['response_schema']

            # 更新API响应引用
            if '200' in api['responses'] and 'content' in api['responses']['200']:
                api['responses']['200']['content']['application/json']['schema'] = {
                    '$ref': f'#/components/schemas/{schema_name}'
                }

        # 处理请求模型
        if api.get('request_body') and 'content' in api['request_body']:
            schema_name = generate_schema_name(path, method, is_response=False)
            request_schema = api['request_body']['content']['application/json']['schema']
            schemas[schema_name] = request_schema

            # 更新API请求体引用
            api['request_body']['content']['application/json']['schema'] = {
                '$ref': f'#/components/schemas/{schema_name}'
            }

    return schemas


def generate_operation_id(path, method):
    """
    生成唯一且语义清晰的 operationId，避免重复
    新格式：{method}{Resource}Id{SubResource}
    例如：/executions/{id}/builds -> getExecutionsIdBuilds
    例如：/bugs/{id} -> deleteBugsId
    """
    method_lower = method.lower()

    # 分割路径
    parts = [p for p in path.strip('/').split('/') if p]

    # 处理路径部分
    processed_parts = []
    for part in parts:
        if part.startswith('{') and part.endswith('}'):
            # 将路径参数替换为 'Id'
            processed_parts.append('Id')
        else:
            # 将资源名称首字母大写
            processed_parts.append(part[0].upper() + part[1:])

    # 使用原始HTTP方法名称作为前缀
    method_prefix = method_lower

    # 组合 operationId
    operation_id = method_prefix + ''.join(processed_parts)

    return operation_id


def build_openapi_spec(api_list):
    """
    根据接口信息构建OpenAPI字典
    """
    info_md_path = os.path.join("api_doc", "info.md")
    info_data = parse_info_md(info_md_path)

    # 提取所有schema定义
    schemas = extract_schemas_from_apis(api_list)

    # 构建基本OpenAPI结构
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
        'paths': {},
        'components': {
            'schemas': schemas,
            'securitySchemes': {
                'TokenAuth': {
                    'type': 'apiKey',
                    'in': 'query',
                    'name': 'Token',
                    'description': '禅道API认证Token'
                }
            }
        },
        'security': [
            {'TokenAuth': []}
        ]
    }

    # 收集所有标签
    tags = set()
    for api in api_list:
        if not api:
            continue
        path = api['path']
        first_segment = path.strip('/').split('/')[0] if '/' in path.strip('/') else path.strip('/')
        if first_segment:
            tags.add(first_segment)

    # 添加标签定义
    openapi['tags'] = [{'name': tag, 'description': f'{tag} 相关接口'} for tag in sorted(tags)]

    # 构建路径
    for api in api_list:
        if not api:
            continue

        path = api['path']
        method = api['method']

        if path not in openapi['paths']:
            openapi['paths'][path] = {}

        # 确定标签
        first_segment = path.strip('/').split('/')[0] if '/' in path.strip('/') else path.strip('/')
        api_tags = [first_segment] if first_segment else []

        # 生成operationId
        operation_id = generate_operation_id(path, method)

        # 构建操作对象
        operation = {
            'tags': api_tags,
            'operationId': operation_id,
            'summary': api['description'],
            'parameters': api['parameters'],
            'responses': api['responses'],
            'security': [{'TokenAuth': []}]
        }

        # 添加请求体（如果有）
        if api.get('request_body'):
            operation['requestBody'] = api['request_body']

        openapi['paths'][path][method] = operation

    return openapi


def main():
    api_dir = 'api_doc'
    md_files = glob.glob(os.path.join(api_dir, '*.md'))
    logger.info(f"发现 {len(md_files)} 个Markdown文件")

    # 过滤掉info.md
    md_files = [f for f in md_files if os.path.basename(f) != 'info.md']
    logger.info(f"处理 {len(md_files)} 个API文档文件")

    api_list = []
    for md_file in md_files:
        api = parse_markdown_file(md_file)
        if api:
            api_list.append(api)

    logger.info(f"成功解析 {len(api_list)} 个API")

    openapi_spec = build_openapi_spec(api_list)

    # 只生成一个文件
    output_file = os.path.join('api_doc', 'zentao_api_docs.yaml')
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(openapi_spec, f, allow_unicode=True, sort_keys=False)
    logger.info(f"已生成OpenAPI文件: {output_file}")


if __name__ == '__main__':
    main()
