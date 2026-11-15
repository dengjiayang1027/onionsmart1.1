/* Pure score feedback; a trade acknowledgement must never cause an alert. */
const BattleScore = {
  overtaken(previous, current, ownId) {
    const before = previous.find(p => p.id === ownId);
    const after = current.find(p => p.id === ownId);
    if (!before || !after || after.rank >= before.rank) return [];
    return current.filter(p => p.id !== ownId && after.profit > p.profit &&
      previous.some(old => old.id === p.id && old.profit >= before.profit)).map(p => p.name);
  },
  position(board, ownId) {
    const own = board.find(p => p.id === ownId);
    if (!own) return '等待記分板更新';
    const sign = own.return_pct >= 0 ? '+' : '';
    const gap = own.rank === 1 ? '目前領先' : `距前一名 ${own.gap_pct.toFixed(3)} 個百分點`;
    return `第 ${own.rank} 名 · ${sign}${own.return_pct.toFixed(3)}% · ${gap}`;
  }
};
