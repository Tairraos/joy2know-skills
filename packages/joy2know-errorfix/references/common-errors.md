本文由 `@SKILL.md` 第七节路由到此，只在遇到对应问题时读取。覆盖高频报错的「人话解释 + 常见原因 + 验证命令」。

> 用法：在正文判断出错误属于下表某一类时，取对应条目，用正文第四节的「人话 + 3 原因 + 验证 + 修复」骨架展开。命令里的占位符用尖括号，用户可直接替换。

---

### 1. ECONNREFUSED（连接被拒绝）

- **人话**：你程序去敲一扇门，门那边根本没有服务在听。
- **常见原因**：①目标服务没启动；②地址/端口写错；③连错机器（本机 vs 容器网络）。
- **验证命令**：`telnet <host> <port>` 或 `nc -zv <host> <port>`；本地服务先看进程 `ps aux | grep <服务名>`。

### 2. ETIMEDOUT / 超时（Timeout）

- **人话**：门是开着的，但等了很久没人应答，你先走了。
- **常见原因**：①对方太慢/卡死；②网络不通或防火墙拦截；③超时阈值设太短。
- **验证命令**：`ping <host>`；`curl -m 5 -v <url>` 看卡在哪一步。

### 3. 404 Not Found

- **人话**：门找到了，但你要的那个房间不存在。
- **常见原因**：①URL 路径拼错；②资源未部署/未创建；③路由没匹配上（少了前缀或后缀）。
- **验证命令**：`curl -i <url>` 看真实返回；对比文档确认路径；本地查路由表。

### 4. 403 Forbidden / Permission denied（权限拒绝）

- **人话**：房间在，但你没钥匙进不去。
- **常见原因**：①文件/目录权限不足；②账号没授权；③SELinux/容器以非 root 跑却访问受限路径。
- **验证命令**：`ls -l <文件>`；`id` 看当前用户；`sudo -u <用户> <命令>` 验证是否权限问题。

### 5. ModuleNotFoundError / No module named（找不到模块）

- **人话**：你想用个工具，但工具没装进这个环境。
- **常见原因**：①没装依赖（`pip install` 漏了）；②装到了别的 Python 环境；③虚拟环境没激活。
- **验证命令**：`which python` / `python -m pip list | grep <模块>`；确认是否该先 `source venv/bin/activate`。

### 6. 端口被占用（Address already in use / Port X is occupied）

- **人话**：你想占的座位已经有人坐了。
- **常见原因**：①上一次进程没退干净；②别的程序用了同端口；③重复启动。
- **验证命令**：`lsof -i :<port>`（mac/Linux）；`netstat -ano | findstr :<port>`（Windows）；结束占用进程或换端口。

### 7. 证书过期 / 不安全（CERT_HAS_EXPIRED / SSL_ERROR）

- **人话**：对方出示的身份证过期了，你不敢信。
- **常见原因**：①服务器证书真的过期；②系统时间不对；③自签证书未被信任。
- **验证命令**：`openssl s_client -connect <host>:<port> 2>/dev/null | openssl x509 -noout -dates`；`date` 核对本机时间。

### 8. OOM / 内存不足（Out Of Memory / killed）

- **人话**：活儿太多，脑子（内存）撑爆了，系统把你干掉了。
- **常见原因**：①一次读入过大文件；②内存泄漏/无限增长；③容器内存上限太小。
- **验证命令**：`dmesg | grep -i oom`；容器看 `kubectl describe pod` 的 OOMKilled；用 `top`/`htop` 观察峰值。

### 9. 编码乱码（UnicodeDecodeError / 乱码）

- **人话**：文件用的是另一种文字编码，你按错的编码去读，读成了天书。
- **常见原因**：①文件是 GBK 你当 UTF-8 读；②终端编码不匹配；③读写两边编码不一致。
- **验证命令**：`file <文件>` 看编码；Python 读时显式 `encoding="utf-8"` 或 `encoding="gbk"`；`iconv -f gbk -t utf-8 <文件>` 转码验证。

### 10. 数据库连不上（Access denied / can't connect to MySQL server）

- **人话**：仓库门打不开——要么密码错，要么仓库根本没开。
- **常见原因**：①账号/密码/库名错；②数据库服务未启动；③只允许本机连接（bind-address）。
- **验证命令**：`mysql -u <用户> -p -h <host>` 或 `psql -h <host>`；服务端看 `systemctl status <db>`、配置文件 bind-address。

### 11. 命令找不到（command not found / 不是内部或外部命令）

- **人话**：你让系统跑一个程序，系统压根不认识这个名字。
- **常见原因**：①没安装该工具；②装了但不在 PATH；③拼错命令名。
- **验证命令**：`which <命令>`；`echo $PATH`；确认包名与命令名是否一致（如 `python3` vs `python`）。

### 12. 磁盘满 / 空间不足（No space left on device / ENOSPC）

- **人话**：抽屉塞满了，再也放不进东西。
- **常见原因**：①日志/缓存堆积；②大文件未清理；③inode 用完（小文件过多）。
- **验证命令**：`df -h` 看空间；`df -i` 看 inode；`du -sh * | sort -h` 找大户清理。

---

**备注**：以上命令均为诊断用途，修复动作（改配置、重启、删文件）需用户在确认环境后执行。涉及删除/重启的，正文中必须给出「先确认再执行」的提示。
