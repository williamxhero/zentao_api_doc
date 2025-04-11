import os
import sys
import logging
from verify_api_docs import verify_api_docs

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # 确保HTML目录存在
    html_dir = 'api_doc/html'
    if not os.path.exists(html_dir):
        logger.error(f"HTML目录 {html_dir} 不存在，请先运行爬虫")
        sys.exit(1)
    
    # 确保Markdown目录存在
    md_dir = 'api_doc'
    if not os.path.exists(md_dir):
        logger.error(f"Markdown目录 {md_dir} 不存在")
        sys.exit(1)
    
    # 运行验证
    report_file = 'api_doc/verification_report.md'
    results = verify_api_docs(html_dir, md_dir, report_file)
    
    # 输出结果
    logger.info(f"验证完成: 总计 {results['total']} 个API，匹配 {results['match']} 个，不匹配 {results['mismatch']} 个")
    logger.info(f"详细报告已保存到 {report_file}")

if __name__ == '__main__':
    main()
