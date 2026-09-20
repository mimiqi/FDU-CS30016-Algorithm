'use strict';
// Auditor-written transcription of experiment 01, not code from the original answer.
// Conventions: fresh zero damage per NEXT, copied states, stable IDs, frozen movement snapshot.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const existing = require('../rts-core.js');
const scenarios = require('../rts-scenarios.js');
const LIMIT = 250000;

function transcribeAnswer(input) {
  const units = input.units;
  const N = units.length;
  const length = units.map(u => Math.hypot(u.x - input.goal.x, u.y - input.goal.y));
  const L = length.map(d => Math.ceil(d / 2));
  const initial = units.map(() => [55, 0, 0]); // health, cooldown, movement count
  const positions = s => s.map((u, i) => {
    if (u[2] >= L[i]) return [input.goal.x, input.goal.y];
    const f = 2 * u[2] / length[i];
    return [units[i].x + f * (input.goal.x - units[i].x),
      units[i].y + f * (input.goal.y - units[i].y)];
  });
  const encode = s => JSON.stringify(s);
  const terminal = s => ['friendly', 'enemy'].some(t =>
    !s.some((u, i) => u[0] > 0 && units[i].team === t));
  const value = s => s.reduce((v, u, i) => v + (units[i].team === 'friendly' ? u[0] : 0), 0);
  const metric = s => [s.reduce((v, u) => v + Math.ceil(u[0] / 10), 0),
    s.reduce((v, u, i) => v + (u[0] > 0 ? L[i] - u[2] : 0), 0),
    s.reduce((v, u) => v + u[1], 0)];
  const dist = (p, i, j) => Math.hypot(p[i][0] - p[j][0], p[i][1] - p[j][1]);
  function targets(s, p, i) {
    return units.map((_, j) => j).filter(j => s[j][0] > 0 &&
      units[i].team !== units[j].team && dist(p, i, j) <= 6);
  }
  function* actions(s) {
    const p = positions(s);
    function* generate(i, a) {
      if (i === N) { yield [...a]; return; }
      const opts = units[i].team === 'friendly' && s[i][0] > 0 && s[i][1] === 0 ?
        [...targets(s, p, i), -1] : [-1];
      for (const j of opts) { a[i] = j; yield* generate(i + 1, a); }
    }
    yield* generate(0, []);
  }
  function next(s, action) {
    const p = positions(s), attack = [...action], damage = Array(N).fill(0);
    for (let i = 0; i < N; i++) {
      if (units[i].team !== 'enemy' || !s[i][0] || s[i][1]) continue;
      attack[i] = targets(s, p, i).sort((a, b) => dist(p, i, a) - dist(p, i, b) ||
        Number(units[a].id.slice(1)) - Number(units[b].id.slice(1)))[0] ?? -1;
    }
    attack.forEach(j => { if (j >= 0) damage[j] += 10; });
    const out = s.map((u, i) => [Math.max(0, u[0] - damage[i]), u[1], u[2]]);
    if (terminal(out)) return out.map(u => u[0] ? u : [0, 0, 0]);
    for (let i = 0; i < N; i++) {
      if (!out[i][0]) { out[i] = [0, 0, 0]; continue; }
      out[i][1] = attack[i] >= 0 ? 1 : Math.max(0, s[i][1] - 1);
      // p is never updated inside this loop, as required by the original prose.
      if (attack[i] < 0 && targets(out, p, i).length === 0) out[i][2] = Math.min(s[i][2] + 1, L[i]);
    }
    return out;
  }
  const memo = new Map(), choice = new Map(), active = new Set();
  let transitions = 0, maxDepth = 0;
  function solve(s, depth = 0) {
    if (terminal(s)) return value(s);
    const key = encode(s);
    if (memo.has(key)) return memo.get(key);
    assert.ok(!active.has(key), 'A cycle contradicts the answer termination proof');
    if (memo.size + active.size >= LIMIT) throw new Error('Audit state budget reached; no verdict');
    active.add(key); maxDepth = Math.max(maxDepth, depth);
    let best = -Infinity, bestAction = null;
    for (const a of actions(s)) {
      const s2 = next(s, a), before = metric(s), after = metric(s2);
      transitions++;
      const firstChange = before.findIndex((v, i) => v !== after[i]);
      assert.ok(firstChange >= 0 && after[firstChange] < before[firstChange], 'Potential did not decrease');
      const v = solve(s2, depth + 1);
      if (v > best) { best = v; bestAction = a; }
    }
    active.delete(key); memo.set(key, best); choice.set(key, bestAction);
    return best;
  }
  function verifyTrace() {
    let s = initial, reference = existing.createState(input), ticks = 0;
    while (!terminal(s)) {
      const a = choice.get(encode(s));
      assert.ok(a, 'Missing recovered action');
      const mapped = Object.fromEntries(a.flatMap((j, i) => j < 0 ? [] : [[units[i].id, units[j].id]]));
      const before = encode(s);
      const s2 = next(s, a);
      assert.equal(encode(s), before, 'NEXT mutated its argument');
      reference = existing.step(reference, mapped).state;
      const p2 = positions(s2);
      for (let i = 0; i < N; i++) {
        assert.equal(s2[i][0], reference.units[i].hp, 'Recovered trace health mismatch');
        if (s2[i][0] && !terminal(s2)) {
          assert.equal(s2[i][1], reference.units[i].cooldown);
          assert.ok(Math.hypot(p2[i][0] - reference.units[i].x, p2[i][1] - reference.units[i].y) < 1e-10);
        }
      }
      s = s2; ticks++;
      assert.ok(ticks <= 12 * N + L.reduce((a, b) => a + b, 0));
    }
    assert.equal(value(s), memo.get(encode(initial)));
    return ticks;
  }
  const optimum = solve(initial);
  return { optimum, states: memo.size, transitions, maxDepth, recoveredTicks: verifyTrace() };
}

