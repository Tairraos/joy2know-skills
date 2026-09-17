# 交付文档规范 · 骨架 / 视觉 / 校验

## 一、默认骨架（六节）

用户没特别要求时按这个走。节可以合并，但不建议删；要删须在文末说明理由。

### 第 01 节 · 总览

- 时间轴：起止时间 + 关键转折点
- 关键数字：对话数 / 提问数 / 产物数 / 文件数（**注明计数口径**）
- 「这一阶段实际做完的几件事」——说结果，不说过程

### 第 02–0N 节 · 逐对话

每个对话固定三段式：

**① 我问了什么**
- 把原文**改编为结构化条目**：保留原意、追问顺序、硬性交付要求、被否定过的方案
- **不要 1:1 照抄口语**，也不要总结到看不出原意图
- 多轮追问用编号或分点列，让人看出思路是怎么推进的

**② AI 怎么答**
- **大幅精简**：只留结论、判据、可复用事实
- **表格优先于段落**
- 不复述过程，不复述工具的中间输出

**③ 产物**
- 名字 + 类型 + 位置
- 与「产物总表」呼应，不在这里展开内容

### 第 0N+1 节 · 产物总表

| 列 | 说明 |
|---|---|
| 名字 | 文件名（含扩展名） |
| 来源对话 | 哪个 session（编号或 ID 前 8 位） |
| 类型 | HTML 报告 / 交付包 / 脚本 / 说明文档 |
| 完整路径 | 绝对路径 |

**总表是这份文档最实用的部分**——用户靠它找文件。名字必须与磁盘上的实际文件名逐字一致。

### 第 0N+2 节 · 沉淀结论

把反复验证过的判据抽出来，**脱离对话上下文也能单独用**。写法：一句结论 + 一句依据 + 一句适用边界。

### 第 0N+3 节 · 未完结事项

显式列出没做完的事、卡在哪、下一步最该动的是什么。**这一节的价值是让下一阶段不用重新摸一遍。**

### 最后节 · 归档说明

- 归档范围（从哪到哪、几个文件）
- 校验方式与结果（md5 / `diff -r`）
- **例外文件及原因**（对不上归属的、未纳入的）
- 原空间有没有被改动

## 二、视觉系统（本系列既有）

单文件 HTML、**浅色主题**、自包含 CSS（不依赖外部资源）。

```css
:root{
  --s:#2f6f6a;   /* 结论 / 成功 */
  --e:#8a5a2b;   /* 强调 / 提示 */
  --c:#3d5a80;   /* 信息 / 引用 */
  --a:#7a4a6b;   /* 警告 / 反例 */
  --bg:#fbfaf7;
  --text-1:#1f2023;
  --text-2:#5c6066;
  --line:#e4e1da;
}
```

- 四色标签用于区分「结论 / 强调 / 信息 / 反例」四类内容
- `.sk` 卡片用于包裹一段独立结论
- `.callout` 提示块用于放需要显眼的提醒
- **引用英文原文必须给三层**，视觉上要能区分：

```html
<div class="blk orig">英文原文（等宽、灰底）</div>
<div class="blk trans">逐句中文翻译（白底）</div>
<div class="blk note">中文解读（浅底色块，讲它在约束什么）</div>
```

> 只给「原文 + 解读」会被退回——中间那层逐句翻译是必须的。代码标识符（工具名 / 字段名 / 模块名）保留英文原文。

## 三、写完必做的两道校验

### 3.1 HTML 标签平衡

```python
from html.parser import HTMLParser
VOID = {'br','hr','img','meta','link','input','col','source'}
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack=[]; self.err=[]
    def handle_starttag(self, t, a):
        if t in VOID: return
        self.stack.append((t, self.getpos()))
    def handle_endtag(self, t):
        if t in VOID: return
        if not self.stack: self.err.append(('extra', t, self.getpos())); return
        if self.stack[-1][0] != t:
            self.err.append(('mismatch', t, self.getpos(), 'expected ' + self.stack[-1][0]))
            for i in range(len(self.stack)-1, -1, -1):
                if self.stack[i][0] == t:
                    del self.stack[i:]; return
        else:
            self.stack.pop()

p = P(); p.feed(open(path, encoding='utf-8').read())
print("errors:", p.err[:8]); print("unclosed:", p.stack)
```

**`errors` 与 `unclosed` 都必须为空**。写完大文件后最容易在 Edit 处留下截断片段，这一步能兜住。

### 3.2 归档一致性

```bash
md5 -q "<源文件>"; md5 -q "<目标文件>"     # 单文件
diff -r "<源目录>" "<目标目录>"              # 目录递归；无输出=一致
```

批量归档时逐份比对，并打印 OK/FAIL 清单。**校验不通过就不算完成，不要先宣布完成再补校验。**

## 四、交付时的表达约定

- **先给结论，再给结构化细节。**
- 给数字时**顺带说明口径**（尤其提问数）。
- 例外情况**单独列出来说**，不要塞在脚注里。
- 不写「我做了 A、B、C」式的过程汇报；写「结果是 X，依据是 Y，例外是 Z」。
