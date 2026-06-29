#!/usr/bin/env python3
"""
自动更新 README.md 的往期列表
用法: python3 scripts/update_readme.py
"""
import re
import glob
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content"
README_FILE = REPO_ROOT / "README.md"

def get_periodicals():
    """获取所有期数文件，按期数排序"""
    files = []
    for f in CONTENT_DIR.glob("HelloDaily*.md"):
        # 提取期数
        match = re.search(r'HelloDaily(\d+)\.md', f.name)
        if match:
            num = int(match.group(1))
            files.append((num, f))
    files.sort(key=lambda x: x[0])
    return files

def generate_table(files):
    """生成往期表格（5列）"""
    if not files:
        return ""
    
    # 表头
    cols = [":card_index:", ":jack_o_lantern:", ":beer:", ":fish_cake:", ":"]
    
    rows = []
    row = []
    for i, (num, f) in enumerate(files):
        link = f"[第 {num:03d} 期](content/HelloDaily{num:03d}.md)"
        row.append(link)
        
        if len(row) == 5:
            rows.append(row)
            row = []
    
    # 处理最后一行
    if row:
        while len(row) < 5:
            row.append("")
        rows.append(row)
    
    # 生成 markdown 表格
    lines = []
    # 表头
    lines.append("| " + " | ".join(cols[:5]) + " |")
    lines.append("| " + " | ".join(["-------"] * 5) + " |")
    # 数据行
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)

def update_readme():
    """更新 README.md 中的往期部分"""
    files = get_periodicals()
    
    if not files:
        print("没有找到期数文件")
        return
    
    # 最新一期
    latest_num, latest_file = files[-1]
    
    # 读取最新一期的标题和简介
    content = latest_file.read_text(encoding='utf-8')
    
    # 生成往期表格
    table = generate_table(files)
    
    # 读取当前 README
    readme = README_FILE.read_text(encoding='utf-8')
    
    # 更新最新一期链接
    latest_link = f"📅 **[《HelloDaily》第 {latest_num:03d} 期](content/HelloDaily{latest_num:03d}.md)** · {latest_file.stat().st_mtime}"
    
    # 替换最新一期部分
    readme = re.sub(
        r'📅 \*\*.*?\*\* · \d{4}-\d{2}-\d{2}',
        latest_link,
        readme
    )
    
    # 替换往期表格
    # 找到 ## 往期 和 ## 关于 之间的内容
    pattern = r'(## 往期\n).*?(?=\n## 关于)'
    replacement = f"## 往期\n\n{table}\n"
    readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)
    
    # 写回
    README_FILE.write_text(readme, encoding='utf-8')
    print(f"已更新 README.md，当前共 {len(files)} 期")

if __name__ == "__main__":
    update_readme()
