# 生成工具把提示词藏在图的哪里

> 这份文档解决一件事：**用户说「提示词丢了」时，去哪儿找、能不能找回来。**
> 很多生成工具默认把提示词与全部参数**写进图片文件本身**，不需要旁挂文件。找对了位置，几千张图的历史提示词是现成的。

---

## 一、PNG 的三种文本块（先搞清容器，否则一半的图读不出来）

PNG 规范从 1996 年起就允许在像素数据之外放任意键值对文本。三种块，**只认第一种会漏掉很多图**：

| 块类型 | 编码 | 是否压缩 | 典型使用者 |
|---|---|---|---|
| `tEXt` | Latin-1，明文 | 无 | Automatic1111 的 `parameters` |
| `zTXt` | 关键字明文、值用 zlib 压缩 | **有** | **ComfyUI 的大 JSON 经常落在这里** |
| `iTXt` | UTF-8，压缩标志可选 | 可选 | XMP、部分工具、含中文/非拉丁字符的元数据 |

**要点：**
- `zTXt` 的关键字是明文、值是 deflate 压缩流 —— 不解压只能看到关键字名，看不到内容。Python 标准库 `zlib` 即可解，脚本已处理。
- `iTXt` 在关键字后依次是「压缩标志（1 字节）+ 压缩方法（1 字节）+ 语言标记 + `\0` + 翻译后关键字 + `\0` + 正文」，跳过这两段才能拿到正文，**多字节解析错位会读出乱码**。
- PNG 没有 EXIF —— 这是个流传很广的误解。PNG 用文本块，JPEG/WebP 才走 EXIF。

---

## 二、各工具落点总表

| 工具 | 容器 / 块 | 关键字（keyword） | 内容形态 |
|---|---|---|---|
| **ComfyUI** | PNG `tEXt` 或 `zTXt` | `prompt`、`workflow` | 两个 JSON |
| **Automatic1111 / Forge** | PNG `tEXt` | `parameters` | 一段纯文本 |
| **InvokeAI** | PNG 文本块 | `invokeai_metadata`、`sd-metadata` | JSON |
| **Fooocus / NovelAI** | PNG 文本块 | `Comment` | JSON |
| **Midjourney** | **EXIF `description`** | — | 提示词文本 |
| DALL·E / Firefly | 不含提示词 | — | 只写来源与溯源信息（如 C2PA 清单） |

**这张表决定的事：** 只有第一列的 ComfyUI / A1111 系是「提示词随图走」的主力；Midjourney 那些走了 EXIF，是另一套解析路径（见第五节）。

---

## 三、ComfyUI：两个 JSON，取哪个、怎么取

ComfyUI 的默认输出节点会往图里塞**两个** JSON：

| 关键字 | 是什么 | 用途 |
|---|---|---|
| `prompt` | **API 执行图**：节点 id → 类型 + 已解析的输入值 | **要数据就取它** |
| `workflow` | **UI 画布图**：节点位置、尺寸、连线、分组 | 要在 ComfyUI 里还原画布才需要 |

> 官方对这两个字段的说明（原文）：
> `workflow` — the complete workflow graph, including nodes, links, and layout information.
> `prompt` — the API prompt used to execute the workflow. It contains the nodes and inputs required for execution.
>
> **中文翻译：**
> `workflow` —— 完整的工作流图，包含节点、连线与布局信息。
> `prompt` —— 用于执行工作流的 API 提示词（执行图），包含执行所需的节点与输入。
>
> **中文解读：** 两者分工明确 —— `workflow` 服务于「前端还原画布」，`prompt` 服务于「执行」。想要提示词、种子、步数这类**数据**，去 `prompt`；`workflow` 里也有同样的值，但被埋在节点小部件的数组里（顺序依赖节点版本），解析起来脆得多。**取 `prompt`。**

### `prompt` 的结构与取值路径

顶层是「节点 id → 节点对象」的扁平映射：

```json
{
  "3": {"class_type": "KSampler", "inputs": {"seed": 88213, "steps": 28, "cfg": 7.5,
        "sampler_name": "dpmpp_2m", "scheduler": "karras",
        "positive": ["6", 0], "negative": ["7", 0]}},
  "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux-dev.safetensors"}},
  "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "lina under the rain"}, "_meta": {"title": "Positive"}},
  "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, watermark"}, "_meta": {"title": "Negative"}}
}
```

