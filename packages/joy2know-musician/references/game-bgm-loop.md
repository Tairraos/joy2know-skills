本文由 `@SKILL.md` 第七节路由到此。只在用户要纯器乐、游戏 BGM 或循环素材时读取（D / E 路径）。

# 纯器乐 · 游戏 BGM · 无缝循环

## 一、为什么这条路径要单独一套写法

Suno 是在**歌曲**上训出来的，而歌的重心就是人声。你写一段乐器描述、不写歌词，
模型的默认反应不是"安静地弹"，而是**去补一个人声进来**——哼唱、ooh/ahh 垫音、
若有似无的背景女声、念白。社区把这类现象叫「人声幻觉 / 幽灵人声」。

所以纯器乐不是「把歌词删掉」这么简单：**删歌词只是撤走了邀请，还得把门关上。**
下面四道门，一道都不够。

## 二、压住人声的四道门（缺一道就会漏）

| # | 门 | 具体做法 | 它挡什么 |
|---|---|---|---|
| 1 | 平台开关 | 打开生成页的 **Instrumental** 开关 | 挡住"唱出歌词"这件事。它**挡不住**无词人声 |
| 2 | Style 前置声明 | `instrumental, no vocals` 写在 **Style 最前**，而不是中间或末尾 | 靠位置的权重压制流派自带的人声联想 |
| 3 | 方括号外留空 | 标签之外一个字符都不留；标题、"instrumental" 这类备注也别写进去 | 方括号外的一切，Suno 都会尝试唱出来 |
| 4 | 排除 / 负面字段 | `vocals, singing, humming, vocalizations, spoken word, choir` | 挡住门 1 漏掉的无词人声——**这道门最关键** |

**为什么第 2 道门要放最前：** Style 里同时有 `instrumental` 与 `pop / trap / soul / gospel` 这类
"人声为重心"的流派词时，两条信号在打架，谁在前面谁更响。
把人声声明靠前 + 换掉人声联想强的流派，比在后面补一句 `no vocals` 有效得多。

**为什么第 4 道门最可靠：** 在 Style 里写否定词，模型读到的仍然是「vocals」这个概念本身；
排除字段是专门用来**剔除**的机制，处理方式不同。

## 三、Style 字段怎么改（对照有人认为声版的九字段）

| 字段 | 有人声 | 纯器乐 |
|---|---|---|
| 1 Language | `Mandarin` | **并入下一位**，写 `Instrumental, No vocals` |
| 2 Accent | `Standard Mandarin Enunciation` | 同上（**删掉**，不能保留发音要求） |
| 3 Genre | `Acoustic Indie Folk` | 保持，但优先选纯器乐联想强的：`Ambient` / `Cinematic` / `Post-rock` / `Lo-fi` |
| 4 Vocal description | `Soft breathy female vocals` | **换成演奏主体**：`Solo grand piano` / `Lead violin` / `Muted jazz guitar` |
| 5 Instruments | 用 `+` 连接 | 同左，另加 `+ subtle pads` 这类铺底 |
| 6 Mood | `Healing and nostalgic` | 保留，但偏中性：`Calm and spacious` |
| 7 Tempo | `76 BPM` | **必须写死数字**（循环场景是硬要求） |
| 8 Atmosphere | `Intimate room reverb` | 常换成更宽的空间：`Wide reverb` |
| 9 Production | `Polished analog production` | 加循环关键词：`Seamless loop, No fade in, No fade out, Consistent dynamics` |

**标签总数控制在 4–7 个强描述。** 堆到十几个标签时，模型开始"平均化"互相冲突的风格，
纯器乐的信号也被稀释——**简化 Style** 本身就是压制幽灵人声的一招。

## 四、无缝循环

### 生成侧：让首尾能接上

1. **Style 里写** `seamless loop, no fade in, no fade out`。
2. **BPM 写死。** 不写 BPM 的输出会漂移，导出后你会看到循环点落在小节中间——**这条最省事也最容易被跳过**。
3. **结构标签按小节编号，并明确要求首尾同源：**

```
[Loop Start – Sparse low piano motif, single sustained string pad]
[Build – Add second string layer one octave up]
[Climax – Light percussion enters, sustained chord]
[Resolve – Strip back to opening texture]
[Loop End – Match opening exactly for clean splice, No fade out]
```

4. **收束段不要用 `[Outro – Fade out ...]`。** 淡出是循环的天敌：它让每一圈之间出现一个音量豁口。
   收束要写成"回到开头"的样子（上面的 `[Loop End – Match opening ...]`）。
   **但 `[End]` 这个必留标签要留着**——脚本靠它确认结构完整，写成复合式即可：
   `[End – Return to opening chord and texture, Clean cut, No fade out]`。

### 后期侧：无缝是在编辑器里做出来的

> 交付给用户时必须讲清这一点：**提示词包不产出无缝文件**。

1. **裁到整数小节。** 在波形上找重复段的起止，按拍点切齐，**头尾那些 AI 自作主张的收尾音一律剪掉**。
2. **标 loop point。** 在编辑器里标记循环入点 / 出点（多数引擎读这个标记，没有标记就靠文件名约定）。
3. **交叉淡化（crossfade）。** 接缝处做 0.5–1 秒（更精细的 5–20 ms）交叉淡化，听不出接缝为止。
4. **试听三圈。** 连续放三遍，中间不能有咔哒声、音量跳变、和弦错位。

### 循环 QA 清单（交付前自查，也拿来答用户的"这样能行吗"）

