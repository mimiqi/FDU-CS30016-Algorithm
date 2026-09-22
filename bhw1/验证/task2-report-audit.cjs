'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const records = path.join(__dirname, '..', '实验原始记录', '2026-09-21_03_任务二Luna轻度三题');
const hashes = JSON.parse(fs.readFileSync(path.join(records, '04_原始记录校验值.json'), 'utf8').replace(/^\uFEFF/, ''));
for (const entry of hashes) {
  const actual = crypto.createHash('sha256').update(fs.readFileSync(path.join(records, entry.file))).digest('hex');
  assert.equal(actual.toUpperCase(), entry.hash.toUpperCase(), `原始记录发生变化：${entry.file}`);
}
const dp = new Float64Array(513);
dp[1] = dp[2] = dp[3] = 1;
for (let n = 4; n <= 512; n++) {
  const r = Math.floor(n / (31 - Math.clz32(n)));
  assert(r >= 1 && r < n);
  dp[n] = dp[r] + dp[n - r] + n;
}
function direct(n) {
  let work = 0;
  function C(m) {
    if (m <= 3) { work++; return; }
    const k = Math.floor(Math.log2(m));
    const r = Math.floor(m / k);
    assert(r >= 1 && r < m);
    C(r);
    C(m - r);
    for (let i = 1; i <= m; i++) work++;
  }
  C(n);
  return work;
}
for (let n = 1; n <= 512; n++) assert.equal(direct(n), dp[n], `n=${n}`);
const result = {
  status: 'passed',
  rawRecordHashesVerified: hashes.length,
  directRecursionCases: 512,
  testedRange: '1 <= n <= 512',
  note: '直接执行全部 work() 并与独立动态规划计数比较。渐近结论仍由报告中的数学证明给出。',
};
if (process.argv.includes('--write')) {
  fs.writeFileSync(path.join(__dirname, '任务二_C题_审计检查.json'), JSON.stringify(result, null, 2) + '\n');
}
console.log(JSON.stringify(result, null, 2));
