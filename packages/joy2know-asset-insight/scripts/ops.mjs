#!/usr/bin/env node
/**
 * ops.mjs —— 拉开放平台运营数据，按四把尺子算成一页 HTML 报告。
 *
 *   node ops.mjs --out <输出.html> [--days 30] [--no-report]
 *   node ops.mjs --json [--days 30]                只出原始数据
 *
 * 数据源：POST /api/v2/open-platform/asset-metrics/daily
 * 凭证：复用 开放平台发布 技能的 ~/.workbuddy/secrets/open-workbuddy.json（600、不入git）
 *
 * ⚠️ 三个坑（详见 SKILL.md / references/metrics.md）：
 *   ① 接口是 /asset-metrics/daily —— 照 /capabilities/* 猜会全 404
 *   ② startTime/endTime 必须是 "YYYY-MM-DD" 字符串（传数字报「请求体不是合法 JSON」）
 *   ③ metricTypes 只认 6 个值，塞别的值整个请求 code 100001
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36';
const CRED = path.join(os.homedir(), '.workbuddy/secrets/open-workbuddy.json');
const API = 'https://open.workbuddy.cn/api/v2/open-platform';
const METRICS = ['installs', 'calls', 'activeUsers', 'frequency', 'weekRetention', 'errorRate'];
const HERE = path.dirname(fileURLToPath(import.meta.url));

function cred() {
  let c = null;
  try { c = JSON.parse(fs.readFileSync(CRED, 'utf8')); } catch { /* 下面统一提示 */ }
  if (!c || !c.cookie || !c.partyId) {
    console.error('需要先登录 WorkBuddy 开放平台：');
    console.error('  node ~/.workbuddy/skills/开放平台状态直读/scripts/ow.mjs login');
    console.error('还没账号 → 先去 https://open.workbuddy.cn/ 注册并完成开发者认证。');
    process.exit(4);
  }
  return c;
}
const H = (c) => ({ 'content-type': 'application/json', 'user-agent': UA, 'x-party-id': c.partyId, cookie: c.cookie });

async function post(p, body) {
  const c = cred();
  const r = await fetch(API + p, { method: 'POST', headers: H(c), body: JSON.stringify(body), redirect: 'manual' });
  if (r.status === 302 || r.status === 303) {
    console.error('凭证已失效，请重跑登录：node ~/.workbuddy/skills/开放平台状态直读/scripts/ow.mjs login');
    process.exit(4);
  }
  return r.json();
}

const ymd = (x) => new Date(x).toISOString().slice(0, 10);
const V = (o, k) => (o && o[k] && o[k].value != null) ? o[k].value : 0;
const pct = (a, b) => b ? (a / b * 100) : 0;
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** 资产清单：专家用 profession 做显示名（displayName 全是品牌署名，无区分度） */
async function assetMeta() {
  const m = new Map();
  for (const t of ['skill', 'expert']) {
    const l = await post('/capabilities/list', { page: 1, pageSize: 100, filters: [{ name: 'capability_type', values: [t] }] });
    for (const i of (l.data?.items || [])) {
      const label = t === 'expert' ? (i.profession?.zh || i.name) : (i.displayName?.zh || i.name);
      m.set(i.assetId, { label, pkg: i.name, type: t, status: i.status });
    }
  }
  return m;
}

async function fetchWindow(ids, days) {
  const end = ymd(Date.now()), start = ymd(Date.now() - (days - 1) * 864e5);
  const r = await post('/asset-metrics/daily', { assetIds: ids, metricTypes: METRICS, startTime: start, endTime: end });
  if (r.code !== 0) throw new Error(`${days} 天窗口拉取失败：${JSON.stringify(r).slice(0, 200)}`);
  return { start, end, assetData: r.data.assetData || [], platformDailyTotal: r.data.platformDailyTotal || [] };
}

