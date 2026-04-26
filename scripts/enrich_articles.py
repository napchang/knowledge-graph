#!/usr/bin/env python3
"""
鑷寘鍚涔夊寮鸿剼鏈?瀵圭己澶变腑鏂囨爣棰?鎽樿/闃呰绮惧崕鐨勬枃绔狅紝鎵归噺璋冪敤 DeepSeek API 鐢熸垚
鏇存柊 article_enrich_cache.json锛堟寜 link 鍋氱ǔ瀹?key锛?"""

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

# Prioritize today's articles to ensure they get enriched first
pending.sort(key=lambda x: (0 if x['is_today'] else 1, x['link']))
print(f'Prioritized {sum(1 for p in pending if p["is_today"])} today articles to front of queue')

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


def generate_one(art):
    """Generate Chinese content for one article"""
    title_en = art['title_en']
    summary_en = art['summary_en']
    link = art['link']
    missing = art['missing']
    
    if not title_en and not summary_en:
        return link, {'cn_title': '', 'cn_summary': '', 'reading_highlight': ''}
    
    # 闃插尽閿欎綅锛氬鏋?summary 涓虹┖鎴栨槑鏄句笉鍖归厤锛岄檷绾т负浠呭熀浜庢爣棰樼敓鎴?    has_valid_summary = bool(summary_en) and len(summary_en) > 30
    
    prompt = f"""璇蜂负浠ヤ笅鑻辨枃鏂囩珷鐢熸垚涓枃鍐呭銆傝姹傚噯纭€佷笓涓氥€佺鍚堜腑鏂囬槄璇讳範鎯€?
{'娉ㄦ剰锛氬師鏂囨憳瑕佺己澶辨垨涓嶅彲闈狅紝璇蜂富瑕佹牴鎹爣棰樻帹鏂枃绔犲唴瀹瑰苟鐢熸垚銆? if not has_valid_summary else ''}

鍘熸枃鏍囬锛歿title_en}
鍘熸枃鎽樿锛歿summary_en}

璇蜂弗鏍兼寜浠ヤ笅鏍煎紡杈撳嚭锛堜笉瑕佹坊鍔犻澶栬鏄庯級锛?
銆愪腑鏂囨爣棰樸€?10-15瀛楋紝鍑嗙‘浼犺揪鏍稿績涓婚

銆愪腑鏂囨憳瑕併€?50-80瀛楋紝姒傛嫭鏂囩珷瑕佺偣

銆愰槄璇荤簿鍗庛€?300-500瀛楋紝缁撴瀯涓猴細
- 銆愭牳蹇冭鐐广€戞枃绔犵殑鏍稿績瑙傜偣鎴栫珛鍦?- 銆愬叧閿彂鐜般€戞敮鎾戣鐐圭殑鍏抽敭鏁版嵁鎴栦簨瀹?- 銆愯涓氭剰涔夈€戝 AI 琛屼笟鐨勫惎绀?- 銆愯鍔ㄥ缓璁€戠粰璇昏€呯殑鍏蜂綋寤鸿

璇█瑕佹眰锛氬彛璇寲銆佹湁娲炶鎰燂紝涓嶈绠€鍗曠炕璇戙€?"""
    
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
                
                if '銆愪腑鏂囨爣棰樸€? in result:
                    parts = result.split('銆愪腑鏂囨爣棰樸€?, 1)[1]
                    title_part = parts.split('銆?, 1)[0].strip()
                    cn_title = title_part.replace('銆?, '').strip()[:30]
                
                if '銆愪腑鏂囨憳瑕併€? in result:
                    parts = result.split('銆愪腑鏂囨憳瑕併€?, 1)[1]
                    summary_part = parts.split('銆?, 1)[0].strip()
                    cn_summary = summary_part.replace('銆?, '').strip()[:200]
                
                if '銆愰槄璇荤簿鍗庛€? in result:
                    hl_part = result.split('銆愰槄璇荤簿鍗庛€?, 1)[1].strip()
                    reading_highlight = hl_part[:1500]
                
                # Self-validation: check if cn_title relates to title_en
                if cn_title and title_en:
                    title_keywords = [w.lower() for w in title_en.replace('-', ' ').split() if len(w) > 4 and w.isalpha()]
                    cn_title_lower = cn_title.lower()
                    # Check if any English keyword appears in Chinese title (transliterated or not)
                    # Simple heuristic: if title_en has strong keywords, cn_title should at least mention related concepts
                    # This is a loose check; main defense is at the collector level
                    if title_keywords and not any(kw[:4] in cn_title_lower for kw in title_keywords[:3]):
                        # If cn_title seems completely unrelated, mark as suspicious but still use it
                        print(f"  鈿狅笍 Generated cn_title may be mismatched: {cn_title[:30]} vs {title_en[:40]}")
                
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
    
    with ThreadPoolExecutor(max_workers=2) as executor:
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
