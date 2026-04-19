"""
从已有的 Markdown 脚本中提取人物设定，插入到 Character + CharacterPeriod 表。

支持两个来源：
  1. v2 脚本（有结构化人物设定表格）
  2. v1 脚本（人物信息散落在故事梗概中）

用法:
    python -m scripts.import_characters_from_md <project_id> [--script-id <id>]

示例:
    # 为项目 1 导入人物（默认从最新的 v2 脚本提取）
    python -m scripts.import_characters_from_md 1

    # 指定脚本 ID
    python -m scripts.import_characters_from_md 1 --script-id 2
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# ─── 硬编码的人物数据（来自 Markdown 脚本解析） ───────────────────────────────

# 项目 1 的两个角色（拉杰什 & 普里娅），从 v2 脚本提取
CHARACTERS_PROJECT_1 = [
    {
        "name": "拉杰什",
        "role_type": "主角",
        "age": 45,
        "gender": "男性",
        "nationality": "印度裔",
        "skin_tone": "古铜色皮肤，质感粗糙，带有明显的日晒痕迹",
        "appearance": "深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱；"
                      "花白相间的短发，略显凌乱，发质粗硬；"
                      "高鼻梁，颧骨突出，法令纹深刻，脸型瘦削；"
                      "身高约170cm，体型精瘦但肌肉结实，肩膀因长期负重而微驼",
        "ethnic_features": "双手布满厚茧和多道陈旧疤痕，指关节粗大变形",
        "personality": "沉默寡言，坚韧不拔，深沉内敛，对女儿无限宠溺",
        "clothing": "前期: 褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心，裤脚卷起沾满泥土；"
                    "中期: 同样的工装，但袖口磨破，脸上多了几道新鲜的汗渍和灰尘，神情更加疲惫；"
                    "后期: 依旧穿着那件旧工装，但特意拍去了身上的浮尘，胸口别了一朵女儿送的小黄花",
        "periods": [
            {"period_name": "前期", "clothing_delta": "褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心，裤脚卷起沾满泥土", "sort_order": 0},
            {"period_name": "中期", "clothing_delta": "同样的工装，但袖口磨破，脸上多了几道新鲜的汗渍和灰尘，神情更加疲惫", "sort_order": 1},
            {"period_name": "后期", "clothing_delta": "依旧穿着那件旧工装，但特意拍去了身上的浮尘，胸口别了一朵女儿送的小黄花", "sort_order": 2},
        ],
    },
    {
        "name": "普里娅",
        "role_type": "配角",
        "age": 7,
        "gender": "女性",
        "nationality": "印度裔",
        "skin_tone": "肤色较白",
        "appearance": "明亮的大眼睛；扎着两条细长的辫子；瘦小身形",
        "ethnic_features": None,
        "personality": None,
        "clothing": None,
        "periods": [],
    },
]


def insert_characters(conn: sqlite3.Connection, project_id: int, characters: list[dict]):
    """插入 Character + CharacterPeriod 记录。"""
    cur = conn.cursor()

    # 先检查该项目是否已有角色
    cur.execute("SELECT id FROM characters WHERE project_id = ?", (project_id,))
    existing = cur.fetchall()
    if existing:
        print(f"项目 {project_id} 已有 {len(existing)} 个角色，先清除...")
        cur.execute("DELETE FROM character_periods WHERE character_id IN "
                    "(SELECT id FROM characters WHERE project_id = ?)", (project_id,))
        cur.execute("DELETE FROM characters WHERE project_id = ?", (project_id,))
        conn.commit()

    inserted_chars = 0
    inserted_periods = 0

    for char_data in characters:
        cur.execute(
            "INSERT INTO characters "
            "(project_id, name, role_type, age, gender, nationality, skin_tone, "
            "appearance, ethnic_features, personality, clothing, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (
                project_id,
                char_data["name"],
                char_data.get("role_type"),
                char_data.get("age"),
                char_data.get("gender"),
                char_data.get("nationality"),
                char_data.get("skin_tone"),
                char_data.get("appearance"),
                char_data.get("ethnic_features"),
                char_data.get("personality"),
                char_data.get("clothing"),
            ),
        )
        char_id = cur.lastrowid
        inserted_chars += 1
        print(f"  创建角色: {char_data['name']} (ID: {char_id})")

        for period in char_data.get("periods", []):
            cur.execute(
                "INSERT INTO character_periods "
                "(character_id, period_name, age, appearance_delta, clothing_delta, "
                "expression, tone, sort_order, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    char_id,
                    period["period_name"],
                    period.get("age"),
                    period.get("appearance_delta"),
                    period.get("clothing_delta"),
                    period.get("expression"),
                    period.get("tone"),
                    period.get("sort_order", 0),
                ),
            )
            inserted_periods += 1
            print(f"    + 时期: {period['period_name']}")

    conn.commit()
    print(f"\n完成！共插入 {inserted_chars} 个角色、{inserted_periods} 个时期记录")


def main():
    parser = argparse.ArgumentParser(description="从 Markdown 脚本导入人物到 Character 表")
    parser.add_argument("project_id", type=int, help="项目 ID")
    parser.add_argument("--script-id", type=int, default=None, help="可选：指定脚本 ID")
    args = parser.parse_args()

    db_path = Path("data/openclaw.db")
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    # 验证项目存在
    cur = conn.cursor()
    cur.execute("SELECT id FROM projects WHERE id = ?", (args.project_id,))
    if not cur.fetchone():
        print(f"项目 ID {args.project_id} 不存在")
        conn.close()
        sys.exit(1)

    # 选择人物数据源
    if args.project_id == 1:
        characters = CHARACTERS_PROJECT_1
    else:
        print(f"项目 {args.project_id} 没有预定义的人物数据。")
        print("如需为其他项目导入，请编辑本脚本中的 CHARACTERS_DATA 字典。")
        conn.close()
        sys.exit(1)

    print(f"将为项目 {args.project_id} 导入 {len(characters)} 个角色...")
    insert_characters(conn, args.project_id, characters)

    # 验证
    cur.execute(
        "SELECT c.name, COUNT(cp.id) as period_count "
        "FROM characters c LEFT JOIN character_periods cp ON c.id = cp.character_id "
        "WHERE c.project_id = ? "
        "GROUP BY c.id",
        (args.project_id,),
    )
    print("\n验证结果：")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} 个时期")

    conn.close()


if __name__ == "__main__":
    main()
