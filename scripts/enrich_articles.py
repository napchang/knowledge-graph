#!/usr/bin/env python3
"""
自包含语义增强脚本
对缺失中文标题/摘要/阅读精华的文章，批量调用 DeepSeek API 生成
更新 article_enrich_cache.json（按 link 做稳定 key）
"""

import json, os, requests, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-0d56e22365da4a05a805986e4be431ba')
API_URL = 'https://api.deepseek.com/v1/chat/completions'

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

cache_path = os.path.join(base_dir, 'article_enrich_cache.json')
graph_path = os.path.join(base_dir, 'graph-data.json')

# Load cache
cache = {}
if os.path.exists(cache_path):
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f'Loaded enrich cache: {len(cache)} articles')
    except Exception as e:
        print(f'Cache load failed: {e}')

# Load graph data to find articles needing enrichment
with open(graph_path, 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

# Data integrity guard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_guard import assert_graph_sanity
assert_graph_sanity(graph_data)

articles = [n for n in graph_data['nodes'] if n.get('type') == 'article']

# Find articles missing Chinese content or reading highlight
pending = []
for art in articles:
    link = art.get('link', '')
    if not link:
        continue
    cached = cache.get(link, {})
    missing = []
    if not cached.get('cn_title') and not art.get('cn_title'):
        missing.append('cn_title')
    if not cached.get('cn_summary') and not art.get('cn_summary'):
        missing.append('cn_summary')
    if not cached.get('reading_highlight') and not art.get('reading_highlight'):
        missing.append('reading_highlight')
    if missing:
        pending.append({
            'link': link,
            'title_en': art.get('title_en', '') or art.get('title', '') or art.get('label', ''),
            'summary_en': art.get('summary', ''),
            'missing': missing,
            'is_today': art.get('is_today', False)
        })

print(f'Total articles: {len(articles)}')
print(f'Pending enrichment: {len(pending)}')
if not pending:
    print('All articles already enriched!')
    sys.exit(0)

# Show breakdown
missing_cn_title = sum(1 for p in pending if 'cn_title' in p['missing'])
missing_cn_summary = sum(1 for p in pending if 'cn_summary' in p['missing'])
missing_hl = sum(1 for p in pending if 'reading_highlight' in p['missing'])
print(f'  Missing cn_title: {missing_cn_title}')
print(f'  Missing cn_summary: {missing_cn_summary}')
print(f'  Missing reading_highlight: {missing_hl}')

# Sort: today articles first, then by link for determinism
pending.sort(key=lambda x: (0 if x.get('is_today') else 1, x['link']))


def generate_one(art):
    """Generate Chinese content for one article"""
    title_en = art['title_en']
    summary_en = art['summary_en']
    link = art['link']
    missing = art['missing']
    
    if not title_en and not summary_en:
        return link, {'cn_title': '', 'cn_summary': '', 'reading_highlight': ''}
    
    # 防错位：如果 summary 为空或不匹配，降级为仅基于标题生成
    has_valid_summary = bool(summary_en) and len(summary_en) > 30
    
    prompt = f"""请为以下英文文章生成中文内容。要求准确、专业、符合中文阅读习惯。
{'注意：原文摘要缺失或不可靠，请主要根据标题推断文章内容并生成。' if not has_valid_summary else ''}

原文链接（务必确认）：{link}
原文标题：{title_en}
原文摘要：{summary_en}

请严格按以下格式输出（不要添加额外说明）：

【中文标题】
10-15字，准确传达核心主题

【中文摘要】
50-80字，概括文章要点

【阅读精华】
300-500字，结构为：
- 【核心论点】文章的核心观点或立场
- 【关键发现】支撑论点的关键数据或事实
- 【行业意义】对 AI 行业的启示
- 【行动建议】给读者的具体建议

语言要求：口语化、有洞见感，不要简单翻译。
"""
    
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1200,
        'temperature': 0.7
    }
    
    for attempt in range(3):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                result = r.json()['choices'][0]['message']['content'].strip()
                
                # Parse result
                cn_title = ''
                cn_summary = ''
                reading_highlight = ''
                
                if '【中文标题】' in result:
                    parts = result.split('【中文标题】', 1)[1]
                    title_part = parts.split('【', 1)[0].strip()
                    cn_title = title_part.replace('】', '').strip()[:30]
                
                if '【中文摘要】' in result:
                    parts = result.split('【中文摘要】', 1)[1]
                    summary_part = parts.split('【', 1)[0].strip()
                    cn_summary = summary_part.replace('】', '').strip()[:200]
                
                if '【阅读精华】' in result:
                    hl_part = result.split('【阅读精华】', 1)[1].strip()
                    reading_highlight = hl_part[:1500]
                
                # Validate: highlight must contain core keywords from title
                if reading_highlight and cn_title:
                    import re
                    title_keywords = re.findall(r'[\u4e00-\u9fff]{2,}', cn_title)
                    if title_keywords:
                        hl_lower = reading_highlight.lower()
                        matches = sum(1 for kw in title_keywords if kw in hl_lower)
                        if matches == 0:
                            print(f"  [WARN] Highlight mismatch for {link[:50]}, clearing highlight")
                            reading_highlight = ''
                
                # Fallback: if parsing failed but we have content, use heuristics
                if not cn_title and result:
                    lines = [l.strip() for l in result.split('\n') if l.strip()]
                    for line in lines:
                        if any('\u4e00' <= c <= '\u9fff' for c in line) and len(line) <= 30:
                            cn_title = line[:30]
                            break
                
                return link, {
                    'cn_title': cn_title,
                    'cn_summary': cn_summary,
                    'reading_highlight': reading_highlight,
                    'enriched_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
            else:
                print(f"  API error {r.status_code} for {link[:50]}: {r.text[:80]}")
                time.sleep(2)
        except Exception as e:
            print(f"  Exception for {link[:50]}: {str(e)[:80]}")
            time.sleep(2)
    
    return link, {'cn_title': '', 'cn_summary': '', 'reading_highlight': ''}


# Process in small batches with conservative rate limiting
batch_size = 5
save_interval = 10
processed = 0
success = 0

for batch_start in range(0, len(pending), batch_size):
    batch = pending[batch_start:batch_start + batch_size]
    batch_num = batch_start // batch_size + 1
    total_batches = (len(pending) - 1) // batch_size + 1
    print(f"\nBatch {batch_num}/{total_batches}: {len(batch)} articles")
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(generate_one, art): art for art in batch}
        for future in as_completed(futures):
            link, result = future.result()
            if link not in cache:
                cache[link] = {}
            if result.get('cn_title'):
                cache[link]['cn_title'] = result['cn_title']
                cache[link]['enriched_at'] = result.get('enriched_at', '')
            if result.get('cn_summary'):
                cache[link]['cn_summary'] = result['cn_summary']
                cache[link]['enriched_at'] = result.get('enriched_at', '')
            if result.get('reading_highlight'):
                cache[link]['reading_highlight'] = result['reading_highlight']
                cache[link]['enriched_at'] = result.get('enriched_at', '')
            
            processed += 1
            has_any = bool(result.get('cn_title') or result.get('reading_highlight'))
            if has_any:
                success += 1
            print(f"  [{processed}/{len(pending)}] {link[:50]}...: {'OK' if has_any else 'FAIL'}")
    
    # Save cache after each batch
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"  Cache saved: {len(cache)} entries")
    
    # Rate limit: delay between batches
    if batch_start + batch_size < len(pending):
        time.sleep(3)

print(f"\n=== Done ===")
print(f"Processed: {processed}, Success: {success}, Total cache: {len(cache)}")
print(f"Cache saved to: {cache_path}")
