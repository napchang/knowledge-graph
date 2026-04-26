#!/usr/bin/env python3
"""
鏁版嵁涓€鑷存€ч獙璇佽剼鏈?姣忔鐢熸垚 graph-data.json 鍚庤嚜鍔ㄨ繍琛岋紝妫€鏌ヤ腑鏂囪鐩栫巼銆佸瓧娈靛畬鏁存€х瓑
澶辫触鏃惰繑鍥為潪闆堕€€鍑虹爜锛岃Е鍙?GitHub Actions 澶辫触閫氱煡
"""

import json, sys, random

def validate():
    with open('graph-data.json', 'r', encoding='utf-8') as f:
        gd = json.load(f)
    
    articles = [n for n in gd['nodes'] if n.get('type') == 'article']
    today_arts = [a for a in articles if a.get('is_today')]
    
    errors = []
    warnings = []
    
    # 1. 涓枃鏍囬瑕嗙洊鐜囨鏌?    if today_arts:
        with_cn_title = sum(1 for a in today_arts if a.get('cn_title'))
        coverage = with_cn_title / len(today_arts)
        print(f"[CHECK] 浠婃棩鏂囩珷涓枃鏍囬瑕嗙洊鐜? {with_cn_title}/{len(today_arts)} ({coverage:.1%})")
        if coverage < 0.75:
            errors.append(f"浠婃棩鏂囩珷涓枃鏍囬瑕嗙洊鐜囦粎 {coverage:.1%}锛屼綆浜?80% 闃堝€?)
    
    # 2. 闃呰绮惧崕瑕嗙洊鐜囨鏌?    if today_arts:
        with_hl = sum(1 for a in today_arts if a.get('reading_highlight'))
        hl_coverage = with_hl / len(today_arts)
        print(f"[CHECK] 浠婃棩鏂囩珷闃呰绮惧崕瑕嗙洊鐜? {with_hl}/{len(today_arts)} ({hl_coverage:.1%})")
        if hl_coverage < 0.75:
            errors.append(f"浠婃棩鏂囩珷闃呰绮惧崕瑕嗙洊鐜囦粎 {hl_coverage:.1%}锛屼綆浜?80% 闃堝€?)
    
    # 3. 瀛楁绫诲瀷妫€鏌?    bad_fields = 0
    for a in articles:
        for field in ['cn_title', 'cn_summary', 'reading_highlight']:
            val = a.get(field)
            if val is not None and not isinstance(val, str):
                bad_fields += 1
    if bad_fields:
        errors.append(f"鍙戠幇 {bad_fields} 涓潪瀛楃涓茬被鍨嬬殑瀛楁鍊?)
    else:
        print(f"[CHECK] 瀛楁绫诲瀷妫€鏌ラ€氳繃")
    
    # 4. 閿欓厤鍡呮帰锛氶殢鏈烘娊鏍锋鏌?highlight 涓庢爣棰樼浉鍏虫€?    sample = [a for a in articles if a.get('reading_highlight') and a.get('title_en')]
    if len(sample) >= 5:
        checked = random.sample(sample, 5)
        mismatches = 0
        for a in checked:
            hl = a['reading_highlight'].lower()
            title = a['title_en'].lower()
            # 绠€鍗曞惎鍙戝紡锛歨ighlight 涓簲璇ヨ嚦灏戝寘鍚爣棰樹腑鐨勬煇涓叧閿瘝
            title_words = [w for w in title.replace('-', ' ').split() if len(w) > 4]
            if title_words:
                match = any(w in hl for w in title_words[:3])
                if not match:
                    mismatches += 1
        print(f"[CHECK] 閿欓厤鍡呮帰: 鎶芥牱 5 绡囷紝鍙戠幇 {mismatches} 绡囧彲鑳介敊閰?)
        if mismatches >= 3:
            warnings.append(f"閿欓厤鍡呮帰鍙戠幇 {mismatches}/5 绡囧彲鑳介敊閰嶏紝寤鸿妫€鏌?cache")
    
    # 5. title_en 蹇呴』涓鸿嫳鏂囷紙鏃犱腑鏂囧瓧绗︼級
    bad_title_en = sum(1 for a in articles if a.get('title_en') and any('\u4e00' <= c <= '\u9fff' for c in a['title_en']))
    if bad_title_en:
        warnings.append(f"{bad_title_en} 绡囨枃绔犵殑 title_en 鍖呭惈涓枃瀛楃")
    else:
        print(f"[CHECK] title_en 璇█妫€鏌ラ€氳繃")
    
    # 6. 鍏ㄩ噺鏂囩珷涓枃瑕嗙洊鐜囩粺璁?    total_with_cn = sum(1 for a in articles if a.get('cn_title'))
    total_coverage = total_with_cn / len(articles) if articles else 1.0
    print(f"[CHECK] 鍏ㄩ噺鏂囩珷涓枃鏍囬瑕嗙洊鐜? {total_with_cn}/{len(articles)} ({total_coverage:.1%})")
    
    # 7. 鍏ㄩ噺闃呰绮惧崕瑕嗙洊鐜囩粺璁?    total_with_hl = sum(1 for a in articles if a.get('reading_highlight'))
    total_hl_coverage = total_with_hl / len(articles) if articles else 1.0
    print(f"[CHECK] 鍏ㄩ噺闃呰绮惧崕瑕嗙洊鐜? {total_with_hl}/{len(articles)} ({total_hl_coverage:.1%})")
    
    # 8. 閲嶅鏂囩珷妫€娴?    from collections import Counter
    links = [a.get('link', '') for a in articles if a.get('link')]
    dup_links = [link for link, count in Counter(links).items() if count > 1]
    if dup_links:
        errors.append(f"鍙戠幇 {len(dup_links)} 涓噸澶嶉摼鎺ョ殑鏂囩珷鑺傜偣")
    else:
        print(f"[CHECK] 閲嶅鏂囩珷妫€娴嬮€氳繃")
    
    # 9. 鏁版嵁閲忛闄嶆娴?    if len(articles) < 500:
        errors.append(f"鏂囩珷鎬绘暟浠?{len(articles)}锛屼弗閲嶄綆浜庡巻鍙叉按骞筹紙~1000+锛夛紝鍙兘鏁版嵁涓㈠け")
    else:
        print(f"[CHECK] 鏁版嵁閲忔娴嬮€氳繃: {len(articles)} 绡囨枃绔?)
    
    # 10. 浠婃棩鏂囩珷鏁伴噺寮傚父
    today_count = len(today_arts)
    if today_count == 0:
        warnings.append("浠婃棩鏂囩珷鏁伴噺涓?0锛岃妫€鏌ラ噰闆嗘祦绋?)
    elif today_count < 5:
        warnings.append(f"浠婃棩鏂囩珷浠?{today_count} 鏉★紝浣庝簬姝ｅ父姘村钩")
    else:
        print(f"[CHECK] 浠婃棩鏂囩珷鏁伴噺妫€娴嬮€氳繃: {today_count} 鏉?)
    
    # 11. title-summary 涓€鑷存€ф娴嬶紙闃插尽 feedparser 閿欎綅锛?    def check_title_summary_match(title, summary, min_overlap=0.2):
        if not title or not summary or len(summary) < 50:
            return True
        title_words = [w.strip('.,-:;!?').lower() for w in title.split() if len(w.strip('.,-:;!?')) >= 4]
        if not title_words:
            return True
        summary_lower = summary.lower()
        matches = sum(1 for w in title_words if w in summary_lower)
        return matches / len(title_words) >= min_overlap
    
    mismatch_count = sum(1 for a in articles if not check_title_summary_match(a.get('title_en', ''), a.get('summary', '')))
    mismatch_rate = mismatch_count / len(articles) if articles else 0
    print(f"[CHECK] title-summary 涓€鑷存€? {len(articles) - mismatch_count}/{len(articles)} 閫氳繃 ({1-mismatch_rate:.1%})")
    if mismatch_rate > 0.1:
        errors.append(f"title-summary 閿欎綅鐜?{mismatch_rate:.1%}锛屼弗閲嶈秴鏍囷紙闃堝€?10%锛夈€俧eedparser 鍙兘杩斿洖浜嗛敊浣嶆暟鎹紝璇锋鏌ラ噰闆嗗櫒銆?)
    elif mismatch_rate > 0.05:
        warnings.append(f"title-summary 閿欎綅鐜?{mismatch_rate:.1%}锛屽缓璁鏌?RSS 閲囬泦婧?)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"楠岃瘉缁撴灉: {len(errors)} 涓敊璇? {len(warnings)} 涓鍛?)
    
    for e in errors:
        try:
            print(f"  [FAIL] ERROR: {e}")
        except UnicodeEncodeError:
            print(f"  [FAIL] ERROR: {e.encode('ascii', 'replace').decode()}")
    for w in warnings:
        try:
            print(f"  [WARN] WARNING: {w}")
        except UnicodeEncodeError:
            print(f"  [WARN] WARNING: {w.encode('ascii', 'replace').decode()}")
    
    if not errors and not warnings:
        try:
            print("  [OK] 全部通过")
        except UnicodeEncodeError:
            print("  [OK] All passed")
    
    return len(errors) == 0

if __name__ == '__main__':
    ok = validate()
    sys.exit(0 if ok else 1)
