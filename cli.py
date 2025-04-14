from zentao_crawler.factory import WebCrawlerFactory
import logging
import os
import shutil
import glob

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

    # 清理保存目录
    output_dir = "api_doc"
    html_dir = os.path.join(output_dir, "html")

    # 清理Markdown文件
    if os.path.exists(output_dir):
        md_files = glob.glob(os.path.join(output_dir, "*.md"))
        for file in md_files:
            # 保留README.md、verification_report.md等非爬虫生成的文件
            if os.path.basename(file) not in ["README.md", "verification_report.md"]:
                os.remove(file)
                logger.info(f"删除文件: {file}")
    else:
        os.makedirs(output_dir)
        logger.info(f"创建目录: {output_dir}")

    # 清理HTML目录
    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
        logger.info(f"删除目录: {html_dir}")
    os.makedirs(html_dir)
    logger.info(f"创建目录: {html_dir}")

    # 清理YAML文件
    yaml_files = glob.glob(os.path.join(output_dir, "*.yaml"))
    for file in yaml_files:
        os.remove(file)
        logger.info(f"删除文件: {file}")

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
