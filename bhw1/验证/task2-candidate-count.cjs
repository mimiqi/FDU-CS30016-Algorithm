// 仅计算候选 C 的 work() 次数；用动态规划求递推值，
// 不代表被分析算法使用记忆化，也不以本脚本运行时间代替原算法复杂度。
// 用法：node bhw1/验证/task2-candidate-count.cjs [最大 log2(n)，默认 20]
'use strict';
const maxExponent = Number(process.argv[2] ?? 20);
if (!Number.isInteger(maxExponent) || maxExponent < 4 || maxExponent > 24) {
  throw new Error('最大指数须为 4 到 24 的整数。');
}
const limit = 2 ** maxExponent;
const counts = new Float64Array(limit + 1);
counts[1] = counts[2] = counts[3] = 1;
for (let n = 4; n <= limit; n++) {
  const k = 31 - Math.clz32(n);
  const r = Math.floor(n / k);
  if (r < 1 || r >= n) throw new Error(`子问题未严格缩小：n=${n}, r=${r}`);
  counts[n] = counts[r] + counts[n - r] + n;
  if (!Number.isSafeInteger(counts[n])) throw new Error('计数超出精确整数范围。');
}
const results = [];
for (let exponent = 4; exponent <= maxExponent; exponent += 2) {
  const n = 2 ** exponent;
  results.push({
    n,
    workCalls: counts[n],
    dividedByNLogN: counts[n] / (n * exponent),
    dividedByNLogSquaredNOverLogLogN:
      counts[n] / (n * exponent * exponent / Math.log2(exponent)),
  });
}
console.log(JSON.stringify({
  baseCase: 'n <= 3: work() 一次并返回',
  note: '有限规模的精确操作计数，仅为理论推导的辅助检查，不是渐近证明。',
  results,
}, null, 2));