| 想要 | 去哪儿取 |
|---|---|
| 正向 / 负向提示词 | `CLIPTextEncode` 节点的 `inputs.text` |
| 种子 / 步数 / CFG / 采样器 / 调度器 | `KSampler`（或 `KSamplerAdvanced`）的 `inputs` |
| 模型名 | `CheckpointLoaderSimple` 的 `inputs.ckpt_name`（UNET 系则看 `unet_name`） |

**连线是关键，别靠节点标题猜正负。** `KSampler.inputs.positive` / `.negative` 的值形如 `["6", 0]`，意思是「取自节点 6 的第 0 个输出」。顺着它走到对应的 `CLIPTextEncode`，才是**真正**的正/负提示词。

`_meta.title` 只是画布上的显示名，用户可以随手改成任何东西。**拿不到连线时才退回标题启发式**，并在台账里把依据记成 `comfy-basis:title`（连线路走通记 `comfy-basis:link`），这样误判能被看见。

**前提条件：** 文件必须由 ComfyUI 的**默认**保存节点写出。第三方保存节点（WebP / JPEG / 视频输出）通常不写这些元数据；用 `--disable-metadata` 启动过 ComfyUI 的话也没有。

---

## 四、Automatic1111 / Forge：一段文本，坑在标点

只写一个块，关键字 `parameters`，值是**一段纯文本**：

```
a cinematic poster of lina standing in the rain, neon reflections, 35mm
Negative prompt: blurry, watermark, extra fingers
Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 2847193056, Size: 1024x1536, Model hash: 6ce0161689, Model: flux-dev
```

三段结构：**正向提示词**（可多行）→ 一行以 `Negative prompt:` 开头 → 一行以 `Steps:` 开头。

### 两个必须绕开的解析陷阱

**陷阱一：不能按逗号从头切。** 提示词自己就含逗号（`rain, neon reflections, 35mm`），按逗号切会把提示词和参数搅在一起。正确做法是**先锚定 `Steps:` 这一行**，它之前的全归提示词。

**陷阱二：参数行里的逗号也不总能切。** 例如：

```
Lora hashes: "detail_tweak: 7c6bad76eb, film_grain: 11aa22bb"
```

引号里还有一个逗号。朴素切分会把这个值切成两半、后半段解析成垃圾键。**切分时要跟踪引号状态**（脚本里的 `_split_top_level` 就是干这个的）。

### 取值对照

`Steps` → steps · `Sampler` → sampler · `CFG scale` → cfg · `Seed` → seed · `Size` → 生成尺寸 · `Model` → 模型名 · `Model hash` → 模型指纹 · `Denoising strength` → denoise · `Lora hashes` → LoRA 指纹。

**注意 `Size` 是「生成时的目标尺寸」，不是文件的实际像素尺寸。** 图可能被缩放或裁剪过 —— 实际尺寸要读图片头部，两者不一致时以头部为准。

---

## 五、其他工具

| 工具 | 情况 |
|---|---|
| **InvokeAI** | `invokeai_metadata` / `sd-metadata` 里放 JSON，浅提取即可 |
| **Fooocus / NovelAI** | `Comment` 块里放 JSON |
| **Midjourney** | 提示词在 **EXIF `description`**，不在 PNG 文本块里。本脚本不解析 EXIF —— 见下节 |

---

## 六、已知不支持（说清楚，别猜）

| 情况 | 为什么读不到 | 替代办法 |
|---|---|---|
| **A1111 存成 JPEG / WebP** | 参数写进 **EXIF `UserComment`**，不是 PNG 文本块 | `exiftool -UserComment image.jpg` |
| **Midjourney 的图** | 提示词在 EXIF `description` | `exiftool -Description image.png` |
| **ComfyUI 存成 MP4 / WebM** | 元数据在**容器级标签**（MP4 的 `©cmt` 注释原子），不在图像块里 | `exiftool` 或专门的容器解析工具 |
| **第三方保存节点输出的图** | 那些节点大多压根不写元数据 | 只能靠同源 `.txt`/`.json` |
| **被重新编码过的图** | 任何重存都可能丢掉文本块 | 无解，回不到过去 |

**这些不做「尽力而为的猜测」** —— 读不到就在台账里标 `未提供`，并把发现过的文本块名记进 `flags`，需要原文时用 `--keep-raw-meta` 落一份。

---

## 七、自己动手验证（不用装任何东西）

```bash
# 看这张图里有哪些文本块（macOS / Linux 自带 strings）
strings image.png | head -40

# 有 exiftool 的话，读得更清楚
exiftool -a -G1 -PNG:all image.png
exiftool -b -Workflow image.png | head -c 500
```

