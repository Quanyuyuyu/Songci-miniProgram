// 题壁数据加工：日期格式化、署名词牌雅号、留言排序
// 抽为独立模块，便于页面复用与离线自测（tools/test_board.js）

// 词牌雅号池：与 ci-index 的 14 张词牌卡呼应。
// 署名留言若未指定 penName，按 id 稳定映射一个（同一条留言每次渲染结果一致）。
const PEN_NAMES = [
  '鹧鸪天', '踏莎行', '浣溪沙', '临江仙', '蝶恋花', '水调歌头',
  '念奴娇', '如梦令', '卜算子', '青玉案', '一剪梅', '满庭芳',
  '声声慢', '扬州慢'
];

function hashCode(s) {
  let h = 0;
  const str = String(s || '');
  for (let i = 0; i < str.length; i += 1) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h;
}

// '2026-09-06' → '9月6日'；跨年则显示为 '2025年12月8日'
function formatDate(iso) {
  if (!iso) return '';
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(String(iso).trim());
  if (!m) return String(iso);
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const prefix = y === new Date().getFullYear() ? '' : y + '年';
  return prefix + mo + '月' + d + '日';
}

// 原始 messages → 渲染用留言列表（最新在前，同日期后发布者在前）
function normalize(raw) {
  const list = Array.isArray(raw && raw.messages) ? raw.messages : [];
  const rows = [];
  list.forEach((m, i) => {
    const content = typeof m.content === 'string' ? m.content.trim() : '';
    if (!content) return;
    const id = m.id || ('m' + (i + 1));
    const penName = m.penName || PEN_NAMES[hashCode(id) % PEN_NAMES.length];
    rows.push({
      id: id,
      content: content,
      dateText: formatDate(m.date),
      nameText: m.anonymous ? '佚名' : penName,
      _date: String(m.date || ''),
      _order: i
    });
  });
  rows.sort((a, b) => {
    const c = b._date.localeCompare(a._date);
    return c !== 0 ? c : b._order - a._order;
  });
  return rows.map((r) => ({
    id: r.id,
    content: r.content,
    dateText: r.dateText,
    nameText: r.nameText
  }));
}

module.exports = { PEN_NAMES, formatDate, normalize };