| 检查项 | 通过标准 |
|---|---|
| 头尾拼接 | 连放三圈无咔哒、无提速或掉拍 |
| 无人声 | 没有哼唱、口哨、ooh/ahh、人声采样 |
| 能量稳定 | 循环内不出现突兀的鼓点进入或乐器消失 |
| 时长 | 覆盖目标用途（短视频类留 3 秒余量） |
| 频谱 | 中频（约 300 Hz–3 kHz）不拥挤 —— 要垫在人声/配音下的尤其注意 |

## 五、游戏 BGM 的动态分层（可选，但很值）

游戏音乐"随状态变化"的常规做法是**竖切分层**：同一场景做多层同源音乐，引擎按玩家状态切换或叠加。

| 层 | 内容 | 触发 |
|---|---|---|
| 1 氛围床 | 稀疏、无节奏、只铺底 | 探索 / 待机 |
| 2 加节奏 | 加轻打击乐或持续弦乐 | 发现敌人、进入紧张区 |
| 3 战斗全奏 | 鼓 + 旋律 + 全部编制 | 进入战斗 |
| 4 升级层 | 叠加铜管 / 人声式 pad / 更高密度 | Boss 二阶段、危机 |

**硬要求：各层同 BPM、同调性、同和声框架。** 一层 D 小调 80 BPM、另一层漂到 82 BPM，交叉淡化就会"跑调"。
做法：从**同一版 Style** 出发，用 Extend / Remix 逐层加浓，让模型参考前面的输出；
**不要**为每一层另起一版 Style —— 那是两首不同的曲子，不是一层音乐。

## 六、Stinger 与过渡段

- **Stinger**：短（2–8 秒）、有明确终止感，用于胜利、结算、拾取、弹窗。
  **它不循环**：写 `[Outro – Resolved, Final hit, Clean ending]` 这种带终止感的收束是对的，别套用循环那四条约束。
- **过渡段**：加载画面、场景切换用的过门。一两小节、留尾巴，便于接到下一首的开头。

## 七、导出与响度（常见目标值，按你的发布平台规范再校对）

| 用途 | 格式 | 参考响度 |
|---|---|---|
| 存档 / 再处理 | WAV | 不做归一化，留动态余量 |
| 短视频平台 | MP3 320 kbps | −14 ~ −10 LUFS（平台不同有差异） |
| 配音 / 播客垫乐 | WAV / MP3 | 比人声低 8–12 dB，**别盖住语音** |
| 纯音乐展示 | 任意 | 约 −14 LUFS，避免削波 |

**Stems（分轨）**：需要更细的分层控制时，可导出分轨（鼓 / 贝斯 / 旋律 / 人声等）。
**具体支持情况与导出参数，以你当前 Suno 版本的实际表现为准** —— 本技能不写死版本差异。

## 八、四套可直接改的模板

**① 专注 / 学习（Lo-fi）**
```
Instrumental, No vocals, Lo-fi Hip Hop, Dusty vinyl crackle, Warm Rhodes piano, Soft mellow beat,
Calm and cozy, 76 BPM, Warm tape saturation, Seamless loop, No fade in, No fade out, Consistent dynamics
```

**② 空间 / 环境（Ambient）**
```
Instrumental, No vocals, Ambient, Evolving synth pads, Spacious reverb, Slow textural drift,
Calm and meditative, 68 BPM, Cavernous space, Seamless loop, No fade in, No fade out
```

**③ 游戏探索（Orchestral / Fantasy）**
```
Instrumental, No vocals, Cinematic Orchestral, Flute and harp lead, Warm strings bed, No percussion,
Curious and gentle, 84 BPM, Wide natural reverb, Seamless loop, No fade in, No fade out, Consistent dynamics
```

**④ 游戏战斗（重点）**
```
Instrumental, No vocals, Industrial Orchestral, Driving low strings, Taiko and low brass, Aggressive pulse,
Tense and propulsive, 128 BPM, Tight punchy mix, Seamless loop, No fade in, No fade out
```

对应结构（把上面的标签换成自己的乐器/情绪）：
```
[Loop Start – Sparse motif, single instrument, No percussion]
[Build – Layer strings, Rising tension]
[Climax – Full arrangement, Driving percussion, Wide stereo]
[Resolve – Strip back to opening texture]
[End – Return to opening chord and texture, Clean cut, No fade out]
```

## 九、失败模式对照

| 症状 | 先改什么 | 别做什么 |
|---|---|---|
| 出现哼唱 / ooh-ahh | Style 删净人声词（含语言与发音要求）→ 用排除字段 → 简化 Style 到 4–7 个标签 | 别只把开关关了就当没事 |
| 出现清晰唱词 | 检查方括号外是否有残留文字；确认 Instrumental 开关已开 | 别在 Style 里再加一句 `no lyrics` |
| 循环接不上、有咔哒 | 锁死 BPM → 首尾同源 → 编辑器里裁到整数小节 + 交叉淡化 | 别反复重生成同一版 Style |
| 越循环越烦 | 去掉强旋律钩子，降动态起伏，减配器厚度 | 别靠加更多乐器去"丰富" |
| 时长不够 | 用 Extend 续接，**Style 必须原样复制**，并写 `continue instrumental` | 别从头重新生成整首 |
| 中频糊、盖住配音 | 减中频乐器密度，做高通滤掉 80 Hz 以下浑浊 | 别整体降音量了事 |

## 十、版本不确定性（写进产出里，别自己吞掉）

Suno 的标签支持范围、时长上限、排除字段的有无、Stems 导出权限、是否有 Studio 的 loop 标记功能
——**这些都随版本变**。不确定时照实说：

> 「以你当前 Suno 版本的实际表现为准；这套写法我在多数版本上都见过有效，但标签是概率性提示，不是硬开关。」

**禁止**把某个版本的行为当成通用事实写进产出。用户拿到的是一份提示词包，
不是一份"保证书"。
