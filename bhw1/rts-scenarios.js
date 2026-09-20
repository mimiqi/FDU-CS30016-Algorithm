(function (root, factory) {
  const data = factory();
  if (typeof module === 'object' && module.exports) module.exports = data;
  else root.RTS_SCENARIOS = data;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  return {
    counterexample: {
      name: '同属性反例：攻击时机影响终局', goal: { x: 0, y: 0 },
      description: 'tick 3：E1 剩余 45 点生命且本轮攻击；E2 剩余 55 点生命、下一 tick 攻击。先杀谁，会改变 F1 能否在 tick 9 再攻击一次。',
      units: [
        { id: 'F1', team: 'friendly', x: -10, y: 0 },
        { id: 'F2', team: 'friendly', x: -7, y: 0 },
        { id: 'E1', team: 'enemy', x: 3, y: 0 },
        { id: 'E2', team: 'enemy', x: 4.5, y: 0 }
      ]
    },
    demo: {
      name: '基础演示：集火优于就近攻击', goal: { x: 15, y: 8.5 },
      description: '从对称位置接敌。这个场景用于理解集火；单个场景获胜不能证明算法总是最优。',
      units: [
        { id: 'F1', team: 'friendly', x: 4, y: 7 },
        { id: 'F2', team: 'friendly', x: 4, y: 10 },
        { id: 'E1', team: 'enemy', x: 26, y: 7 },
        { id: 'E2', team: 'enemy', x: 26, y: 10 }
      ]
    }
  };
});
