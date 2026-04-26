"""
数据完整性守卫模块
防止在不完整数据环境下误运行生成脚本
"""
import os
import sys

# 保守阈值（Actions 环境实际值远高于此）
MIN_EXPECTED_MD_FILES = 80       # geo-knowledge-base/ 最少 markdown 文件数
MIN_EXPECTED_AGGREGATED_DIRS = 15 # RSS 数据聚合目录数
MIN_EXPECTED_ARTICLES = 500       # graph-data.json 最少文章数


def assert_kb_complete(kb_dir, min_files=MIN_EXPECTED_MD_FILES):
    """检查 geo-knowledge-base/ 是否完整"""
    md_files = []
    for root, dirs, files in os.walk(kb_dir):
        for f in files:
            if f.endswith('.md') and f != 'README.md':
                md_files.append(os.path.join(root, f))
    
    if len(md_files) < min_files:
        print(f"[FATAL] geo-knowledge-base/ 只有 {len(md_files)} 个 markdown 文件，")
        print(f"        低于安全阈值 {min_files}。")
        print(f"        本地数据不完整，禁止运行生成脚本。")
        print(f"        数据生成应在 GitHub Actions 中执行。")
        sys.exit(1)
    
    print(f"[GUARD] geo-knowledge-base/ 检查通过: {len(md_files)} 个文件")
    return True


def assert_rss_complete(data_dir, min_dirs=MIN_EXPECTED_AGGREGATED_DIRS):
    """检查 RSS 聚合数据源是否完整"""
    if not os.path.exists(data_dir):
        print(f"[FATAL] RSS 数据源目录不存在: {data_dir}")
        print(f"        禁止运行生成脚本。")
        sys.exit(1)
    
    dirs = [d for d in os.listdir(data_dir) if d.startswith('20') and os.path.isdir(os.path.join(data_dir, d))]
    if len(dirs) < min_dirs:
        print(f"[FATAL] RSS 数据源 {data_dir} 只有 {len(dirs)} 个日期目录，")
        print(f"        低于安全阈值 {min_dirs}。")
        print(f"        本地数据不完整，禁止运行生成脚本。")
        sys.exit(1)
    
    print(f"[GUARD] RSS 数据源检查通过: {len(dirs)} 个日期目录")
    return True


def assert_graph_sanity(graph_data, min_articles=MIN_EXPECTED_ARTICLES):
    """检查生成的图谱数据是否合理"""
    articles = [n for n in graph_data.get('nodes', []) if n.get('type') == 'article']
    today_arts = [a for a in articles if a.get('is_today')]
    
    errors = []
    
    if len(articles) < min_articles:
        errors.append(f"文章总数仅 {len(articles)}，严重低于历史水平（~1000+），可能数据丢失")
    
    if len(today_arts) == 0:
        errors.append("今日文章数量为 0，请检查采集流程")
    elif len(today_arts) < 5:
        errors.append(f"今日文章仅 {len(today_arts)} 条，低于正常水平")
    
    # 重复检测
    from collections import Counter
    links = [a.get('link', '') for a in articles if a.get('link')]
    dup_links = [link for link, count in Counter(links).items() if count > 1]
    if dup_links:
        errors.append(f"发现 {len(dup_links)} 个重复链接的文章节点")
    
    if errors:
        print("[FATAL] 图谱数据异常:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    
    print(f"[GUARD] 图谱数据检查通过: {len(articles)} 篇文章, {len(today_arts)} 条今日")
    return True
