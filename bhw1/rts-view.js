/* Presentation only. All combat rules and target decisions live in rts-core.js. */
(() => {
  'use strict';
  const R = window.RTS, scenarios = window.RTS_SCENARIOS;
  const byId = id => document.getElementById(id);
  const canvas = byId('battlefield'), ctx = canvas.getContext('2d');
  const scenarioSelect = byId('scenarioSelect'), strategySelect = byId('strategySelect');
  const speedSelect = byId('speedSelect'), playButton = byId('playButton');
  const WIDTH = 900, HEIGHT = 450;
  const labels = { default: '默认就近攻击', model: '旧模型集火', corrected: '人工修正版' };
  const descriptions = {
    default: '每个 Ready 单位独立攻击最近目标；距离并列时按编号。',
    model: '按虚拟生命值从低到高分配攻击；本策略的全局最优性主张已被反例否定。',
    corrected: '在原战斗规则下枚举全部合法攻击和等待，通过记忆化搜索选择最优后续收益。'
  };
  const solvers = new Map();
  let state, last = null, logs = [], playing = false, timer = null, error = null;
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function scenario() { return scenarios[scenarioSelect.value]; }
  function transform(p) {
    if (scenarioSelect.value === 'counterexample') return { x: 530 + 32 * p.x, y: 225 - 32 * p.y };
    return { x: p.x * 30, y: 225 + (p.y - 8.5) * 30 };
  }
  function scale() { return scenarioSelect.value === 'counterexample' ? 32 : 30; }
  function policy() {
    if (strategySelect.value === 'model') return R.model(state);
    if (strategySelect.value === 'default') return R.nearest(state);
    let solver = solvers.get(scenarioSelect.value);
    if (!solver) {
      solver = R.createSolver();
      solver.solve(R.createState(scenario()));
      solvers.set(scenarioSelect.value, solver);
    }
    return solver.action(state);
  }
  function stop() {
    playing = false; clearTimeout(timer); timer = null; playButton.textContent = '播放';
  }
  function step() {
    if (R.terminal(state) || error) return;
    try {
      const tick = state.tick;
      last = R.step(state, policy());
      state = last.state;
      const attack = last.attacks.length ? last.attacks.map(a => `${a.attacker}→${a.target}(${a.damage})`).join('，') : '无攻击';
      const movement = last.moved.length ? `；${last.moved.join('、')} 移动` : '；无移动';
      const deaths = last.deaths.length ? `；${last.deaths.join('、')} 死亡` : '';
      logs.push(`Tick ${tick}：${attack}${movement}${deaths}`);
      if (R.terminal(state)) stop();
    } catch (e) {
      error = e.message; stop();
    }
    render();
  }
  function reset() {
    stop(); state = R.createState(scenario()); last = null; error = null;
    logs = ['初始状态：双方属性完全相同，生命55，全部 Ready。'];
    render();
  }
  function loop() {
    if (!playing) return;
    step();
    if (playing) timer = setTimeout(loop, Number(speedSelect.value));
  }
  function status() {
    if (error) return '计算中止';
    if (R.terminal(state)) {
      const f = state.units.some(u => u.alive && u.team === 'friendly');
      const e = state.units.some(u => u.alive && u.team === 'enemy');
      return f ? '己方胜利' : e ? '敌方胜利' : '双方全灭';
    }
    if (!last) return '待开始';
    return last.attacks.length ? '交战中' : last.moved.length ? '移动中' : '原地等待冷却';
  }
  function draw() {
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    ctx.strokeStyle = css('--border'); ctx.lineWidth = 1;
    for (let x = 50; x < WIDTH; x += 50) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, HEIGHT); ctx.stroke();
    }
    for (let y = 25; y < HEIGHT; y += 50) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(WIDTH, y); ctx.stroke();
    }
    const g = transform(state.goal);
    ctx.strokeStyle = css('--goal'); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(g.x, g.y, 11, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = css('--goal'); ctx.font = '14px Segoe UI, Microsoft YaHei, sans-serif';
    ctx.textAlign = 'center'; ctx.fillText('G', g.x, g.y + 36);
    for (const u of state.units.filter(u => u.alive)) {
      const p = transform(u);
      ctx.strokeStyle = css(u.team === 'friendly' ? '--friendly' : '--enemy');
      ctx.globalAlpha = .18; ctx.setLineDash([6, 7]); ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(p.x, p.y, u.range * scale(), 0, Math.PI * 2); ctx.stroke();
    }
    ctx.globalAlpha = 1; ctx.setLineDash([]);
    // Curves separate coincident attack paths without changing unit positions.
    (last?.attacks || []).forEach((a, i) => {
      const p = transform(a.from), q = transform(a.to);
      const mid = { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 + (i % 2 ? 1 : -1) * (28 + i * 10) };
      ctx.strokeStyle = css('--attack'); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.quadraticCurveTo(mid.x, mid.y, q.x, q.y); ctx.stroke();
      const angle = Math.atan2(q.y - mid.y, q.x - mid.x);
      ctx.beginPath(); ctx.moveTo(q.x - 8 * Math.cos(angle - .5), q.y - 8 * Math.sin(angle - .5));
      ctx.lineTo(q.x, q.y); ctx.lineTo(q.x - 8 * Math.cos(angle + .5), q.y - 8 * Math.sin(angle + .5)); ctx.stroke();
    });
    for (const u of state.units) {
      const p = transform(u), upper = Number(u.id.slice(1)) % 2 === 1;
      const labelY = p.y + (upper ? -86 : 65);
      const labelX = p.x + (u.team === 'friendly' ? -20 : 28);
      ctx.globalAlpha = u.alive ? 1 : .35;
      ctx.fillStyle = css(u.team === 'friendly' ? '--friendly' : '--enemy');
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = css('--muted'); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(p.x, p.y + (upper ? -10 : 10)); ctx.lineTo(labelX, labelY + (upper ? 38 : -18)); ctx.stroke();
      ctx.fillStyle = css('--text'); ctx.textAlign = 'center';
      ctx.font = '600 18px Segoe UI, Microsoft YaHei, sans-serif'; ctx.fillText(u.id, labelX, labelY);
      ctx.font = '17px Segoe UI, Microsoft YaHei, sans-serif';
      ctx.fillText(`${u.hp}/55`, labelX, labelY + 21);
      ctx.fillStyle = css('--muted'); ctx.fillText(!u.alive ? '已死亡' : u.cooldown ? `CD ${u.cooldown}` : 'Ready', labelX, labelY + 40);
    }
    ctx.globalAlpha = 1;
  }
  function render() {
    if (!state) return;
    byId('strategyNote').textContent = descriptions[strategySelect.value];
    byId('scenarioNote').textContent = scenario().description;
    byId('tickValue').textContent = last ? state.tick - 1 : '—';
    byId('friendlyHpValue').textContent = R.value(state);
    byId('enemyAliveValue').textContent = state.units.filter(u => u.alive && u.team === 'enemy').length;
    byId('statusValue').textContent = status();
    byId('stepButton').disabled = R.terminal(state) || !!error;
    byId('criticalNote').hidden = !(scenarioSelect.value === 'counterexample' && state.tick === 3);
    const log = byId('eventLog'); log.replaceChildren();
    logs.forEach((entry, i) => { const li = document.createElement('li'); li.textContent = entry;
      if (i === logs.length - 1) li.className = 'latest'; log.appendChild(li); });
    log.scrollTop = log.scrollHeight;
    const rows = byId('unitRows'); rows.replaceChildren();
    state.units.forEach(u => {
      const tr = document.createElement('tr');
      [u.id, u.hp, `(${Number(u.x.toFixed(3))}, ${Number(u.y.toFixed(3))})`,
        !u.alive ? '死亡' : u.cooldown ? `CD ${u.cooldown}` : 'Ready'].forEach(value => {
        const td = document.createElement('td'); td.textContent = value; tr.appendChild(td);
      }); rows.appendChild(tr);
    });
    const result = byId('resultBox'); result.hidden = !R.terminal(state) && !error;
    if (error) result.textContent = `搜索未完成：${error}`;
    else if (R.terminal(state)) result.textContent = `${labels[strategySelect.value]}结束于 tick ${state.tick - 1}，己方最终生命值 ${R.value(state)}。` +
      (strategySelect.value === 'corrected' ? '此策略由完整精确搜索求得。' : '切换算法会从相同初始输入重置。');
    draw();
  }
  function resize() {
    const ratio = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = WIDTH * ratio; canvas.height = HEIGHT * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0); render();
  }
  playButton.addEventListener('click', () => {
    if (playing) { stop(); return; }
    if (R.terminal(state) || error) reset();
    playing = true; playButton.textContent = '暂停'; loop();
  });
  byId('stepButton').addEventListener('click', () => { stop(); step(); });
  byId('resetButton').addEventListener('click', reset);
  scenarioSelect.addEventListener('change', reset); strategySelect.addEventListener('change', reset);
  speedSelect.addEventListener('change', () => {
    if (playing) { clearTimeout(timer); timer = setTimeout(loop, Number(speedSelect.value)); }
  });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
  new ResizeObserver(resize).observe(canvas);
  reset(); resize();
})();
