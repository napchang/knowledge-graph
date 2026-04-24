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
# Fallback for local recovery: prefer full historical data from sibling repo
_base_abs = os.path.abspath(BASE_DIR)
alt2 = os.path.join(os.path.dirname(_base_abs), "rss_source", "napchang-rss-news-aggregator-0506567", "data", "aggregated")
if os.path.exists(alt2) and len(os.listdir(alt2)) > len(os.listdir(DATA_DIR)):
    DATA_DIR = alt2
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
    """获取层级Topic标签 (Obsidian风格: Parent/Child)"""
    title = article.get("title", "").lower()
    summary = article.get("cn_summary", "").lower()
    content = article.get("content", "").lower()
    combined = title + " " + summary + " " + content
    tags = []
    
    if category == "ai-search":
        if "geo" in combined:
            if "local" in combined or "ecommerce" in combined or "电商" in combined:
                tags.append("GEO/本地电商")
            elif "strategy" in combined or "策略" in combined:
                tags.append("GEO/策略")
            else:
                tags.append("GEO")
        if "aeo" in combined:
            if "platform" in combined or "平台" in combined:
                tags.append("AEO/平台优化")
            else:
                tags.append("AEO")
        if "seo" in combined:
            if "technical" in combined or "技术" in combined or "audit" in combined:
                tags.append("SEO/技术优化")
            elif "content" in combined or "内容" in combined:
                tags.append("SEO/内容策略")
            else:
                tags.append("SEO")
        if "rank" in combined or "metric" in combined or "measure" in combined or "kpi" in combined:
            tags.append("搜索度量")
        if "algorithm" in combined or "search engine" in combined or "检索" in combined:
            tags.append("搜索技术/算法")
        if "platform" in combined or "chatgpt" in combined or "perplexity" in combined or "claude" in combined:
            tags.append("平台/AI搜索产品")
        if not tags:
            tags.append("搜索技术")
    
    elif category == "agentic-b2b":
        if "marketing" in combined:
            if "automation" in combined or "workflow" in combined or "自动" in combined:
                tags.append("Marketing/Automation")
            elif "email" in combined or "邮件" in combined:
                tags.append("Marketing/Email")
            elif "content" in combined or "内容" in combined:
                tags.append("Marketing/Content")
            elif "strategy" in combined or "cmo" in combined or "战略" in combined:
                tags.append("Marketing/Strategy")
            else:
                tags.append("Marketing")
        if "sales" in combined or "crm" in combined:
            if "crm" in combined or "salesforce" in combined or "hubspot" in combined:
                tags.append("Sales/CRM")
            else:
                tags.append("Sales")
        if "customer" in combined or "cx" in combined or "experience" in combined or "体验" in combined:
            tags.append("CX/客户体验")
        if "automation" in combined or "agentic" in combined or "workflow" in combined:
            if "workflow" in combined:
                tags.append("Automation/Workflow")
            else:
                tags.append("Automation")
        if "strategy" in combined or "plan" in combined:
            tags.append("B2B/Strategy")
        if not tags:
            tags.append("B2B/Strategy")
    
    elif category == "academic":
        if "algorithm" in combined or "算法" in combined:
            tags.append("学术/算法")
        if "model" in combined or "architecture" in combined or "架构" in combined:
            if "transformer" in combined or "llm" in combined or "gpt" in combined:
                tags.append("学术/模型架构")
            else:
                tags.append("学术/模型架构")
        if "nlp" in combined or "language" in combined or "语言" in combined:
            tags.append("学术/NLP")
        if "vision" in combined or "image" in combined or "多模态" in combined:
            tags.append("学术/CV")
        if "retrieval" in combined or "search" in combined or "检索" in combined:
            tags.append("学术/信息检索")
        if "paper" in combined or "research" in combined or "论文" in combined or "study" in combined:
            tags.append("学术前沿")
        if not tags:
            tags.append("学术前沿")
    
    else:  # ai-industry
        if "builder" in combined or "developer" in combined or "开发者" in combined:
            tags.append("行业/Builder动态")
        if "launch" in combined or "release" in combined or "product" in combined or "发布" in combined:
            tags.append("行业/产品发布")
        if "fund" in combined or "invest" in combined or "million" in combined or "融资" in combined:
            tags.append("行业/融资")
        if "openai" in combined or "google" in combined or "meta" in combined or "anthropic" in combined or "microsoft" in combined:
            tags.append("行业/大厂战略")
        if "agent" in combined or "智能体" in combined:
            tags.append("行业/Agent生态")
        if not tags:
            tags.append("行业/趋势")
    
    return tags

def load_existing_cn_content():
    """Load existing Chinese content from old markdown files to preserve across updates"""
    existing = {}
    if not os.path.exists(KB_DIR):
        return existing
    for cat in os.listdir(KB_DIR):
        cat_dir = os.path.join(KB_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        for md_file in os.listdir(cat_dir):
            if md_file == 'README.md':
                continue
            filepath = os.path.join(cat_dir, md_file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                continue
            parts = re.split(r'\n### ', content)
            for part in parts[1:]:
                lines = part.strip().split('\n')
                link = ''
                cn_title = ''
                cn_summary = ''
                for line in lines:
                    line = line.strip()
                    if line.startswith('- **链接**:'):
                        link = line.split(':', 1)[1].strip()
                    elif line.startswith('- **标题(CN)**:'):
                        cn_title = line.split(':', 1)[1].strip()
                    elif line.startswith('- **摘要(CN)**:'):
                        cn_summary = line.split(':', 1)[1].strip()
                if link and (cn_title or cn_summary):
                    existing[link] = {'cn_title': cn_title, 'cn_summary': cn_summary}
    print(f'Loaded existing Chinese content: {len(existing)} articles')
    return existing

def update_kb():
    """主函数：更新知识库"""
    print("=== 开始更新知识库 ===")
    
    # Preserve existing Chinese content across updates
    existing_cn = load_existing_cn_content()
    
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
                        link = article.get("link", "")
                        old = existing_cn.get(link, {})
                        title = article.get("cn_title", "") or old.get('cn_title', '') or article.get("title", "")
                        summary = article.get("cn_summary", "") or old.get('cn_summary', '') or article.get("content", "")[:150]
                        date = article.get("published", "")[:10]
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### {title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        if article.get("cn_title") or old.get('cn_title'):
                            f.write(f"- **标题(CN)**: {title}\n")
                        if article.get("cn_summary") or old.get('cn_summary'):
                            f.write(f"- **摘要(CN)**: {summary}\n")
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
                        link = article.get("link", "")
                        old = existing_cn.get(link, {})
                        title = article.get("cn_title", "") or old.get('cn_title', '') or article.get("title", "")
                        summary = article.get("cn_summary", "") or old.get('cn_summary', '') or article.get("content", "")[:150]
                        pub_date = article.get("published", "")[:10]
                        source = article.get("source", "Unknown")
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### [{source}] {title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {pub_date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        if article.get("cn_title") or old.get('cn_title'):
                            f.write(f"- **标题(CN)**: {title}\n")
                        if article.get("cn_summary") or old.get('cn_summary'):
                            f.write(f"- **摘要(CN)**: {summary}\n")
                        f.write(f"- **摘要**: {summary}\n\n")
    
    total = sum(len(v) for v in articles_by_cat.values())
    print(f"\n[OK] 知识库更新完成")
    print(f"   总计文章: {total}")
    for cat, articles in articles_by_cat.items():
        print(f"   {cat}: {len(articles)} 篇")

if __name__ == "__main__":
    update_kb()
