#!/usr/bin/env node
/**
 * 晓得·天音音乐人 · 结构校验器（tianyin_check.mjs）
 *
 * 校验「可直接粘贴进网易天音 AI作歌」的交付文本：
 *   - 简易模式：主输入 = 位置参数文件（创作灵感，≤1000 字）
 *   - 高级模式：主输入 = --style（风格描述，≤1000 字）+ 位置参数文件（歌词）
 *   - 控件回传：--title / --singer / --tag / --instrumental / --chorus-first
 *
 * 判据来源（2026-10-18 登录态真机实测，DOM maxlength 与控件行为）：
 *   灵感 1000 · 风格描述 1000 · 歌名 30 · 18 风格标签（单选）· 18 虚拟歌手 ·
 *   纯音乐开关只在简易模式 · 参考音频 WAV/FLAC/MP3/AAC/M4A/OGG 30s-10min ≤100MB
 *
 * 零第三方依赖：只 import node:fs。无网络、无账号、无密钥、无额度。
 *
 * 退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 用法错误（缺 --mode / 文件不存在 / --selftest 失败）
 */
import { readFileSync, existsSync } from 'node:fs';

const MAX_MAIN = 1000;   // 灵感 / 风格描述上限（DOM maxlength 实测）
const MAX_TITLE = 30;    // 歌名上限（DOM maxlength 实测）
const SECTION_LINES = [4, 8]; // 每段行数建议区间（写法规则，非平台硬限制）
const MIN_MAIN = 20;     // 主输入短于此长度 → 四要素写不全（WARN）

// 18 个风格标签（2026-10-18 实测；平台会变，故未知标签只 WARN 不 FAIL）
const STYLE_TAGS = [
  '黑人福音', 'R&B', '网感流行', '摇滚', '欢乐儿歌', 'DJ', '氛围雷击顿', '抒情流行',
  '蒸汽波', 'hip-hop', 'kpop', '孟菲斯说唱', '怀旧港风', '现代流行', '民谣', '爵士',
  '国风', 'J-pop',
];

// 18 位虚拟歌手（2026-10-18 实测弹层；同上，未知只 WARN）
const SINGERS = [
  '普兰', '李秋彦', '季然', '欧阳山姆', '代代', '郑同', '许冠一', 'MC阿威',
  '佳欣', '波波', '布布', '于潇潇', '瑞克', '林小甜', '祝宁', '林婉非',
  '阿宽哥', '仁泽',
];

// 中文歌语言声明（命中任一即算有）
const LANG_DECL = ['全部使用简体中文', '全部使用中文', '简体中文演唱', '用中文唱'];
const EN_DECL = ['Sing in English', 'English lyrics', 'sing in english'];
// 无人声意向（纯音乐路线主输入里应出现）
const NO_VOCAL = ['不要人声', '无人声', '纯音乐', '纯器乐', ' instrumental', 'instrumental', 'no vocal'];
// 承诺词（防幻觉：交付文本不许承诺生成效果）
const PROMISE_WORDS = ['保证能出', '一定能出', '百分百出', '保证生成出', '必定会出'];

// 段落标记：[段名] 或 【段名】。段名上限 40 字——必须装得下
// 「副歌 – 重复上面的副歌，末句改成「比相爱更勇敢」」这类带重复标注的长标记
// （2026-10-18 首轮上限写 20，长标记被当歌词行吞掉、段行数误报，CLI 真跑抓到）
const SECTION_RE = /^\s*[\[【]([^\]】]{1,40})[\]】]/;

function parseArgs(argv) {
  const args = { _: [], mode: null, style: null, title: null, singer: null, tag: null,
                 instrumental: false, chorusFirst: false, selftest: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--mode') args.mode = argv[++i];
    else if (a === '--style') args.style = argv[++i];
    else if (a === '--title') args.title = argv[++i];
    else if (a === '--singer') args.singer = argv[++i];
    else if (a === '--tag') args.tag = argv[++i];
    else if (a === '--instrumental') args.instrumental = true;
    else if (a === '--chorus-first') args.chorusFirst = true;
    else if (a === '--selftest') args.selftest = true;
    else if (a === '--help' || a === '-h') args.help = true;
    else if (a.startsWith('--')) return { error: `未知参数 ${a}` };
    else args._.push(a);
  }
  return args;
}

