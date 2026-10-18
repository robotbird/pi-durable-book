#!/usr/bin/env python3
"""校验书中全部本地相对链接的有效性。在工作区根目录运行：python3 scripts/validate_links.py"""
import re, os, glob, sys

# 工作区根：取第一个参数；否则从 skill 目录向上找（含 README.md 与 book/ 的目录）；再退回默认路径
DEFAULT = "/Users/robotbird/Works/yepeng/pibook/pidurable"
if len(sys.argv) > 1:
    d = sys.argv[1]
else:
    d = os.path.dirname(os.path.abspath(__file__))
    while not (os.path.isfile(os.path.join(d, "README.md")) and os.path.isdir(os.path.join(d, "book"))):
        parent = os.path.dirname(d)
        if parent == d:
            d = DEFAULT
            break
        d = parent
if not (os.path.isfile(os.path.join(d, "README.md")) and os.path.isdir(os.path.join(d, "book"))):
    sys.exit(f"无效的工作区根：{d}")
os.chdir(d)
bad, total = 0, 0
files = glob.glob("book/**/*.md", recursive=True) + ["README.md", "SUMMARY.md"]
for md in files:
    base = os.path.dirname(md)
    for m in re.finditer(r"\]\(([^)h][^)]*?)\)", open(md).read()):
        total += 1
        if not os.path.exists(os.path.normpath(os.path.join(base, m.group(1)))):
            bad += 1
            print(f"  BAD: {md} -> {m.group(1)}")
print(f"本地链接 {total} 个, 失效 {bad} 个")
sys.exit(1 if bad else 0)
