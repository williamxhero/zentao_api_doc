# 禅道API爬虫与OpenAPI生成工具

## 项目简介

本项目基于Python和Selenium，自动登录禅道系统，批量爬取REST API文档，  
生成结构化的Markdown接口文档，并支持一键转换为OpenAPI 3.0规范的yaml文件，  
方便导入Swagger UI、Apifox等API管理工具。

---
** 放弃了**
** 禅道文档错误非常多，无法自动爬取，所以放弃了。**

比如：

* http://localhost/zentao/dev-api-restapi-57.html
  * 没有写“请求相应”，只有“响应示例”
* /zentao/dev-api-restapi-14.html /zentao/dev-api-restapi-69.html ...
  * 请求响应 和 响应示例 严重不符
* /zentao/dev-api-restapi-4.html
  * 请求体 code 类型 和 请求响应 code 类型不一致
  
懒得再写了
