#!/usr/bin/env python3
"""
HelloDaily 自动生成脚本
零 token 消耗，纯 API 调用
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path("/opt/HelloDaily")
CONTENT_DIR = REPO / "content"
README = REPO / "README.md"

# 语言 emoji 映射
LANG_EMOJI = {
    "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷",
    "Go": "🐹", "Rust": "🦀", "Java": "☕", "Kotlin": "🐘",
    "C": "🐅", "C++": "🐸", "C#": "🐉", "Ruby": "💎",
    "Swift": "🦉", "PHP": "🐘", "Scala": "🔥", "Dart": "🎯",
    "Shell": "🐚", "HTML": "🌐", "CSS": "🎨", "Lua": "🌙",
    "Haskell": "λ", "Elixir": "💧", "Perl": "🐪",
}

# 中文关键词检测
RE_CHINESE = re.compile(r"[\u4e00-\u9fff]")

# 无意义描述关键词（跳过这些项目）
MEANINGLESS_DESCS = [
    "a", "an", "the", "none", "no description", "project", "test",
    "demo", "example", "just for fun", "learning", "tutorial",
    "my first", "practice", "nothing", "update", "fix",
]


def run(cmd, timeout=30):
    """运行命令"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def translate(text):
    """Google 免费翻译：英文 → 中文"""
    if not text or len(text) < 5:
        return text
    if RE_CHINESE.search(text):
        return text  # 已经是中文
    try:
        q = urllib.parse.quote(text[:500])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
        out, code = run(["curl", "-s", url], timeout=10)
        if code == 0 and out:
            data = json.loads(out)
            parts = []
            for item in data[0]:
                if item[0]:
                    parts.append(item[0])
            result = "".join(parts)
            return result if result else text
    except Exception:
        pass
    return text


def is_valid_project(r):
    """判断项目是否适合推荐"""
    desc = (r.get("description") or "").strip().lower()
    name = r.get("full_name", "")
    stars = r.get("stargazers_count", 0)
    
    # 排除过少 stars
    if stars < 100:
        return False
    
    # 排除无意义描述
    if any(kw in desc for kw in MEANINGLESS_DESCS) and len(desc) < 20:
        return False
    
    # 排除企业级/过大的项目（太复杂不适合入门）
    if stars > 100000:
        # 太火的巨无霸项目，一般人用不上
        pass  # 还是保留，量大管饱
    
    return True


