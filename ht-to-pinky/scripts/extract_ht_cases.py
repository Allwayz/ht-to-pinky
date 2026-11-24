#!/usr/bin/env python3
"""Validate HomeTrans test_case.md files and print their scenarios as JSON.

This only checks structure and flags steps Pinky cannot judge. It does not
rewrite cases.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCENARIO_RE = re.compile(r"^### Scenario\s+(\d+-\d+):\s*(.*?)\s*$")
TAG_RE = re.compile(r"\[(P\d+|推导|SKIP(?::[^\]]*)?)\]")
ACTION_RE = re.compile(r"^[-*]\s*动作：\s*(.*)$")
EXPECTED_RE = re.compile(r"^[-*]\s*预期结果：\s*(.*)$")
POINTS_RE = re.compile(r"^[-*]\s*测试点：\s*$")
TP_RE = re.compile(r"^[-*]\s*(TP-\d+(?:（[^）]+）)?)\s*[:：]\s*(.*)$")
COND_RE = re.compile(r"^[-*]\s*(条件\d+)\s*[:：]\s*(.*)$")
HALFWIDTH_FIELD_RE = re.compile(r"^[-*]\s*(动作|预期结果|测试点|前置条件):")

CAMERA_RE = re.compile(
    r"相机|摄像头|二维码|扫码|手电筒|QR\s*code|QR code|flashlight|flash light",
    re.IGNORECASE,
)
MEASURE_RE = re.compile(r"撑高|高度|省略|滚动|像素|单行")
VAGUE_RE = re.compile(r"^(点击|点|按)(继续|确定|提交|下一步|完成)$")
NON_ACTION_RE = re.compile(r"使.{0,12}返回|模拟|构造|注入")
DELETION_RE = re.compile(
    r"注销|销户|"
    r"(?:删除|移除)(?:账号|帐户|账户|用户)|"
    r"(?:账号|帐户|账户|用户)(?:删除|注销)|"
    r"(?:删除|移除)(?:文件|内容|照片|图片|邮件|消息|会话|聊天记录|文件夹|目录|笔记|备忘录|联系人|日历|事件|录音|视频|文档)|"
    r"内容删除|永久删除|批量删除|"
    r"清空(?:回收站|垃圾箱|废纸篓)|"
    r"(?:移入|移到|移至)回收站|"
    r"点击「删除」|点击删除|点「删除」|点删除|"
    r"delete\s+account|remove\s+account|deactivate\s+account|close\s+account|"
    r"delete\s+(?:the\s+|this\s+|my\s+)?(?:file|files|content|photo|photos|message|folder|note)s?|"
    r"move\s+to\s+trash",
    re.IGNORECASE,
)


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            files.extend(sorted(path.rglob("test_case.md")))
        elif path.is_file():
            files.append(path)
        else:
            raise SystemExit(f"找不到文件或目录: {raw}")
    if not files:
        raise SystemExit("没有找到 test_case.md")
    return files


def split_actions(action: str) -> list[str]:
    return [part.strip() for part in action.split(" -> ") if part.strip()]


def parse_scenario(header: str, body: list[str], scenario_id: str) -> dict:
    title = TAG_RE.sub("", header).strip()
    tags = TAG_RE.findall(header)
    skip = next((tag for tag in tags if tag.startswith("SKIP")), None)
    action = ""
    expected = ""
    preconditions: list[str] = []
    points: list[dict] = []
    seen_points = False
    errors: list[str] = []

    for line in body:
        stripped = line.strip()
        if not stripped:
            continue
        if HALFWIDTH_FIELD_RE.match(stripped):
            errors.append(f"Scenario {scenario_id} 使用了半角冒号")
        if match := ACTION_RE.match(stripped):
            action = match.group(1).strip()
        elif match := EXPECTED_RE.match(stripped):
            expected = match.group(1).strip()
        elif POINTS_RE.match(stripped):
            seen_points = True
        elif match := TP_RE.match(stripped):
            points.append({"id": match.group(1), "text": match.group(2).strip()})
        elif match := COND_RE.match(stripped):
            preconditions.append(match.group(2).strip())

    if not action:
        errors.append(f"Scenario {scenario_id} 缺少动作")
    if not expected:
        errors.append(f"Scenario {scenario_id} 缺少预期结果")
    if not seen_points or not points:
        errors.append(f"Scenario {scenario_id} 缺少测试点")

    actions = split_actions(action)
    blob = "\n".join([title, action, expected, *(point["text"] for point in points)])
    flags: list[str] = []
    if skip:
        flags.append("skip")
    if CAMERA_RE.search(blob):
        flags.append("camera")
    if DELETION_RE.search(blob):
        flags.append("deletion")
    if MEASURE_RE.search(blob):
        flags.append("measurement")
    if any(VAGUE_RE.match(step) for step in actions):
        flags.append("vague_control")
    if any(NON_ACTION_RE.search(step) for step in actions):
        flags.append("not_a_screen_action")

    return {
        "id": scenario_id,
        "title": title,
        "tags": tags,
        "skip": skip,
        "preconditions": preconditions,
        "action": action,
        "actions": actions,
        "expected": expected,
        "test_points": points,
        "flags": flags,
        "errors": errors,
    }


def parse_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    errors: list[str] = []
    if "## Scenario List" not in text:
        errors.append("缺少 ## Scenario List")
    if "### Scenario " not in text:
        errors.append("没有 ### Scenario")

    scenarios: list[dict] = []
    current_header: tuple[str, str] | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current_header, body
        if current_header is None:
            return
        scenario_id, header = current_header
        scenarios.append(parse_scenario(header, body, scenario_id))
        current_header = None
        body = []

    for line in lines:
        match = SCENARIO_RE.match(line.strip())
        if match:
            flush()
            current_header = (match.group(1), match.group(2))
            continue
        if current_header and line.startswith("## "):
            flush()
            continue
        if current_header:
            body.append(line)
    flush()

    for scenario in scenarios:
        errors.extend(scenario["errors"])

    return {
        "file": str(path),
        "title": title,
        "valid": not errors,
        "errors": errors,
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="提取并校验 HomeTrans test_case.md")
    parser.add_argument("paths", nargs="+", help="test_case.md 文件或包含它们的目录")
    args = parser.parse_args()

    files = collect_files(args.paths)
    reports = [parse_file(path) for path in files]
    json.dump(reports, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if any(not report["valid"] for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
