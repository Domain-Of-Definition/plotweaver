from app.chapter_parser import ParsedChapter
from app.models import Character


SYSTEM_PROMPT = """你是一个中文小说改编剧本的专业编剧助理。

你必须把小说章节改编成结构化 JSON 草稿，而不是最终 YAML。
后端会负责角色 ID 分配，所以你不要输出 character_id。

核心规则：
1. 按真实剧情顺序切分 scene。一个章节可以有多个 scene。
2. body 只允许四种 type：environment、action、performance、transition。
3. environment 表示环境、物件、声音、天气、空间氛围，没有具体人物主体。
4. action 表示某个具体人物的无台词行为，必须给 character_name。
5. performance 表示同一个人物的“说话前动作 + 台词 + 说话后动作”，必须给 character_name。
6. pre_action 和 post_action 可以是空字符串，不要为了填字段编造动作。
7. action.text、performance.pre_action、performance.post_action 必须去掉该人物自己的主语。
   例如 character_name 是“林辰”时，写“俯身掀开塑料布”，不要写“林辰俯身掀开塑料布”。
8. 电话、广播、对讲机里的对话不是“旁白”。如果能从上下文判断说话人，就填写真实说话人。
9. 场景描写不要错误归到某个人名下。没有明确人物执行主体时，用 environment。
10. 尽量保留原文中的有效场景信息、动作信息和关键对话，但可以删去重复心理描写和解释性水分。
11. 不要为了动作块强行创造“未知角色”。如果原文是“门被打开”“椅子被拉开”“杯子被放下”等没有明确执行人的被字句，优先输出 environment。
12. 如果被字句后文马上出现明确人物进入或执行动作，可以将后续明确动作归给该人物，但不要把“门被打开”单独写成“未知角色”的 action。

电话对白特别规则：
1. “接通电话、按下录音键、拿出手机、望着屏幕”等动作通常属于接电话的人。
2. “听筒传出：‘……’”“电话那头说：‘……’”“对方说：‘……’”里的引号内容属于电话另一端的人，不属于接电话的人。
3. 如果后文能出现电话另一端的身份或姓名，必须用该真实角色名；如果暂时未知，可使用“来电者”“电话那头的男人”等临时角色名。
4. 接电话者的回应，例如“认识。”，才属于接电话者。
5. “对方挂断电话”属于电话另一端角色的 post_action，不要写成接电话者的动作。
6. 电话中的每一句引号对白都要保留，不要漏掉威胁、要求、地址、条件等关键信息。

电话场景示例拆分：
- 接电话者：（拿出手机，接通电话，按下录音键）
- 电话另一端角色：林先生是吗，请问您认识郑小明同学吗？
- 接电话者：认识。
- 电话另一端角色：哦，小明现在在我手上，请戴好钱包，来颜家巷沧水桥认领，谢谢合作。（挂断电话）
- 接电话者：（望着屏幕上的号码，一时间没有反应过来）

你必须只输出一个合法 JSON 对象，不要输出 markdown，不要解释。
"""


def build_chapter_prompt(
    chapter: ParsedChapter,
    existing_characters: list[Character],
    previous_summary: str = "",
) -> str:
    registry_text = format_character_registry(existing_characters)
    summary_text = previous_summary.strip() or "无。"

    return f"""请将当前小说章节转换为 LLMChapterDraft JSON。

输出 JSON 顶层结构必须是：
{{
  "chapter_index": 1,
  "chapter_title": "章节标题",
  "summary": "本章 200 字以内摘要",
  "scenes": [
    {{
      "source_hint": "原文追溯提示",
      "title": "场景短标题",
      "camera_location": "内景/外景/内外景/特殊/未知",
      "setting": "具体地点",
      "time_of_day": "时间，如 傍晚/雨夜/凌晨三点/未知",
      "characters_present": ["角色中文名"],
      "new_characters": [
        {{
          "name": "角色正式展示名",
          "aliases": ["别名或称呼"],
          "description": "角色简短描述",
          "role_type": "protagonist/antagonist/supporting/minor/unknown"
        }}
      ],
      "body": [
        {{"type": "environment", "text": "没有具体人物主体的环境或声画描写"}},
        {{"type": "action", "character_name": "角色名", "text": "去掉主语的人物动作"}},
        {{"type": "performance", "character_name": "角色名", "pre_action": "去掉主语的说话前动作，可为空", "dialogue": "台词", "post_action": "去掉主语的说话后动作，可为空"}},
        {{"type": "transition", "text": "切至："}}
      ]
    }}
  ]
}}

已知角色注册表：
{registry_text}

上一章摘要：
{summary_text}

当前章节：
章节序号：{chapter.index}
章节标题：{chapter.title}

章节正文：
{chapter.text}
"""


def format_character_registry(characters: list[Character]) -> str:
    if not characters:
        return "无。"

    lines: list[str] = []
    for character in characters:
        aliases = "、".join(character.aliases) if character.aliases else "无"
        lines.append(
            f"- {character.name}；别名：{aliases}；"
            f"描述：{character.description or '无'}；类型：{character.role_type}"
        )
    return "\n".join(lines)
