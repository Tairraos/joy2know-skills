#!/usr/bin/env node
// mureka_check.mjs —— Mureka 双栏提示词结构校验（零依赖，Node 标准库）
//
// 用法：
//   node scripts/mureka_check.mjs <歌词文件> --style "<风格栏全文>" [--title "<歌名>"] [--instrumental] [--loop]
//   node scripts/mureka_check.mjs --selftest
//
// 退出码：0 = 无 FAIL；1 = 有 FAIL（含自检失败）；2 = 用法错误 / 文件读不了
// 纪律：WARN 不影响退出码，但逐条打印（不允许静默）；错误信息必须能指导下一步。

import { readFileSync } from 'node:fs';

// ---------- 工具 ----------

const codePoints = (s) => Array.from(s ?? '').length;
const CJK = /[\u4e00-\u9fff]/;

function parseArgs(argv) {
  const out = { _: [], style: '', title: '', instrumental: false, loop: false, selftest: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--style') out.style = argv[++i] ?? '';
    else if (a === '--title') out.title = argv[++i] ?? '';
    else if (a === '--instrumental') out.instrumental = true;
    else if (a === '--loop') out.loop = true;
    else if (a === '--selftest') out.selftest = true;
    else if (a === '--help' || a === '-h') out.help = true;
    else out._.push(a);
  }
  return out;
}

// 去掉「No vocals / Instrumental」这两个器乐声明词后再查人声词，避免声明本身被误报
function vocalsLeftover(style) {
  const stripped = style.replace(/no\s+vocals?/gi, '').replace(/instrumental/gi, '');
  const m = stripped.match(/vocal|singer|humming|哼唱|人声|歌声/i);
  return m ? m[0] : null;
}

// 去掉「no fade in / no fade out / without fade」这类否定声明后再查淡出，否则声明本身会被当成违规
function hasFadeOut(text) {
  const stripped = (text ?? '')
    .replace(/no\s+fade\s+(in|out)/gi, '')
    .replace(/without\s+fade(\s+(in|out))?/gi, '');
  return /fade\s*out|fading/i.test(stripped);
}

// 按「段落标签」切节统计正文行数（不按空行——实际歌词常不空行分隔，按空行会误报长段）
function maxSectionLines(lyrics) {
  let max = 0;
  let cur = 0;
  for (const raw of lyrics.split('\n')) {
    const l = raw.trim();
    if (l.startsWith('[') && l.endsWith(']')) {
      max = Math.max(max, cur);
      cur = 0;
    } else if (l) {
      cur += 1; // 语言声明句独占开头一「节」，1 行，不会误报
    }
  }
  return Math.max(max, cur);
}

// ---------- 核心校验 ----------

/**
 * @returns {{id:string, level:'FAIL'|'WARN'|'OK', msg:string, hint?:string}[]}
 */
