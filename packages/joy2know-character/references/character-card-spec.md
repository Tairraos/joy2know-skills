本文由 `@SKILL.md` 第七节路由到此，只在「要落盘一张角色卡」或「不确定某个字段怎么填」时读取。两种格式等价，按用户工具链选一种，不要混用。

# 角色卡字段规范（Character Card Spec）

## 一、字段清单

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 角色代号，英文小写，用于文件名 `char_<name>.yaml` |
| `art_style` | 建议 | 画风，如 赛璐璐 / 厚涂 / 像素 / 写实 |
| `seed` | 建议 | 可复现随机种子，固定后长相更稳 |
| `weights` | 可选 | 生成权重，如 `character: 1.0`、`style: 0.8` |
| `locked_anchors` | 是 | 连续性锁：每条「颜色+材质+物体」最小短语，逐字进提示词 |
| `state_excluded` | 建议 | 不上锁、每镜单独写的状态：expression / pose / wet 等 |
| `ref_images` | 可选 | 参考图路径列表，用于校准锚点 |
| `variant` | 可选 | 换造型时独立块，另起一把锁（见 SKILL 规则 4） |

> 字段「够用但不啰嗦」：太少锁不住一致性，太多每次生成超长且互相干扰。必填两项（`name` + `locked_anchors`）是底线。

## 二、YAML 落盘格式

```yaml
name: lina
art_style: 赛璐璐动画
seed: 42817
weights:
  character: 1.0
  style: 0.8
locked_anchors:
  - pale blue chunky knit wool sweater
  - round black framed glasses
  - shoulder-length ash brown hair
state_excluded:
  - expression
  - pose
  - wet / damaged
ref_images:
  - ./refs/lina_front.png
  - ./refs/lina_side.png
```

## 三、Markdown 落盘格式

```markdown
# 角色卡 · Lina

- 代号：lina
- 画风：赛璐璐动画
- 种子：42817
- 权重：character 1.0 / style 0.8

## 连续性锁（逐字进提示词）
- pale blue chunky knit wool sweater
- round black framed glasses
- shoulder-length ash brown hair

## 不上锁（每镜单独写）
- expression（表情）
- pose（姿势）
- wet / damaged（湿身/破损）

## 参考图
- ./refs/lina_front.png
- ./refs/lina_side.png
```

## 四、完整示例（含换造型 variant）

```yaml
name: lina
art_style: 赛璐璐动画
seed: 42817
locked_anchors:
  - shoulder-length ash brown hair
  - round black framed glasses
state_excluded: [expression, pose]
ref_images: [./refs/lina_front.png]

variant:
  name: lina_battle
  locked_anchors:
    - matte black tactical vest
    - thigh-length charcoal combat coat
  state_excluded: [expression, pose, damaged]
```

> 日常与战斗是两套固定外观 → 两个 `locked_anchors` 块，互不串味。这正对应 SKILL 规则 4「一个角色一把锁，换造型另起一把」。

## 五、落盘约定

- 文件名：`char_<name>.yaml` 或 `char_<name>.md`，放项目内 `characters/` 目录。
- 多角色场景：每人一个文件，拼装时各读各的卡。
- 校验：写卡后确认 `locked_anchors` 每条都是最小名词短语、无句号、无动作/状态/数量。
