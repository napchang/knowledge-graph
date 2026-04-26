#!/usr/bin/env python3
"""
紧急清理 graph-data.json 和 today-graph-data.json 中的重复节点
按 link 去重，保留第一个出现的节点，修复 edges
"""

import json, os, sys
from collections import Counter

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def dedup_graph(graph_path):
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data['nodes'])
    
    # Step 1: identify duplicates by link
    seen_links = set()
    unique_nodes = []
    removed_ids = set()
    
    for node in data['nodes']:
        if node.get('type') == 'article':
            link = node.get('link', '')
            if link in seen_links:
                removed_ids.add(node['id'])
                continue
            seen_links.add(link)
        unique_nodes.append(node)
    
    # Step 2: filter edges - remove any edge referencing removed nodes
    unique_edges = []
    for edge in data['edges']:
        src = edge.get('source', '')
        tgt = edge.get('target', '')
        if src in removed_ids or tgt in removed_ids:
            continue
        unique_edges.append(edge)
    
    removed_count = original_count - len(unique_nodes)
    
    data['nodes'] = unique_nodes
    data['edges'] = unique_edges
    
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'[DEDUP] {graph_path}: removed {removed_count} duplicate nodes, {len(data["edges"])} edges remaining')
    return removed_count

# Clean graph-data.json
removed_full = dedup_graph(os.path.join(base_dir, 'graph-data.json'))

# Clean today-graph-data.json
removed_today = dedup_graph(os.path.join(base_dir, 'today-graph-data.json'))

print(f'\nTotal duplicates removed: {removed_full + removed_today}')
