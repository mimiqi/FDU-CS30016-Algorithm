'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../rts-core.js');
const scenarios = require('../rts-scenarios.js');

function compact(run) {
  return { value: run.value, lastTick: run.state.tick - 1, trace: run.trace.map(t => ({
    tick: t.tick, attacks: t.attacks.map(a => `${a.attacker}→${a.target}`),
    health: Object.fromEntries(t.state.units.map(u => [u.id, u.hp])),
    positions: Object.fromEntries(t.state.units.map(u => [u.id, [u.x, u.y]])),
    cooldowns: Object.fromEntries(t.state.units.map(u => [u.id, u.cooldown])),
    moved: t.moved, deaths: t.deaths
  })) };
}

// Independent integer half-unit simulator: no shared transition, policy, or solver.
// This enumerates reachable states breadth-first on the one-dimensional counterexample.
function independentCounterexample() {
  const units = ['F1', 'F2', 'E1', 'E2'];
  const initial = { x: [-20, -14, 6, 9], h: [55, 55, 55, 55], c: [0, 0, 0, 0] };
  const encode = s => JSON.stringify(s);
  const queue = [initial], seen = new Set([encode(initial)]);
  let best = -Infinity, edges = 0, terminals = 0;
  for (let head = 0; head < queue.length; head++) {
    const s = queue[head];
    if ((!s.h[0] && !s.h[1]) || (!s.h[2] && !s.h[3])) {
      best = Math.max(best, s.h[0] + s.h[1]); terminals++; continue;
    }
    const targetList = i => s.h.map((hp, j) => j).filter(j =>
      s.h[j] > 0 && (i < 2) !== (j < 2) && Math.abs(s.x[i] - s.x[j]) <= 12);
    const options = [0, 1].map(i => s.h[i] && !s.c[i] ? [-1, ...targetList(i)] : [-1]);
    const enemies = [2, 3].map(i => {
      if (!s.h[i] || s.c[i]) return -1;
      return targetList(i).sort((a, b) => Math.abs(s.x[i] - s.x[a]) - Math.abs(s.x[i] - s.x[b]) || a - b)[0] ?? -1;
    });
    for (const a of options[0]) for (const b of options[1]) {
      const attacks = [a, b, ...enemies], lost = [0, 0, 0, 0];
      attacks.forEach(t => { if (t >= 0) lost[t] += 10; });
      const h = s.h.map((hp, i) => Math.max(0, hp - lost[i]));
      const c = s.c.map((cd, i) => h[i] ? (attacks[i] >= 0 ? 1 : Math.max(0, cd - 1)) : 0);
      const x = [...s.x];
      if ((h[0] || h[1]) && (h[2] || h[3])) {
        const move = units.map((_, i) => h[i] > 0 && attacks[i] < 0 && !h.some((hp, j) =>
          hp > 0 && (i < 2) !== (j < 2) && Math.abs(s.x[i] - s.x[j]) <= 12));
        move.forEach((yes, i) => { if (yes) x[i] -= Math.sign(x[i]) * Math.min(4, Math.abs(x[i])); });
      }
      const next = { x, h, c }, k = encode(next); edges++;
      if (!seen.has(k)) { seen.add(k); queue.push(next); }
    }
  }
  return { best, states: seen.size, edges, terminals, method: '独立半整数坐标 BFS，枚举所有攻击和等待' };
}

const report = { rules: R.STATS, cases: {} };
for (const [name, scenario] of Object.entries(scenarios)) {
  const start = R.createState(scenario);
  for (const u of start.units) for (const [attribute, expected] of Object.entries(R.STATS)) {
    assert.equal(u[attribute], expected, `${name}/${u.id}/${attribute}`);
  }
  const solver = R.createSolver();
  const optimal = solver.solve(start);
  const runs = { default: R.simulate(start, R.nearest), model: R.simulate(start, R.model),
    corrected: R.simulate(start, s => solver.action(s)) };
  assert.equal(runs.corrected.value, optimal);
  assert.ok(optimal >= runs.model.value && optimal >= runs.default.value);
  report.cases[name] = { input: scenario, optimal, search: solver.stats(),
    runs: Object.fromEntries(Object.entries(runs).map(([k, run]) => [k, compact(run)])) };
  console.log(`${name}: nearest=${runs.default.value}, model=${runs.model.value}, corrected=${optimal}; states=${solver.stats().states}`);
}
assert.equal(report.cases.counterexample.runs.model.value, 0);
assert.equal(report.cases.counterexample.optimal, 5);
assert.deepEqual(report.cases.counterexample.runs.model.trace[3].attacks, ['F1→E1', 'F2→E1', 'E1→F1']);
assert.deepEqual(report.cases.counterexample.runs.corrected.trace[3].attacks, ['F1→E2', 'F2→E2', 'E1→F1']);
assert.equal(report.cases.counterexample.runs.model.trace[8].health.F1, 0);
assert.equal(report.cases.counterexample.runs.corrected.trace[8].health.F1, 5);
const independent = independentCounterexample();
assert.equal(independent.best, report.cases.counterexample.optimal);
report.independentCheck = independent;

// Geometry must be checked on one snapshot, independent of array traversal order.
const initial = R.createState(scenarios.counterexample);
const reversed = { ...initial, units: [...initial.units].reverse() };
const positions = s => Object.fromEntries([...s.units].sort((a,b) => a.id.localeCompare(b.id)).map(u => [u.id, [u.x,u.y]]));
assert.deepEqual(positions(R.step(initial, {}).state), positions(R.step(reversed, {}).state));
assert.deepEqual(R.step(initial, {}).state.units.map(u => u.x), [-8, -5, 1, 2.5]);
// A unit killed this tick still contributes its already chosen attack.
const duel = R.createState({ goal: { x:0,y:0 }, units:[
  {id:'F1',team:'friendly',x:0,y:0},{id:'E1',team:'enemy',x:1,y:0}
] });
duel.units.forEach(u => { u.hp = 5; });
assert.deepEqual(R.step(duel, {F1:'E1'}).state.units.map(u => u.hp), [0,0]);
console.log(`Independent BFS: optimum=${independent.best}, states=${independent.states}; all assertions passed.`);
if (process.argv.includes('--write')) {
  fs.writeFileSync(path.join(__dirname, 'RTS集火算法_验证结果.json'), JSON.stringify(report, null, 2) + '\n');
  console.log('Wrote RTS集火算法_验证结果.json');
}
