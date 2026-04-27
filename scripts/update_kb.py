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

# Data integrity guard: prevent running with incomplete local data
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_guard import assert_rss_complete, assert_kb_complete
assert_rss_complete(DATA_DIR)
assert_kb_complete(KB_DIR)

def classify_category(article):
    """判断文章属于哪个Category"""
    title = article.get("title", "").lower()
    summary = article.get("cn_summary", "").lower()
    content = article.get("content", "").lower()
    source = article.get("source", "").lower()
    combined = title + " " + summary + " " + content + " " + source
    
    # AI搜索关键词
    search_keywords = ["geo", "aeo", "seo", "search engine", "ranking", "perplexity", "sge", "google search", "bing", "search optimization", "ai search", "search strategy", "search roadmap", "search audit"]
    if any(k in combined for k in search_keywords):
        return "ai-search"
    
    # Agentic B2B关键词
    b2b_keywords = ["agentic", "b2b", "marketing", "sales", "crm", "customer experience", "cx", "automation", "ap automation", "workflow"]
    if any(k in combined for k in b2b_keywords):
        return "agentic-b2b"
    
    # 学术研究关键词 (收紧: 需要明确的学术指标)
    academic_keywords = ["paper", "research paper", "arxiv", "algorithm", "mit ", "stanford", "university research", "conference", "neurips", "icml", "acl", "cvpr"]
    # 同时检查是否有学术来源
    academic_sources = ["arxiv", "mit", "stanford", "researchgate", "academia.edu"]
    has_academic_kw = any(k in combined for k in academic_keywords)
    has_academic_src = any(s in source for s in academic_sources)
    if has_academic_kw or has_academic_src:
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
    
    else:  # ai-industry - flat tags without "行业/" prefix
        title_lower = article.get("title", "").lower()
        
        # 1. 大厂动态 (优先匹配)
        if any(k in combined for k in ["openai", "chatgpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "sam altman", "奥特曼", "sora", "o1", "o3", "open ai"]):
            tags.append("OpenAI动态")
        if any(k in combined for k in ["google", "gemini", "bard", "deepmind", "alphabet", "waymo", "google ai"]):
            tags.append("谷歌动态")
        if any(k in combined for k in ["meta", "facebook", "llama", "instagram", "whatsapp", "meta ai"]):
            tags.append("Meta动态")
        if any(k in combined for k in ["anthropic", "claude", "克劳德", "constitutional ai", "claude 3", "claude 4"]):
            tags.append("Anthropic动态")
        if any(k in combined for k in ["microsoft", "azure", "copilot", "bing", "microsoft ai"]):
            tags.append("微软动态")
        if any(k in combined for k in ["nvidia", "黄仁勋", "jensen"]):
            tags.append("英伟达动态")
        if any(k in combined for k in ["x.ai", "xai", "grok", "elon musk", "musk"]):
            tags.append("xAI动态")
        
        # 2. 模型与产品
        if any(k in combined for k in ["model release", "新模型", "模型发布", "foundation model", "大模型", "llm release", "model launch"]):
            tags.append("模型发布")
        if any(k in combined for k in ["product launch", "feature", "new tool", "app release", "产品发布", "新功能", "工具上线", "应用发布", "platform launch"]):
            tags.append("产品动态")
        
        # 3. Agent与开发者
        if any(k in combined for k in ["agent", "智能体", "multi-agent", "autonomous agent", "ai agent", "crewai", "langchain", "autogpt", "computer use"]):
            tags.append("Agent生态")
        if any(k in combined for k in ["cursor", "windsurf", "claude code", "github copilot", "devin", "coding assistant", "code generation", "代码生成", "编程助手"]):
            tags.append("开发者工具")
        
        # 4. 商业与硬件
        if any(k in combined for k in ["fund", "invest", "million", "billion", "valuation", "acquisition", "并购", "融资", "投资", "估值", "series a", "series b", "ipo", "startup", "独角兽"]):
            tags.append("融资并购")
        if any(k in combined for k in ["enterprise", "deploy", "adoption", "企业", "落地", "商用", "b2b", "saas", "workflow", "integration", "数字化转型"]):
            tags.append("企业落地")
        if any(k in combined for k in ["chip", "gpu", "hardware", "芯片", "算力", "推理", "training", "tpu", "apple silicon", "nvlink", "cluster", "数据中心", "云"]):
            tags.append("硬件算力")
        
        # 5. 监管与其他
        if any(k in combined for k in ["regulation", "policy", "safety", "监管", "政策", "法规", "安全", "风险", "合规", "gdpr", "copyright", "lawsuit", "诉讼", "反垄断"]):
            tags.append("监管安全")
        
        # 6. 兜底: 根据标题做最后分类
        if not tags:
            if any(k in title_lower for k in ["openai", "chatgpt", "gpt", "sam altman", "sora"]):
                tags.append("OpenAI动态")
            elif any(k in title_lower for k in ["google", "gemini", "deepmind", "bard"]):
                tags.append("谷歌动态")
            elif any(k in title_lower for k in ["meta", "llama", "facebook"]):
                tags.append("Meta动态")
            elif any(k in title_lower for k in ["anthropic", "claude"]):
                tags.append("Anthropic动态")
            elif any(k in title_lower for k in ["microsoft", "azure", "copilot"]):
                tags.append("微软动态")
            elif any(k in title_lower for k in ["nvidia", "gpu", "芯片", "算力"]):
                tags.append("硬件算力")
            elif any(k in title_lower for k in ["agent", "智能体", "copilot"]):
                tags.append("Agent生态")
            elif any(k in title_lower for k in ["cursor", "devin", "github copilot", "编程"]):
                tags.append("开发者工具")
            elif any(k in title_lower for k in ["fund", "融资", "投资", "million", "billion", "估值"]):
                tags.append("融资并购")
            elif any(k in title_lower for k in ["launch", "发布", "product", "model", "新版本"]):
                tags.append("产品动态")
            elif any(k in title_lower for k in ["builder", "startup", "创始人", "创业"]):
                tags.append("创业动态")
            else:
                tags.append("AI动态")
    
    return tags

def load_existing_cn_content():
    """Load existing Chinese content from old markdown files to preserve across updates.
    Also load from rss-data/geo-knowledge-base/ if available (source of truth for enriched Chinese content)."""
    existing = {}
    
    def scan_kb_dir(kb_dir_path, label):
        count = 0
        if not os.path.exists(kb_dir_path):
            return 0
        for cat in os.listdir(kb_dir_path):
            cat_dir = os.path.join(kb_dir_path, cat)
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
                    if not lines:
                        continue
                    # Parse title line: "### [Source] Title" or "### Title"
                    title_line = lines[0].strip().lstrip('#').strip()
                    title_line = re.sub(r'^\[.*?\]\s*', '', title_line)
                    link = ''
                    cn_title = ''
                    cn_summary = ''
                    for line in lines[1:]:
                        line = line.strip()
                        if line.startswith('- **链接**:'):
                            link = line.split(':', 1)[1].strip()
                        elif line.startswith('- **标题(CN)**:'):
                            cn_title = line.split(':', 1)[1].strip()
                        elif line.startswith('- **摘要(CN)**:'):
                            cn_summary = line.split(':', 1)[1].strip()
                        elif line.startswith('- **摘要**:'):
                            # rss-news-aggregator format: Chinese summary in 摘要 field
                            val = line.split(':', 1)[1].strip()
                            if val and len(val) > 10 and not val.startswith('http'):
                                cn_summary = val
                    # If no explicit cn_title, use the title line if it looks Chinese
                    if not cn_title and title_line:
                        # Heuristic: if title contains Chinese characters, use it as cn_title
                        if any('\u4e00' <= c <= '\u9fff' for c in title_line):
                            cn_title = title_line
                    if link and (cn_title or cn_summary):
                        existing[link] = {'cn_title': cn_title, 'cn_summary': cn_summary}
                        count += 1
        return count
    
    # First scan local knowledge-graph geo-kb
    local_count = scan_kb_dir(KB_DIR, 'local')
    
    # Then scan rss-data geo-kb (source of truth, overwrites local)
    rss_kb_dir = os.path.join(os.path.dirname(KB_DIR), 'rss-data', 'geo-knowledge-base')
    if not os.path.exists(rss_kb_dir):
        rss_kb_dir = os.path.join(os.path.dirname(os.path.dirname(KB_DIR)), 'rss-data', 'geo-knowledge-base')
    rss_count = scan_kb_dir(rss_kb_dir, 'rss-data')
    
    print(f'Loaded Chinese content: {local_count} from local, {rss_count} from rss-data, total {len(existing)} articles')
    return existing

def update_kb():
    """主函数：更新知识库"""
    print("=== 开始更新知识库 ===")
    
    # Preserve existing Chinese content across updates
    existing_cn = load_existing_cn_content()
    
    def _to_nested(pkt):
        """将 CAP flat IP 转换为 legacy nested 格式（兼容现有代码）"""
        if 'packet_id' in pkt or 'cn' in pkt:
            return pkt  # 已经是 nested
        flat = pkt
        se = flat.get('supporting_evidence', [])
        return {
            'packet_id': flat.get('id', ''),
            'source': {
                'name': flat.get('source_name', ''),
                'type': flat.get('source_slug', ''),
                'credibility': (flat.get('citations', [{}])[0] or {}).get('credibility', 'C'),
            },
            'en': {'title': '', 'summary': '', 'full_text': ''},
            'cn': {
                'title': flat.get('title', ''),
                'summary': flat.get('content', ''),
                'highlight': {
                    'claim_one_line': flat.get('core_thesis', ''),
                    'why_matters': se[0] if se else '',
                    'surprise_factor': (flat.get('claims_to_verify', ['']) or [''])[0],
                }
            },
            'metadata': {
                'category': flat.get('category', ''),
                'tags': [],
                'published': '',
                'collected': flat.get('created_at', ''),
                'importance': flat.get('tier', 3),
            },
            'quality': {
                'distill_density': flat.get('style_tags', {}).get('density', 0.14),
                'fact_check_status': 'unverified',
                'freshness_days': 0,
                'surprise_factor': 0.5,
            },
            'evidence': {
                'core_claims': [{'text': t} for t in se[1:]] if len(se) > 1 else [],
                'citations': flat.get('citations', []),
            },
            'voice_print_free': True,
            '_ip_flat': flat,  # 保留原始 flat 供其他脚本使用
        }
    
    # Load article packets (new source of truth for Chinese content)
    packet_map = {}
    packet_files = [
        os.path.join(DATA_DIR, 'latest_ip_packets.json'),
        os.path.join(DATA_DIR, 'ip_packets.json'),
        os.path.join(DATA_DIR, 'latest_packets.json'),
        os.path.join(DATA_DIR, 'article_packets.json'),
    ]
    # Also check dated subdirectories for packets
    for date_dir in sorted([d for d in os.listdir(DATA_DIR) if d.startswith('2026')]):
        for fname in ['ip_packets.json', 'article_packets.json']:
            dated_packet = os.path.join(DATA_DIR, date_dir, fname)
            if os.path.exists(dated_packet):
                packet_files.insert(0, dated_packet)
    
    for pf in packet_files:
        if os.path.exists(pf):
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    pdata = json.load(f)
                packets = pdata.get('packets', [])
                is_flat = pdata.get('schema') == 'cap_flat' or 'core_thesis' in (packets[0] if packets else {})
                for pkt in packets:
                    if is_flat:
                        link = (pkt.get('citations', [{}])[0] or {}).get('url', '')
                        pkt = _to_nested(pkt)
                    else:
                        citations = pkt.get('evidence', {}).get('citations', [])
                        link = citations[0].get('url', '') if citations else ''
                    if link:
                        packet_map[link] = pkt
                print(f'Loaded {len(packets)} article packets from {pf} (schema: {"flat" if is_flat else "nested"})')
                break  # Use first found
            except Exception as e:
                print(f'Failed to load packets from {pf}: {e}')
    
    # Fallback: load article enrich cache (legacy)
    enrich_cache = {}
    enrich_cache_path = os.path.join(BASE_DIR, 'article_enrich_cache.json')
    if os.path.exists(enrich_cache_path):
        try:
            with open(enrich_cache_path, 'r', encoding='utf-8') as f:
                enrich_cache = json.load(f)
            print(f'Loaded legacy enrich cache: {len(enrich_cache)} articles')
        except Exception as e:
            print(f'Failed to load enrich cache: {e}')
    
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
                        cache = enrich_cache.get(link, {})
                        pkt = packet_map.get(link, {})
                        en_title = article.get("title", "")
                        # Priority: packet > article field > existing > legacy cache
                        cn_title = (pkt.get('cn', {}).get('title', '') 
                                    or article.get("cn_title", "") 
                                    or old.get('cn_title', '') 
                                    or cache.get('cn_title', ''))
                        cn_summary = (pkt.get('cn', {}).get('summary', '') 
                                      or article.get("cn_summary", "") 
                                      or old.get('cn_summary', '') 
                                      or cache.get('cn_summary', ''))
                        cn_highlight = pkt.get('cn', {}).get('highlight', {})
                        en_summary = article.get("content", "")[:150] or article.get("summary", "")[:150]
                        date = article.get("published", "")[:10]
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### {en_title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        if cn_title:
                            f.write(f"- **标题(CN)**: {cn_title}\n")
                        if cn_summary:
                            f.write(f"- **摘要(CN)**: {cn_summary}\n")
                        if cn_highlight:
                            if cn_highlight.get('claim_one_line'):
                                f.write(f"- **精华**: {cn_highlight['claim_one_line']}\n")
                            if cn_highlight.get('why_matters'):
                                f.write(f"- **重要性**: {cn_highlight['why_matters']}\n")
                            if cn_highlight.get('surprise_factor'):
                                f.write(f"- **反直觉点**: {cn_highlight['surprise_factor']}\n")
                        f.write(f"- **摘要**: {en_summary}\n\n")
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
                        cache = enrich_cache.get(link, {})
                        pkt = packet_map.get(link, {})
                        en_title = article.get("title", "")
                        # Priority: packet > article field > existing > legacy cache
                        cn_title = (pkt.get('cn', {}).get('title', '') 
                                    or article.get("cn_title", "") 
                                    or old.get('cn_title', '') 
                                    or cache.get('cn_title', ''))
                        cn_summary = (pkt.get('cn', {}).get('summary', '') 
                                      or article.get("cn_summary", "") 
                                      or old.get('cn_summary', '') 
                                      or cache.get('cn_summary', ''))
                        cn_highlight = pkt.get('cn', {}).get('highlight', {})
                        en_summary = article.get("content", "")[:150] or article.get("summary", "")[:150]
                        pub_date = article.get("published", "")[:10]
                        source = article.get("source", "Unknown")
                        tags = ", ".join(article["_tags"])
                        
                        f.write(f"### [{source}] {en_title}\n")
                        f.write(f"- **链接**: {link}\n")
                        f.write(f"- **日期**: {pub_date}\n")
                        f.write(f"- **采集日期**: {article['_date']}\n")
                        f.write(f"- **Category**: {cat.replace('-', ' ').title()}\n")
                        f.write(f"- **Topic**: `{tags}`\n")
                        if cn_title:
                            f.write(f"- **标题(CN)**: {cn_title}\n")
                        if cn_summary:
                            f.write(f"- **摘要(CN)**: {cn_summary}\n")
                        if cn_highlight:
                            if cn_highlight.get('claim_one_line'):
                                f.write(f"- **精华**: {cn_highlight['claim_one_line']}\n")
                            if cn_highlight.get('why_matters'):
                                f.write(f"- **重要性**: {cn_highlight['why_matters']}\n")
                            if cn_highlight.get('surprise_factor'):
                                f.write(f"- **反直觉点**: {cn_highlight['surprise_factor']}\n")
                        f.write(f"- **摘要**: {en_summary}\n\n")
    
    total = sum(len(v) for v in articles_by_cat.values())
    print(f"\n[OK] 知识库更新完成")
    print(f"   总计文章: {total}")
    for cat, articles in articles_by_cat.items():
        print(f"   {cat}: {len(articles)} 篇")

if __name__ == "__main__":
    update_kb()
