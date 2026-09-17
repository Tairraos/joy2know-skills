本文由 `@SKILL.md` 第七节路由到此，只在遇到「危险命令怎么标级、有没有更安全的写法」时读取。

# 危险命令模式库与四级等级

## 一、四级危险等级判定标准

| 等级 | 含义 | 判定信号 | 前置动作（必须给） |
|---|---|---|---|
| **极高危** | 不可逆删除 / 覆盖 | `rm -rf`、格式化、`DROP`、`TRUNCATE`、无 WHERE 的 `DELETE`/`UPDATE`、`git reset --hard` | 先备份 / 先 SELECT 看行数 / 先 `--dry-run`；**禁止**未经确认产出 |
| **危险** | 批量修改 / 覆盖 | `mv` 批量、`sed -i`、`git push --force`、无确认的重命名脚本 | 先 `ls`/打印预览确认范围 |
| **谨慎** | 影响可控但有副作用 | 有 WHERE 的 `UPDATE`、单文件写入、`chmod`、`kill` 指定 PID | 说明影响对象，确认目标 |
| **安全** | 只读 | `grep`、`cat`、`SELECT`、`ls`、正则匹配、`wc` | 无需前置 |

原则：拿不准就往高一级标，并说明「未能确认影响范围，按 X 级处理」。

## 二、常见危险模式 → 安全替代

| 危险写法 | 等级 | 安全替代 | 关键点 |
|---|---|---|---|
| `rm -rf /path` | 极高危 | `rm -ri /path`（交互确认）或先 `ls /path` 看内容 | 路径务必先预览再删 |
| `DELETE FROM t` | 极高危 | `SELECT * FROM t WHERE <条件>` 先看，再 `DELETE FROM t WHERE <条件>` | 永远先补 WHERE |
| `UPDATE t SET c=v` | 极高危 | `UPDATE t SET c=v WHERE <条件>` | 无 WHERE 即全表更新 |
| `DROP TABLE t` | 极高危 | 先 `SELECT COUNT(*) FROM t` 确认，再 `DROP TABLE t`（建议先改名暂存） | 不可逆 |
| `TRUNCATE t` | 极高危 | 改为 `DELETE FROM t WHERE <条件>` 或先备份 | 清空无法回滚 |
| `git reset --hard` | 极高危 | `git stash` 暂存，或 `git checkout -- <file>` 单文件 | 丢失未提交更改 |
| `sed -i 's/a/b/' f` | 危险 | 先 `sed 's/a/b/' f` 打印看结果，确认后再加 `-i` | 不带 `-i` 只预览 |
| `mv *.log /bak` | 危险 | 先 `ls *.log` 确认匹配范围，再 `mv` | 通配符范围先预览 |
| `git push --force` | 危险 | `git push --force-with-lease` | 别人已推会保护 |
| `chmod -R 777 /` | 谨慎 | 仅对目标目录 `chmod`，不用 `-R` 递归到根 | 范围收敛 |

## 三、正则表达式安全注意

- 灾难性回溯：嵌套量词如 `(a+)+` 配长串可能卡死，改为原子组或简化结构。
- 贪婪 vs 非贪婪：`.*` 默认贪婪，提取用 `.*?` 更稳。成对示例：正 `a.*b` 吞到最后一个 b；反 `a.*?b` 差在 `?`，停在第一个 b。
- 锚点缺失：要整串匹配必须加 `^...$`，否则子串即命中。

## 四、SQL 影响范围自查清单

1. 有没有 WHERE？没有 → 极高危，禁止直接给。
2. WHERE 条件能不能用 SELECT 先验证命中行数？能 → 先给 SELECT 版。
3. 是不是联表？联表 DELETE/UPDATE 先 LIMIT 1 试跑。
4. 是否影响生产库？是 → 必须提示在备份/从库上先验证。

## 五、给用户的二次确认话术模板

- 极高危：「这条会 [删除/覆盖] [对象]，不可逆。请先确认 [范围]，或我先给你 SELECT/备份版？」
- 危险：「这条会批量 [改动]，我先给预览版，你确认范围后我再加执行参数。」
- 禁止直接说「复制运行即可」对待上述任一层级。

## 六、更多高危命令模式（扩展库）

| 危险写法 | 等级 | 安全替代 | 关键点 |
|---|---|---|---|
| `git clean -fd` | 极高危 | 先 `git clean -nd` 预览将删文件 | 未跟踪文件会消失 |
| `docker rm -f <id>` | 危险 | 先 `docker ps` 确认容器 | 强制删运行中容器 |
| `find . -name x -delete` | 极高危 | 先 `find . -name x -print` 看清单 | `-delete` 不可恢复 |
| `dd if= of=` | 极高危 | 确认 of= 目标，先备份目标盘 | 写错盘即覆盖 |
| `chown -R user /` | 谨慎 | 只对目标目录 `chown`，不用 `-R` 到根 | 范围收敛 |
| `:> file` / `> file` | 危险 | 先 `cp file file.bak` 备份 | 截断清空文件 |
| `cp a b`（b 已存在） | 谨慎 | `cp -i a b` 交互确认覆盖 | 静默覆盖 |
| `rsync --delete src dst` | 危险 | 先 `rsync -n --delete` 干跑看差异 | 删目标多余文件 |
| `pkill -f xxx` | 危险 | 先 `pgrep -f xxx` 看匹配进程 | 误杀其他进程 |
| `mysqldump ... > out.sql`（out 已存在） | 谨慎 | 先确认 out 路径或改名 | 覆盖已有备份 |

## 七、dry-run 优先对照表

任何极高危 / 危险动作，产出前先给「预览 / 验证」等价命令，让用户先看到影响范围：

| 危险动作 | 预览 / 验证命令 |
|---|---|
| 删除文件 | `ls` / `echo` 目标路径 |
| 删库 / 清表 | `SELECT` 看命中行数 |
| 批量 `mv` | `ls` 通配符匹配结果 |
| `sed -i` | 先 `sed` 不带 `-i` 打印 |
| `find -delete` | `find -print` 清单 |
| `rsync --delete` | `rsync -n` 干跑 |
| `git clean` | `git clean -nd` |
| `docker rm` | `docker ps` 确认 |

记住：先给「看得到影响」的版本，再给「真执行」的版本；后者必须在用户逐字确认后才给。
