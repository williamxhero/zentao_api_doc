"""
爬虫工厂模块，用于创建不同版本的爬虫实例
"""

# 导入特定版本的爬虫实现
from .crawler_21_6 import WebCrawler_21_6

class WebCrawlerFactory:
    """
    爬虫工厂类，用于创建不同版本的爬虫
    """
    
    @staticmethod
    def create_crawler(version, login_url, api_doc_url, username, password, output_dir="api_doc"):
        """
        创建爬虫实例
        
        Args:
            version: 爬虫版本，如 "21.6"
            login_url: 登录页面URL
            api_doc_url: API文档页面URL
            username: 用户名
            password: 密码
            output_dir: 输出目录
            
        Returns:
            BaseWebCrawler: 爬虫实例
        """
        if version == "21.6":
            return WebCrawler_21_6(login_url, api_doc_url, username, password, output_dir)
        else:
            raise ValueError(f"不支持的爬虫版本: {version}")
