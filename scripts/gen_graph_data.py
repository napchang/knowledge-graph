import os, re, json
from datetime import datetime

def check_title_summary_match(title, summary, min_overlap=0.2):
    """妫€鏌?title 鍜?summary 鏄惁鍖归厤銆俧eedparser 鍦ㄦ煇浜?RSS feed 涓婁細鍑虹幇閿欎綅銆?""
    if not title or not summary or len(summary) < 50:
        return True
    title_words = [w.strip('.,-:;!?').lower() for w in title.split() if len(w.strip('.,-:;!?')) >= 4]
    if not title_words:
        return True
    summary_lower = summary.lower()
    matches = sum(1 for w in title_words if w in summary_lower)
    return matches / len(title_words) >= min_overlap

import sys
# Determine base dir: repo root (where geo-knowledge-base lives)
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

kb_dir = os.path.join(base_dir, 'geo-knowledge-base')

# Data integrity guard: prevent running with incomplete local data
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_guard import assert_kb_complete
assert_kb_complete(kb_dir)

# Try load reading highlights cache
READING_HIGHLIGHTS = {}
hl_cache_path = os.path.join(base_dir, 'reading_highlights_cache.json')
if os.path.exists(hl_cache_path):
    try:
        with open(hl_cache_path, 'r', encoding='utf-8') as f:
            READING_HIGHLIGHTS = json.load(f)
        print(f'Loaded reading highlights: {len(READING_HIGHLIGHTS)} articles')
    except Exception as e:
        print(f'Failed to load highlights: {e}')

# Try load article enrich cache (unified source for Chinese content + reading highlights)
ENRICH_CACHE = {}
enrich_cache_path = os.path.join(base_dir, 'article_enrich_cache.json')
if os.path.exists(enrich_cache_path):
    try:
        with open(enrich_cache_path, 'r', encoding='utf-8') as f:
            ENRICH_CACHE = json.load(f)
        print(f'Loaded enrich cache: {len(ENRICH_CACHE)} articles')
    except Exception as e:
        print(f'Failed to load enrich cache: {e}')

categories = ['ai-search', 'agentic-b2b', 'ai-industry', 'academic']
cat_names = {
    'ai-search': 'AI鎼滅储',
    'agentic-b2b': 'Agentic B2B',
    'ai-industry': 'AI琛屼笟鍔ㄦ€?,
    'academic': '瀛︽湳鐮旂┒'
}
# New color scheme from user
cat_colors = {
    'ai-search': '#FF6B35',      # 鐮存檽姗?    'agentic-b2b': '#4A7BC3',    # 椋炲ぉ钃?    'ai-industry': '#E6B85C',    # 澶у湴閲?    'academic': '#5A92E5'        # 鍗囧崕钃?}
cat_desc = {
    'ai-search': '鎼滅储寮曟搸浼樺寲銆丟EO銆丄EO銆丼EO銆佹帓鍚嶇畻娉曘€佹悳绱骇鍝佸晢涓氬寲',
    'agentic-b2b': '钀ラ攢鑷姩鍖栥€侀攢鍞伐鍏枫€丆RM銆乄orkflow銆丠ubSpot妗嗘灦銆佸鎴蜂綋楠?,
    'ai-industry': '浜у搧鍙戝竷銆佽瀺璧勫姩鎬併€佸ぇ鍘傛垬鐣ャ€丅uilder鍔ㄦ€併€佽涓氳秼鍔?,
    'academic': '璁烘枃鍙戝竷銆佺畻娉曠爺绌躲€佹ā鍨嬫灦鏋勶紙MIT/Stanford/arXiv锛?
}

# Use latest collection date from knowledge base as "today"
# This ensures users see the most recently collected articles
all_collection_dates = []
for cat in categories:
    cat_dir = os.path.join(kb_dir, cat)
    if not os.path.exists(cat_dir):
        continue
    for md_file in os.listdir(cat_dir):
        m = re.match(r'(\d{4}-\d{2}-\d{2})\.md$', md_file)
        if m:
            all_collection_dates.append(m.group(1))
today_str = max(all_collection_dates) if all_collection_dates else datetime.now().strftime('%Y-%m-%d')

def parse_date(date_str):
    """Parse various date formats to datetime object"""
    if not date_str:
        return None
    formats = [
        '%Y-%m-%d',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d %b %Y',
        '%a, %d %b %Y %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            pass
    # Fallback: try to extract date-like substring
    import re
    m = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y-%m-%d')
        except:
            pass
    return None

def is_today(date_str):
    d = parse_date(date_str)
    if not d:
        return False
    return d.strftime('%Y-%m-%d') == today_str

def is_recent(date_str):
    d = parse_date(date_str)
    if not d:
        return False
    from datetime import timedelta
    today_d = datetime.strptime(today_str, '%Y-%m-%d')
    return (today_d - d).days <= 2

articles = []
seen_article_links = set()  # deduplicate across all markdown files
for cat in categories:
    cat_dir = os.path.join(kb_dir, cat)
    if not os.path.exists(cat_dir):
        continue
    for md_file in os.listdir(cat_dir):
        if md_file == 'README.md':
            continue
        filepath = os.path.join(cat_dir, md_file)
        # Extract collection date from filename (e.g., "2026-04-22.md")
        collection_date = ''
        m = re.match(r'(\d{4}-\d{2}-\d{2})\.md$', md_file)
        if m:
            collection_date = m.group(1)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        parts = re.split(r'\n### ', content)
        for part in parts[1:]:
            lines = part.strip().split('\n')
            if len(lines) < 2:
                continue
            title_line = lines[0].strip().lstrip('#').strip()
            # Extract source prefix like "[Semrush Blog]" if present
            source_prefix = ''
            m = re.match(r'^\[(.*?)\]\s*(.*)', title_line)
            if m:
                source_prefix = m.group(1)
                en_title = m.group(2).strip()
            else:
                en_title = title_line
            link = date = collection_date_from_file = topic_str = summary = ''
            cn_title = ''
            cn_summary = ''
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('- **閾炬帴**:'):
                    link = line.split(':', 1)[1].strip()
                elif line.startswith('- **鏃ユ湡**:'):
                    date = line.split(':', 1)[1].strip()
                elif line.startswith('- **閲囬泦鏃ユ湡**:'):
                    collection_date_from_file = line.split(':', 1)[1].strip()
                elif line.startswith('- **Topic**:'):
                    m = re.search(r'`(.+?)`', line)
                    if m:
                        topic_str = m.group(1)
                elif line.startswith('- **鏍囬(CN)**:'):
                    cn_title = line.split(':', 1)[1].strip()
                elif line.startswith('- **鎽樿(CN)**:'):
                    cn_summary = line.split(':', 1)[1].strip()
                elif line.startswith('- **鎽樿**:'):
                    summary = line.split(':', 1)[1].strip()
            if en_title and link:
                # 闃插尽閿欎綅鏁版嵁锛氭鏌?title 鍜?summary 鏄惁鍖归厤
                if not check_title_summary_match(en_title, summary):
                    print(f'  鈿狅笍 Title-summary mismatch in markdown, clearing summary: {en_title[:50]}')
                    summary = ''
                cache = ENRICH_CACHE.get(link, {})
                # Use collection date for is_today: article field > filename > published date
                effective_collection_date = collection_date_from_file or collection_date or date
                today_check_date = effective_collection_date
                articles.append({
                    'title': en_title,
                    'link': link,
                    'date': date,
                    'category': cat,
                    'topics': [t.strip() for t in topic_str.split(',')] if topic_str else [],
                    'summary': summary,
                    'cn_title': cn_title or cache.get('cn_title', ''),
                    'cn_summary': cn_summary or cache.get('cn_summary', '') or summary or en_title or '',
                    'key_insight': cache.get('key_insight', ''),
                    'importance': cache.get('importance', 3),
                    'is_important_source': cache.get('is_important_source', False),
                    'is_major_news': cache.get('is_major_news', False),
                    'is_today': is_today(today_check_date),
                    'is_recent': is_recent(today_check_date),
                    'collection_date': effective_collection_date
                })

# Smart truncation: ensure each category gets minimum representation
# Then fill remaining slots with newest articles across all categories
MIN_PER_CAT = 30
MAX_TOTAL = 2000

# Sort all articles by date first
articles.sort(key=lambda x: (x.get('collection_date', ''), x.get('date', '')), reverse=True)

selected = []
selected_links = set()

# Step 1: guarantee minimum per category
for cat in categories:
    cat_arts = [a for a in articles if a['category'] == cat]
    for art in cat_arts[:MIN_PER_CAT]:
        link = art.get('link', '')
        if link and link not in selected_links:
            selected.append(art)
            selected_links.add(link)

# Step 2: fill remaining slots with top articles from all categories
remaining_slots = MAX_TOTAL - len(selected)
if remaining_slots > 0:
    for art in articles:
        link = art.get('link', '')
        if link and link not in selected_links:
            selected.append(art)
            selected_links.add(link)
            remaining_slots -= 1
            if remaining_slots <= 0:
                break

articles = selected
# Re-sort final selection
articles.sort(key=lambda x: (x.get('collection_date', ''), x.get('date', '')), reverse=True)

# Build article index map: use link as stable key
art_index = {art['link']: i for i, art in enumerate(articles)}

nodes = []
edges = []
tag_to_cat = {}
topic_articles = {}

# Category nodes
for cat in categories:
    nodes.append({
        'id': f'cat_{cat}',
        'type': 'category',
        'label': cat_names[cat],
        'color': cat_colors[cat],
        'size': 50,
        'description': cat_desc[cat]
    })

# Tag normalization: fix vague academic tags
ACADEMIC_TAG_MAP = {
    '鐮旂┒': '瀛︽湳鍓嶆部',
    '璁烘枃': '椤朵細璁烘枃',
}
def normalize_topic(topic, art):
    """Normalize vague tags, especially for academic category"""
    if art['category'] == 'academic' and topic.lower() in ('鐮旂┒', 'research', '璁烘枃', 'paper'):
        # Try to extract meaningful topic from title
        title = art.get('cn_title', '') or art.get('title', '')
        # Extract key technical terms
        tech_terms = re.findall(r'(LLM|RAG|妫€绱鍚戦噺|鐭ヨ瘑鍥捐氨|澶氭ā鎬亅骞昏|鎺ㄧ悊|鐢熸垚|瀵归綈|寰皟|棰勮缁億Transformer|BERT|GPT|Embedding|璇箟鎼滅储|瀵规瘮瀛︿範|淇℃伅妫€绱?', title, re.I)
        if tech_terms:
            return tech_terms[0]
        # Try English technical terms from title
        en_terms = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', title)
        for t in en_terms:
            if len(t) > 3 and t.lower() not in ('the', 'and', 'for', 'with', 'from', 'how', 'new', 'use', 'using', 'based', 'approach', 'method'):
                return t.strip()
        return '瀛︽湳鍓嶆部'
    return ACADEMIC_TAG_MAP.get(topic, topic)

# Collect topic 鈫?articles mapping & build hierarchy
for art in articles:
    for topic in art['topics']:
        topic = normalize_topic(topic, art)
        if topic not in topic_articles:
            topic_articles[topic] = []
            tag_to_cat[topic] = art['category']
        topic_articles[topic].append(art)

# Build hierarchical tags (Obsidian style: Parent/Child)
hierarchy_edges = []  # parent_tag -> child_tag
parent_tags = {}  # parent_name -> {cat, children_count, articles}

for topic, art_list in topic_articles.items():
    cat = tag_to_cat.get(topic, 'ai-industry')
    if '/' in topic:
        parent_name = topic.split('/')[0]
        # Create parent tag if not exists
        if parent_name not in parent_tags:
            parent_tags[parent_name] = {'cat': cat, 'count': 0, 'arts': set()}
        parent_tags[parent_name]['count'] += len(art_list)
        for a in art_list:
            parent_tags[parent_name]['arts'].add(id(a))
        # Mark hierarchical relationship
        hierarchy_edges.append((f'tag_{parent_name}', f'tag_{topic}'))

# Track created tag nodes to avoid duplicates (a tag can be both parent and plain)
created_tag_ids = set()

# Create parent tag nodes
for parent_name, info in parent_tags.items():
    cat = info['cat']
    count = info['count']
    avg_imp = sum(a.get('importance', 3) for a in articles if id(a) in info['arts']) / max(len(info['arts']), 1)
    tag_id = f'tag_{parent_name}'
    created_tag_ids.add(tag_id)
    nodes.append({
        'id': tag_id,
        'type': 'tag',
        'label': parent_name,
        'category': cat,
        'color': cat_colors.get(cat, '#64748B'),
        'size': 20 + min(count * 0.8, 18),
        'count': count,
        'avg_importance': round(avg_imp, 1),
        'is_parent_tag': True
    })
    edges.append({
        'source': f'cat_{cat}',
        'target': tag_id,
        'value': 2,
        'label': '鍖呭惈'
    })
    # Parent tag only connects to child tags, not articles (to avoid overcrowding)

# Create child tag nodes (including non-hierarchical tags)
# Skip tags already created as parent tags
for topic, art_list in topic_articles.items():
    cat = tag_to_cat.get(topic, 'ai-industry')
    tag_id = f'tag_{topic}'
    if tag_id in created_tag_ids:
        # Already created as parent tag; only add article edges
        for art in art_list:
            idx = art_index.get(art['link'])
            if idx is None:
                continue
            edges.append({
                'source': tag_id,
                'target': f'art_{idx}',
                'value': 1,
                'label': '鍏宠仈'
            })
        continue
    created_tag_ids.add(tag_id)
    count = len(art_list)
    avg_imp = sum(a.get('importance', 3) for a in art_list) / len(art_list)
    nodes.append({
        'id': tag_id,
        'type': 'tag',
        'label': topic,
        'category': cat,
        'color': cat_colors.get(cat, '#64748B'),
        'size': 14 + min(count * 1.0, 16),
        'count': count,
        'avg_importance': round(avg_imp, 1),
        'is_parent_tag': False
    })
    if '/' in topic:
        parent_name = topic.split('/')[0]
        edges.append({
            'source': f'tag_{parent_name}',
            'target': tag_id,
            'value': 2,
            'label': '瀛愮被'
        })
    else:
        edges.append({
            'source': f'cat_{cat}',
            'target': tag_id,
            'value': 2,
            'label': '鍖呭惈'
        })
    for art in art_list:
        idx = art_index.get(art['link'])
        if idx is None:
            continue
        edges.append({
            'source': tag_id,
            'target': f'art_{idx}',
            'value': 1,
            'label': '鍏宠仈'
        })

# Deduplicate labels
label_counts = {}
for art in articles:
    base_label = art['cn_title'][:26] + '...' if art.get('cn_title') and len(art['cn_title']) > 26 else (art['cn_title'] or art['title'][:26] + '...')
    label_counts[base_label] = label_counts.get(base_label, 0) + 1

# Article nodes
for i, art in enumerate(articles):
    has_tag = len(art['topics']) > 0 and any(t in topic_articles for t in art['topics'])
    imp = art.get('importance', 3)
    is_today_flag = art.get('is_today', False)
    is_important = art.get('is_important_source', False)
    is_major = art.get('is_major_news', False)
    
    # Size based on importance + boosts
    size = 5 + imp * 1.2
    if is_important:
        size += 2
    if is_major:
        size += 2
    if is_today_flag:
        size += 1.5
    
    # Border style based on importance
    border_width = 1
    border_color = '#ffffff'
    if imp >= 5:
        border_width = 3
        border_color = '#FF6B35'  # 鐮存檽姗欒竟妗?    elif imp >= 4:
        border_width = 2
        border_color = '#E6B85C'  # 澶у湴閲戣竟妗?    elif is_important:
        border_width = 2
        border_color = '#4A7BC3'  # 椋炲ぉ钃濊竟妗?    
    # Build unique label
    base_label = art['cn_title'][:26] + '...' if art.get('cn_title') and len(art['cn_title']) > 26 else (art['cn_title'] or art['title'][:26] + '...')
    if label_counts.get(base_label, 0) > 1:
        source_prefix = art.get('source', '')[:8]
        if source_prefix:
            display_label = source_prefix + ': ' + base_label
        else:
            display_label = base_label
    else:
        display_label = base_label
    
    nodes.append({
        'id': f'art_{i}',
        'type': 'article',
        'label': display_label,
        'title_en': art['title'],
        'cn_title': art.get('cn_title', ''),
        'link': art['link'],
        'date': art['date'],
        'collection_date': art.get('collection_date', art['date']),
        'summary': art['summary'][:120],
        'cn_summary': (art.get('cn_summary') or art.get('summary') or art.get('title') or '')[:120],
        'key_insight': art.get('key_insight', ''),
        'category': art['category'],
        'tags': art['topics'] if art['topics'] else [],
        'color': cat_colors.get(art['category'], '#64748B'),
        'size': size,
        'importance': imp,
        'is_today': is_today_flag,
        'is_recent': art.get('is_recent', False),
        'is_important_source': is_important,
        'is_major_news': is_major,
        'border_width': border_width,
        'border_color': border_color,
        'reading_highlight': ENRICH_CACHE.get(art['link'], {}).get('reading_highlight', '') or READING_HIGHLIGHTS.get(art['link'], '')
    })
    # Hidden anchor edge: category -> article (for layout attraction)
    edges.append({
        'source': f'cat_{art["category"]}',
        'target': f'art_{i}',
        'value': 1,
        'label': '',
        'type': 'layout-anchor',
        'hidden': True
    })

# Cross-category edges: tags sharing articles
article_tags = {}
for topic, art_list in topic_articles.items():
    for art in art_list:
        idx = art_index.get(art['link'])
        if idx is None:
            continue
        if idx not in article_tags:
            article_tags[idx] = []
        article_tags[idx].append(topic)

for idx, tags in article_tags.items():
    if len(tags) > 1:
        for i in range(len(tags)):
            for j in range(i+1, len(tags)):
                t1, t2 = tags[i], tags[j]
                c1, c2 = tag_to_cat.get(t1), tag_to_cat.get(t2)
                if c1 and c2 and c1 != c2:
                    edges.append({
                        'source': f'tag_{t1}',
                        'target': f'tag_{t2}',
                        'value': 1,
                        'type': 'cross',
                        'label': '璺ㄤ富棰?
                    })

# Inter-category connections (thematic links between the 4 main categories)
# These represent semantic relationships between domains
inter_cat_links = [
    ('cat_ai-search', 'cat_agentic-b2b', '鎼滅储椹卞姩B2B鑾峰'),
    ('cat_ai-search', 'cat_ai-industry', '鎼滅储浜у搧鍟嗕笟鍖?),
    ('cat_ai-search', 'cat_academic', '鎼滅储绠楁硶鐮旂┒'),
    ('cat_agentic-b2b', 'cat_ai-industry', 'B2B AI浜у搧'),
    ('cat_agentic-b2b', 'cat_academic', 'Agentic鐮旂┒'),
    ('cat_ai-industry', 'cat_academic', '浜у鐮旇浆鍖?)
]
for src, tgt, label in inter_cat_links:
    edges.append({
        'source': src,
        'target': tgt,
        'value': 1,
        'type': 'inter-cat',
        'label': label,
        'dashes': True
    })

# Deduplicate edges: same (source, target, type) should not appear twice
seen_edges = set()
deduped_edges = []
for e in edges:
    key = (e.get('source'), e.get('target'), e.get('type', ''))
    if key not in seen_edges:
        seen_edges.add(key)
        deduped_edges.append(e)
    else:
        print(f'[WARN] Duplicate edge removed: {key}')
edges = deduped_edges

# Today's summary by category
today_summary = {}
for cat in categories:
    cat_articles = [a for a in articles if a['category'] == cat and a.get('is_today')]
    today_summary[cat] = {
        'count': len(cat_articles),
        'titles': [a.get('cn_title') or a['title'] for a in cat_articles[:5]]
    }

graph_data = {
    'generated_at': datetime.now().isoformat(),
    'date': today_str,
    'total_articles': len(articles),
    'today_articles': sum(1 for a in articles if a.get('is_today')),
    'recent_articles': sum(1 for a in articles if a.get('is_recent')),
    'categories': categories,
    'category_names': cat_names,
    'category_colors': cat_colors,
    'category_descriptions': cat_desc,
    'today_summary': today_summary,
    'nodes': nodes,
    'edges': edges
}

output_path = os.path.join(base_dir, 'graph-data.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(graph_data, f, ensure_ascii=False, indent=2)

# Stats
art_with_edges = set()
for e in edges:
    t = e.get('target', '')
    if t.startswith('art_'):
        art_with_edges.add(t)

print(f'Graph data saved: {len(nodes)} nodes, {len(edges)} edges')
print(f'Articles: {len(articles)}, with edges: {len(art_with_edges)}, isolated: {len(articles) - len(art_with_edges)}')
print(f'Tags: {len(topic_articles)}')
print(f'Today: {sum(1 for a in articles if a.get("is_today"))}, Recent: {sum(1 for a in articles if a.get("is_recent"))}')
