# ScreenYAML v2.3 Schema 规范

ScreenYAML v2.3 是 PlotWeaver 的结构化剧本交换格式，用于将 3 个章节以上的中文小说文本转换为可编辑、可校验、可预览的剧本初稿。

本版本的核心原则是：大模型负责语义理解和剧本草稿生成，后端负责确定性的角色 ID 对齐、字段归一化、Schema 校验和 YAML 序列化。

## 1. 设计目标

- 支持多章节小说按章处理、按场景流式输出。
- 保留小说到剧本的来源追溯信息。
- 区分环境描写、人物动作、人物台词和转场。
- 适配中文小说常见的“动作 + 台词 + 动作”复合表达。
- 避免正文块 UUID 等对本系统运行价值不高的冗余字段。
- 由后端掌握角色 ID 主权，降低大模型跨章节乱配 ID 的风险。

## 2. LLM Draft 与最终 ScreenYAML 的边界

系统内部建议分为两层数据：

1. `LLMSceneDraft`
   - 由大模型输出。
   - 可以包含角色名、别名、场景标题、环境、动作、台词等语义草稿。
   - 不信任其中的 `character_id`。

2. `ScreenYAML`
   - 由后端归一化后生成。
   - 后端根据角色注册表分配和修正 `character_id`。
   - 最终输出给前端、下载文件和 Schema 校验的都是此结构。

## 3. 完整 YAML 示例

```yaml
meta:
  title: "暗夜无声"
  author: "原著作者"
  version: "2.3.0"
  language: "zh-CN"
  source_chapters:
    - index: 1
      title: "第一章：暴雨将至"
    - index: 2
      title: "第二章：鱼档的秘密"

characters:
  - id: "char_001"
    name: "林辰"
    aliases:
      - "林老师"
      - "老林"
    description: "宏景市心理顾问，冷静敏锐，习惯在沉默中观察细节。"
    role_type: "protagonist"

  - id: "char_002"
    name: "王春花"
    aliases:
      - "春花姐"
    description: "春水街水产店老板娘，刚烫完头，精明市侩，嗓门很大。"
    role_type: "supporting"

scenes:
  - index: 1
    source_chapter_index: 2
    source_hint: "水产店讨价还价至广播响起片段"
    title: "春水街水产店"
    camera_location: "外景"
    setting: "春水街老王水产摊位前"
    time_of_day: "傍晚"
    characters_present:
      - "char_001"
      - "char_002"
    body:
      - type: "environment"
        text: "暴雨初歇，水泥路面坑洼处积着脏水。霓虹灯牌在水洼里泛着破碎的光，一条鲫鱼在塑料盆里剧烈打挺。"

      - type: "performance"
        character_id: "char_002"
        character_name: "王春花"
        pre_action: "刚烫完头，拎着钱包走近，盯着盆里的鲫鱼。"
        dialogue: "十块钱十块钱，五毛钱零头算了啊！"
        post_action: "从皮夹里掏出破旧的十元纸币，强行塞进店主手里。"

      - type: "action"
        character_id: "char_001"
        character_name: "林辰"
        text: "避开飞溅的水滴，目光落在案板下露出的一角塑料布上。"

      - type: "transition"
        text: "切至："
```

## 4. 顶层字段

### `meta`

剧本元数据。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `title` | string | 是 | 剧本或小说标题。无法识别时可使用上传文件名。 |
| `author` | string | 否 | 原著作者或编剧名，未知时可为空字符串。 |
| `version` | string | 是 | ScreenYAML 版本，当前为 `2.3.0`。 |
| `language` | string | 是 | 文本语言，中文小说默认 `zh-CN`。 |
| `source_chapters` | array | 是 | 输入小说章节列表。 |

### `source_chapters[]`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `index` | integer | 是 | 原小说章节序号，从 1 开始。 |
| `title` | string | 是 | 原小说章节标题。 |

### `characters`

全局角色注册表。角色 ID 由后端统一分配和维护，大模型只能提供角色识别线索。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 稳定角色 ID，例如 `char_001`。 |
| `name` | string | 是 | 角色正式中文名或最适合展示的称呼。 |
| `aliases` | array[string] | 是 | 小说中出现过的别名、称呼或代称。无别名时为空数组。 |
| `description` | string | 是 | 角色简短描述。 |
| `role_type` | string | 是 | 角色类型，建议值：`protagonist`、`antagonist`、`supporting`、`minor`、`unknown`。 |

### `scenes`

扁平化场景数组。系统不强制使用“幕”结构，因为按章节流式转换时，扁平场景更稳定，也更容易连续编号。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `index` | integer | 是 | 全剧连续场景序号，从 1 开始。 |
| `source_chapter_index` | integer | 是 | 对应原小说章节序号。 |
| `source_hint` | string | 否 | 原文追溯提示，例如“水产店讨价还价片段”。 |
| `title` | string | 是 | 场景短标题。 |
| `camera_location` | string | 是 | 镜头空间，建议值：`内景`、`外景`、`内外景`、`特殊`、`未知`。 |
| `setting` | string | 是 | 场景地点。 |
| `time_of_day` | string | 是 | 场景时间。允许弹性字符串，例如 `傍晚`、`雨夜`、`凌晨三点`。 |
| `characters_present` | array[string] | 是 | 本场出现角色 ID。最终值建议由后端根据正文块自动汇总。 |
| `body` | array | 是 | 场景正文块，按时间顺序排列。 |

