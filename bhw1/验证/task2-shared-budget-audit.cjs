'use strict';
// 原算法按实际顺序递归；用整数加法累计循环中的 work 次数。
// 与按递归树每层覆盖的叶子前缀计算的独立公式交叉验证。
const assert = require('node:assert/strict');
function simulate(n, initialBudget) {
  let budget = initialBudget;
  let workCalls = 0;
  let leaves = 0;
  function visit(m) {
    workCalls += m;
    if (m === 1) { leaves++; return; }
    visit(m / 2);
    if (budget > 0) { budget--; visit(m / 2); }
  }
  visit(n);
  return { workCalls, leaves, remainingBudget: budget };
}
function formula(n, budget) {
  let workCalls = 0;
  for (let size = n; size >= 1; size /= 2) {
    workCalls += size * Math.ceil((budget + 1) / size);
  }
  return workCalls;
}
let checked = 0;
for (let h = 2; h <= 10; h++) {
  const n = 2 ** h;
  for (let b = 0; b < n; b++) {
    const actual = simulate(n, b);
    assert.equal(actual.workCalls, formula(n, b));
    assert.equal(actual.leaves, b + 1);
    assert.equal(actual.remainingBudget, 0);
    checked++;
  }
}
const samples = [];
for (let h = 2; h <= 20; h += 2) {
  const n = 2 ** h, budget = Math.floor(n / h);
  const actual = simulate(n, budget);
  assert.equal(actual.workCalls, formula(n, budget));
  samples.push({ n, initialBudget: budget, ...actual, workCallsOverN: actual.workCalls / n });
}
console.log(JSON.stringify({
  note: '有限计数用于辅助验证，渐近结论另有证明。',
  exhaustiveSmallBudgetCases: checked,
  samples,
}, null, 2));
