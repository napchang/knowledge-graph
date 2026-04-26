#!/usr/bin/env python3
"""
批量生成文章深度阅读精华 (reading_highlight)
使用 DeepSeek API，并行处理，支持断点续传
"""

import json, os, requests, time
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = 'sk-0d56e22365da4a05a805986e4be431ba'
API_URL = 'https://api.deepseek.com/v1/chat/completions'

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

cache_path = os.path.join(base_dir, 'reading_highlights_cache.json')
graph_path = os.path.join(base_dir, 'graph-data.json')

# Load cache
cache = {}
if os.path.exists(cache_path):
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f'Loaded cache: {len(cache)} articles')
    except Exception as e:
        print(f'Cache load failed: {e}')

# Load graph data
with open(graph_path, 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

articles = [n for n in graph_data['nodes'] if n.get('type') == 'article']
print(f'Total articles to process: {len(articles)}')

# Find articles needing generation (use link as stable key)
pending = []
for art in articles:
    art_key = art.get('link', art['id'])
    if art_key not in cache or not cache[art_key]:
        pending.append(art)

print(f'Pending: {len(pending)} (cached: {len(articles) - len(pending)})')

if not pending:
    print('All articles already have highlights!')
    exit(0)

def generate_one(art):
    """Generate reading highlight for one article"""
    title = art.get('cn_title', '') or art.get('title', '') or art.get('label', '')
    summary = art.get('cn_summary', '') or art.get('summary', '') or ''
    insight = art.get('key_insight', '') or ''
    
    if not title and not summary:
        return art.get('link', art['id']), ''
    
    prompt = f"""请为以下文章生成一段"深度阅读精华"，要求：
1. 让没读过原文的人掌握80%核心思想
2. 结构清晰：【核心论点】→【关键发现】→【行业意义】→【行动建议】
3. 语言口语化、有洞见感，不要简单翻译摘要
4. 300-500字中文

文章标题：{title}
文章摘要：{summary}
关键洞察：{insight or '无'}
"""
    
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 800,
        'temperature': 0.7
    }
    
    for attempt in range(3):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                result = r.json()['choices'][0]['message']['content'].strip()
                return art.get('link', art['id']), result
            else:
                print(f"  API error {r.status_code} for {art['id']}: {r.text[:80]}")
                time.sleep(2)
        except Exception as e:
            print(f"  Exception for {art['id']}: {str(e)[:80]}")
            time.sleep(2)
    
    return art['id'], ''

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
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(generate_one, art): art for art in batch}
        for future in as_completed(futures):
            art_key, result = future.result()
            cache[art_key] = result
            processed += 1
            if result:
                success += 1
            print(f"  [{processed}/{len(pending)}] {art_key[:40]}...: {'OK' if result else 'FAIL'}")
    
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