export function checkPack({ lyrics = '', style = '', title = '', instrumental = false, loop = false }) {
  const F = [];
  const add = (id, level, msg, hint) => F.push({ id, level, msg, ...(hint ? { hint } : {}) });

  const tagLines = lyrics.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('[') && l.endsWith(']'));
  const nonTagLines = lyrics
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !(l.startsWith('[') && l.endsWith(']')));
  const hasCJK = CJK.test(lyrics);

  // ---- 歌词栏 ----
  if (codePoints(lyrics) > 5000)
    add('L1', 'FAIL', `歌词 ${codePoints(lyrics)} 字，超过上限 5000`, '砍段或压缩行数——先砍桥段与重复原文照抄段');

  if (!instrumental && hasCJK) {
    const head = lyrics.slice(0, 160);
    const declaresLang = /(简体中文|中文|普通话|国语|粤语|Cantonese)/i.test(head) && /(不要|不用|禁止|避免|别|no\s|without)/i.test(head);
    if (!declaresLang)
      add('L2', 'FAIL', '中文歌词缺语言声明句', '在歌词栏最前加一行：「全部使用简体中文，不要夹杂英文词，不要把拼音写进去。」');
  }

  if (!instrumental) {
    for (const need of ['Intro', 'Chorus', 'Outro']) {
      if (!tagLines.some((t) => new RegExp(`^\\[\\s*${need}\\b`, 'i').test(t)))
        add('L3', 'FAIL', `缺必需段落标签 [${need}]`, `有人声包 ${need} 不可省；精简版至少保留 Intro + Chorus + Outro`);
    }
  }

  const chorusCount = tagLines.filter((t) => /^\[\s*chorus\b/i.test(t)).length;
  if (!instrumental && chorusCount >= 2 && !/重复|repeat/i.test(lyrics))
    add('L4', 'WARN', `副歌出现 ${chorusCount} 次但全篇没有「重复 / Repeat」标注`, '第二遍副歌写「[Chorus – 重复上面的副歌（，末句改成…）]」或原文照抄');

  if (!instrumental) {
    const maxLines = maxSectionLines(lyrics);
    if (maxLines > 8) add('L5', 'WARN', `最长一节有 ${maxLines} 行（建议每段 4–6 行）`, '中文长段是吞字重灾区；拆成两段或删到 6 行以内');
  }

  // ---- 风格栏 ----
  if (codePoints(style) > 1000) add('S1', 'FAIL', `风格栏 ${codePoints(style)} 字，超过上限 1000`, '并句删冗词，别删信息块');
  if (!/\b\d{2,3}\s*BPM\b|\bBPM\s*\d{2,3}\b/i.test(style))
    add('S2', 'FAIL', '风格栏没有 BPM', '写具体数字或窄区间，如「88 BPM」「BPM 92 to 98」；循环包必须写死单个数字');
  if (!/(female|male)\s+vocal|no\s+vocals|instrumental/i.test(style))
    add('S3', 'FAIL', '风格栏没有人声声明', '写「female vocal / male vocal」；器乐写「No vocals」');

  if (instrumental) {
    if (!/no\s+vocals|instrumental/i.test(style))
      add('S4', 'FAIL', '器乐包风格栏缺「No vocals」首句', '首句写 No vocals（或 Instrumental），并提醒用户打开「纯音乐」开关');
    const leftover = vocalsLeftover(style);
    if (leftover)
      add('S4', 'FAIL', `器乐包风格栏出现人声词「${leftover}」`, '删光所有人声词——写了就等于让模型用哼唱把人声补回来');
    if (nonTagLines.length > 0)
      add('X1', 'FAIL', `器乐包歌词栏方括号外有内容（首处：「${nonTagLines[0].slice(0, 20)}…」）`, '清空歌词栏或只留段落标签；同时提醒打开「纯音乐」开关');
  }

  if (loop) {
    if (!/seamless\s+loop/i.test(style))
      add('S5', 'FAIL', '循环包风格栏缺「seamless loop」', '写「seamless loop, no fade in, no fade out」');
    if (hasFadeOut(style)) add('S5', 'FAIL', '风格栏出现 fade out', '循环素材禁淡出：结尾段写「回到开头的和弦与织体、干净切断」');
    if (hasFadeOut(tagLines.join('\n'))) {
      const bad = tagLines.find((t) => /fade\s*out|fading/i.test(t));
      add('S5', 'FAIL', `段落标签出现 fade out（${bad}）`, '循环素材禁淡出：结尾段写「回到开头的和弦与织体、干净切断」');
    }
    if (/BPM\s*\d{2,3}\s*(to|-|–|~)\s*\d{2,3}/i.test(style) || /\d{2,3}\s*(to|-|–|~)\s*\d{2,3}\s*BPM/i.test(style))
      add('S5', 'FAIL', '循环包 BPM 写成了区间', '循环点要落在小节上，BPM 必须写死单个数字');
  }

  if (/standard\s+mandarin\s+enunciation|language\s*:/i.test(style))
    add('W1', 'WARN', '风格栏出现 Suno 式语言锁（Standard Mandarin Enunciation / Language:）', 'Mureka 的人声语言靠歌词栏语言声明体现，风格栏只管曲风与人声质感——删掉这段');

  // ---- 标题 ----
  if (title && codePoints(title) > 50) add('T1', 'FAIL', `歌名 ${codePoints(title)} 字，超过上限 50`, '改短歌名');

  return F;
}

// ---------- 报告 ----------

function report(findings) {
  const fails = findings.filter((f) => f.level === 'FAIL');
  const warns = findings.filter((f) => f.level === 'WARN');
  if (findings.length === 0) {
    console.log('[OK] 全部检查通过（0 FAIL / 0 WARN）');
  } else {
    for (const f of findings) {
      const tag = f.level === 'FAIL' ? '[FAIL]' : '[WARN]';
      console.log(`${tag} ${f.id} ${f.msg}`);
      if (f.hint) console.log(`       ↳ ${f.hint}`);
    }
    console.log(`—— ${fails.length} FAIL / ${warns.length} WARN ——`);
  }
  return fails.length > 0 ? 1 : 0;
}

