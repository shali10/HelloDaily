#!/usr/bin/env python3
"""
HelloDaily 自动生成脚本 v2
单次搜索 + 程序分类，保证多样性，min API 调用
"""
import json
import os
import random
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path


REPO = Path("/opt/HelloDaily")
CONTENT_DIR = REPO / "content"
README = REPO / "README.md"

# 从 git remote 提取 GitHub token
_GIT_REMOTE = None
_GITHUB_TOKEN = None


def get_token():
    global _GITHUB_TOKEN
    if _GITHUB_TOKEN:
        return _GITHUB_TOKEN
    try:
        out, _ = run(["git", "-C", str(REPO), "remote", "-v"])
        for line in out.split("\n"):
            if "github.com" in line and "fetch" in line:
                m = re.search(r"https://([^@]+)@github\.com", line)
                if m:
                    _GITHUB_TOKEN = m.group(1)
                    return _GITHUB_TOKEN
    except Exception:
        pass
    return None


RE_CHINESE = re.compile(r"[\u4e00-\u9fff]")

MEANINGLESS_DESCS = {
    "a", "an", "the", "none", "no description", "project", "test",
    "demo", "example", "just for fun", "learning", "tutorial",
    "my first", "practice", "nothing", "update", "fix",
}

# 关键词 → 分类映射（用于程序化分类）
CATEGORY_KEYWORDS = [
    ("🛠 开发工具", ["devtool", "debug", "ide", "compiler", "linter", "formatter", "plugin",
                      "extension", "sdk", "framework", "scaffold", "boilerplate", "template",
                      "monitoring", "logging", "testing", "ci/cd", "docker", "kubernetes",
                      "config", "dotfile", "package", "dependency", "build", "deploy"]),
    ("⚡ 效率提升", ["productivity", "automation", "workflow", "shortcut", "launcher",
                      "clipboard", "note", "todo", "timer", "pomodoro", "habit",
                      "manager", "organizer", "tracker", "alarm", "reminder",
                      "hotkey", "macro", "snippet", "template"]),
    ("🎨 视觉创意", ["visualization", "graphics", "animation", "glsl", "shader",
                      "svg", "canvas", "webgl", "three", "d3", "chart", "plot",
                      "diagram", "drawing", "pixel", "ascii", "font", "typography",
                      "color", "theme", "icon", "emoji", "image"]),
    ("🎮 游戏娱乐", ["game", "engine", "rpg", "fps", "puzzle", "retro", "emulator",
                      "minecraft", "chess", "card", "board", "simulator",
                      "gamedev", "godot", "unity", "unreal", "sprite"]),
    ("📚 学习资源", ["tutorial", "awesome-list", "cheatsheet", "education", "course",
                      "book", "ebook", "learn", "practice", "exercise",
                      "interview", "algorithm", "data-structure", "problem",
                      "roadmap", "guide", "handbook", "wiki"]),
    ("💻 命令行神器", ["cli", "terminal", "shell", "bash", "zsh", "fish", "tui",
                      "command", "alias", "pipe", "grep", "sed", "awk",
                      "tmux", "screen", "ssh", "httpie", "curl"]),
    ("📱 桌面/移动", ["desktop", "mobile", "app", "electron", "tauri", "flutter",
                      "react-native", "swiftui", "compose", "widget",
                      "cross-platform", "native", "ui", "spa"]),
    ("🌐 Web 前端", ["react", "vue", "angular", "svelte", "solidjs", "nextjs",
                      "nuxt", "astro", "css", "tailwind", "bootstrap",
                      "component", "design-system", "landing", "portfolio"]),
    ("🔧 数据处理", ["database", "sql", "nosql", "etl", "data-pipeline",
                      "analytics", "big-data", "spark", "hadoop", "pandas",
                      "dataframe", "csv", "excel", "spreadsheet", "json",
                      "api", "graphql", "rest", "grpc"]),
    ("🎯 有趣项目", ["fun", "art", "music", "creative", "generative", "procedural",
                      "blender", "3d", "vr", "ar", "iot", "hardware",
                      "raspberry", "arduino", "robot", "drone", "diy"]),
]

# AI 相关关键词（避免过度推荐）
AI_BLOCKLIST = {"llm", "gpt", "chatgpt", "openai", "langchain", "rag", "vector-db",
                "fine-tune", "prompt", "diffusion", "stable-diffusion", "qwen", "llama",
                "mistral", "gemini", "claude", "copilot", "codex"}


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def translate(text):
    if not text or len(text) < 5:
        return text
    if RE_CHINESE.search(text):
        return text
    try:
        q = urllib.parse.quote(text[:500])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
        out, code = run(["curl", "-s", url], timeout=10)
        if code == 0 and out:
            data = json.loads(out)
            parts = [item[0] for item in data[0] if item[0]]
            result = "".join(parts)
            return result if result else text
    except Exception:
        pass
    return text


