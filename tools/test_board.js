// 题壁模块离线自测：node tools/test_board.js
// 校验日期格式化、署名词牌雅号、留言排序与兜底数据接线
const path = require('path');
const { formatDate, normalize, PEN_NAMES } = require('../miniprogram/utils/board.js');
const fallback = require('../miniprogram/services/fallback.js');
const registry = require('../miniprogram/services/registry.js');

let pass = 0;
let fail = 0;

function check(name, actual, expected) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) {
    pass += 1;
    console.log('  OK   ' + name);
  } else {
    fail += 1;
    console.log('  FAIL ' + name + '\n         期望 ' + e + '\n         实际 ' + a);
  }
}

console.log('=== 1. 接线检查 ===');
check('registry 已注册 board', typeof registry.board, 'function');
check('registry.board 路径', registry.board(), '/data/board.json');
check('fallback.board 存在', Array.isArray(fallback.board && fallback.board.messages), true);

console.log('\n=== 2. 日期格式化 ===');
const thisYear = new Date().getFullYear();
check('同年省略年份', formatDate(thisYear + '-09-06'), '9月6日');
check('跨年显示年份', formatDate('2025-12-08'), '2025年12月8日');
check('个位数月日', formatDate(thisYear + '-01-03'), '1月3日');
check('空值返回空', formatDate(''), '');
check('非法格式原样返回', formatDate('昨天'), '昨天');

console.log('\n=== 3. 留言归一化与排序（最新在前）===');
const raw = {
  messages: [
    { id: 'b1', content: '第一则', date: thisYear + '-09-01', anonymous: true },
    { id: 'b2', content: '第二则', date: thisYear + '-09-08', anonymous: false },
    { id: 'b3', content: '第三则', date: thisYear + '-09-05', anonymous: false, penName: '念奴娇' }
  ]
};
const out = normalize(raw);
check('条数', out.length, 3);
check('最新在前', out.map((m) => m.id), ['b2', 'b3', 'b1']);
check('匿名显示佚名', out.find((m) => m.id === 'b1').nameText, '佚名');
check('署名用指定雅号', out.find((m) => m.id === 'b3').nameText, '念奴娇');
check('署名未指定则自动分配', PEN_NAMES.includes(out.find((m) => m.id === 'b2').nameText), true);
check('日期已格式化', out[0].dateText, '9月8日');

console.log('\n=== 4. 边界情况 ===');
check('空数组', normalize({ messages: [] }), []);
check('null 输入', normalize(null), []);
check('messages 缺失', normalize({}), []);
check('空白内容被过滤', normalize({ messages: [{ id: 'x', content: '   ', date: thisYear + '-09-01' }] }), []);
check('日期缺失不崩', normalize({ messages: [{ id: 'y', content: '无日期', anonymous: true }] })[0].dateText, '');
check('同日期按发布顺序倒序', normalize({
  messages: [
    { id: 'p1', content: '先', date: thisYear + '-09-09', anonymous: true },
    { id: 'p2', content: '后', date: thisYear + '-09-09', anonymous: true }
  ]
}).map((m) => m.id), ['p2', 'p1']);

console.log('\n=== 5. 雅号分配稳定性 ===');
const a1 = normalize({ messages: [{ id: 'fix1', content: 'x', anonymous: false }] })[0].nameText;
const a2 = normalize({ messages: [{ id: 'fix1', content: 'x', anonymous: false }] })[0].nameText;
check('同一 id 多次渲染结果一致', a1, a2);
check('雅号来自词牌池', PEN_NAMES.includes(a1), true);

console.log('\n———————————————');
console.log('通过 ' + pass + ' 项，失败 ' + fail + ' 项');
process.exit(fail === 0 ? 0 : 1);
