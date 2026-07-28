// type -> 远端 JSON 路径映射（唯一注册表）
// key 语义：索引类 type 不用 key；详情类 type 用 key 拼接路径
module.exports = {
  'course':        () => '/data/course.json',
  'weeks':         () => '/data/weeks.json',
  'semester':      (key) => `/data/semester-${key}.json`,
  'schedule':      () => '/data/schedule.json',
  'archive-index': () => '/data/archive-index.json',
  'archive':       (key) => `/data/archive-${key}.json`,
  'ci-index':      () => '/data/ci-index.json',
  'ci-intensive':  (key) => `/data/ci-intensive/${key}.json`,
  'ci-skim':       () => '/data/ci-skim.json',
  'cipai':         () => '/data/cipai.json',
  'maps':          () => '/data/maps.json',
  'books':         () => '/data/books.json',
  'work':          (key) => `/data/works/${key}.json`
};
