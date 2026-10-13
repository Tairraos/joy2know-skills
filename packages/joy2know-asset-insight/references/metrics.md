# 运营数据接口与分析方法

> 给 `joy2know-asset-insight` 取用。**所有内容来自 2026-10-13 的真实调用**。
> 平台没有公开文档，这份是从前端 chunk 挖出接口 + 实际请求验证得到的。

---

## 一、接口

```
POST /api/v2/open-platform/asset-metrics/daily
```

**请求体**

```json
{
  "assetIds":   ["os_xxxx", "oe_yyyy"],
  "metricTypes": ["installs","calls","activeUsers","frequency","weekRetention","errorRate"],
  "startTime":  "2026-09-14",
  "endTime":    "2026-10-13"
}
```

**响应**

```json
{ "code": 0, "data": {
  "query": { "startTime": "...", "endTime": "...", "metricTypes": [...] },
  "assetData": [{
    "assetId": "os_xxxx", "assetName": "晓得·音乐人", "assetType": "skill",
    "overview": {                                  // ← 窗口内汇总
      "installs":     { "value": 44, "status": "ready" },
      "calls":        { "value": 54, "status": "ready" },
      "activeUsers":  { "value": 31, "status": "ready" },
      "frequency":    { "value": 1.85, "status": "ready" },
      "weekRetention":{ "value": 0.136, "status": "ready" },
      "errorRate":    { "value": null, "status": "na" }
    },
    "daily": [ { "date": "2026-09-17",
                 "metrics": { "installs": {"value":0,"status":"ready"}, ... } } ]
  }],
  "platformDailyTotal": [ ... ]                    // 平台级日汇总
}}
```

### `status` 三态 —— **别把 null 当 0**

| status | 含义 | 处理 |
|---|---|---|
| `ready` | 有值 | 正常用 |
| `pending` | 数据还没算完 | **不要当 0**，会导致趋势图掉坑 |
| `na` | 本指标对该资产不适用 | 排除，别参与均值 |

> 实测 `errorRate` 在全部资产上**恒为 `na`** —— 平台目前不下发这一项，**任何基于它的结论都是编的**。

---

## 二、三个坑（照 `/capabilities/*` 的规律猜会全错）

### ① 接口名不在常规前缀清单里

前面挖到的接口都是 `/capabilities/*`、`/messages` 这种；运营数据是独立的
**`/asset-metrics/daily`**。找法：在前端 `page-*.js` 里搜
`metricsPort.getAssetDailyMetrics`。

**猜路径全部 404**：`/operations`、`/operations/stats`、`/analytics/overview`、
`/capabilities/stats`、`/metrics` … 一个都不对。

### ② 时间是 `"YYYY-MM-DD"` 字符串，不是时间戳

传毫秒时间戳会报：

```
{"code":100001,"msg":"请求体不是合法 JSON"}
```

⚠️ **这个报错极具误导性** —— JSON 结构明明合法。
真正的意思是「字段类型不对」。前端源码里是这么转的：

```js
function w(e){ return new Date(e).toISOString().slice(0,10) }   // → "2026-09-14"
```

### ③ `metricTypes` 只认 6 个值，多一个就整单失败

```
installs · calls · activeUsers · frequency · weekRetention · errorRate
```

塞进别的一律返回 **`code 100001`**（**不是**「忽略未知指标」）。
实测加了 `hourlyCalls` → 整个请求失败，六个指标一个都拿不到。

---

## 三、指标读法

| 指标 | 单位 | 读法 | 陷阱 |
|---|---|---|---|
| `installs` | 次 | 入口热度 | 装得多不代表在用 |
| `calls` | 次 | **使用强度的主排序依据** | — |
| `activeUsers` | 人 | 覆盖面 | ⚠️ **各资产独立去重，跨资产相加会重复计人** |
| `frequency` | 次/人 | ≥3 算形成习惯；≈1 是「试一下就走」 | 分母是 activeUsers，样本小时波动大 |
| `weekRetention` | 0~1 | 下周还回来的比例 | 多数资产为 0，见下 |
| `errorRate` | — | **本次实测恒为 `na`** | 不要用 |

---

## 四、四把尺子（固定分析顺序）

### 尺子 1 · 集中度

```
Top3 调用 / 全站调用
```

- **> 70%** → 头部集中，**资源压头部**，长尾不要平均用力
- **30%~70%** → 相对分散
- **< 30%** → 没有明显赢家，值得做形态复盘

### 尺子 2 · 粘性

```
calls ÷ installs        （每个安装被调用了多少次）
```

| 区间 | 含义 |
|---|---|
| **> 3** | 强粘性 —— 用户主动回来用 |
| 1.5 ~ 3 | 正常 |
| **≈ 1** | 「装了就试一次」，体验或引导有问题 |

**安装高 + 粘性低 = 装了不用**。数据只能**指出位置**，
**为什么不用要去查首次使用流程** —— 不要从数据直接编原因。

### 尺子 3 · 留存

统计 `weekRetention > 0` 的资产个数：

- **全站为 0** → 问题**不在单个资产**，在「首次使用没形成习惯钩子」，这是结构性问题
- **个别非零** → 去看那几个做对了什么（它们的首次体验有什么不同）

### 尺子 4 · 加速

```
近 7 天调用 ÷ 30 天调用
```

| 区间 | 含义 |
|---|---|
| **≥ 40%** | 近期在加速 |
| 10% ~ 40% | 平稳 |
| **< 10%** | 热度已过去（30 天前火过） |

⚠️ **样本 < 5 次调用不要算比例** —— 分母太小，1 次变 2 次就是 100%。

---

## 五、报告口径（每条都要写进报告）

1. **只用有数据的资产**：接口**只返回有访问记录的资产**。没出现 ≠ 表现差。
2. **日序列有跳日**：平台只在有活动时落点。「有效天数」要用 **调用 > 0 的天数**，不能用 `daily.length` 直接当满窗。
3. **活跃用户不可跨资产相加**（去重口径不同）。
4. **三档窗口一起拉**：7 / 30 / 90 天。单窗口看不出斜率。
5. **样本太小的要明说**：装 1 次、调 2 次的资产必须标「样本不足，需再观察」，**不能据此判死刑**。
6. **不做平台未开的维度**：来源渠道、地域、机型 —— 没有就是没有，**不推测**。

---

## 六、未验证 / 已知限制

- ⚠️ **`platformDailyTotal` 未解析**：返回了但字段结构未细究，报告未使用。
- ⚠️ **是否存在「导出」或「按渠道拆分」的接口未探测**：运营页面上有「查看详情」按钮，点开可能有更细的维度，**本次未挖**。
- ⚠️ **分页/上限未验证**：一次传了 35 个 assetId 正常返回；**更多是否分批（前端代码里有 200 个一批的逻辑）未测**。
- ⚠️ **留存窗口定义未确认**：`weekRetention` 的「次周」如何界定（自然周还是滚动 7 天）**平台未说明**，本报告按比例读，不做绝对解读。