## 5. Body Block 类型

`body` 中的每个块必须属于以下四类之一。

### 5.1 `environment`

环境块。用于描写空间、天气、声音、光线、物件、氛围等，没有明确人物执行主体。

```yaml
- type: "environment"
  text: "街灯在积水里晃动，远处传来断续的广播声。"
```

约束：

- 不包含 `character_id`。
- 不包含 `character_name`。
- 不写成某个人的动作。

### 5.2 `action`

动作块。用于描写某个角色没有台词的行为。

```yaml
- type: "action"
  character_id: "char_001"
  character_name: "林辰"
  text: "俯身掀开塑料布，神色逐渐凝住。"
```

约束：

- 必须包含 `character_id` 和 `character_name`。
- `text` 应去掉角色自己的主语。
- 不应写成 `林辰俯身掀开塑料布`，应写成 `俯身掀开塑料布`。

### 5.3 `performance`

表演块。用于表达同一角色的“说话前动作 + 台词 + 说话后动作”。

```yaml
- type: "performance"
  character_id: "char_002"
  character_name: "王春花"
  pre_action: "刚烫完头，拎着钱包走近。"
  dialogue: "十块钱十块钱，五毛钱零头算了啊！"
  post_action: "从皮夹里掏出破旧的十元纸币，强行塞进店主手里。"
```

约束：

- 必须包含 `character_id` 和 `character_name`。
- `dialogue` 必须是角色说出的内容。
- `pre_action` 和 `post_action` 可以为空字符串。
- `pre_action` 与 `post_action` 应去掉角色自己的主语。
- 当一句台词附近有同一角色的动作时，优先合并成 `performance`。

### 5.4 `transition`

转场块。用于表达视听切换、场景跳转或剧本转场提示。

```yaml
- type: "transition"
  text: "切至："
```

约束：

- 可选使用。
- 不应滥用。普通段落切换不一定需要转场块。

## 6. 异常标记

正常块不需要写 `status`。

当后端无法可靠修复某个角色或字段冲突时，可以给相关块增加：

```yaml
status: "needs_review"
review_note: "角色名与已有角色表无法唯一匹配，请人工核对。"
```

前端可据此高亮该行，让作者快速定位需要打磨的内容。

## 7. 角色归一化规则

后端 `normalizer.py` 负责角色归一化。

规则建议：

1. 优先信任自然语言角色名 `character_name`。
2. 使用 `name` 和 `aliases` 匹配已有角色注册表。
3. 若唯一匹配成功，使用已有 `character_id`。
4. 若未匹配到，创建新角色 ID。
5. 若出现多重匹配或 ID 与名字冲突，保留可读文本，标记 `needs_review`。
6. 最终 YAML 中的 `character_id` 必须来自后端归一化结果。

## 8. 流式输出策略

系统采用块状流式，而不是 token 级 JSON 流式。

后端处理流程：

1. 解析上传小说并识别章节，要求至少 3 章。
2. 按章节顺序调用大模型。
3. 大模型返回完整的场景草稿 JSON。
4. 后端用 Pydantic 进行结构校验。
5. 后端用 normalizer 进行角色 ID 对齐、动作去主语和字段兜底。
6. 后端将校验后的完整场景通过 SSE 推送到前端。
7. 全部完成后序列化为最终 ScreenYAML。

建议 SSE 事件：

| 事件 | 说明 |
| --- | --- |
| `progress` | 当前进度，例如已完成章节数、场景数。 |
| `chapter_started` | 某章节开始处理。 |
| `scene_completed` | 一个完整场景通过校验并可追加显示。 |
| `validation_result` | YAML 或场景校验结果。 |
| `final_yaml` | 最终完整 YAML。 |
| `error` | 转换、解析、模型调用或校验错误。 |
| `done` | 流结束。 |

## 9. 设计原因总结

### 扁平 `scenes`

小说天然按章节推进，而比赛项目需要快速稳定地按章流式转换。扁平场景数组比“幕-场”结构更适合增量输出和连续编号。

### `performance` 表演块

中文小说经常把动作、台词和后续动作写在同一叙事单元内。`performance` 可以自然表达：

```text
人物名：（说话前动作）台词（说话后动作）
```

这比强行拆成多个 `action` 和 `dialogue` 块更符合中文剧本阅读体验。

### 中文剧本场景头

ScreenYAML 的场景字段渲染为中文剧本时，建议使用两行场景头：

```text
第 {scene_index} 场 （第 {source_chapter_index} 章）
{camera_location} / {setting} / {time_of_day}
```

这样既能保留全剧连续场次，也能追溯到原小说章节。

### `environment` 与 `action` 分离

环境描写没有人物主体，人物动作有明确执行者。分开后，前端预览可以清楚区分：

```text
（雨声渐密，街灯闪烁。）
林辰：（俯身掀开塑料布。）
```

### 后端掌握角色 ID

大模型适合理解语义，不适合维护跨章节稳定 ID。后端统一分配 `character_id`，可以避免同一角色在不同章节被映射成不同 ID。

### 正常块不写 `status`

只有异常块才写 `status: needs_review`，可以减少 YAML 噪音，让作者更容易阅读和编辑。