> **为什么 `strings` 就能看到：** `tEXt` 块是**未压缩明文**，且写在像素数据之前 —— 提示词常常就在文件最开头的几百字节里。这也正是它容易被忽略的原因：大家都在看图，没人看文件。

---

## 八、隐私提醒（顺手要检查的事）

这些元数据在**方便复现**的同时，也会泄露原本不打算公开的东西：

| 会泄露什么 | 说明 |
|---|---|
| **本机绝对路径与用户名** | ComfyUI 的节点把文件路径原样序列化进 JSON，常出现 `/Users/<你的名字>/...` 或 `C:\Users\<你的名字>\...` |
| 模型与 LoRA 文件名 | 可能含私有微调、客户名的命名 |
| 工作流结构 | 复杂工作流是长期打磨的产物，随图一起送人 |
| 备注节点内容 | 画布上写给自己看的提醒，也会被序列化 |

**脚本做的事：** 扫到疑似本机绝对路径就在 `flags` 里记 `meta-has-local-path`，并在 `scan` 与 `stats` 里提醒条数。

**脚本不做的事：** 不改用户的图片。要清理用专门工具（按块剥离，不重新编码像素）。

> 官方对这类数据的定性（原文）：
> Treat embedded metadata as optional and untrusted input. Validate that a value is valid JSON before using it.
>
> **中文翻译：** 把内嵌元数据当作「可选的、不可信的输入」；使用前先校验取到的值是不是合法 JSON。
>
> **中文解读：** 官方自己就打了预防针 —— 这些块可能没有、可能被工具改写、可能格式对不上版本。所以解析必须**容错**（JSON 解析失败就当没有），且**不允许**为了让台账"完整"而凭空补值。这正是 SKILL.md 第六节防幻觉规则的现实依据。

---

## 九、与同系列技能对接的文件契约

除了图内元数据，「晓得」系列另外两个技能也会产出**同源文件**。台账读它们的**固定字段**，不读别的。

### 来自「晓得·角色档案」（`--characters <目录>`）

| 项 | 约定 |
|---|---|
| 文件名 | `char_<name>.yaml` 或 `char_<name>.md`（两种格式等价，落在 `characters/` 目录） |
| 台账只读 | `name`（角色代号）、`locked_anchors`（连续性锁短语列表） |
| 台账怎么用 | ① 校验 `role` 是否在卡里 → 不在报 `unknown-role`；② 逐条比对锚点短语是否出现在提示词里 → 全不中报 `anchor-miss`，部分中报 `anchor-partial` |
| 台账不会做的事 | **不代填 `role`**。角色卡里有 `lina` 不等于 `lina_01.png` 就是 lina —— 那是凭文件名推断，禁止 |
| 已知边界 | 只取第一个 `locked_anchors` 块，`variant` 的独立锚点块**不参与**锚点比对（只登记为已知角色名，避免误报未知角色） |

### 来自「晓得·分镜工」（`--storyboard <shots目录>`）

| 项 | 约定 |
|---|---|
| 清单 | `manifest.json`：`shots[]` 每项含 `index` / `tag`(`shot_001`) / `start` / `end` / `duration` / `firstframe` / `clip` |
| 提示词包 | `prompts.md`：按 `## shot_001` 分段，条目形如 `- 提示词：<全文>`、`- 时长：3.2s`、`- 景别/运镜：…` |
| 台账怎么用 | 文件名匹配 `shot_NNN` 的素材 → 记 `shot_id`；**没有时长就补清单的实测时长**；**没有提示词就补提示词包里的提示词** |
| 台账不会做的事 | 不改写分镜提示词、不推断镜头数、不替它判断时长是否越限（那是分镜工的规则 4） |
| 降级 | 文件名里的镜头号在清单里找不到 → 记进报告，不硬塞 |

### 创作字段的取值优先级（高 → 低）

1. **用户用 `set` 给定**的值
2. 素材自己的**同源文件**（`同名 .txt` / `.json`）
3. 素材的**图内元数据**（本文第三、四节）
4. **分镜提示词包**（只在素材自己没有提示词时才用）

**顺序不能颠倒** —— 越靠前的越贴近「这份素材自己声明的信息」。把第 4 条排到最后，是因为分镜提示词描述的是**镜头**，首帧图只是它的一部分；素材自己若有更具体的提示词，以它为准。
