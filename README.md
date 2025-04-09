# 禅道API爬虫与OpenAPI生成工具

## 项目简介

本项目基于Python和Selenium，自动登录禅道系统，批量爬取REST API文档，  
生成结构化的Markdown接口文档，并支持一键转换为OpenAPI 3.0规范的yaml文件，  
方便导入Swagger UI、Apifox等API管理工具。

---

## 主要功能

- 自动登录禅道，支持版本检测
- 批量爬取API接口，生成Markdown文档
- 支持多层嵌套参数的表格格式
- 自动生成`info.md`，记录禅道版本、爬取时间、API地址、账号等信息
- 将所有Markdown批量转换为OpenAPI 3.0规范的yaml文件
- 目录结构清晰，方便维护和扩展

---

## 目录结构

```
.
├── cli.py                  # 命令行入口，运行爬虫
├── md2openapi.py           # Markdown转OpenAPI工具
├── requirements.txt        # 依赖库
├── README.md               # 项目说明
├── api_doc/                # 爬取结果目录
│   ├── *.md               # 各API的Markdown文档
│   ├── info.md            # 爬虫元信息
│   └── zentao_api_docs.yaml.yaml  # 生成的OpenAPI文件
└── zentao_crawler/         # 爬虫核心代码
    ├── __init__.py
    ├── base_crawler.py     # 爬虫基类
    ├── crawler_21_6.py     # 禅道21.6版本实现
    └── factory.py          # 爬虫工厂
```

---

## 使用方法

### 1. 安装依赖

确保已安装Python 3.12+，并安装依赖库：

```
pip install -r requirements.txt
```

### 2. 配置禅道信息

编辑 `cli.py` 中的：

- `login_url`
- `api_doc_url`
- `username`
- `password`

### 3. 运行爬虫，生成Markdown

```
python cli.py
```

- 会自动登录禅道，爬取API文档
- 生成 `api_doc/` 目录，包含所有接口的Markdown文件
- 自动生成 `api_doc/info.md`，记录版本、时间、URL等信息

### 4. 将Markdown转换为OpenAPI

```
python md2openapi.py
```

- 读取 `api_doc/` 下所有Markdown
- 生成 `api_doc/openapi_generated.yaml`
- 可导入Swagger UI、Apifox等工具使用

---

## Markdown接口文档规范

- 标题格式：`### METHOD /path`
- 描述段落
- 请求参数表格
- 响应参数表格，支持多层嵌套
- 嵌套用 "**字段名 对象**" 或 "**字段名 数组元素**" 标题区分
- 响应示例代码块

详见 `zentao_crawler/base_crawler.py` 中 `crawl()` 方法注释。

---

## 未来改进方向

- 支持命令行参数配置
- 自动识别禅道版本
- 支持更多禅道版本
- 更丰富的参数类型识别
- 自动上传OpenAPI到API管理平台

---

## 版权声明

仅供学习与内部使用，禁止用于非法用途。