def is_valid_project(r):
    desc = (r.get("description") or "").strip().lower()
    name = r.get("full_name", "")
    stars = r.get("stargazers_count", 0)

    if stars < 50 or stars > 50000:
        return False
    if any(kw in desc for kw in MEANINGLESS_DESCS) and len(desc) < 20:
        return False
    return True


def classify_project(r):
    """根据描述和 topics 分类"""
    desc = (r.get("description") or "").lower()
    topics = [t.lower() for t in r.get("topics", [])]
    lang = (r.get("language") or "").lower()
    text = f"{desc} {' '.join(topics)} {lang}"

    # AI 检测 - 如果太多 AI 特征，定为 AI 类但不完全排除
    ai_hits = sum(1 for kw in AI_BLOCKLIST if kw in text)
    if ai_hits >= 3:
        return None  # 纯 AI 项目跳过

    # 匹配分类关键词
    scores = []
    for cat_name, keywords in CATEGORY_KEYWORDS:
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores.append((score, cat_name))

    if scores:
        scores.sort(reverse=True)
        return scores[0][1]

    # 按语言兜底
    lang_cat_map = {
        "python": "🔧 数据处理",
        "javascript": "🌐 Web 前端",
        "typescript": "🌐 Web 前端",
        "go": "💻 命令行神器",
        "rust": "💻 命令行神器",
        "c": "🛠 开发工具",
        "c++": "🛠 开发工具",
        "java": "📱 桌面/移动",
        "kotlin": "📱 桌面/移动",
        "swift": "📱 桌面/移动",
        "dart": "📱 桌面/移动",
        "ruby": "⚡ 效率提升",
        "shell": "💻 命令行神器",
        "lua": "🎮 游戏娱乐",
    }
    return lang_cat_map.get(lang, None)


def get_next_number():
    files = list(CONTENT_DIR.glob("HelloDaily*.md"))
    nums = [int(f.stem.replace("HelloDaily", "")) for f in files if re.match(r"HelloDaily\d+\.md", f.name)]
    return max(nums) + 1 if nums else 1


def get_previous_projects(count=2):
    files = sorted(CONTENT_DIR.glob("HelloDaily*.md"))
    prev = set()
    for f in files[-count:]:
        content = f.read_text(encoding="utf-8")
        for m in re.finditer(r'\*\*\[([^\]]+)\]\([^)]+\)', content):
            prev.add(m.group(1))
    return prev


def fetch_repos():
    """单次大搜索 + 程序分类"""
    token = get_token()
    headers = ["-H", f"Authorization: token {token}"] if token else []

    since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    # 搜索：近期活跃、中等规模、非垄断的优质项目
    queries = [
        f"stars:100..5000 pushed:>{since}",
        f"stars:50..1000 pushed:>{since}",
    ]

    all_items = []
    seen = set()
    for q in queries:
        encoded_q = urllib.parse.quote(q)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page=60"
        cmd = ["curl", "-s"] + headers + [url]
        out, code = run(cmd, timeout=20)
        if code != 0 or not out:
            print(f"  API 请求失败: {out[:100]}")
            continue
        try:
            data = json.loads(out)
            for r in data.get("items", []):
                name = r["full_name"]
                if name not in seen and is_valid_project(r):
                    seen.add(name)
                    all_items.append(r)
        except json.JSONDecodeError:
            continue

    print(f"  API 获取 {len(seen)} 个有效项目")

    # 分类
    classified = {}
    uncategorized = []
    for r in all_items:
        cat = classify_project(r)
        if cat:
            if cat not in classified:
                classified[cat] = []
            if len(classified[cat]) < 5:
                classified[cat].append(r)
        else:
            uncategorized.append(r)
            if len(uncategorized) > 10:
                break

    # 确保每个分类至少有项目
    result = []
    for cat_name, _ in CATEGORY_KEYWORDS:
        repos = classified.get(cat_name, [])
        if repos:
            random.shuffle(repos)
            result.append((cat_name, repos[:3]))

    # 补充未分类的到有缺失的分类
    filled_cats = {n for n, _ in result}
    for cat_name, _ in CATEGORY_KEYWORDS:
        if cat_name not in filled_cats and uncategorized:
            result.append((cat_name, uncategorized[:2]))
            uncategorized = uncategorized[2:]

    random.shuffle(result)
    return result


