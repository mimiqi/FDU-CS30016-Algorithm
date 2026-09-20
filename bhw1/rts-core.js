/* Shared deterministic simulator for the browser and the audit runner. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RTS = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const STATS = Object.freeze({ hp: 55, attack: 10, armor: 0, range: 6, speed: 2, interval: 2 });
  const EPS = 1e-9; // Only for floating-point geometry; HP/cooldown/state keys are integers.
  function createState(scenario) {
    return { tick: 0, goal: { ...scenario.goal }, units: scenario.units.map(u => ({
      ...STATS, ...u, maxHp: STATS.hp, originX: u.x, originY: u.y,
      moves: 0, cooldown: 0, alive: true
    })) };
  }
  function distance(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
  function idOrder(a, b) { return Number(a.id.slice(1)) - Number(b.id.slice(1)); }
  function candidates(state, u) {
    return state.units.filter(v => v.alive && v.team !== u.team && distance(u, v) <= u.range + EPS);
  }
  function ready(state, team) {
    return state.units.filter(u => u.alive && u.team === team && u.cooldown === 0).sort(idOrder);
  }
  function terminal(state) {
    return !state.units.some(u => u.alive && u.team === 'friendly') ||
      !state.units.some(u => u.alive && u.team === 'enemy');
  }
  function value(state) {
    return state.units.filter(u => u.alive && u.team === 'friendly').reduce((sum, u) => sum + u.hp, 0);
  }
  function nearest(state, team = 'friendly') {
    const actions = {};
    for (const u of ready(state, team)) {
      let best = null;
      for (const v of candidates(state, u)) {
        if (!best || distance(u, v) < distance(u, best) - EPS ||
            (Math.abs(distance(u, v) - distance(u, best)) <= EPS && idOrder(v, best) < 0)) best = v;
      }
      if (best) actions[u.id] = best.id;
    }
    return actions;
  }
  function model(state) {
    const virtualHp = new Map(state.units.filter(u => u.alive).map(u => [u.id, u.hp]));
    const actions = {};
    for (const u of ready(state, 'friendly')) {
      let best = null;
      for (const v of candidates(state, u)) {
        if (virtualHp.get(v.id) <= 0) continue;
        if (!best || virtualHp.get(v.id) < virtualHp.get(best.id) ||
            (virtualHp.get(v.id) === virtualHp.get(best.id) &&
             (v.hp < best.hp || (v.hp === best.hp && idOrder(v, best) < 0)))) best = v;
      }
      if (best) {
        actions[u.id] = best.id;
        virtualHp.set(best.id, Math.max(0, virtualHp.get(best.id) - u.attack));
      }
    }
    return actions;
  }
  function key(state) {
    return state.units.map(u => u.alive ? `${u.hp},${u.moves},${u.cooldown}` : '0').join('|');
  }
  function step(state, friendlyActions) {
    if (terminal(state)) throw new Error('Battle already ended');
    const actions = { ...friendlyActions, ...nearest(state, 'enemy') };
    const incoming = new Map();
    const attacks = [];
    for (const [attackerId, targetId] of Object.entries(actions)) {
      const u = state.units.find(v => v.id === attackerId);
      const v = state.units.find(w => w.id === targetId);
      if (!u || !v || !u.alive || !v.alive || u.cooldown !== 0 ||
          u.team === v.team || distance(u, v) > u.range + EPS) throw new Error('Illegal attack');
      const hit = Math.max(0.5, u.attack - v.armor);
      incoming.set(v.id, (incoming.get(v.id) || 0) + hit);
      attacks.push({ attacker: u.id, target: v.id, damage: hit, from: { x: u.x, y: u.y }, to: { x: v.x, y: v.y } });
    }
    const next = { tick: state.tick + 1, goal: { ...state.goal }, units: state.units.map(u => {
      const hp = u.alive ? Math.max(0, u.hp - (incoming.get(u.id) || 0)) : 0;
      return { ...u, hp, alive: hp > 0,
        cooldown: hp <= 0 ? 0 : actions[u.id] ? u.interval - 1 : Math.max(0, u.cooldown - 1) };
    }) };
    const movers = terminal(next) ? [] : next.units.filter(u => u.alive && !actions[u.id] &&
      candidates(next, u).length === 0 && distance(u, next.goal) > EPS);
    // Compute the whole eligible set before changing any positions.
    for (const u of movers) {
      u.moves += 1;
      const d = Math.hypot(next.goal.x - u.originX, next.goal.y - u.originY);
      const fraction = Math.min(1, u.moves * u.speed / d);
      u.x = u.originX + (next.goal.x - u.originX) * fraction;
      u.y = u.originY + (next.goal.y - u.originY) * fraction;
    }
    return { state: next, attacks, moved: movers.map(u => u.id),
      deaths: next.units.filter(u => !u.alive && state.units.find(v => v.id === u.id).alive).map(u => u.id) };
  }
  function* jointActions(state) {
    const units = ready(state, 'friendly');
    const choices = units.map(u => [...candidates(state, u).sort(idOrder).map(v => v.id), null]);
    function* visit(i, actions) {
      if (i === units.length) { yield { ...actions }; return; }
      for (const target of choices[i]) {
        if (target) actions[units[i].id] = target; else delete actions[units[i].id];
        yield* visit(i + 1, actions);
      }
    }
    yield* visit(0, {});
  }
  function createSolver({ maxStates = 300000 } = {}) {
    const memo = new Map(), choice = new Map();
    let transitions = 0;
    function solve(state) {
      if (terminal(state)) return value(state);
      const k = key(state);
      if (memo.has(k)) return memo.get(k);
      if (memo.size >= maxStates) throw new Error('Exact search exceeded state budget; no optimality result');
      let best = -Infinity, bestAction = null;
      // Model action orders the search only; all other actions, including wait, remain legal.
      const preferred = model(state);
      const actions = (function* () { yield preferred; yield* jointActions(state); })();
      const seenSuccessors = new Set();
      for (const action of actions) {
        const next = step(state, action).state;
        transitions += 1;
        const nk = key(next);
        if (nk === k || seenSuccessors.has(nk)) continue;
        seenSuccessors.add(nk);
        const result = solve(next);
        if (result > best) { best = result; bestAction = { ...action }; }
      }
      if (!bestAction) throw new Error('No terminating action under the stated rules');
      memo.set(k, best); choice.set(k, bestAction);
      return best;
    }
    return { solve, action(state) { solve(state); return { ...choice.get(key(state)) }; },
      stats() { return { states: memo.size, transitions }; } };
  }
  function simulate(initial, policy, maxTicks = 1000) {
    let state = initial;
    const trace = [];
    while (!terminal(state)) {
      if (trace.length >= maxTicks) throw new Error('Simulation tick limit reached');
      const action = policy(state);
      const result = step(state, action);
      trace.push({ tick: state.tick, action, ...result });
      state = result.state;
    }
    return { value: value(state), state, trace };
  }
  return { STATS, createState, distance, candidates, ready, terminal, value, nearest, model,
    key, step, jointActions, createSolver, simulate };
});
