#!/usr/bin/env python3
"""
数据一致性验证脚本
每次生成 graph-data.json 后自动运行，检查中文覆盖率、字段完整性等
失败时返回非零退出码，触发 GitHub Actions 失败通知
"""

import json, sys, random

def validate():
    with open('graph-data.json', 'r', encoding='utf-8') as f:
        gd = json.load(f)
    
    articles = [n for n in gd['nodes'] if n.get('type') == 'article']
    today_arts = [a for a in articles if a.get('is_today')]
    
    errors = []
    warnings = []
    
    # 1. 中文标题覆盖率检查
    if today_arts:
        with_cn_title = sum(1 for a in today_arts if a.get('cn_title'))
        coverage = with_cn_title / len(today_arts)
        print(f"[CHECK] 今日文章中文标题覆盖率: {with_cn_title}/{len(today_arts)} ({coverage:.1%})")
        if coverage < 0.8:
            errors.append(f"今日文章中文标题覆盖率仅 {coverage:.1%}，低于 80% 阈值")
    
    # 2. 阅读精华覆盖率检查
    if today_arts:
        with_hl = sum(1 for a in today_arts if a.get('reading_highlight'))
        hl_coverage = with_hl / len(today_arts)
        print(f"[CHECK] 今日文章阅读精华覆盖率: {with_hl}/{len(today_arts)} ({hl_coverage:.1%})")
        if hl_coverage < 0.8:
            errors.append(f"今日文章阅读精华覆盖率仅 {hl_coverage:.1%}，低于 80% 阈值")
    
    # 3. 字段类型检查
    bad_fields = 0
    for a in articles:
        for field in ['cn_title', 'cn_summary', 'reading_highlight']:
            val = a.get(field)
            if val is not None and not isinstance(val, str):
                bad_fields += 1
    if bad_fields:
        errors.append(f"发现 {bad_fields} 个非字符串类型的字段值")
    else:
        print(f"[CHECK] 字段类型检查通过")
    
    # 4. 错配嗅探：随机抽样检查 highlight 与标题相关性
    sample = [a for a in articles if a.get('reading_highlight') and a.get('title_en')]
    if len(sample) >= 5:
        checked = random.sample(sample, 5)
        mismatches = 0
        for a in checked:
            hl = a['reading_highlight'].lower()
            title = a['title_en'].lower()
            # 简单启发式：highlight 中应该至少包含标题中的某个关键词
            title_words = [w for w in title.replace('-', ' ').split() if len(w) > 4]
            if title_words:
                match = any(w in hl for w in title_words[:3])
                if not match:
                    mismatches += 1
        print(f"[CHECK] 错配嗅探: 抽样 5 篇，发现 {mismatches} 篇可能错配")
        if mismatches >= 3:
            warnings.append(f"错配嗅探发现 {mismatches}/5 篇可能错配，建议检查 cache")
    
    # 5. title_en 必须为英文（无中文字符）
    bad_title_en = sum(1 for a in articles if a.get('title_en') and any('\u4e00' <= c <= '\u9fff' for c in a['title_en']))
    if bad_title_en:
        warnings.append(f"{bad_title_en} 篇文章的 title_en 包含中文字符")
    else:
        print(f"[CHECK] title_en 语言检查通过")
    
    # 6. 全量文章中文覆盖率统计
    total_with_cn = sum(1 for a in articles if a.get('cn_title'))
    total_coverage = total_with_cn / len(articles) if articles else 1.0
    print(f"[CHECK] 全量文章中文标题覆盖率: {total_with_cn}/{len(articles)} ({total_coverage:.1%})")
    
    # 7. 全量阅读精华覆盖率统计
    total_with_hl = sum(1 for a in articles if a.get('reading_highlight'))
    total_hl_coverage = total_with_hl / len(articles) if articles else 1.0
    print(f"[CHECK] 全量阅读精华覆盖率: {total_with_hl}/{len(articles)} ({total_hl_coverage:.1%})")
    
    # 8. 重复文章检测
    from collections import Counter
    links = [a.get('link', '') for a in articles if a.get('link')]
    dup_links = [link for link, count in Counter(links).items() if count > 1]
    if dup_links:
        errors.append(f"发现 {len(dup_links)} 个重复链接的文章节点")
    else:
        print(f"[CHECK] 重复文章检测通过")
    
    # 9. 数据量骤降检测
    if len(articles) < 500:
        errors.append(f"文章总数仅 {len(articles)}，严重低于历史水平（~1000+），可能数据丢失")
    else:
        print(f"[CHECK] 数据量检测通过: {len(articles)} 篇文章")
    
    # 10. 今日文章数量异常
    today_count = len(today_arts)
    if today_count == 0:
        warnings.append("今日文章数量为 0，请检查采集流程")
    elif today_count < 5:
        warnings.append(f"今日文章仅 {today_count} 条，低于正常水平")
    else:
        print(f"[CHECK] 今日文章数量检测通过: {today_count} 条")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"验证结果: {len(errors)} 个错误, {len(warnings)} 个警告")
    
    for e in errors:
        print(f"  ❌ ERROR: {e}")
    for w in warnings:
        print(f"  ⚠️  WARNING: {w}")
    
    if not errors and not warnings:
        print("  ✅ 全部通过")
    
    return len(errors) == 0

if __name__ == '__main__':
    ok = validate()
    sys.exit(0 if ok else 1)
