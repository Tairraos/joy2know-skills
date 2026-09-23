# WorkBuddy 会话记录 · 存储结构与解析细则

> 核验日期 2026-09-14（本机实测）。平台版本演进后字段可能变化，**遇到解析为空先回头看结构，不要先改逻辑去凑结果**。

## 一、目录与文件

```
~/.workbuddy/
├── workbuddy.db                     会话与空间的索引库（SQLite）
├── workspace-display-names.json     空间路径 → 显示名
├── edge-sync-mapping-v4.db          云同步映射（勿动）
└── projects/
    └── <空间路径，"/" 全换成 "-">/
        ├── <sessionUuid>.jsonl            会话正文，一行一 JSON
        ├── <sessionUuid>.meta.json        运行态（acpConnectionId / mode / expertId / teamName）
        └── <sessionUuid>.file-rollback.ndjson  文件回滚记录
```

路径映射示例：

| 空间真实路径 | project 目录名 |
|---|---|
| `/Users/you/Desktop/myproj` | `Users-you-Desktop-myproj` |
| `/Users/you/Desktop/tmp/2026-09-11-08-59-17` | `Users-you-Desktop-tmp-2026-09-11-08-59-17` |

**一个空间可能对应多个 project 目录**（前缀相同）。症状：某个空间的对话只看到一部分。处理：

```bash
ls ~/.workbuddy/projects/ | grep <路径关键词>
```

逐个看各自 jsonl 的时间范围，再合起来判断。

## 二、索引库（只读使用）

```python
import sqlite3
con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)   # ★ 只读打开
```

| 表 | 关键字段 | 用途 |
|---|---|---|
| `sessions` | `id` `cwd` `title` `custom_title` `status` `created_at` `updated_at` `deleted_at` | **`cwd` 就是"空间归属"**；**客户端界面**按它分组。`deleted_at` 非空=已删。
> 注意：`scripts/extract_flow.py` **不读这张表** —— 它按每个 jsonl 里带 `cwd` 的记录分组。此表用于**交叉核对**（例如界面显示的空间与脚本列出的对不上时） |
| `workspaces` | 空间登记 | 与 `workspace-display-names.json` 互为佐证 |

> **纪律：归纳任务永远用只读模式打开。** 改 `sessions.cwd` 属于"搬家"操作，会牵动 `edge-sync-mapping-v4.db` 里的云同步映射，有被云端按原空间拉回的风险。归档/归纳都不需要它。

`cwd` 分组速查：

```sql
SELECT cwd, count(*) n, max(updated_at) last FROM sessions GROUP BY cwd ORDER BY n DESC;
```

## 三、jsonl 记录结构

每行一个 JSON 对象，`type` 共 6 种：

| `type` | 说明 |
|---|---|
| `message` | 对话消息，另有 `role` 字段（`user` / `assistant`） |
| `function_call` | **工具调用**，有 `name` 与 `arguments`（JSON 字符串） |
| `function_call_result` | 工具返回 |
| `reasoning` | 思考过程 |
| `file-history-snapshot` | 文件历史快照 |
| `ai-title` | 自动生成的会话标题 |

通用字段：`timestamp`（**毫秒**）、`type`、部分记录带 `cwd`。

### 3.1 用户提问

```python
if d.get("type") == "message" and d.get("role") == "user":
    raw = "".join(c.get("text", "")
                  for c in (d.get("content") or [])
                  if isinstance(c, dict) and c.get("type") == "input_text")
```

`raw` 里包含巨大的上下文注入（`<system-reminder>` 身份文件、`<user_info>`、模式提醒、记忆块……）。
**真实提问只包在 `<user_query>…</user_query>` 里**，必须先剥壳：

```python
m = re.search(r"<user_query>(.*?)</user_query>", raw, re.S)
q = m.group(1).strip() if m else raw
```

剥壳失败时的兜底：删掉 `<system-reminder>` / `<ide_opened_file>` / `<identity_context>` / `<memory>` 各块。

### 3.2 回答

```python
if d.get("type") == "message" and d.get("role") == "assistant":
    txt = "".join(c.get("text", "")
                  for c in (d.get("content") or [])
                  if isinstance(c, dict) and c.get("type") in ("output_text", "text"))
```

一条回答常被拆成多个 block（正文 + 工具调用前的说明），需**按时间顺序拼读**，不要只看第一个。

### 3.3 产物清单（关键）

```python
if d.get("type") == "function_call" and d.get("name") in ("Write", "Edit", "MultiEdit", "CreateFile"):
    args = json.loads(d.get("arguments") or "{}")
    p = args.get("file_path") or args.get("path") or ""
```

按首次出现顺序去重，统计每个路径的调用次数与操作类型。

## 四、坑清单（按踩坑频率排序）

1. **`function_call` ≠ `tool_call`。** 用 `tool_call` 过滤得到 0 条，会误判成"这个对话没产出任何文件"。这是最高频的坑。
2. **`<user_query>` 必须剥壳。** 否则几万字的上下文注入会被当成用户提问。
3. **同一 prompt 会重复出现**（上下文重注入 / 续接 / 压缩后重放），必须去重。「请继续执行任务」属**辅助轮**，不是独立提问。
4. **回答文字 ≠ 产物清单。** 回答会漏提、会提错、还会提到别的对话产出的文件。产物只认 `function_call` 的 `file_path`。
5. **一个空间可能对应多个 project 目录**（见第一节）。
6. **时间戳是毫秒**：`datetime.fromtimestamp(ts / 1000)`。
7. **jsonl 可能个别行损坏。** 逐行 `try/except json.JSONDecodeError` 跳过，不要让一行坏数据打断整份解析。
8. **`deleted_at` 非空的会话仍在记录里。** 计数时按需排除。

## 五、环境纪律

- 用**受管理的 Python**；脚本不联网、不写入 `~/.workbuddy` 下任何文件。
- 只读打开所有 `.db`。
- 输出默认写到 `/tmp/flow`，不要写回会话目录。