function charLen(s) { return [...s].length; }

/** 按段落标记切节，返回 [{name, lines[]}]；无标记时整篇算一节 */
function splitSections(text) {
  const lines = text.split(/\r?\n/);
  const sections = [];
  let cur = null;
  for (const line of lines) {
    const m = line.match(SECTION_RE);
    if (m) {
      cur = { name: m[1].trim(), lines: [] };
      sections.push(cur);
    } else {
      if (!cur) { cur = { name: '(无标记)', lines: [] }; sections.push(cur); }
      if (line.trim()) cur.lines.push(line.trim());
    }
  }
  return sections.filter(s => s.lines.length > 0 || sections.length > 1 || s.name !== '(无标记)');
}

function runChecks(fileText, rawArgs) {
  // 默认值归一：调用方（含 --selftest 用例）可能省略键，省略必须等价于「未传」。
  // ⚠ 不能写 `args.x !== null` 判「传没传」——省略的键是 undefined，!== null 会漏过去再 .trim() 崩。
  const args = {
    mode: null, style: null, title: null, singer: null, tag: null,
    instrumental: false, chorusFirst: false, ...rawArgs,
  };
  const R = [];
  const fail = (id, msg, hint) => R.push({ id, level: 'FAIL', msg, hint });
  const warn = (id, msg, hint) => R.push({ id, level: 'WARN', msg, hint });
  const info = (id, msg) => R.push({ id, level: 'INFO', msg });

  // ---- 模式 ----
  if (args.mode !== 'simple' && args.mode !== 'advanced') {
    fail('M1', `--mode 必填且只能是 simple 或 advanced（当前 ${args.mode === null ? '缺失' : args.mode}）`,
      '简易模式传 --mode simple；高级模式传 --mode advanced');
    return { results: R, fail: 1, warn: 0 };
  }

  // ---- 主输入长度 ----
  if (args.mode === 'simple') {
    if (args.style !== null) {
      warn('A2', '简易模式没有「风格描述」栏——--style 的内容应写进创作灵感一段话',
        '把风格四要素并进灵感文本；要走高级双栏请改 --mode advanced');
    }
    if (charLen(fileText) > MAX_MAIN) {
      fail('S1', `创作灵感 ${charLen(fileText)} 字 > ${MAX_MAIN} 字上限（DOM maxlength 实测）`,
        '压到四要素一句式：曲风 + 乐器 + 人声 + 情绪氛围，删冗词不删信息');
    } else if (charLen(fileText) < MIN_MAIN) {
      warn('S0', `创作灵感只有 ${charLen(fileText)} 字——四要素（曲风/乐器/人声/氛围）大概写不全`,
        '至少补到 20 字以上；用户只说一两个词时，由你补全并写进「假设与待替换」');
    }
  } else {
    if (args.style === null || args.style === '') {
      fail('A1', '高级模式必填 --style（风格描述全文）', '把风格描述四要素一句式完整传给 --style');
    } else if (charLen(args.style) > MAX_MAIN) {
      fail('A1', `风格描述 ${charLen(args.style)} 字 > ${MAX_MAIN} 字上限（DOM maxlength 实测）`,
        '删冗词不删信息；四要素齐即可，不必堆满上限');
    }
  }

  // ---- 歌词栏（高级 + 有人声）----
  if (args.mode === 'advanced' && !args.instrumental) {
    const sections = splitSections(fileText);
    const tagged = sections.filter(s => s.name !== '(无标记)').length;
    if (tagged < 2) {
      warn('L1', `歌词只有 ${tagged} 个段落标记——天音不强制标签，但标记能减少结构误判`,
        '段首独立行写 [主歌]/[副歌]/[桥段] 等，全篇统一中或英一种');
    }
    for (const s of sections) {
      if (s.name === '(无标记)') continue;
      if (s.lines.length < SECTION_LINES[0] || s.lines.length > SECTION_LINES[1]) {
        warn('L2', `段落「${s.name}」${s.lines.length} 行，超出 ${SECTION_LINES[0]}–${SECTION_LINES[1]} 行建议区间`,
          '并段或拆段；行太长也是吞字主因，靠标点自然断句');
      }
    }
    const hasDecl = LANG_DECL.some(d => fileText.includes(d)) || EN_DECL.some(d => fileText.includes(d));
    if (!hasDecl) {
      warn('L3', '歌词栏未见语言声明句', '中文歌在最前写「全部使用简体中文」；英文歌写 Sing in English.');
    }
    const chorusCount = sections.filter(s => /副歌|chorus/i.test(s.name)).length;
    if (chorusCount >= 2 && !/重复/.test(fileText)) {
      warn('L4', `副歌出现 ${chorusCount} 次但全文没有「重复」标注`,
        '第二遍副歌写「[副歌 – 重复上面的副歌]」或原文照抄，不许让模型猜');
    }
  }

  // ---- 纯音乐路线 ----
  if (args.instrumental) {
    // I1 只对高级模式成立：高级模式的位置参数才是「歌词栏」。
    // 简易模式的位置参数是「创作灵感」（主输入），永远不该为空，不在此列。
    if (args.mode === 'advanced' && fileText.trim() !== '') {
      fail('I1', '纯音乐路线歌词栏必须留空——没人唱，贴词会招来人声',
        '删掉歌词栏内容；器乐意图全部写进主输入（简易：灵感；高级：风格描述）');
    }
    const main = args.mode === 'simple' ? fileText : (args.style || '');
    if (!NO_VOCAL.some(w => main.toLowerCase().includes(w.toLowerCase().trim()))) {
      warn('I2', '纯音乐路线的主输入里未见无人声意向（不要人声/纯音乐/纯器乐）',
        '在主输入里明写「不要人声」；并确认简易模式「纯音乐」开关已打开');
    }
    if (args.mode === 'advanced') {
      warn('I0', '高级模式没有「纯音乐」开关（实测）——器乐路线优先走简易模式开关',
        '仍用高级模式时，把「纯音乐、不要人声」写进风格描述并注明「以你当前界面为准」');
    }
  }

  // ---- 控件回传 ----
  if (args.title !== null && charLen(args.title) > MAX_TITLE) {
    fail('T1', `歌名 ${charLen(args.title)} 字 > ${MAX_TITLE} 字上限（DOM maxlength 实测）`, '压到 30 字以内，或留空');
  } else if (args.title === null) {
    warn('T0', '未传 --title（歌名可留空，但交付清单里应给出建议歌名）', '给一个 ≤30 字的建议歌名，或明确写「留空」');
  }
  if (args.singer !== null) {
    if (args.mode === 'simple') {
      warn('V2', '简易模式没有「虚拟歌手音色」选择器（实测在高级模式）',
        '想指定歌手请改走高级模式；简易模式只写灵感 + 纯音乐开关');
    } else if (!SINGERS.includes(args.singer.trim())) {
      warn('V1', `虚拟歌手「${args.singer}」不在 2026-10-18 实测的 18 人名单里`,
        '平台会增减歌手：以用户当前界面为准；确认名字无误再交付');
    }
  }
  if (args.tag !== null && !STYLE_TAGS.includes(args.tag.trim())) {
    warn('G1', `风格标签「${args.tag}」不在 2026-10-18 实测的 18 个标签里`,
      '平台会更新标签：以用户当前界面为准；新标签按其声线描述现场适配');
  }
  if (args.chorusFirst) {
    info('C1', '副歌前置已开启——平台会自动识别副歌并前置：确认副歌有一句 3–9 字能独立站住的钩子');
  }

  // ---- 防幻觉：承诺词 ----
  for (const w of PROMISE_WORDS) {
    if (fileText.includes(w) || (args.style || '').includes(w)) {
      warn('P1', `交付文本出现承诺词「${w}」`, '改为「建议同版生成 2–3 次挑一版」；AI 音乐有随机性');
      break;
    }
  }

  const f = R.filter(r => r.level === 'FAIL').length;
  const w = R.filter(r => r.level === 'WARN').length;
  return { results: R, fail: f, warn: w };
}

