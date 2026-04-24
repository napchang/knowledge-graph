#!/usr/bin/env python3
"""
自动更新知识库脚本
从data/aggregated/读取RSS数据，分类后更新geo-knowledge-base/目录
"""

import json
import os
import re
import glob
from datetime import datetime

# 自动检测基础目录
if os.path.exists("/github/workspace"):
    BASE_DIR = "/github/workspace"
elif os.path.exists("geo-knowledge-base"):
    BASE_DIR = "."
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Support rss-data/ subdirectory for GitHub Actions workflow
if os.path.exists(os.path.join(BASE_DIR, "rss-data", "data", "aggregated")):
    DATA_DIR = os.path.join(BASE_DIR, "rss-data", "data", "aggregated")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data", "aggregated")
KB_DIR = os.path.join(BASE_DIR, "geo-knowledge-base")

def classify_category(article):
    """判断文章属于哪个Category"""
    title = article.get("title", "").lower()
    summary = article.get("cn_summary", "").lower()
    content = article.get("content", "").lower()
    source = article.get("source", "").lower()
    combined = title + " " + summary + " " + content + " " + source
    
    # AI搜索关键词
    search_keywords = ["geo", "aeo", "seo", "search engine", "ranking", "perplexity", "sge", "google search", "bing", "search optimization"]
    if any(k in combined for k in search_keywords):
        return "ai-search"
    
    # Agentic B2B关键词
    b2b_keywords = ["agentic", "b2b", "marketing", "sales", "crm", "customer experience", "cx", "automation", "ap automation", "workflow"]
    if any(k in combined for k in b2b_keywords):
        return "agentic-b2b"
    
    # 学术研究关键词
    academic_keywords = ["paper", "research", "algorithm", "model", "study", "mit ", "stanford", "university", "conference"]
    if any(k in combined for k in academic_keywords):
        return "academic"
    
    # 默认AI行业动态
    return "ai-industry"

def get_topic_tags(article, category):
    """获取Topic标签"""
    title = article.get("title", "").lower()
    summary = article.get("cn_summary", "").lower()
    combined = title + " " + summary
    tags = []
    
    if category == "ai-search":
        if "geo" in combined: tags.append("GEO")
        if "aeo" in combined: tags.append("AEO")
        if "seo" in combined: tags.append("SEO")
        if "rank" in combined or "metric" in combined or "measure" in combined: tags.append("度量指标")
        if "platform" in combined or "chatgpt" in combined or "perplexity" in combined: tags.append("平台特定")
        if "algorithm" in combined or "search engine" in combined: tags.append("搜索技术")
        if not tags: tags.append("搜索技术")
    
    elif category == "agentic-b2b":
        if "marketing" in combined: tags.append("marketing")
        if "sales" in combined: tags.append("sales")
        if "strategy" in combined or "cmo" in combined or "plan" in combined: tags.append("strategy")
        if "customer" in combined or "cx" in combined or "experience" in combined: tags.append("CX")
        if "automation" in combined or "agentic" in combined or "workflow" in combined: tags.append("automation")
        if not tags: tags.append("strategy")
    
    elif category == "academic":
        if "algorithm" in combined: tags.append("算法")
        if "model" in combined or "architecture" in combined: tags.append("模型架构")
        if "nlp" in combined or "language" in combined: tags.append("NLP")
        if "vision" in combined or "image" in combined: tags.append("CV")
        if "retrieval" in combined or "search" in combined: tags.append("信息检索")
        if not tags: tags.append("研究")
    
    else:  # ai-industry
        if "builder" in combined or "developer" in combined: tags.append("builder动态")
        if "launch" in combined or "release" in combined or "product" in combined: tags.append("产品发布")
        if "fund" in combined or "invest" in combined or "million" in combined: tags.append("融资")
        if "openai" in combined or "google" in combined or "meta" in combined: tags.append("大厂战略")
        if not tags: tags.append("行业趋势")
    
    return tags

def update_kb():
    """主函数：更新知识库"""
    print("=== 开始更新知识库 ===")
    
    # 收集所有文章
    articles_by_cat = {
        "ai-industry": [],
        "ai-search": [],
        "agentic-b2b": [],
        "academic": []
    }
    
    # 遍历所有日期
    dates = sorted([d for d in os.listdir(DATA_DIR) if d.startswith("2026")])
    
    for date_dir in dates:
        # 读取所有 tier 文件
        tier_files = [
            "tier1_builders.json",
            "tier2_geo_b2b.json", 
            "tier3_ai_news.json",
            "aggregated.json"
        ]
        seen_links = set()
        for tier_file in tier_files:
            filepath = os.path.join(DATA_DIR, date_dir, tier_file)
            if not os.path.exists(filepath):
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            articles_list = data.get("articles", [])
            if not articles_list and isinstance(data, list):
                articles_list = data
            for article in articles_list:
                link = article.get("link", "")
                if link in seen_links:
                    continue
                seen_links.add(link)
                article["_date"] = date_dir
                cat = classify_category(article)
                article["_category"] = cat
                article["_tags"] = get_topic_tags(article, cat)
                articles_by_cat[cat].append(article)
    
    # 写入文件
    for cat, articles in articles_by_cat.items():
        if not articles:
            continue
        
        cat_dir = os.path.join(KB_DIR, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        # 按来源分组
        by_source = {}
        other_articles = []
        
        for article in articles:
            source = article.get("source", "Unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(article)
        
        # 写单独来源文件（≥3篇）
        for source, source_articles in by_source.items():
            if len(source_articles) >= 3:
                filename = source.lower().replace(" ", "-").replace("/", "-") + ".md"
                filepath = os.path.join(cat_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {source} 文章\n\n")
                    f.write(f"> Category: {cat.replace('-', ' ').title()} | 来源: {source}\n\n---\n\n")
                    
                    for article in source_articles:
                        title = article.get("cn_title", article.get("title", ""))
                        link = article.get("link", "")
                        date = article.get("published", "")[:10]
                        summary = article.get("cn_summary", article.get("content", "")[:150])
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### {title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        f.write(f"- **摘要**: {summary}\n\n")
            else:
                other_articles.extend(source_articles)
        
        # 写零散文章（按日期）
        if other_articles:
            by_date = {}
            for article in other_articles:
                d = article["_date"]
                if d not in by_date:
                    by_date[d] = []
                by_date[d].append(article)
            
            for date, date_articles in sorted(by_date.items()):
                filepath = os.path.join(cat_dir, f"{date}.md")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {date} 文章汇总\n\n")
                    f.write(f"> Category: {cat.replace('-', ' ').title()}\n\n---\n\n")
                    
                    for article in date_articles:
                        title = article.get("cn_title", article.get("title", ""))
                        link = article.get("link", "")
                        pub_date = article.get("published", "")[:10]
                        source = article.get("source", "Unknown")
                        summary = article.get("cn_summary", article.get("content", "")[:150])
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### [{source}] {title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {pub_date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        f.write(f"- **摘要**: {summary}\n\n")
    
    total = sum(len(v) for v in articles_by_cat.values())
    print(f"\n[OK] 知识库更新完成")
    print(f"   总计文章: {total}")
    for cat, articles in articles_by_cat.items():
        print(f"   {cat}: {len(articles)} 篇")

if __name__ == "__main__":
    update_kb()