// Independent BFS oracle for collinear cases: current coordinates are exact half-unit integers.
// This does not reuse the transcription's state encoding, transition, or recursion.
function integerOracle(input) {
  const n = input.units.filter(u => u.team === 'friendly').length;
  assert.ok(input.units.slice(0, n).every(u => u.team === 'friendly'));
  assert.ok(input.units.slice(n).every(u => u.team === 'enemy'));
  assert.ok(input.units.every(u => u.y === input.goal.y));
  const N = input.units.length, goal = 2 * input.goal.x;
  const initial = { h: Array(N).fill(55), cd: Array(N).fill(0), x: input.units.map(u => 2 * u.x) };
  assert.ok(Number.isInteger(goal) && initial.x.every(Number.isInteger));
  const queue = [initial], seen = new Set([JSON.stringify(initial)]);
  let best = -Infinity, edges = 0;
  for (let head = 0; head < queue.length; head++) {
    const s = queue[head];
    if (!s.h.slice(0, n).some(Boolean) || !s.h.slice(n).some(Boolean)) {
      best = Math.max(best, s.h.slice(0, n).reduce((a, b) => a + b, 0)); continue;
    }
    const inRange = i => s.h.map((hp, j) => j).filter(j => s.h[j] > 0 &&
      (i < n) !== (j < n) && Math.abs(s.x[i] - s.x[j]) <= 12);
    let combinations = [[]];
    for (let i = 0; i < n; i++) {
      const options = s.h[i] && !s.cd[i] ? [-1, ...inRange(i)] : [-1];
      combinations = combinations.flatMap(a => options.map(j => [...a, j]));
    }
    const enemy = [];
    for (let i = n; i < N; i++) {
      enemy.push(!s.h[i] || s.cd[i] ? -1 :
        (inRange(i).sort((a, b) => Math.abs(s.x[i] - s.x[a]) - Math.abs(s.x[i] - s.x[b]) || a - b)[0] ?? -1));
    }
    for (const friendly of combinations) {
      const attack = [...friendly, ...enemy];
      const h = s.h.map((hp, j) => Math.max(0, hp - 10 * attack.filter(t => t === j).length));
      const cd = s.cd.map((v, i) => h[i] ? (attack[i] >= 0 ? 1 : Math.max(0, v - 1)) : 0);
      const x = s.x.map((v, i) => {
        if (!h.slice(0, n).some(Boolean) || !h.slice(n).some(Boolean) || !h[i] || attack[i] >= 0) return v;
        const blocked = h.some((hp, j) => hp > 0 && (i < n) !== (j < n) && Math.abs(s.x[i] - s.x[j]) <= 12);
        return blocked ? v : v + Math.sign(goal - v) * Math.min(4, Math.abs(goal - v));
      });
      const next = { h, cd, x }, key = JSON.stringify(next); edges++;
      if (!seen.has(key)) {
        if (seen.size >= LIMIT) throw new Error('Oracle state budget reached; no verdict');
        seen.add(key); queue.push(next);
      }
    }
  }
  return { optimum: best, states: seen.size, transitions: edges };
}

