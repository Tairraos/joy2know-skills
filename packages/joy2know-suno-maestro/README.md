# Suno 音乐大师（joy2know-suno-maestro）

> 把「一段想法」炼成能直接粘进 Suno 的三段提示词包。

## 他解决什么问题

Suno 的输入是「标题 + Style + 歌词」三段——写好就能出歌，写不好就白跑一次：

- Style 里不先锁语言口音，生成的歌开口就漂、方言直接破音；
- 歌词没标段落与重复位置，结构跑、该重复的副歌被改写；
- 想要纯器乐或循环 BGM，却被人声幻觉与淡出毁了素材；Style 里明明写好的东西被 Variety 悄悄改掉。

他站在**粘贴之前**动手：把想法炼成三段结构化文本（Style 九字段锁 + 带段落标签的歌词），
跑一遍结构校验，再附上粘贴前要点对的界面设置——包括那个最容易被忽略的「Variety 归 0」。

## 三条底线

1. **只产出提示词文本。** 不生成音频、不调用任何生成接口、不带账号与密钥；粘贴生成是用户自己在
   Suno 里的动作。AI 音乐有随机性——他提高命中率，不承诺效果。
2. **人声锁写在 Style 第一字段。** 有人声锁语言口音、器乐写 `Instrumental, No vocals`——两形态不许混写，
   这是生成跑偏的第一原因。
3. **结构校验由脚本算。** 校验器在 `skills/joy2know-musician/scripts/suno_check.py`，
   FAIL 修到零才交付，WARN 逐条给处理说明；觉得判定不对，先回技能规则核对，不临场发明第三种口径。

## 擅长的体裁

**治愈系中文歌**为默认落点（有画面感、带人生哲理，接受面最广）；**粤语歌**有完整的词汇锁 +
协音字 + 声调补偿方案，防撕裂防破音，其他方言（客家 / 闽南 / 潮州 / 四川 / 上海 / 东北话）按同一套适配；
**纯器乐与循环 BGM** 另有写法（压制人声幻觉、锁死 BPM、首尾同源）。流行、City Pop 等其他曲风按同一套九字段适配。

## 包内容

```
joy2know-suno-maestro/
├── .codebuddy-plugin/plugin.json            核心配置
├── agents/joy2know-suno-maestro.md          角色定义（系统提示词）
├── avatars/expert.png                       头像 512×512（由构建注入）
├── skills/joy2know-musician/                内置技能（方法论与校验器，由构建注入）
│   ├── SKILL.md                             四层分清 / 判定路由 / 核心规则 / 交付格式
│   ├── references/
│   │   ├── suno-syntax.md                   Suno 语法细节
│   │   ├── model-and-controls.md            模型与控件（Variety 行为、Style Persona）
│   │   ├── healing-style.md                 治愈文风内核
│   │   ├── cantonese-lock.md                粤语词汇锁与协音
│   │   └── game-bgm-loop.md                 游戏循环 BGM 写法
│   └── scripts/
│       └── suno_check.py                    结构校验器（含方言自检）
└── README.md
```

**方法论主体在 `skills/joy2know-musician/`，与独立上架的技能包同源。** 角色定义只规定流程与验收标准，
不重复技能内容——避免同一份规则两处维护导致版本漂移。

> **形态说明**：上面的目录树是**构建后所得包的形态**。仓库里的**源包**只有
> `.codebuddy-plugin/plugin.json`、`agents/joy2know-suno-maestro.md`、`skills.json` 与 `README.md` ——
> `avatars/` 由构建从仓库根 `avatars/joy2know-suno-maestro.png` 注入；`skills/` 由构建按 `skills.json`
> 声明的名单，从 `packages/<技能名>/` 复制**唯一真源**（本包内不存副本）。

## 怎么用

装上之后直接提问即可，不需要点名模式。

| 你说 | 他做 |
|---|---|
| 给我写一首能粘进 Suno 的歌 | 五问走默认值 → 三段提示词包 + 界面动作 |
| 写一首深夜便利店主题的粤语歌 | 粤语词汇锁 → 防破音指令 → 方言自检 → 脚本校验 → 交付 |
| 做一段游戏里的循环 BGM | 器乐路径：No vocals + 锁 BPM + 首尾同源 → 脚本校验 → 交付 |
| 这份提示词帮我检查一下再粘 | 跑结构校验器，FAIL 修零、WARN 逐条说明 |
| 我什么都还没想好 | 全默认治愈中文歌直接产出，替你定的项逐条写在「假设与待替换」 |

## 版本

1.0.1 · 作者：晓得乐

## 署名

晓得乐 · joy2know
