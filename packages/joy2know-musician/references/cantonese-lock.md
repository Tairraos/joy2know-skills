本文由 `@SKILL.md` 第七节路由到此。只在用户指定粤语或其他方言时读取。

# 方言防跑偏 · 以粤语为范本

## 一、为什么会跑偏

Suno 的训练语料里普通话占绝对多数。你写粤语歌词，它会：
1. **底层语系冲突** —— 同一个字，普通话发音和粤语发音是两套系统，模型在两套之间拉扯，输出听起来「不是纯正的哪一边」；
2. **声调撕裂** —— 粤语有六个声调，比普通话多两个，模型在拉长音时找不到对应的声调落点，就会跑调或破音；
3. **入声字爆音** —— 粤语的入声字（-p / -t / -k 结尾）短促，被拖成长音时极易产生电流破音和突发增益过载。

所以防跑偏不是「多加几个粤语词」，是**三处同时上锁**。

## 二、三处锁

### 锁 1：Style 最前端的语言锁（三层）

```
Cantonese, Cantopop, Traditional Cantonese Enunciation
```

**禁止**只写 `Chinese`。也要避免混入宽泛词（如 `Asian pop`）。

### 锁 2：歌词开头的两行

```
[Language: Cantonese]
[Accent: Traditional Cantonese, Hong Kong]
```

### 锁 3：歌词正文的词汇锁

用**高频强特征方言字**彻底卡死普通话音轨。粤语的锁：

| 类别 | 用这些 |
|---|---|
| 结构助词 | 嘅、咗、嗰、啲 |
| 否定 | 唔、冇、未 |
| 判断 | 系 |
| 人称 | 我哋、你哋、佢 |
| 疑问 | 边度、点解、咩、几时 |
| 时间 | 而家、嗰阵、一阵、仲 |
| 语气 | 啦、喎、啩、嘞、呢 |
| 动词 | 睇、讲、食、瞓、攞、揸、企、行 |

**反例（语系污染，必跑偏）：** 粤语歌词里出现「的、了、是、我们、什么、的时候」——
用**繁体**书写时同理（「我們、什麼、的時候」），脚本简繁成对检查，两种写法都会被报出。
一旦混入，模型会在粤语和普通话之间反复横跳。

## 三、入声字与破音风险

粤语入声字（-p / -t / -k 收尾）被拖长音时最容易破。常见风险字：

| 风险字 | 问题 | 替代 |
|---|---|---|
| 不（bat） | 短促爆破 | 唔 |
| 白（baak） | -k 收尾，长音易爆 | 雪白 → 用「苍白」或改写 |
| 哭（huk） | -k 收尾 + 高调 | 喊、流泪 |
| 失 / 湿 / 速 | -t / -k 收尾 | 走失 → 唔见咗 |
| 急（gap） | -p 收尾 | 慢慢、赶 |
| 出（ceot） | -t 收尾，长音破 | 离开、行出 |

**处理顺序：** 优先换成意思相近的平顺字；换不掉就保留，但做声调补偿（见下）。

## 四、声调补偿

遇到必须保留的风险字，在字前或字后垫一个开口元音，把音高垫平：

```
(ah)  唔(oh...)  喊(ah)
```

写在括号内，Suno 会把它当作人声的延长处理，避开爆破点。

**同时 Style 里必须写明：**
```
Smooth vocals, Polished production
```
并**禁用** `distorted`、`bitcrushed` 这类会产生高频冲突的指令。

## 五、完整示例

```
### 2. Style (Suno Optimized)
Cantonese, Cantopop, Traditional Cantonese Enunciation, Acoustic Indie Folk,
Soft breathy female vocals, Fingerpicked acoustic guitar + warm piano + light strings,
Healing and nostalgic, 76 BPM, Intimate room reverb, Smooth vocals, Polished production

**歌曲风格：** 粤语治愈系民谣，气声女声，木吉他配暖钢琴与轻弦乐，76 BPM，平滑人声

### 3. Lyrics (Suno Structure)
[Language: Cantonese]
[Accent: Traditional Cantonese, Hong Kong]
[Intro – Muted piano loop, soft static crackle]
(—distant rain—)
(sample: "食咗饭未") [whispered]
[Verse 1 – Half-whispered, Intimate, Close-mic]
窗边嗰盏灯 仲亮住
我坐喺度 冇嘢想讲
碗汤凉咗 都唔记得饮
[Chorus – Grand and anthemic, Layered vocals, Wide stereo]
最热闹嘅孤独 系有人陪住都觉得远
(ah)
```

## 六、其他方言的通用原则

粤语的机制可以平移到任何方言，只需替换三样东西：

1. **特征字表** —— 换成该方言的强特征虚词（如闽南语的「的」用「ê」、四川话的「啥子、巴适、要得」）
2. **风险字表** —— 换成该方言中促音、入声、高调的字
3. **语系锁** —— Style 里写该方言的具体分支名，不要写宽泛的上位词

**不确定时怎么办：** 明确告诉用户「这个方言我没有把握」，并建议先生成一句试听再决定整首。**不要**硬着头皮写完整首然后让用户自己试错——生成成本是用户的。

## 七、校验

```bash
python3 scripts/suno_check.py 歌词.txt --dialect cantonese
```

脚本会检查：特征字密度（低于阈值说明语系没锁死）、是否混入普通话虚词、风险字命中、Style 语言锁是否到位。
