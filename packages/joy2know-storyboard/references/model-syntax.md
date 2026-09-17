本文由 `@SKILL.md` 第七节路由到此，只在遇到「要按某模型写提示词」时读取。本文件是配置，不是规范说明——改模型语法只动这里，不要动 SKILL.md。

# 各视频模型提示词语法对照（配置表）

每个模型一段。写提示词时只复制对应 `[模型]` 下的**结构模板**，把 `<...>` 替换成 `shots/manifest.json` 的真实值。

字段约定：`<主体>` 角色/物体；`<场景>` 环境；`<动作>` 行为；`<运镜>` 取 `@references/shot-language.md` 术语；`<时长>` ≤ 该模型 `max_duration`；`<首帧>` 首帧图路径。

---

## [Seedance]（字节）
- **max_duration：** 10s（单次生成；更长需多镜拼接）
- **结构模板：**
  ```
  <主体> in <场景>, <动作>. Camera: <运镜>. Shot size: <景别>. Duration: <时长>s.
  Style: <风格尾缀>. First frame reference: <首帧路径>.
  ```
- **特殊约束：** 中文提示词可用，但运镜/景别建议保留英文术语；支持「尾帧参考」可加 `End frame: <路径>`。
- **示例：**
  ```
  A girl in pale blue chunky knit wool sweater standing on a rainy station platform, looking up.
  Camera: slow push-in. Shot size: close-up. Duration: 4s.
  Style: cinematic, soft light. First frame reference: shots/shot_001_firstframe.png.
  ```

## [Runway]（Gen-3/Gen-4）
- **max_duration：** 10s（Gen-4 支持更长，按账号额度）
- **结构模板：**
  ```
  <镜头描述>, <运镜>, <时长>. <风格尾缀>.
  ```
- **特殊约束：** 偏好「一句话电影感」写法，动作放前、运镜紧跟；支持 `Motion Brush` 局部运动（不在文本提示词内）。
- **示例：**
  ```
  A close-up of a girl in a pale blue chunky knit wool sweater, slow push-in, 4 seconds, cinematic soft light.
  ```

## [Kling]（可灵）
- **max_duration：** 10s（专业版可更长）
- **结构模板：**
  ```
  主体：<主体>
  场景：<场景>
  动作：<动作>
  运镜：<运镜>
  时长：<时长>秒
  风格：<风格尾缀>
  ```
- **特殊约束：** 中文提示词原生友好；支持「图像参考」单独上传首帧，文本里可省首帧路径。
- **示例：**
  ```
  主体：穿浅蓝粗针织羊毛衫的女孩
  场景：雨天火车站台
  动作：抬头望向列车
  运镜：缓慢推近
  时长：4秒
  风格：电影感、柔光
  ```

## [Sora]（OpenAI）
- **max_duration：** 20s（当前上限，随版本变动，以官网为准）
- **结构模板：**
  ```
  <主体> <动作> in <场景>. <运镜>. The shot lasts <时长> seconds. <风格尾缀>.
  ```
- **特殊约束：** 自然语言长句友好，但实体描述要具体；不支持显式首帧路径字段，靠首帧图另行上传。
- **示例：**
  ```
  A girl wearing a pale blue chunky knit wool sweater looks up at a rainy station platform.
  Slow push-in. The shot lasts 4 seconds. Cinematic, soft light.
  ```

## [Pika]（补充）
- **max_duration：** 6s（Pika 1.5/2.0，以官网为准）
- **结构模板：** `<动作>, <运镜>, <时长>s, <风格尾缀>`
- **特殊约束：** 句子短、强调动作与运动；支持 `Pikaffects` 特效词。

## [Vidu]（补充）
- **max_duration：** 8s（以官网为准）
- **结构模板：** `<主体> <动作> <场景>，<运镜>，<时长>秒，<风格尾缀>`
- **特殊约束：** 中文友好，支持「参考图」单独上传。

---

# 时长上限速查（写提示词前先对这里）

| 模型 | max_duration | 备注 |
|---|---|---|
| Seedance | 10s | 更长需多镜拼接 |
| Runway | 10s | Gen-4 视额度 |
| Kling | 10s | 专业版可更长 |
| Sora | 20s | 随版本变动 |
| Pika | 6s | 以官网为准 |
| Vidu | 8s | 以官网为准 |

> 上限会随版本变化。本表为初版快照；若用户说某模型已上调，以用户给的为准并在提示词里标注「时长上限按用户提供值」。
