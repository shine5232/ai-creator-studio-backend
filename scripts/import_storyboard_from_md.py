"""
从已有的 Markdown 脚本文件解析分镜数据，插入到 Storyboard + Shot 表。

用法:
    python -m scripts.import_storyboard_from_md <script_id> <md_file_path>

示例:
    python -m scripts.import_storyboard_from_md 1 "data/projects/1/scripts/铁手琴音孟买父亲的无声誓言_v2.md"
"""

import re
import sqlite3
import sys
from pathlib import Path


def parse_duration(time_range: str) -> float:
    """从时间范围字符串解析时长，如 '0-3s' → 3.0"""
    if not time_range:
        return 3.0
    m = re.match(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*s?", time_range)
    if m:
        return round(float(m.group(2)) - float(m.group(1)), 1)
    m = re.match(r"(\d+(?:\.\d+)?)\s*s", time_range)
    if m:
        return float(m.group(1))
    return 3.0


def parse_shots_from_md(md_text: str) -> list[dict]:
    """从 Markdown 表格格式的分镜脚本中解析出每个镜头的详细信息。"""
    shots = []

    # 匹配幕标题：### 第1幕：尘埃中的仰望（0-15s）
    act_pattern = re.compile(
        r"###\s*第(\d+)幕[：:]\s*(.+?)（(.+?)）"
    )

    # 匹配镜头标题：**镜头 1 | 0-3s | 孟买废料回收站**
    shot_header_pattern = re.compile(
        r"\*\*镜头\s*(\d+)\s*\|\s*([^\|]+?)\s*\|\s*(.+?)\*\*"
    )

    # 匹配表格行：| **镜头** | 特写 |
    field_pattern = re.compile(
        r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|"
    )

    lines = md_text.split("\n")
    current_act_number = 0
    current_act_name = ""
    current_act_time = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测幕标题
        act_match = act_pattern.match(line)
        if act_match:
            current_act_number = int(act_match.group(1))
            current_act_name = act_match.group(2).strip()
            current_act_time = act_match.group(3).strip()
            i += 1
            continue

        # 检测镜头标题
        shot_match = shot_header_pattern.match(line)
        if shot_match:
            shot_num = int(shot_match.group(1))
            shot_time = shot_match.group(2).strip()
            shot_location = shot_match.group(3).strip()

            # 收集后续表格行
            fields = {}
            j = i + 1
            # 跳过表头行 (| 项目 | 描述 |)
            while j < len(lines):
                row = lines[j].strip()
                if not row or not row.startswith("|"):
                    break
                field_match = field_pattern.match(row)
                if field_match:
                    key = field_match.group(1).strip()
                    val = field_match.group(2).strip()
                    if key != "项目":  # 跳过表头
                        fields[key] = val
                j += 1

            # 组装描述
            desc_parts = []
            if fields.get("人物"):
                desc_parts.append(f"人物: {fields['人物']}")
            if fields.get("环境"):
                desc_parts.append(f"环境: {fields['环境']}")
            if fields.get("事件"):
                desc_parts.append(f"事件: {fields['事件']}")
            if fields.get("台词"):
                desc_parts.append(f"台词: {fields['台词']}")
            description = "；".join(desc_parts) if desc_parts else f"镜头 {shot_num}"

            shots.append({
                "shot_number": shot_num,
                "act_number": current_act_number,
                "act_name": current_act_name,
                "act_time": current_act_time,
                "time_range": shot_time,
                "location": shot_location,
                "shot_type": fields.get("镜头", ""),
                "characters": fields.get("人物", ""),
                "environment": fields.get("环境", ""),
                "event": fields.get("事件", ""),
                "dialog": fields.get("台词", ""),
                "tone": fields.get("色调", ""),
                "mood": fields.get("氛围", ""),
                "description": description,
                "duration": parse_duration(shot_time),
            })
            i = j
            continue

        i += 1

    return shots


def main():
    if len(sys.argv) < 3:
        print("用法: python -m scripts.import_storyboard_from_md <script_id> <md_file_path>")
        sys.exit(1)

    script_id = int(sys.argv[1])
    md_path = Path(sys.argv[2])

    if not md_path.exists():
        print(f"文件不存在: {md_path}")
        sys.exit(1)

    # 解析 Markdown
    md_text = md_path.read_text(encoding="utf-8")
    shots = parse_shots_from_md(md_text)
    if not shots:
        print("未找到分镜数据")
        sys.exit(1)

    print(f"解析到 {len(shots)} 个镜头")

    # 连接 SQLite 数据库
    db_path = Path("data/openclaw.db")
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # 检查脚本是否存在
    cur.execute("SELECT id, project_id FROM scripts WHERE id = ?", (script_id,))
    row = cur.fetchone()
    if not row:
        print(f"脚本 ID {script_id} 不存在")
        conn.close()
        sys.exit(1)
    project_id = row[1]
    print(f"脚本 {script_id} 属于项目 {project_id}")

    # 检查是否已有 storyboard
    cur.execute("SELECT id FROM storyboards WHERE script_id = ?", (script_id,))
    existing = cur.fetchone()
    if existing:
        storyboard_id = existing[0]
        # 检查是否已有 shots
        cur.execute("SELECT COUNT(*) FROM shots WHERE storyboard_id = ?", (storyboard_id,))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"Storyboard {storyboard_id} 已存在 {count} 个镜头，跳过")
            conn.close()
            return
        print(f"Storyboard {storyboard_id} 已存在但没有镜头，将插入镜头")
    else:
        # 创建 storyboard
        total_duration = sum(s["duration"] for s in shots)
        cur.execute(
            "INSERT INTO storyboards (script_id, total_shots, total_duration, created_at, updated_at) "
            "VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (script_id, len(shots), int(total_duration)),
        )
        storyboard_id = cur.lastrowid
        print(f"创建 Storyboard ID: {storyboard_id}")

    # 插入 shots
    total_duration = 0
    for s in shots:
        total_duration += s["duration"]
        cur.execute(
            "INSERT INTO shots "
            "(storyboard_id, shot_number, act_name, time_range, shot_type, description, "
            "tone, mood, image_prompt, image_status, video_prompt, video_status, video_duration, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (
                storyboard_id,
                s["shot_number"],
                s["act_name"],
                s["time_range"],
                s["shot_type"],
                s["description"],
                s["tone"],
                s["mood"],
                None,  # image_prompt 为空
                "pending",
                None,  # video_prompt 为空
                "pending",
                s["duration"],
            ),
        )
        print(f"  镜头 {s['shot_number']}: {s['act_name']} | {s['time_range']} | {s['shot_type']} | {s['tone']} | {s['mood']}")

    # 更新 storyboard 总时长
    cur.execute(
        "UPDATE storyboards SET total_shots = ?, total_duration = ? WHERE id = ?",
        (len(shots), int(total_duration), storyboard_id),
    )

    conn.commit()
    conn.close()

    print(f"\n完成！共插入 {len(shots)} 个镜头到 Storyboard {storyboard_id}")


if __name__ == "__main__":
    main()
