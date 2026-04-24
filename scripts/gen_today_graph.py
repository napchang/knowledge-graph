#!/usr/bin/env python3
"""
生成今日-only 的图谱数据 today-graph-data.json
从 graph-data.json 中提取今日文章及相关节点
"""

import json, os

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

# Load full graph data
graph_path = os.path.join(base_dir, 'graph-data.json')
with open(graph_path, 'r', encoding='utf-8') as f:
    full_data = json.load(f)

# Step 1: collect today's article nodes
today_article_ids = set()
today_articles = []
for n in full_data['nodes']:
    if n.get('type') == 'article' and n.get('is_today'):
        today_article_ids.add(n['id'])
        today_articles.append(n)

# Step 2: collect edges connected to today articles, and their tags
today_tag_ids = set()
related_edges = []

for e in full_data['edges']:
    src = e.get('source', '')
    tgt = e.get('target', '')
    if src in today_article_ids or tgt in today_article_ids:
        related_edges.append(e)
        if src.startswith('tag_'):
            today_tag_ids.add(src)
        if tgt.startswith('tag_'):
            today_tag_ids.add(tgt)

# Step 3: collect category nodes connected to those tags
# Also collect cat->tag edges
today_cat_ids = set()
for e in full_data['edges']:
    src = e.get('source', '')
    tgt = e.get('target', '')
    if src.startswith('cat_') and tgt in today_tag_ids:
        today_cat_ids.add(src)
        related_edges.append(e)
    elif tgt.startswith('cat_') and src in today_tag_ids:
        today_cat_ids.add(tgt)
        related_edges.append(e)

# Step 4: deduplicate edges
seen_edges = set()
unique_edges = []
for e in related_edges:
    key = (e.get('source', ''), e.get('target', ''))
    if key not in seen_edges:
        seen_edges.add(key)
        unique_edges.append(e)

# Step 5: build node list
needed_node_ids = today_article_ids | today_tag_ids | today_cat_ids
today_nodes = [n for n in full_data['nodes'] if n['id'] in needed_node_ids]

# Ensure category descriptions are present
for n in today_nodes:
    if n.get('type') == 'category':
        cat_id = n['id'].replace('cat_', '')
        n['description'] = full_data.get('category_descriptions', {}).get(cat_id, '')

# Build today data
today_data = {
    'generated_at': full_data.get('generated_at', ''),
    'date': full_data.get('date', ''),
    'total_articles': len(today_articles),
    'today_articles': len(today_articles),
    'categories': full_data.get('categories', []),
    'category_names': full_data.get('category_names', {}),
    'category_colors': full_data.get('category_colors', {}),
    'category_descriptions': full_data.get('category_descriptions', {}),
    'nodes': today_nodes,
    'edges': unique_edges
}

output_path = os.path.join(base_dir, 'today-graph-data.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(today_data, f, ensure_ascii=False, indent=2)

print(f'Today graph saved: {len(today_nodes)} nodes, {len(unique_edges)} edges')
print(f'Today articles: {len(today_articles)}')

# Category breakdown
from collections import Counter
cat_counts = Counter(a.get('category') for a in today_articles)
for cat, cnt in cat_counts.items():
    print(f'  {cat}: {cnt}')

# Verify categories in nodes
cat_nodes = [n for n in today_nodes if n.get('type') == 'category']
print(f'Category nodes: {len(cat_nodes)}')
for c in cat_nodes:
    print('  ' + c['id'])
