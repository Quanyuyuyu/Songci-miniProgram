const SEASONS = {
  Spring: '春',
  Fall: '秋'
};

function formatTerm(term) {
  if (!term) return '';
  const match = String(term).match(/^(\d{2})(Spring|Fall)$/);
  if (!match) return String(term);
  return '20' + match[1] + ' ' + SEASONS[match[2]];
}

module.exports = { formatTerm };
