# C-Fountain v1 渲染与导出规则

C-Fountain v1 是 PlotWeaver 基于 ScreenYAML v2.3 设计的中文剧本预览与文本导出规则。

ScreenYAML v2.3 是唯一数据源。前端中文剧本预览和 `.fountain` 文本导出都只是不同的渲染视图，不应反向改变 ScreenYAML 的结构。

## 1. 渲染原则

- 保留中文剧本阅读习惯。
- 不拆散 `performance` 复合表演块。
- 空字段动态跳过，不生成空括号。
- `needs_review` 只影响 UI 高亮，不默认进入导出正文。
- 导出文件尽量保持 Fountain-compatible，但不牺牲中文可读性。

## 2. 段落间距

中文预览和 C-Fountain 导出都应保持清晰留白：

- 场景标题前后各空一行。
- 每个 body block 之间空一行。
- 不同 scene 之间至少空两行。
- 不输出多余空括号，例如 `（）`。

## 3. 中文预览映射规则

### 3.1 Scene Header

ScreenYAML:

```yaml
index: 1
source_chapter_index: 2
camera_location: "外景"
setting: "春水街老王水产摊位前"
time_of_day: "傍晚"
```

中文预览：

```text
第 1 场 （第 2 章）
外景 / 春水街老王水产摊位前 / 傍晚
```

### 3.2 Environment

ScreenYAML:

```yaml
- type: "environment"
  text: "暴雨初歇，水泥路面坑洼处积着脏水。"
```

中文预览：

```text
（暴雨初歇，水泥路面坑洼处积着脏水。）
```

### 3.3 Action

ScreenYAML:

```yaml
- type: "action"
  character_name: "林辰"
  text: "俯身掀开塑料布，神色逐渐凝住。"
```

中文预览：

```text
林辰：（俯身掀开塑料布，神色逐渐凝住。）
```

### 3.4 Performance

ScreenYAML:

```yaml
- type: "performance"
  character_name: "王春花"
  pre_action: "刚烫完头，拎着钱包走近。"
  dialogue: "十块钱十块钱，五毛钱零头算了啊！"
  post_action: "从皮夹里掏出破旧的十元纸币，强行塞进店主手里。"
```

中文预览：

```text
王春花：（刚烫完头，拎着钱包走近。）十块钱十块钱，五毛钱零头算了啊！（从皮夹里掏出破旧的十元纸币，强行塞进店主手里。）
```

若 `pre_action` 和 `post_action` 为空：

```text
王春花：十块钱十块钱，五毛钱零头算了啊！
```

### 3.5 Transition

ScreenYAML:

```yaml
- type: "transition"
  text: "切至："
```

中文预览：

```text
切至：
```

## 4. C-Fountain v1 导出规则

### 4.1 Scene Header

导出公式：

```text
第 {scene_index} 场 （第 {source_chapter_index} 章）
{camera_location} / {setting} / {time_of_day}
```

示例：

```text
第 1 场 （第 2 章）
外景 / 春水街老王水产摊位前 / 傍晚
```

若 `camera_location` 是 `未知` 或为空，降级为：

```text
第 {scene_index} 场 （第 {source_chapter_index} 章）
场景 / {setting} / {time_of_day}
```

### 4.2 Environment

导出公式：

```text
（{text}）
```

### 4.3 Action

导出公式：

```text
{character_name}：（{text}）
```

### 4.4 Performance

导出公式：

```text
{character_name}：{pre_action_if_any}{dialogue}{post_action_if_any}
```

其中：

```text
pre_action_if_any = （{pre_action}）
post_action_if_any = （{post_action}）
```

如果动作字段为空，则跳过该部分。

示例：

```text
林辰：（避开飞溅的水滴。）这是什么？
```

```text
林辰：这是什么？
```

### 4.5 Transition

导出公式：

```text
> {text}
```

示例：

```text
> 切至：
```

`>` 是 Fountain 的右对齐转场提示符。C-Fountain v1 使用它增强与 Fountain 阅读器的兼容性。

## 5. needs_review 渲染规则

当 ScreenYAML 块包含：

```yaml
status: "needs_review"
review_note: "角色名与已有角色表无法唯一匹配。"
```

前端预览：

- 不把 `review_note` 插入剧本文本。
- 使用轻微警示背景或左侧提示线标记该块。
- 鼠标悬浮时显示 `review_note`。

C-Fountain 导出：

- 默认不导出 `status` 和 `review_note`。
- 若未来提供“包含 AI 标记”选项，可在正文前输出注释：

```text
# AI提示：角色名与已有角色表无法唯一匹配。
```

## 6. TypeScript 伪代码

```typescript
function wrapAction(text?: string): string {
  const value = text?.trim();
  return value ? `（${value}）` : "";
}

function renderPerformance(block: {
  character_name: string;
  pre_action?: string;
  dialogue: string;
  post_action?: string;
}): string {
  const pre = wrapAction(block.pre_action);
  const post = wrapAction(block.post_action);
  return `${block.character_name}：${pre}${block.dialogue.trim()}${post}`;
}
```
