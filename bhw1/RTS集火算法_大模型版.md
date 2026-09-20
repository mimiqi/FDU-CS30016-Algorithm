# RTS 单位目标选择优化：大模型版

> 来源说明：用户于2026-09-20补充确认，本贪心算法来自此前使用较弱模型得到的真实回答，并选定它作为任务一的主审计对象。当前文件经过后续讨论和整理，按“旧模型回答整理稿”使用；具体模型、早期题干及与原回答的对应关系见[实验记录](./审计记录/RTS集火算法_实验记录.md)。以下“正确性说明”是被审计的错误主张。反例及修正见[人工修正版](./RTS集火算法_人工修正版.md)。

## 回答（整理稿）

默认的就近攻击让每个单位独立选择目标，容易把伤害分散到多个敌人身上。为了减少敌方的攻击次数，可以让所有己方单位共享目标信息，在每个 tick 优先集火最容易被消灭的敌人。

## 算法思想

在每个 tick 开始时，复制所有存活敌人的当前生命值，得到虚拟生命值 `virtualHP`。然后按照己方单位编号从小到大处理所有 Ready 单位。

对当前己方单位 `i`，先找出射程内且虚拟生命值大于 0 的敌人。优先选择虚拟生命值最低的目标；若虚拟生命值相同，则选择实际生命值最低的目标；若仍然相同，则选择编号最小的目标。

选定目标 `j` 后，在虚拟生命值中预先扣除本次伤害：

```math
\operatorname{virtualHP}_j
\leftarrow
\max\left(0,\operatorname{virtualHP}_j-\max(0.5,D_i-A_j)\right)
```

若某个目标的虚拟生命值已经降到 0，说明本 tick 已经分配的攻击足以消灭它。后续单位转而攻击下一个目标，从而避免把更多攻击浪费在同一具即将死亡的单位上。

这个策略与默认就近攻击的主要差别是：默认算法只考虑单个攻击者与目标的距离；集火算法会读取前面单位已经分配的攻击，并让多个单位优先完成同一个击杀。

## 伪代码

```text
function ChooseTargetsByFocusFire(state):
    for each alive enemy j:
        virtualHP[j] = HP[j]

    actions = empty map

    for each friendly unit i in increasing id order:
        if i is not Ready:
            actions[i] = wait
            continue

        candidates = all alive enemies j such that:
            j is within range of i
            and virtualHP[j] > 0

        if candidates is empty:
            actions[i] = wait
            continue

        target = arg min over j in candidates of (
            virtualHP[j],
            HP[j],
            id[j]
        )

        actions[i] = attack target
        damage = max(0.5, attack[i] - armor[target])
        virtualHP[target] = max(
            0,
            virtualHP[target] - damage
        )

    return actions
```

每个 tick 先调用 `ChooseTargetsByFocusFire` 得到己方联合动作；敌方仍按照题目规定，对每个 Ready 单位选择射程内距离最近的己方单位，距离相同时选择编号最小的单位。双方目标均确定后，再同时结算伤害。移动阶段中，只要单位射程内仍存在存活敌方单位，该单位就保持原位；只有射程内没有敌人且本 tick 未攻击的单位才向 `G` 移动。

## 正确性说明（整理稿，待审计主张）

敌方单位只有在死亡后才会停止攻击。因此，与把相同伤害分散到多个敌人相比，把伤害优先集中到生命值最低的敌人可以更早完成击杀，并减少之后每个 tick 中可能发动攻击的敌方数量。

虚拟生命值记录了同一 tick 内已经分配给各目标的伤害，使后续单位能够延续前面单位的集火选择，同时避开已经会被本轮攻击消灭的目标。因此，每个 tick 都先消灭当前最容易击杀的敌人，可以让敌方存活数量下降得尽可能快。

敌方存活数量越少，未来能够造成的总伤害越低，所以重复执行该策略能够使己方最终保留的总生命值最大。

## 复杂度

设己方单位数为 `n`，敌方单位数为 `m`。每个 tick 最多为每个己方单位检查全部敌方单位，因此时间复杂度为：

```math
O(nm)
```

虚拟生命值和动作表所需的额外空间为：

```math
O(n+m)
```

## 当前对局中的表现

可视化示例中，双方各有两个完全相同的单位，生命值为 55、攻击力为 10、射程为 6、移动速度为 2。默认算法会让两个己方单位分别攻击各自最近的敌人，而本算法会让它们优先攻击同一个目标，因此能够更早减少敌方单位数量。

该基础示例只能说明此策略在一个对局中有效。现已找到双方初始生命值、攻击力、护甲、射程、移速、攻击间隔均相同的反例：本策略最终生命值为 0，合法替代策略为 5，精确搜索的最优值也为 5。算法正文保留原有决策规则供审计。
