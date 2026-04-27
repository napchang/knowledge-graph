#!/usr/bin/env python3
"""
娓呴櫎閿欎綅鏂囩珷鐨?enrich 缂撳瓨
閬嶅巻 graph-data.json 妫€娴?title-summary 閿欎綅锛屼粠 article_enrich_cache.json 涓垹闄ゅ搴旀潯鐩?鍦?enrich_articles.py 涔嬪墠杩愯锛岀‘淇濋敊浣嶆枃绔犱細琚噸鏂?enrich锛堝熀浜庢纭殑鏁版嵁锛?"""

import json, os, sys

def check_title_summary_match(title, summary, min_overlap=0.2):
    if not title or not summary or len(summary) < 50:
        return True
    title_words = [w.strip('.,-:;!?').lower() for w in title.split() if len(w.strip('.,-:;!?')) >= 4]
    if not title_words:
        return True
    summary_lower = summary.lower()
    matches = sum(1 for w in title_words if w in summary_lower)
    return matches / len(title_words) >= min_overlap

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

graph_path = os.path.join(base_dir, 'graph-data.json')
cache_path = os.path.join(base_dir, 'article_enrich_cache.json')

# Load graph data
with open(graph_path, 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

articles = [n for n in graph_data['nodes'] if n.get('type') == 'article']

# Find mismatched articles (title-summary mismatch)
mismatched_links = []
for a in articles:
    title = a.get('title_en', '')
    summary = a.get('summary', '')
    if not check_title_summary_match(title, summary):
        mismatched_links.append(a.get('link', ''))

print(f'[CLEAN] Total articles: {len(articles)}')
print(f'[CLEAN] Title-summary mismatched: {len(mismatched_links)}')

if not mismatched_links:
    print('[CLEAN] No mismatched articles found. Nothing to clean.')
    sys.exit(0)

# Load cache
cache = {}
if os.path.exists(cache_path):
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f'[CLEAN] Loaded cache: {len(cache)} entries')
    except Exception as e:
        print(f'[CLEAN] Cache load failed: {e}')
        sys.exit(1)

# Remove mismatched entries from cache
removed = 0
for link in mismatched_links:
    if link in cache:
        del cache[link]
        removed += 1

# Save cleaned cache
with open(cache_path, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f'[CLEAN] Removed {removed} mismatched entries from cache')
print(f'[CLEAN] Cache now has {len(cache)} entries')
print('[CLEAN] These articles will be re-enriched with correct data on next run.')