// ---------- 自检 ----------

const VOCAL_STYLE =
  'Mandarin folk blues, 88 BPM, emotional male vocal, fingerpicked guitar + harmonica + brushed drums, warm and wistful, late-night kitchen scene, intimate room reverb';
const VOCAL_LYRICS = `全部使用简体中文，不要夹杂英文词，不要把拼音写进去。

[Intro – 安静的吉他]
[Verse 1 – 半念半唱]
锅铲刮过锅底的声响
是这十年最安稳的闹钟
[Chorus – 开阔，开口韵]
原来最拥挤的
是深夜里没有人的巷
[Chorus – 重复上面的副歌]
[Outro – 渐弱，只剩吉他]
比相爱更勇敢`;

export function selftest() {
  const cases = [];
  const t = (name, fn) => cases.push({ name, fn });

  const ids = (r, level) => r.filter((f) => f.level === level).map((f) => f.id);
  const has = (r, level, id) => r.some((f) => f.level === level && f.id === id);

  t('正常有人声包 → 无 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE, title: '深夜厨房' });
    if (ids(r, 'FAIL').length !== 0) return `应无 FAIL，实得 ${JSON.stringify(ids(r, 'FAIL'))}`;
  });
  t('正常有人声包（4 行一节）→ 无 L5 WARN', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE });
    if (has(r, 'WARN', 'L5')) return `规范 4 行一节不该报长段，实得：${r.find((f) => f.id === 'L5').msg}`;
  });
  t('「no fade out」声明本身不触发淡出检查', () => {
    const style = 'No vocals, Ambient, 72 BPM, solo grand piano, calm, seamless loop, no fade in, no fade out';
    const r = checkPack({ lyrics: '', style, instrumental: true, loop: true });
    const fadeFails = r.filter((f) => f.level === 'FAIL' && f.id === 'S5' && /fade/.test(f.msg));
    if (fadeFails.length !== 0) return `否定声明被误报：${JSON.stringify(fadeFails.map((f) => f.msg))}`;
  });
  t('正常有人声包 → 重复标注被识别（无 L4 WARN）', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE });
    if (has(r, 'WARN', 'L4')) return '已有「重复上面的副歌」，不应报 L4';
  });
  t('中文歌词缺语言声明 → L2 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS.replace(/^全部使用简体中文.*\n+/m, ''), style: VOCAL_STYLE });
    if (!has(r, 'FAIL', 'L2')) return '应报 L2';
  });
  t('缺 [Outro] → L3 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS.replace(/\[Outro[^\n]*\]\n比相爱更勇敢/, ''), style: VOCAL_STYLE });
    if (!has(r, 'FAIL', 'L3')) return '应报 L3';
  });
  t('风格栏无 BPM → S2 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE.replace(', 88 BPM,', ',') });
    if (!has(r, 'FAIL', 'S2')) return '应报 S2';
  });
  t('风格栏无人声声明 → S3 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: 'Mandarin folk blues, 88 BPM, fingerpicked guitar, warm, room reverb' });
    if (!has(r, 'FAIL', 'S3')) return '应报 S3';
  });
  t('风格栏超 1000 字 → S1 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE + ' extra '.repeat(200) });
    if (!has(r, 'FAIL', 'S1')) return '应报 S1';
  });
  t('歌词超 5000 字 → L1 FAIL', () => {
    const long = VOCAL_LYRICS + '\n' + '一'.repeat(5100);
    const r = checkPack({ lyrics: long, style: VOCAL_STYLE });
    if (!has(r, 'FAIL', 'L1')) return '应报 L1';
  });
  t('副歌两遍无重复标注 → L4 WARN', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS.replace('[Chorus – 重复上面的副歌]', '[Chorus – Final]'), style: VOCAL_STYLE });
    if (!has(r, 'WARN', 'L4')) return '应报 L4 WARN';
  });
  t('Suno 语言锁混入风格栏 → W1 WARN', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE + ', Standard Mandarin Enunciation' });
    if (!has(r, 'WARN', 'W1')) return '应报 W1';
  });
  t('正常器乐包 → 无 FAIL', () => {
    const style = 'No vocals, Ambient Cinematic, 72 BPM, solo grand piano + warm pads + subtle cello, calm and spacious, wide reverb, seamless loop';
    const r = checkPack({ lyrics: '[Intro – Solo piano]\n[End – Return to opening chord, clean cut]', style, instrumental: true, loop: true });
    if (ids(r, 'FAIL').length !== 0) return `应无 FAIL，实得 ${JSON.stringify(ids(r, 'FAIL'))}`;
  });
  t('器乐包风格栏带人声词 → S4 FAIL', () => {
    const style = 'No vocals, Ambient, 72 BPM, soft female vocal + piano, calm, wide reverb';
    const r = checkPack({ lyrics: '', style, instrumental: true });
    if (!has(r, 'FAIL', 'S4')) return '应报 S4';
  });
  t('器乐包缺 No vocals → S4 FAIL', () => {
    const r = checkPack({ lyrics: '', style: 'Ambient Cinematic, 72 BPM, solo grand piano, calm, wide reverb', instrumental: true });
    if (!has(r, 'FAIL', 'S4')) return '应报 S4';
  });
  t('器乐包歌词栏有正文 → X1 FAIL', () => {
    const style = 'No vocals, Ambient, 72 BPM, solo grand piano, calm';
    const r = checkPack({ lyrics: '这一行不该出现', style, instrumental: true });
    if (!has(r, 'FAIL', 'X1')) return '应报 X1';
  });
  t('循环包带 fade out → S5 FAIL', () => {
    const style = 'No vocals, Ambient, 72 BPM, solo grand piano, calm, seamless loop';
    const r = checkPack({ lyrics: '[Intro – Piano]\n[Outro – Fade out]', style, instrumental: true, loop: true });
    if (!has(r, 'FAIL', 'S5')) return '应报 S5';
  });
  t('循环包 BPM 写区间 → S5 FAIL', () => {
    const style = 'No vocals, Ambient, BPM 70 to 80, solo grand piano, calm, seamless loop, no fade out';
    const r = checkPack({ lyrics: '', style, instrumental: true, loop: true });
    if (!has(r, 'FAIL', 'S5')) return '应报 S5';
  });
  t('循环包缺 seamless loop → S5 FAIL', () => {
    const style = 'No vocals, Ambient, 72 BPM, solo grand piano, calm, no fade out';
    const r = checkPack({ lyrics: '', style, instrumental: true, loop: true });
    if (!has(r, 'FAIL', 'S5')) return '应报 S5';
  });
  t('歌名超 50 字 → T1 FAIL', () => {
    const r = checkPack({ lyrics: VOCAL_LYRICS, style: VOCAL_STYLE, title: '名'.repeat(51) });
    if (!has(r, 'FAIL', 'T1')) return '应报 T1';
  });
  t('空输入 → 至少 3 条 FAIL（不静默放行）', () => {
    const r = checkPack({ lyrics: '', style: '', instrumental: false });
    if (ids(r, 'FAIL').length < 3) return `空输入应至少 3 条 FAIL，实得 ${JSON.stringify(ids(r, 'FAIL'))}`;
  });

  let bad = 0;
  for (const c of cases) {
    try {
      const err = c.fn();
      if (err) {
        bad++;
        console.log(`[FAIL] 自检项「${c.name}」：${err}`);
      }
    } catch (e) {
      bad++;
      console.log(`[FAIL] 自检项「${c.name}」抛异常：${e && e.message}`);
    }
  }
  if (bad === 0) console.log(`自检 ${cases.length} 项全部通过`);
  return bad === 0 ? 0 : 1;
}

// ---------- 入口 ----------

const args = parseArgs(process.argv.slice(2));
if (args.selftest) {
  process.exit(selftest());
}
if (args.help || args._.length !== 1) {
  console.error('用法：node scripts/mureka_check.mjs <歌词文件> --style "<风格栏全文>" [--title "<歌名>"] [--instrumental] [--loop]');
  console.error('      node scripts/mureka_check.mjs --selftest');
  console.error('退出码：0=无 FAIL；1=有 FAIL；2=用法错误');
  process.exit(2);
}
if (!args.style) {
  console.error('[FAIL] 缺 --style 参数——器乐声明、BPM、循环约束只有拿到风格栏全文才查得出来，别省');
  process.exit(2);
}
let lyrics;
try {
  lyrics = readFileSync(args._[0], 'utf8');
} catch (e) {
  console.error(`[FAIL] 读不了歌词文件「${args._[0]}」：${e.message}——确认路径，或把歌词栏文本存成 txt 再跑`);
  process.exit(2);
}
process.exit(report(checkPack({ lyrics, style: args.style, title: args.title, instrumental: args.instrumental, loop: args.loop })));