def format_periodical(category_repos, num):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 《HelloDaily》第 {num:03d} 期")
    lines.append("> 用心发现 GitHub 上有趣的项目，不止于热门分类。")
    lines.append("")

    for cat_name, repos in category_repos:
        if not repos:
            continue
        lines.append(f"## {cat_name}")
        lines.append("")

        for i, r in enumerate(repos[:3], 1):
            name = r["full_name"]
            url = r["html_url"]
            stars = r["stargazers_count"]
            desc = (r.get("description") or "").strip()
            lang = r.get("language") or ""

            cn_desc = translate(desc) if desc else "暂无简介"
            if len(cn_desc) > 100:
                cn_desc = cn_desc[:97] + "..."

            lang_tag = f" `{lang}`" if lang else ""
            lines.append(f"{i}. **[{name}]({url})** ⭐{format_stars(stars)}{lang_tag}")
            lines.append(f"   {cn_desc}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"本期由 HelloDaily 自动生成 · {today}")
    return "\n".join(lines)


def format_stars(n):
    if n >= 1000:
        return f"{n/1000:.1f}k" if n % 1000 else f"{n//1000}k"
    return str(n)


def update_readme(num, cat_names=None):
    today = datetime.now().strftime("%Y-%m-%d")

    files = sorted(CONTENT_DIR.glob("HelloDaily*.md"))
    rows, row = [], []
    for f in files:
        m = re.match(r"HelloDaily(\d+)\.md", f.name)
        if m:
            link = f"[第 {int(m.group(1)):03d} 期](content/{f.name})"
            row.append(link)
            if len(row) == 5:
                rows.append(row); row = []
    if row:
        while len(row) < 5: row.append("")
        rows.append(row)

    table = "\n".join([
        "| :card_index: | :jack_o_lantern: | :beer: | :fish_cake: | :octocat: |",
        "| ------- | ----- | ------------ | ------ | --------- |"
    ] + ["| " + " | ".join(r) + " |" for r in rows])

    scope_line = ""
    if cat_names:
        short = " · ".join(cat_names[:6])
        scope_line = f"本期涵盖：{short} 等\n"

    readme_content = f"""# HelloDaily

![GitHub stars](https://img.shields.io/github/stars/shali10/HelloDaily?style=flat-square)
![GitHub license](https://img.shields.io/github/license/shali10/HelloDaily?style=flat-square)
![Periodicals](https://img.shields.io/badge/期数-{num:03d}-blue?style=flat-square)

> 每周一三五自动更新，精选 GitHub 上不同领域的开源项目。

## 最新一期

📅 **[《HelloDaily》第 {num:03d} 期](content/HelloDaily{num:03d}.md)** · {today}

{scope_line}## 往期

{table}

## 关于

每周一三五自动搜索 GitHub 开源项目，通过关键词匹配将项目归类到开发工具、效率提升、视觉创意、游戏、学习资源、命令行、桌面应用、Web 前端、数据处理、有趣项目等 10 个领域，避免单一刷 AI 或运维类项目。

## 项目结构

```
HelloDaily/
├── content/              # 每期内容
├── scripts/              # 自动化脚本
├── README.md
└── LICENSE
---

本期由 HelloDaily 自动生成 · 每期覆盖不同领域
"""
    README.write_text(readme_content, encoding="utf-8")


def main():
    print("== HelloDaily 生成器 v2 ==")

    num = get_next_number()
    print(f"准备生成第 {num:03d} 期")

    print("拉取远程仓库...")
    os.chdir(REPO)
    run(["git", "pull", "--rebase"], timeout=20)

    print("获取 GitHub 项目（认证搜索 + 程序分类）...")
    repos = fetch_repos()
    valid = [(n, r) for n, r in repos if r]
    if not valid:
        print("❌ 获取项目失败，退出")
        sys.exit(1)

    total = sum(len(r) for _, r in valid)
    print(f"共 {total} 个项目，{len(valid)} 个分类")

    # 去重
    prev = get_previous_projects(2)
    deduped = [(n, [r for r in rs if r["full_name"] not in prev]) for n, rs in valid]
    deduped = [(n, rs) for n, rs in deduped if rs]

    print("翻译描述并生成内容...")
    content = format_periodical(deduped, num)
    fp = CONTENT_DIR / f"HelloDaily{num:03d}.md"
    fp.write_text(content, encoding="utf-8")
    print(f"已写入 {fp.name}")

    print("更新 README...")
    update_readme(num, [n for n, _ in deduped])

    print("推送仓库...")
    run(["git", "add", "."], timeout=10)
    commit_out, code = run(["git", "commit", "-m", f"发布：《HelloDaily》第 {num:03d} 期"], timeout=10)
    print(commit_out)
    if "nothing to commit" in commit_out.lower():
        return
    push_out, code = run(["git", "push", "origin", "main"], timeout=30)
    print(push_out)

    print(f"\n✅ 《HelloDaily》第 {num:03d} 期 已推送")
    print(f"https://github.com/shali10/HelloDaily/blob/main/content/HelloDaily{num:03d}.md")


if __name__ == "__main__":
    main()