function report(res) {
  const L = [];
  for (const r of res.results) {
    const mark = r.level === 'FAIL' ? '✗' : r.level === 'WARN' ? '!' : '·';
    L.push(`  [${r.level}] ${mark} ${r.id} ${r.msg}`);
    if (r.hint) L.push(`      ↳ ${r.hint}`);
  }
  L.push('');
  if (res.fail > 0) L.push(`[FAIL] ${res.fail} 项必须修完才能交付`);
  else if (res.warn > 0) L.push(`[OK] 无 FAIL；${res.warn} 项 WARN 需逐条给出处理说明`);
  else L.push('[OK] 全部检查通过');
  return L.join('\n');
}

function ids(res, level) { return res.results.filter(r => r.level === level).map(r => r.id); }

// ------------------------------------------------------------------
// 自检：内置正反样本。每条用例断言「某些 id 必须出现 / 必须不出现」。
// ⚠ 断言一律用 ids(res,'FAIL').includes(...) —— 不许用「含子串」式两参调用
// （历史上 has(r,'FAIL') 两参恒 false，用例从诞生起就测不出错）。
// ------------------------------------------------------------------
function selftest() {
  const cases = [];
  const T = (name, fn) => cases.push({ name, fn });

  const goodLyric = `全部使用简体中文。

[主歌 – 半念半唱，贴近话筒]
锅铲刮过锅底的声响
是这十年最安稳的闹钟
油锅滋啦滋啦地响
你在楼下喊我小名

[副歌 – 开阔，开口韵]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
长到能盖住这十年`;

  T('正常高级有人声包 → 0 FAIL / 0 WARN', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '都市 R&B，用吉他伴奏和清澈男声演唱，要那种浪漫又心动的 Vibe，中速，三分钟上下。', title: '晚风很轻', singer: '许冠一', tag: 'R&B' });
    if (ids(res, 'FAIL').length !== 0) throw new Error(`不应有 FAIL：${ids(res, 'FAIL')}`);
    if (ids(res, 'WARN').length !== 0) throw new Error(`不应有 WARN：${ids(res, 'WARN')}`);
  });

  T('正常简易模式包 → 0 FAIL / 0 WARN', () => {
    const res = runChecks('民谣，木吉他指弹伴奏，温暖女声轻轻唱，像夏夜阳台聊天一样松弛，三分钟上下。', { mode: 'simple', title: '夏夜阳台' });
    if (ids(res, 'FAIL').length !== 0 || ids(res, 'WARN').length !== 0) throw new Error(`不应有 FAIL/WARN：${ids(res, 'FAIL')} ${ids(res, 'WARN')}`);
  });

  T('高级缺 --style → A1 FAIL', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: null, title: 'x' });
    if (!ids(res, 'FAIL').includes('A1')) throw new Error('应报 A1');
  });

  T('灵感超 1000 字 → S1 FAIL', () => {
    const res = runChecks('词'.repeat(1001), { mode: 'simple', title: 'x' });
    if (!ids(res, 'FAIL').includes('S1')) throw new Error('应报 S1');
  });

  T('灵感 1000 字整（边界）→ 不报 S1', () => {
    const res = runChecks('词'.repeat(1000), { mode: 'simple', title: 'x' });
    if (ids(res, 'FAIL').includes('S1')) throw new Error('边界值不应报 S1');
  });

  T('风格描述超 1000 字 → A1 FAIL', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '风'.repeat(1001), title: 'x' });
    if (!ids(res, 'FAIL').includes('A1')) throw new Error('应报 A1');
  });

  T('歌名超 30 字 → T1 FAIL', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '歌'.repeat(31) });
    if (!ids(res, 'FAIL').includes('T1')) throw new Error('应报 T1');
  });

  T('缺 --mode → M1 FAIL', () => {
    const res = runChecks(goodLyric, { mode: null });
    if (!ids(res, 'FAIL').includes('M1')) throw new Error('应报 M1');
  });

  T('歌词无段落标记 → L1 WARN', () => {
    const res = runChecks('全部使用简体中文。\n锅铲刮过锅底的声响\n是这十年最安稳的闹钟\n油锅滋啦滋啦地响\n你在楼下喊我小名', { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '无标记' });
    if (!ids(res, 'WARN').includes('L1')) throw new Error('应报 L1');
  });

  T('歌词缺语言声明 → L3 WARN', () => {
    const noDecl = goodLyric.replace('全部使用简体中文。\n\n', '');
    const res = runChecks(noDecl, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '无声声明' });
    if (!ids(res, 'WARN').includes('L3')) throw new Error('应报 L3');
  });

  T('副歌两遍无重复标注 → L4 WARN', () => {
    const two = `全部使用简体中文。

[主歌]
锅铲刮过锅底的声响
是这十年最安稳的闹钟
油锅滋啦滋啦地响
你在楼下喊我小名

[副歌]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
长到能盖住这十年

[副歌]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
长到能盖住这十年`;
    const res = runChecks(two, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '重复' });
    if (!ids(res, 'WARN').includes('L4')) throw new Error('应报 L4');
  });

  T('副歌两遍 + 显式重复标注 → 不报 L4', () => {
    const two = goodLyric + `

[副歌 – 重复上面的副歌]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
长到能盖住这十年`;
    const res = runChecks(two, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '重复' });
    if (ids(res, 'WARN').includes('L4')) throw new Error('有显式重复标注不应报 L4');
  });

  T('段落 10 行超区间 → L2 WARN', () => {
    const long = '全部使用简体中文。\n\n[主歌]\n' + Array.from({ length: 10 }, (_, i) => `第${i + 1}行歌词`).join('\n');
    const res = runChecks(long, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '长段' });
    if (!ids(res, 'WARN').includes('L2')) throw new Error('应报 L2');
  });

  T('纯音乐路线歌词栏有词 → I1 FAIL', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '纯音乐，只有钢琴和轻雨声，不要人声。', instrumental: true, title: '器乐' });
    if (!ids(res, 'FAIL').includes('I1')) throw new Error('应报 I1');
  });

  T('纯音乐路线歌词栏空 + 风格声明齐（高级）→ 0 FAIL', () => {
    const res = runChecks('', { mode: 'advanced', style: '纯音乐，只有钢琴和轻雨声，不要人声，循环着放也不违和。', instrumental: true, title: '器乐' });
    if (ids(res, 'FAIL').length !== 0) throw new Error(`不应有 FAIL：${ids(res, 'FAIL')}`);
  });

  T('纯音乐路线主输入无无人声意向 → I2 WARN', () => {
    const res = runChecks('深夜书房专注背景音乐，只有钢琴和轻雨声，循环着放也不违和。', { mode: 'simple', style: null, instrumental: true, title: '器乐' });
    if (!ids(res, 'WARN').includes('I2')) throw new Error('应报 I2');
  });

  T('简易模式纯音乐包（灵感写全无人声意向）→ 0 FAIL / 0 WARN', () => {
    const res = runChecks('深夜书房专注背景音乐，只有钢琴和轻雨声，不要人声，循环着放也不违和，一小时起步。', { mode: 'simple', style: null, instrumental: true, title: '夜雨钢琴' });
    if (ids(res, 'FAIL').length !== 0 || ids(res, 'WARN').length !== 0) throw new Error(`不应有 FAIL/WARN：${ids(res, 'FAIL')} ${ids(res, 'WARN')}`);
  });

  T('长重复标注段名（25 字）必须被识别为段 → 不误报 L2', () => {
    const longTag = `全部使用简体中文。

[主歌]
锅铲刮过锅底的声响
是这十年最安稳的闹钟
油锅滋啦滋啦地响
你在楼下喊我小名

[副歌]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
长到能盖住这十年

[副歌 – 重复上面的副歌，末句改成「比相爱更勇敢」]
晚风把话吹得很轻
我们装作没听见
路灯把影子拉得很长
比相爱更勇敢`;
    const res = runChecks(longTag, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: '长标注' });
    if (ids(res, 'WARN').includes('L2')) throw new Error('长标注段被吞成歌词行才会报 L2——段名上限已放到 40 字');
    if (ids(res, 'WARN').includes('L4')) throw new Error('有显式重复标注不应报 L4');
  });

  T('未知歌手 → V1 WARN', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: 'x', singer: '张未知' });
    if (!ids(res, 'WARN').includes('V1')) throw new Error('应报 V1');
  });

  T('已知歌手 → 不报 V1', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: 'x', singer: '祝宁' });
    if (ids(res, 'WARN').includes('V1')) throw new Error('已知歌手不应报 V1');
  });

  T('简易模式传 --style → A2 WARN', () => {
    const res = runChecks('民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', { mode: 'simple', style: '都市 R&B', title: 'x' });
    if (!ids(res, 'WARN').includes('A2')) throw new Error('应报 A2');
  });

  T('未知标签 → G1 WARN', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: 'x', tag: '城市blr' });
    if (!ids(res, 'WARN').includes('G1')) throw new Error('应报 G1');
  });

  T('副歌前置 → C1 INFO', () => {
    const res = runChecks(goodLyric, { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: 'x', chorusFirst: true });
    if (!ids(res, 'INFO').includes('C1')) throw new Error('应报 C1');
  });

  T('承诺词 → P1 WARN', () => {
    const res = runChecks(goodLyric + '\n这条保证能出你要的效果。', { mode: 'advanced', style: '民谣，木吉他指弹伴奏，温暖女声轻轻唱，松弛氛围，中速。', title: 'x' });
    if (!ids(res, 'WARN').includes('P1')) throw new Error('应报 P1');
  });

  let pass = 0;
  for (const c of cases) {
    try { c.fn(); console.log(`  ✓ ${c.name}`); pass++; }
    catch (e) { console.log(`  ✗ ${c.name} —— ${e.message}`); }
  }
  console.log(`\n自检 ${pass}/${cases.length} 项通过`);
  return pass === cases.length ? 0 : 1;
}