function line(friendly, enemy, goal = 0) {
  return { goal: { x: goal, y: 0 }, units: [
    ...friendly.map((x, i) => ({ id: `F${i + 1}`, team: 'friendly', x, y: 0 })),
    ...enemy.map((x, i) => ({ id: `E${i + 1}`, team: 'enemy', x, y: 0 }))
  ] };
}
const evidence = path.join(__dirname, '../实验原始记录/2026-09-20_01_独立作答');
const original = fs.readFileSync(path.join(evidence, '02_模型原始回答.md'));
const metadata = JSON.parse(fs.readFileSync(path.join(evidence, '00_实验元数据.json'), 'utf8'));
const hash = crypto.createHash('sha256').update(original).digest('hex').toUpperCase();
assert.equal(hash, metadata.answer_sha256);
assert.equal(original.toString('utf8'), JSON.parse(fs.readFileSync(path.join(evidence, '02_原始消息.json'), 'utf8')).payload.content[0].text);
const report = {
  sourceAnswerSHA256: hash,
  method: '审计者按回答语义转写；一维用独立整数 BFS 比较，恢复轨迹用现有模拟器逐 tick 核对；二维只与现有模拟器交叉验证。',
  conventions: ['每次 NEXT 新建零伤害数组', 'NEXT 不修改调用者状态', '移动判断使用统一快照', '按固定 ID 保留单位', '完整枚举包含等待'],
  limits: '有限测试不代替证明；二维浮点验证不是精确代数数验证；审计状态预算250000，超限即报错。',
  cases: []
};
function check(name, input, group) {
  const model = transcribeAnswer(input);
  const oracle = integerOracle(input);
  assert.equal(model.optimum, oracle.optimum, name);
  report.cases.push({ name, group, input, model, oracle });
}
check('已有同属性反例', scenarios.counterexample, 'named');
check('所有单位初始在目标点', line([0, 0, 0], [0, 0, 0]), 'named');
check('3对1', line([-10, -7, 0], [4.5]), 'named');
check('1对3', line([-10], [-7, 3, 4.5]), 'named');
check('3对2', line([-10, -7, 0], [3, 4.5]), 'named');
check('2对3', line([-10, -7], [0, 3, 4.5]), 'named');
check('平移后非零目标点', line([-7, -4], [6, 7.5], 3), 'named');
console.log('Named cases passed.');
const boundary = [-30, -6.5, -6, -0.5, 0, 0.5, 6, 6.5, 30];
for (const f of boundary) for (const e of boundary) check(`1v1:${f},${e}`, line([f], [e]), 'boundary-grid');
console.log('81 boundary-grid cases passed.');
const grid = [-10, -7, 3, 4.5];
for (const a of grid) for (const b of grid) for (const c of grid) for (const d of grid) {
  check(`2v2:${a},${b};${c},${d}`, line([a, b], [c, d]), 'full-grid');
}
console.log('256 four-unit grid cases passed.');
const demoModel = transcribeAnswer(scenarios.demo);
const demoSolver = existing.createSolver();
const demoExpected = demoSolver.solve(existing.createState(scenarios.demo));
assert.equal(demoModel.optimum, demoExpected);
report.cases.push({ name: '二维基础演示', group: 'two-dimensional', input: scenarios.demo,
  model: demoModel, existingOptimum: demoExpected });
report.summary = {
  cases: report.cases.length,
  exactIntegerOracleCases: report.cases.filter(c => c.oracle).length,
  mismatches: 0,
  modelTransitionsChecked: report.cases.reduce((s, c) => s + c.model.transitions, 0),
  recoveredTicksChecked: report.cases.reduce((s, c) => s + c.model.recoveredTicks, 0),
  knownCounterexampleValue: report.cases[0].model.optimum,
  largestModelStateCount: Math.max(...report.cases.map(c => c.model.states))
};
console.log(JSON.stringify(report.summary, null, 2));
if (process.argv.includes('--write')) {
  fs.writeFileSync(path.join(__dirname, 'RTS集火算法_新回答验证结果.json'), JSON.stringify(report, null, 2) + '\n');
}
