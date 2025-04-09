from zentao_crawler.factory import WebCrawlerFactory
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # 禅道地址和凭据
    login_url = "http://192.168.0.72/zentao/user-login.html"
    api_doc_url = "http://192.168.0.72/zentao/dev-api-restapi.html"
    username = "the_account"
    password = "the_password"

    # 创建爬虫实例
    crawler = WebCrawlerFactory.create_crawler("21.6", login_url, api_doc_url, username, password)

    try:
        # 初始化浏览器
        crawler.setup_driver()

        # 显式登录
        if not crawler.login():
            logger.error("登录失败，程序退出")
            return

        # 执行爬取
        crawler.run_crawl()
        logger.info("爬取完成")

    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
    finally:
        # 关闭浏览器
        crawler.close()


if __name__ == "__main__":
    main()
