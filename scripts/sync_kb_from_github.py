#!/usr/bin/env python3
"""
浠?GitHub 鍚屾瀹屾暣鐨?geo-knowledge-base/ 鏁版嵁鍒版湰鍦?鐢ㄩ€旓細褰撴湰鍦版暟鎹笉瀹屾暣鏃讹紝鎭㈠涓?GitHub 涓€鑷寸殑鐘舵€?
鐢ㄦ硶锛?    python scripts/sync_kb_from_github.py

娉ㄦ剰锛?    - 杩欎細瑕嗙洊鏈湴 geo-knowledge-base/ 涓殑鏂囦欢
    - 涓嶄細鍒犻櫎鏈湴鐙湁鐨勬枃浠讹紙濡傛湁闇€瑕佽鎵嬪姩娓呯悊锛?    - 鍚屾鍚庝粛闇€杩愯 update_kb.py / gen_graph_data.py 绛夌敓鎴愯剼鏈?"""

import os
import subprocess
import sys

def run(cmd, cwd=None):
    """杩愯 shell 鍛戒护骞惰繑鍥炶緭鍑?""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 鍛戒护澶辫触: {cmd}")
        print(f"        {result.stderr.strip()}")
        return None
    return result.stdout.strip()

def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kb_dir = os.path.join(repo_dir, 'geo-knowledge-base')
    
    print("=" * 60)
    print("鐭ヨ瘑搴撴暟鎹悓姝ュ伐鍏?)
    print("=" * 60)
    
    # 妫€鏌ュ綋鍓?geo-knowledge-base/ 鏂囦欢鏁伴噺
    local_files = []
    for root, dirs, files in os.walk(kb_dir):
        for f in files:
            if f.endswith('.md') and f != 'README.md':
                local_files.append(os.path.join(root, f))
    print(f"\n鏈湴 geo-knowledge-base/: {len(local_files)} 涓?markdown 鏂囦欢")
    
    # 妫€鏌ヨ繙绋嬬姸鎬?    print("\n[1/3] 鑾峰彇杩滅▼浠撳簱淇℃伅...")
    fetch_result = run("git fetch origin", cwd=repo_dir)
    if fetch_result is None:
        print("鑾峰彇杩滅▼淇℃伅澶辫触锛岃妫€鏌ョ綉缁滆繛鎺?)
        sys.exit(1)
    
    # 鑾峰彇杩滅▼鏂囦欢鍒楄〃
    print("[2/3] 鑾峰彇杩滅▼ geo-knowledge-base/ 鏂囦欢鍒楄〃...")
    remote_files_raw = run("git ls-tree -r origin/main --name-only geo-knowledge-base/", cwd=repo_dir)
    if remote_files_raw is None:
        print("鑾峰彇杩滅▼鏂囦欢鍒楄〃澶辫触")
        sys.exit(1)
    
    remote_files = [f for f in remote_files_raw.split('\n') if f.endswith('.md') and 'README' not in f]
    print(f"杩滅▼ geo-knowledge-base/: {len(remote_files)} 涓?markdown 鏂囦欢")
    
    # 璁＄畻宸紓
    local_set = set(os.path.relpath(f, repo_dir).replace('\\', '/') for f in local_files)
    remote_set = set(remote_files)
    
    missing = remote_set - local_set
    extra = local_set - remote_set
    
    if missing:
        print(f"\n  鏈湴缂哄け: {len(missing)} 涓枃浠?)
    if extra:
        print(f"  鏈湴澶氫綑: {len(extra)} 涓枃浠?)
    
    if not missing and not extra:
        print("\n鉁?鏈湴鏁版嵁宸蹭笌杩滅▼鍚屾锛屾棤闇€鎿嶄綔")
        return
    
    # 璇㈤棶纭
    print(f"\n[3/3] 鍗冲皢浠庤繙绋嬫鍑?geo-knowledge-base/ 鏂囦欢...")
    response = input("纭鎵ц鍚屾? (yes/no): ")
    if response.lower() not in ('yes', 'y'):
        print("宸插彇娑?)
        return
    
    # 妫€鍑鸿繙绋嬫枃浠?    print("\n姝ｅ湪鍚屾...")
    checkout_result = run("git checkout origin/main -- geo-knowledge-base/", cwd=repo_dir)
    if checkout_result is None:
        print("鍚屾澶辫触")
        sys.exit(1)
    
    # 楠岃瘉
    new_local_files = []
    for root, dirs, files in os.walk(kb_dir):
        for f in files:
            if f.endswith('.md') and f != 'README.md':
                new_local_files.append(os.path.join(root, f))
    
    print(f"\n鉁?鍚屾瀹屾垚锛佹湰鍦?geo-knowledge-base/: {len(new_local_files)} 涓枃浠?)
    print("\n鎻愰啋锛氬悓姝ュ悗濡傞渶閲嶆柊鐢熸垚鍥捐氨鏁版嵁锛岃鍦ㄥ畬鏁存暟鎹幆澧冧笅杩愯锛?)
    print("  python scripts/gen_graph_data.py")
    print("  python scripts/gen_today_graph.py")

if __name__ == '__main__':
    main()