// ------------------------------------------------------------------
function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(`用法：node tianyin_check.mjs <歌词或灵感文件> --mode simple|advanced [选项]

  --style "<风格描述全文>"   高级模式必填
  --title "<歌名>"            ≤30 字
  --singer "<歌手名>"         18 位之一（见 references/singer-cookbook.md）
  --tag "<风格标签>"          18 个之一（见 references/style-tags.md）
  --instrumental             纯音乐路线（歌词栏必须留空）
  --chorus-first             副歌前置开启
  --selftest                 内置正反样本自检
  --help                     本帮助

退出码：0 无 FAIL · 1 有 FAIL · 2 用法错误`);
    return 0;
  }
  if (args.selftest) return selftest();
  if (args.error) { console.log(`用法错误：${args.error}\n跑 --help 看完整用法。`); return 2; }
  if (args.mode !== 'simple' && args.mode !== 'advanced') {
    console.log(`用法错误：--mode 必填且只能是 simple 或 advanced（当前 ${args.mode === null ? '缺失' : args.mode}）\n` +
      `  简易模式：--mode simple（位置参数 = 创作灵感全文）\n` +
      `  高级模式：--mode advanced --style "<风格描述全文>"（位置参数 = 歌词全文）\n跑 --help 看完整用法。`);
    return 2;
  }
  if (args._.length === 0) { console.log('用法错误：缺少位置参数（歌词或灵感文本文件）。跑 --help 看完整用法。'); return 2; }
  const file = args._[0];
  if (!existsSync(file)) { console.log(`用法错误：文件不存在 —— ${file}`); return 2; }
  let text;
  try { text = readFileSync(file, 'utf8'); }
  catch (e) { console.log(`用法错误：读不了文件 ${file} —— ${e.message}`); return 2; }
  // 空文件只在「高级模式 + 纯音乐」时合法（歌词栏留空）；其余一律 FAIL，不静默放行
  if (text.trim() === '' && !(args.mode === 'advanced' && args.instrumental)) {
    console.log(`[FAIL] 文件内容为空：${file}\n` +
      `  ↳ 空输入不静默放行。简易模式的位置参数是创作灵感（必填）；` +
      `高级模式的歌词栏留空只允许纯音乐路线（--instrumental）。`);
    return 1;
  }
  const res = runChecks(text, args);
  console.log(report(res));
  return res.fail > 0 ? 1 : 0;
}

process.exit(main());