def get_next_number():
    """获取下一期的期数"""
    files = list(CONTENT_DIR.glob("HelloDaily*.md"))
    nums = []
    for f in files:
        m = re.search(r"HelloDaily(\d+)\.md", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def fetch_repos():
    """获取 GitHub 热门项目"""
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = (
        f"https://api.github.com/search/repositories"
        f"?q=created:>{since}&sort=stars&order=desc&per_page=50"
    )
    stdout, code = run(["curl", "-s", url], timeout=20)
    if code != 0:
        print(f"GitHub API 请求失败: {stdout}")
        return []
    try:
        data = json.loads(stdout)
        items = data.get("items", [])
        # 过滤有效项目
        valid = [r for r in items if is_valid_project(r)]
        print(f"获取 {len(items)} 个，筛选后 {len(valid)} 个有效项目")
        return valid
    except json.JSONDecodeError:
        return []


def format_periodical(repos, num):
    """格式化 markdown"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 按语言分组
    by_lang = {}
    for r in repos:
        lang = r.get("language") or "其他"
        if lang not in by_lang:
            by_lang[lang] = []
        by_lang[lang].append(r)
    
    # 按语言总 stars 排序
    sorted_langs = sorted(
        by_lang.items(),
        key=lambda x: sum(r["stargazers_count"] for r in x[1]),
        reverse=True
    )
    
    lines = []
    lines.append(f"# 《HelloDaily》第 {num:03d} 期")
    lines.append("> 兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！")
    lines.append("")
    lines.append('<p align="center">')
    lines.append('  <img src="https://raw.githubusercontent.com/521xueweihan/img_logo/master/logo/readme.gif"/>')
    lines.append("</p>")
    lines.append("")
    lines.append("## 内容")
    lines.append("> 以下为本期内容｜每天 9:00 更新")
    lines.append("")
    
    total = 0
    for lang, lang_repos in sorted_langs:
        if total >= 15:
            break
        emoji = LANG_EMOJI.get(lang, "📦")
        lines.append(f"### {emoji} {lang}")
        lines.append("")
        
        for i, r in enumerate(lang_repos[:3], 1):
            if total >= 15:
                break
            
            name = r["full_name"]
            url = r["html_url"]
            stars = r["stargazers_count"]
            desc = (r.get("description") or "").strip()
            
            # 翻译描述
            cn_desc = translate(desc) if desc else "暂无简介"
            
            # 限制描述长度
            if len(cn_desc) > 100:
                cn_desc = cn_desc[:97] + "..."
            
            lines.append(f"{i}. **[@{name}]({url})** ⭐{format_stars(stars)}")
            lines.append(f"   {cn_desc}")
            lines.append("")
            total += 1
    
    lines.append("---")
    lines.append(f"本期由 HelloDaily 自动生成 · {today}")
    lines.append("")
    
    return "\n".join(lines)


def format_stars(n):
    """格式化 stars 数"""
    if n >= 1000:
        return f"{n/1000:.1f}k" if n % 1000 else f"{n//1000}k"
    return str(n)


def update_readme(num):
    """更新 README 往期表格"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 生成往期表格
    files = sorted(CONTENT_DIR.glob("HelloDaily*.md"))
    rows = []
    row = []
    for f in files:
        m = re.search(r"HelloDaily(\d+)\.md", f.name)
        if m:
            link = f"[第 {int(m.group(1)):03d} 期](content/{f.name})"
            row.append(link)
            if len(row) == 5:
                rows.append(row)
                row = []
    if row:
        while len(row) < 5:
            row.append("")
        rows.append(row)
    
    # 生成表格 markdown
    table_lines = [
        "| :card_index: | :jack_o_lantern: | :beer: | :fish_cake: | :octocat: |",
        "| ------- | ----- | ------------ | ------ | --------- |"
    ]
    for r in rows:
        table_lines.append("| " + " | ".join(r) + " |")
    table = "\n".join(table_lines)
    
    # 获取 stars
    stars_badge = ""
    try:
        out, _ = run(["curl", "-s", "https://api.github.com/repos/shali10/HelloDaily"], timeout=10)
        if out:
            stars = json.loads(out).get("stargazers_count", 0)
            stars_badge = "![GitHub stars](https://img.shields.io/github/stars/shali10/HelloDaily?style=flat-square)"
    except:
        pass
    
    readme_content = f"""# HelloDaily

{stars_badge}
![GitHub license](https://img.shields.io/github/license/shali10/HelloDaily?style=flat-square)
![Periodicals](https://img.shields.io/badge/期数-{num:03d}-blue?style=flat-square)

> 每日开源精选，自动推送 GitHub 上有趣、入门级的项目。

## 最新一期

📅 **[《HelloDaily》第 {num:03d} 期](content/HelloDaily{num:03d}.md)** · {today}

## 往期

{table}

## 关于

每天 9:00 自动搜索 GitHub Trending + 热门项目，按语言分类生成 markdown 文件。

## 如何贡献

- 推荐项目：提交 [Issue](https://github.com/shali10/HelloDaily/issues/new?template=recommend.md)
- 提交 PR：参考 [CONTRIBUTING.md](CONTRIBUTING.md)

## 项目结构

```
HelloDaily/
├── content/              # 每期内容
├── templates/            # 模板文件
├── scripts/              # 自动化脚本
├── .github/              # GitHub 配置
├── README.md
├── CONTRIBUTING.md
└── LICENSE
---

本期由 HelloDaily 自动生成 · 每天 9:00 更新
"""
    README.write_text(readme_content, encoding="utf-8")


def main():
    print("== HelloDaily 生成器 ==")
    
    num = get_next_number()
    print(f"准备生成第 {num:03d} 期")
    
    print("拉取远程仓库...")
    os.chdir(REPO)
    run(["git", "pull", "--rebase"], timeout=20)
    
    print("获取 GitHub 热门项目...")
    repos = fetch_repos()
    if not repos:
        print("❌ 获取项目失败，退出")
        sys.exit(1)
    
    print("翻译描述并生成内容...")
    content = format_periodical(repos, num)
    filepath = CONTENT_DIR / f"HelloDaily{num:03d}.md"
    filepath.write_text(content, encoding="utf-8")
    print(f"已写入 {filepath.name}")
    
    print("更新 README...")
    update_readme(num)
    
    print("推送仓库...")
    run(["git", "add", "."], timeout=10)
    commit_out, code = run(["git", "commit", "-m", f"发布：《HelloDaily》第 {num:03d} 期"], timeout=10)
    print(commit_out)
    push_out, code = run(["git", "push", "origin", "main"], timeout=30)
    print(push_out)
    
    print(f"\n✅ 《HelloDaily》第 {num:03d} 期 已推送")
    print(f"https://github.com/shali10/HelloDaily/blob/main/content/HelloDaily{num:03d}.md")


if __name__ == "__main__":
    main()