function buildRows(meta, w30, w7, w90) {
  const rows = w30.assetData.map((a) => {
    const mm = meta.get(a.assetId) || {};
    const o = a.overview || {};
    const f7 = w7.assetData.find((x) => x.assetId === a.assetId);
    const f90 = w90.assetData.find((x) => x.assetId === a.assetId);
    return {
      id: a.assetId, name: mm.label || a.assetName, pkg: mm.pkg || '-', type: a.assetType,
      calls: V(o, 'calls'), ins: V(o, 'installs'), au: V(o, 'activeUsers'),
      freq: V(o, 'frequency'), ret: V(o, 'weekRetention'),
      c7: V(f7?.overview, 'calls'), c90: V(f90?.overview, 'calls'),
      activeDays: (a.daily || []).filter((d) => V(d.metrics, 'calls') > 0).length,
      daily: (a.daily || []).map((d) => ({ date: d.date, calls: V(d.metrics, 'calls'), ins: V(d.metrics, 'installs'), au: V(d.metrics, 'activeUsers') })),
    };
  }).sort((x, y) => y.calls - x.calls);
  return rows;
}

/** 日趋势：各资产 daily 按日聚合 */
function seriesOf(rows) {
  const by = new Map();
  for (const r of rows) for (const d of r.daily) {
    const e = by.get(d.date) || { date: d.date, calls: 0, ins: 0 };
    e.calls += d.calls; e.ins += d.ins; by.set(d.date, e);
  }
  return [...by.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
}

// ─────────────────────────── 报告 ───────────────────────────

function svgChart(series, W = 980, H = 240, PAD = 44) {
  if (!series.length) return '';
  const mx = Math.max(...series.map((s) => s.calls)) || 1;
  const n = series.length;
  const X = (i) => PAD + (W - 2 * PAD) * i / Math.max(1, n - 1);
  const Y = (v) => H - PAD - (H - 2 * PAD) * v / mx;
  const pts = series.map((s, i) => `${X(i).toFixed(1)},${Y(s.calls).toFixed(1)}`).join(' ');
  const area = `${PAD},${H - PAD} ${pts} ${X(n - 1).toFixed(1)},${H - PAD}`;
  const bars = series.map((s, i) => `<rect x="${(X(i) - 5).toFixed(1)}" y="${Y(s.ins).toFixed(1)}" width="10" height="${(H - PAD - Y(s.ins)).toFixed(1)}" fill="#0ea5e9" opacity=".45" rx="2"/>`).join('');
  const dots = series.map((s, i) => `<circle cx="${X(i).toFixed(1)}" cy="${Y(s.calls).toFixed(1)}" r="3" fill="#c2410c"/>`).join('');
  const ticks = series.map((s, i) => (i % 3 === 0 || i === n - 1) ? `<text x="${X(i).toFixed(1)}" y="${H - PAD + 16}" font-size="10" fill="#94a3b8" text-anchor="middle">${s.date.slice(5)}</text>` : '').join('');
  let grid = '';
  for (let k = 0; k <= 4; k++) {
    const v = mx * k / 4, y = Y(v);
    grid += `<line x1="${PAD}" y1="${y.toFixed(1)}" x2="${W - PAD}" y2="${y.toFixed(1)}" stroke="#e2e8f0" stroke-dasharray="3 3"/><text x="${PAD - 8}" y="${(y + 3).toFixed(1)}" font-size="10" fill="#94a3b8" text-anchor="end">${v.toFixed(0)}</text>`;
  }
  return { svg: `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${grid}<polygon points="${area}" fill="#fed7aa" opacity=".5"/>${bars}<polyline points="${pts}" fill="none" stroke="#c2410c" stroke-width="2.5" stroke-linejoin="round"/>${dots}${ticks}</svg>`, W, H };
}

function report(rows, series, win) {
  const sum = (a, k) => a.reduce((s, x) => s + x[k], 0);
  const tot = { calls: sum(rows, 'calls'), ins: sum(rows, 'ins') };
  const t3 = sum(rows.slice(0, 3), 'calls'), t5 = sum(rows.slice(0, 5), 'calls');
  const sk = rows.filter((r) => r.type === 'skill'), ex = rows.filter((r) => r.type === 'expert');
  const avg = (a, k) => a.length ? sum(a, k) / a.length : 0;
  const ratio = avg(sk, 'calls') ? avg(ex, 'calls') / avg(sk, 'calls') : 0;
  const sticky = rows.filter((r) => r.ins > 0).sort((a, b) => (b.calls / b.ins) - (a.calls / a.ins)).slice(0, 6);
  const speed = rows.filter((r) => r.calls >= 5).sort((a, b) => pct(b.c7, b.calls) - pct(a.c7, a.calls)).slice(0, 6);
  const retNonZero = rows.filter((r) => r.ret > 0);
  const top = rows[0] || {};
  const ch = svgChart(series);

  const tr = rows.map((r, i) => `<tr>
    <td class="num">${i + 1}</td>
    <td><span class="nm">${esc(r.name)}</span><span class="pkg">${esc(r.pkg)}</span></td>
    <td><span class="badge ${r.type === 'expert' ? 'ex' : 'sk'}">${r.type === 'expert' ? '专家' : '技能'}</span></td>
    <td class="num b">${r.calls}</td><td class="num">${r.ins}</td><td class="num">${r.au}</td>
    <td class="num">${r.freq.toFixed(1)}</td><td class="num">${r.activeDays}</td>
    <td class="num sm">${r.c7}</td><td class="num sm">${pct(r.c7, r.calls).toFixed(0)}%</td></tr>`).join('\n');

  return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>运营洞察报告 ${win.end}</title>
<style>
:root{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--sub:#64748b;--line:#e2e8f0;--acc:#c2410c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1060px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:27px;margin:0 0 6px}
.meta{color:var(--sub);font-size:13px;margin-bottom:26px}
h2{font-size:19px;margin:38px 0 14px;padding-left:11px;border-left:4px solid var(--acc)}
h3{font-size:15px;margin:22px 0 8px;color:#334155}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin-bottom:16px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.kpi .v{font-size:26px;font-weight:700;letter-spacing:-.5px}
.kpi .l{font-size:12px;color:var(--sub);margin-top:2px}
.kpi.hl .v{color:var(--acc)}
ul{margin:8px 0;padding-left:20px} li{margin:5px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left}
th{font-size:12px;color:var(--sub);font-weight:600;background:#f1f5f9}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.b{font-weight:700} td.sm{color:var(--sub)}
.nm{font-weight:600}
.pkg{display:block;font-size:11px;color:#94a3b8;font-family:ui-monospace,monospace}
.badge{font-size:11px;padding:1.5px 7px;border-radius:99px}
.badge.ex{background:#ffedd5;color:#9a3412} .badge.sk{background:#e0f2fe;color:#075985}
.callout{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:14px 18px;margin:14px 0}
.callout b{color:#9a3412}
.warn{background:#fefce8;border-color:#fde68a} .warn b{color:#854d0e}
.note{font-size:12.5px;color:var(--sub)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}
svg{width:100%;height:auto;display:block}
.lg{display:flex;gap:18px;font-size:12px;color:var(--sub);margin-top:6px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
</style></head><body><div class="wrap">
<h1>运营洞察报告</h1>
<div class="meta">窗口 ${win.start} ~ ${win.end}（近 ${win.days} 天） · 数据源：平台 asset-metrics/daily 接口直读 · 有数据资产 ${rows.length} 个</div>

<h2>一、结论先行</h2>
<div class="callout"><b>① 头部集中度：Top3 占 ${pct(t3, tot.calls).toFixed(1)}%，Top5 占 ${pct(t5, tot.calls).toFixed(1)}%。</b>
${pct(t3, tot.calls) > 70 ? '越过 70% 的集中线 —— <b>资源应压头部，长尾不宜平均用力</b>。' : '未过 70%，分布相对分散。'}
后 ${Math.max(0, rows.length - 5)} 个资产合计仅 ${tot.calls - t5} 次调用。</div>
<div class="callout"><b>② 技能 vs 专家：平均调用量差 ${ratio.toFixed(1)} 倍。</b>
专家 ${ex.length} 个均值 ${avg(ex, 'calls').toFixed(1)} 次，技能 ${sk.length} 个均值 ${avg(sk, 'calls').toFixed(1)} 次
（安装量均值 ${avg(ex, 'ins').toFixed(1)} vs ${avg(sk, 'ins').toFixed(1)}）。</div>
${top.name ? `<div class="callout"><b>③ 头名粘性：${esc(top.name)} 每安装被调用 ${(top.calls / Math.max(1, top.ins)).toFixed(2)} 次</b>（全站均值 ${(tot.calls / Math.max(1, tot.ins)).toFixed(2)} 次）。</div>` : ''}
<div class="callout warn"><b>④ 次周留存：${rows.length} 个资产中仅 ${retNonZero.length} 个非零。</b>
${retNonZero.length === 0 ? '全站留存为 0 —— 问题不在单个资产，而在<b>首次使用没有形成习惯钩子</b>。'
  : '非零的有：' + retNonZero.map((r) => `${esc(r.name)} ${(r.ret * 100).toFixed(1)}%`).join('、') + '。'}</div>

<h2>二、总览</h2>
<div class="kpis">
  <div class="kpi hl"><div class="v">${tot.calls}</div><div class="l">调用量（${win.days} 天）</div></div>
  <div class="kpi"><div class="v">${tot.ins}</div><div class="l">安装量</div></div>
  <div class="kpi"><div class="v">${sum(rows, 'au')}</div><div class="l">活跃用户（累计）</div></div>
  <div class="kpi"><div class="v">${rows.length}</div><div class="l">有数据资产</div></div>
</div>
<p class="note">活跃用户为各资产<b>独立去重</b>的累计口径，跨资产相加会重复计人，仅供量级参考。</p>

<h2>三、访问排行（按调用量）</h2>
<div class="card" style="padding:0;overflow:hidden"><table>
<thead><tr><th>#</th><th>资产</th><th>类型</th><th style="text-align:right">调用</th><th style="text-align:right">安装</th>
<th style="text-align:right">活跃</th><th style="text-align:right">频次</th><th style="text-align:right">有效天</th>
<th style="text-align:right">近7天</th><th style="text-align:right">占30天</th></tr></thead>
<tbody>${tr}</tbody></table></div>
<p class="note">「有效天」= 窗口内调用 &gt; 0 的天数（使用是否稳定）；「占30天」= 近 7 天 / 30 天调用（越大越在加速）。</p>

<h2>四、趋势（${series.length} 天）</h2>
<div class="card">${ch ? ch.svg : '<p class="note">无日序列</p>'}
<div class="lg"><span><span class="sw" style="background:#c2410c"></span>每日调用（折线）</span>
<span><span class="sw" style="background:#0ea5e9;opacity:.45"></span>每日安装（柱）</span></div></div>
<p class="note">安装柱长期低于调用线 ⇒ 增量主要来自<b>既有用户的重复使用</b>，而非新增安装。</p>

<h2>五、原因分析</h2>
<div class="two">
<div class="card"><h3 style="margin-top:0">头部为什么赢</h3><ul>
<li><b>交付物完整度不同</b>：专家/团产出的是可直接使用的成品，技能产出的是中间物料。</li>
<li><b>内嵌带来第二种分发</b>：同一能力作为技能单飞与作为专家内嵌，调用量可能差一个量级。</li>
<li><b>入口少、链条短</b>：用户不必先想「用哪个技能」，直接找角色。</li></ul></div>
<div class="card"><h3 style="margin-top:0">长尾为什么不动</h3><ul>
<li><b>「装了不用」与「没人知道」是两件事</b>：安装低是曝光问题，安装高调用低是体验问题。</li>
<li>个位数样本<b>不足以判死刑</b>，需再攒窗口。</li>
<li><b>留存≈0</b> 说明首次体验没有钩子。</li></ul></div>
</div>
<h3>粘性榜（每安装被调用次数）</h3>
<div class="card"><ul>${sticky.map((r) => `<li><b>${esc(r.name)}</b> — ${r.calls} 调用 / ${r.ins} 安装 = <b>${(r.calls / r.ins).toFixed(2)}</b></li>`).join('')}</ul>
<p class="note">比安装量更能反映真实需求强度。</p></div>
<h3>加速榜（近 7 天占 30 天比例）</h3>
<div class="card"><ul>${speed.map((r) => `<li><b>${esc(r.name)}</b> — 近 7 天 ${r.c7} / 30 天 ${r.calls}（<b>${pct(r.c7, r.calls).toFixed(0)}%</b>）</li>`).join('')}</ul>
<p class="note">≥40% 加速 · 10~40% 平稳 · &lt;10% 热度已过。</p></div>

<h2>六、行动建议</h2>
<div class="card"><ol>
<li><b>资源压头部</b>：迭代前 3 名的输出质量与引导文案，边际收益最高。</li>
<li><b>查「装了不用」</b>：安装 ≥3 但调用 ≤2 的资产，去看首次使用流程断在哪。</li>
<li><b>给长尾技能补第二种分发</b>：挂到对应专家下，是成本最低的提量手段。</li>
<li><b>攻留存</b>：先把「首次使用 → 第二次使用」打通，比继续拉新划算。</li>
<li><b>样本不够的先别动</b>：个位数调用的资产再观察 7~14 天。</li>
</ol></div>

<h2>七、口径与限制</h2>
<div class="card"><ul>
<li><b>接口</b>：<code>POST /api/v2/open-platform/asset-metrics/daily</code>；时间为 <code>YYYY-MM-DD</code> 字符串。</li>
<li><b>指标</b>：installs / calls / activeUsers / frequency / weekRetention / errorRate（本次 errorRate 均为 <code>na</code>，未用）。</li>
<li><b>只返回有数据的资产</b>：未出现在表中 <b>≠ 表现差</b>（可能尚无访问）。</li>
<li><b>日序列有跳日</b>：平台只在有活动时落点。</li>
<li><b>未见维度</b>：来源渠道、地域、机型 —— 平台未开接口，不做推测。</li>
</ul></div>
<p class="note" style="margin-top:30px">晓得乐 · joy2know ｜ 本报告由技能「技能专家运营洞察」生成，可随时重跑</p>
</div></body></html>`;
}

// ─────────────────────────── main ───────────────────────────

const argv = process.argv.slice(2);
const o = {}; for (let i = 0; i < argv.length; i++) { const a = argv[i];
  if (a.startsWith('--')) { const k = a.slice(2); o[k] = (argv[i + 1] && !argv[i + 1].startsWith('--')) ? argv[++i] : true; } }
const days = Number(o.days || 30);

const meta = await assetMeta();
const ids = [...meta.keys()];
const w30 = await fetchWindow(ids, days);
const w7 = await fetchWindow(ids, Math.min(7, days));
const w90 = await fetchWindow(ids, 90);
const rows = buildRows(meta, w30, w7, w90);
const series = seriesOf(rows);

if (o.json) { console.log(JSON.stringify({ window: { start: w30.start, end: w30.end, days }, assets: rows }, null, 1)); process.exit(0); }

// 控制台摘要
const sum = (a, k) => a.reduce((s, x) => s + x[k], 0);
console.log(`运营数据 ${w30.start} ~ ${w30.end}（${days} 天）｜有数据 ${rows.length} / 全站 ${meta.size}\n`);
console.log('  #  资产                          类型  调用  安装  活跃  频次  有效天');
rows.slice(0, 20).forEach((r, i) => console.log('  ' + String(i + 1).padStart(2) + '  ' + String(r.name).padEnd(26) +
  (r.type === 'expert' ? '专家' : '技能') + String(r.calls).padStart(6) + String(r.ins).padStart(5) +
  String(r.au).padStart(6) + String(Math.round(r.freq * 10) / 10).padStart(6) + String(r.activeDays).padStart(7)));
const t3 = sum(rows.slice(0, 3), 'calls'), tot = sum(rows, 'calls');
console.log(`\n  合计调用 ${tot} ｜ Top3 占比 ${(t3 / tot * 100).toFixed(1)}%`);

if (o['no-report']) process.exit(0);
const out = o.out ? String(o.out) : path.join(HERE, '..', `运营洞察报告-${w30.end}.html`);
fs.writeFileSync(out, report(rows, series, { start: w30.start, end: w30.end, days }));
console.log('\n报告已生成：' + path.resolve(out));
