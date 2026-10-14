"""Frozen benchmark, independent CLI calls, blind checks, and offline scoring.

No ground truth is sent to any respondent. --prepare is offline; --run uses
the user's existing Codex login, requested gpt-5.6-luna/low, no tools.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '实验原始记录'
CHECK = ROOT / '验证'
MODEL = 'gpt-5.6-luna'
SEED = 20261014
STYLES = {
    'trace': '采用逐步状态跟踪：按执行顺序记录变量、列表内容和控制流，再给出stdout。',
    'segments': '采用分段归纳：先确定各段对状态的变换，再组合各段，不跳过循环轮次。',
    'dependencies': '采用依赖分析：区分值、对象引用、惰性求值与求值时刻，再推出结果。',
    'branches': '采用边界审查：重点检查分支条件、更新顺序、迭代终止和返回值覆盖。',
}
REVIEWS = {
    'ledger': '你是盲复核者。完全独立逐行重算，列出循环和调用的关键状态，再输出结果。',
    'pitfalls': '你是盲复核者。先定位易错的求值顺序、别名、惰性计算或边界，再从头推导结果。',
    'recompute': '你是盲复核者。将程序按依赖拆分，独立复算各段，检查组合结果的内部一致性。',
}
SYSTEM = ('你是课程实验中的被测轻量模型。本次是新上下文中的单题作答。'
          '严禁使用任何工具、搜索、代码执行、文件访问、其他代理或额外模型调用。'
          '只凭推理预测Python 3程序的完整标准输出；整数无限精度。'
          '只输出JSON对象 {"answer":"完整stdout，用\\n表示换行",'
          '"reason":"不超过100个汉字的简短依据"}，不要Markdown围栏。')

# Frozen before the first formal draw. No randomness in the programs themselves.
PROGRAMS = [
('有限状态更新', '''a = [2, 5, 1, 4, 3]
s = 0
for t in range(8):
    i = (2*t + s) % 5
    j = (i + 2) % 5
    a[i], a[j] = (a[j] + t) % 9, (a[i] + s) % 9
    s = (s + a[(i+1) % 5] - a[j]) % 13
print(a, s)'''),
('循环与别名', '''a = [[1], [2], [3]]
b = a[:]
for i in range(6):
    k = i % 3
    if i % 2 == 0:
        b[k] += [i]
    else:
        b[k] = b[k] + [i]
    a[(k+1) % 3].append(len(b[k]))
print(a)
print(b)'''),
('闭包与可变默认值', '''def make():
    out = []
    box = [1]
    for i in range(4):
        def f(x=i, b=box):
            b[0] += x + i
            return b[0]
        out.append(f)
        if i % 2 == 0:
            box = [box[0] + i]
    return out
fs = make()
print([fs[k]() for k in [2, 0, 3, 1, 2, 0]])
print([f() for f in fs])'''),
('生成器与列表修改', '''a = [1, 2, 3, 4, 5]
g = (a.pop(0) + len(a) for _ in range(len(a)-1))
r = [next(g)]
a.append(r[0] % 3)
r.append(next(g))
a[:] = a[::-1]
r.extend(g)
print(r, a)'''),
('finally与返回引用', '''log = []
def f(n):
    try:
        if n % 3 == 0:
            return log[:]
        if n % 3 == 1:
            return log
        return len(log)
    finally:
        log.append(n)
        if n == 5:
            return log[:]
r = [f(n) for n in [1, 3, 2, 5, 4]]
log.append(9)
print(r)
print(log)'''),
('递归与共享缓存', '''def f(n, memo={0: 1}):
    if n in memo:
        return memo[n]
    memo[n] = f(n-1) + (f(n-2) if n > 1 else 0)
    if n % 2 == 0:
        memo[n-1] += 1
    return memo[n]
print(f(6), f(3), f(5))
print(f(7), f(4), f(1))'''),
('列表迭代中删改', '''a = [2, 1, 3, 2, 4, 1]
r = []
for x in a:
    r.append(x)
    if x % 2 == 0:
        a.remove(x)
    elif len(a) < 7:
        a.append(x+1)
print(r)
print(a)'''),
('布尔短路与副作用', '''a = [1, 2, 3]
def f(x):
    a.append(x)
    return x % 3
r = []
for k in [3, 2, 6, 4, 1]:
    r.append((f(k) and f(k+1)) or (len(a) % 4))
print(r)
print(a)'''),
('切片赋值与原地修改', '''a = [0, 1, 2, 3, 4, 5]
b = a
c = a[::2]
a[1::2] = c[::-1]
c[:] = b[1:5]
b += [len(c)]
a = a + [9]
b[2:5] = c[:2]
print(a)
print(b, c)'''),
('生成器暂停与finally', '''log = []
def g():
    try:
        for i in range(3):
            log.append(i)
            x = yield i + len(log)
            log.append(-1 if x is None else x)
    finally:
        log.append(9)
h = g()
r = [next(h), h.send(4), next(h)]
h.close()
print(r, log)'''),
('嵌套循环与位运算', '''s = 3
r = []
for i in range(1, 5):
    for j in range(i, -1, -1):
        if (s + j) % 3 == 0:
            s ^= (i << 1) + j
            continue
        s = (s*2 + j - i) % 19
        if s % 5 == 0:
            break
    r.append(s)
print(r, s)'''),
('递归与finally覆盖', '''log = []
def f(n):
    try:
        if n < 2:
            return n+1
        return f(n-1) + f(n-2)
    finally:
        log.append(n)
        if n == 2:
            return len(log) % 5
print(f(5))
print(log)'''),
('浅拷贝和对象图', '''a = [[1, 2], [3]]
b = a * 2
c = [x[:] for x in a]
b[0] += [4]
b[1] = b[1] + [5]
a.reverse()
a[0].append(6)
b[2][:1] = c[1]
c[0] = b[3]
print(a)
print(b)
print(c)'''),
('默认参数与递归', '''def f(n, a=[]):
    a.append(n)
    if n > 1:
        r = f(n-2)
    else:
        r = len(a)
    a.append(r)
    return sum(a[-3:])
x = f(5)
y = f(2)
print(x, y)
print(f(0))'''),
('生成器表达式绑定', '''a = [1, 2, 3]
gs = []
for i in range(3):
    gs.append((i*x + len(a) for x in a[:i+1]))
a.append(4)
r = [next(g) for g in gs]
i = 5
a.pop()
print(r)
print([list(g) for g in gs])'''),
('插入与延迟求值', '''a = [1, 2, 3, 4]
g = (x + a[-1] for x in a)
r = [next(g)]
a.insert(0, 7)
r.append(next(g))
a.pop()
r.extend(g)
print(r, a)'''),
('短路与海象赋值', '''a = [2, 0, 3, 1, 0, 4]
s = 1
r = []
for x in a:
    y = ((s := s+x) % 3 and (s := s*2)) or (s := s-1)
    r.append((s, y))
print(r)
print(s)'''),
('排序键的求值时刻', '''a = [4, 1, 3, 2]
log = []
def key(x):
    log.append(x)
    return (x+len(log)) % 3
b = sorted(a, key=key)
c = sorted(b, key=lambda x: (x % 2, -x))
print(b, c)
print(log)'''),
('双向状态变换', '''a, b, c = 2, 3, 5
r = []
for k in range(1, 9):
    a, b = (a+b+k) % 11, (a*2-c) % 11
    if b < a:
        c = (c+b-k) % 13
    else:
        a, c = c % 11, (a+c) % 13
    r.append((a, b, c))
print(r)'''),
('异常控制流', '''r = []
for n in range(5):
    try:
        r.append(10 // (n-2))
        if n % 2:
            continue
        r.append(n)
    except ZeroDivisionError:
        r.append(7)
    else:
        r.append(8)
    finally:
        r.append(-n)
print(r)'''),
]

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def prompt(q, kind, index):
    name = q['styles'][index] if kind == 'gen' else q['reviews'][index]
    style = STYLES[name] if kind == 'gen' else REVIEWS[name]
    return SYSTEM + '\n' + style + '\n\n程序：\n' + q['program'] + '\n'

def prepare():
    if (CHECK/'题库.json').exists():
        raise RuntimeError('题库已冻结；不覆盖已有题库。')
    rng = random.Random(SEED)
    bank = []
    for n, (topic, code) in enumerate(PROGRAMS, 1):
        styles = []
        while len(styles) < 10:
            block = list(STYLES)
            rng.shuffle(block)
            styles.extend(block)
        reviews = list(REVIEWS)
        rng.shuffle(reviews)
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(compile(code, f'Q{n:02}', 'exec'), {})
        bank.append(dict(id=f'Q{n:02}', topic=topic, program=code,
                         gold=capture.getvalue().rstrip('\n'),
                         styles=styles[:10], reviews=reviews))
    dump(CHECK/'题库.json', bank)
    manifest = dict(frozen_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    model=MODEL, reasoning_effort='low', seed=SEED,
                    bank_sha256=sha((CHECK/'题库.json').read_text(encoding='utf-8')),
                    protocol_sha256=sha((ROOT/'实验方案.md').read_text(encoding='utf-8')),
                    programs=20, draws_per_fixed_question=10,
                    method_stages=[4, 7, 10], tie_rule='first-review-then-first-generator',
                    temperature=None, top_p=None)
    dump(CHECK/'冻结清单.json', manifest)
    text = '# 正式题库与离线标准答案\n\n标准答案只用于评分，严禁提供给被测模型。\n'
    for q in bank:
        text += f'\n## {q["id"]} {q["topic"]}\n\n```python\n{q["program"]}\n```\n\n标准输出：\n\n```text\n{q["gold"]}\n```\n'
    (ROOT/'题库与标准答案.md').write_text(text, encoding='utf-8')
    print('Frozen: 20 problems; no formal calls yet.', flush=True)

def norm(answer):
    lines = str(answer).strip('\r\n').splitlines()
    return '\n'.join(re.sub(r'[^\S\n]+', '', line) for line in lines)

def parse(raw):
    try:
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned)
        obj = json.loads(cleaned)
        ans = obj['answer']
        if not isinstance(ans, str) or not ans.strip():
            return None
        return norm(ans)
    except (ValueError, KeyError, TypeError):
        return None

def load_records(qid):
    result = {}
    for p in (DATA/qid).glob('*.json'):
        obj = json.loads(p.read_text(encoding='utf-8'))
        if 'kind' in obj:
            result[(obj['kind'], obj['index'])] = obj
    return result

def best(records, reviews_first=False):
    valid = [r for r in records if r.get('answer') is not None]
    if not valid:
        return None, 0, False
    counts = {}
    for r in valid:
        counts[r['answer']] = counts.get(r['answer'], 0)+1
    maximum = max(counts.values())
    tied = {a for a, count in counts.items() if count == maximum}
    ordered = sorted(valid, key=lambda r: (r['kind'] != 'review', r['index'])) if reviews_first else valid
    winner = next(r['answer'] for r in ordered if r['answer'] in tied)
    return winner, maximum, len(tied) == 1

def display_answer(records, answer):
    for r in records:
        if answer is not None and r['answer'] == answer:
            cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', r['raw'].strip())
            return json.loads(cleaned)['answer']
    return None

def stage_decision(gens, reviews):
    answer, votes, unique = best(gens)
    support = {g['style'] for g in gens if answer is not None and g['answer'] == answer}
    threshold = 2 if len(gens) == 3 else 3
    return bool(answer is not None and unique and votes >= threshold and len(support) >= 2
                and reviews[-1]['answer'] == answer), answer

def replay_method(gens, available_reviews):
    """Frozen policy: only stages 4/7 may stop early; stage 10 always FinalVote."""
    for j, size in enumerate([3, 5, 7]):
        if len(available_reviews) <= j:
            return None
        reviews = available_reviews[:j+1]
        if size == 7:
            return dict(answer=best(gens[:size]+reviews, reviews_first=True)[0],
                        calls=10, stop='budget'), reviews
        stop, answer = stage_decision(gens[:size], reviews)
        if stop:
            return dict(answer=answer, calls=size+len(reviews), stop='verified'), reviews
    raise AssertionError('unreachable')

def call_one(q, kind, index, cli):
    out = DATA/q['id']/f'{kind}_{index+1:02}.json'
    if out.exists():
        return json.loads(out.read_text(encoding='utf-8'))
    out.parent.mkdir(parents=True, exist_ok=True)
    input_text = prompt(q, kind, index)
    input_path = out.with_suffix('.input.txt')
    input_path.write_text(input_text, encoding='utf-8')
    # No shell interpolation; exact UTF-8 prompt sent through stdin.
    cmd = [cli, 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
           '--skip-git-repo-check', '--sandbox', 'read-only', '--model', MODEL,
           '--config', 'model_reasoning_effort="low"', '--config', 'web_search="disabled"',
           '--disable', 'shell_tool', '--disable', 'multi_agent', '--disable', 'apps',
           '--json', '-']
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    begin = time.monotonic()
    completed = subprocess.run(cmd, input=input_text, encoding='utf-8', errors='replace',
                               capture_output=True, timeout=240, cwd=ROOT/'验证'/'isolated')
    out.with_suffix('.events.jsonl').write_text(completed.stdout, encoding='utf-8')
    out.with_suffix('.stderr.txt').write_text(completed.stderr, encoding='utf-8')
    events = []
    for line in completed.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    messages = [e['item']['text'] for e in events if e.get('type') == 'item.completed'
                and e.get('item', {}).get('type') == 'agent_message']
    tools = [e for e in events if e.get('type', '').startswith('item.')
             and e.get('item', {}).get('type') in ('command_execution', 'mcp_tool_call',
                  'web_search', 'file_change', 'collab_tool_call')]
    turns = [e for e in events if e.get('type') == 'turn.completed']
    final = messages[-1] if messages else ''
    record = dict(question=q['id'], kind=kind, index=index,
                  style=(q['styles'] if kind == 'gen' else q['reviews'])[index],
                  requested_model=MODEL, reasoning_effort='low', context='fresh-ephemeral',
                  started_at=started, elapsed_seconds=round(time.monotonic()-begin, 3),
                  command=cmd, prompt_sha256=sha(input_text),
                  raw=final, raw_sha256=sha(final), answer=parse(final),
                  returncode=completed.returncode, tool_events=tools,
                  completed_turns=len(turns), usage=[t.get('usage') for t in turns],
                  thread_ids=[e.get('thread_id') for e in events if e.get('type') == 'thread.started'])
    dump(out, record)
    print(f'{q["id"]} {kind}{index+1:02}: exit={completed.returncode}, '
          f'parsed={record["answer"] is not None}, {record["elapsed_seconds"]}s', flush=True)
    if completed.returncode or tools or len(turns) != 1 or not final:
        raise RuntimeError(f'Invalid single-call execution: {out}; preserved, never silently retried')
    return record

def run_question(q, cli):
    gens = []
    reviews = []
    stopped = False
    # Stage-wise scheduling: the method cannot inspect future baseline draws.
    for stage, size in enumerate([3, 5, 7]):
        while len(gens) < size:
            gens.append(call_one(q, 'gen', len(gens), cli))
        reviews.append(call_one(q, 'review', stage, cli))
        if size == 7 or stage_decision(gens, reviews)[0]:
            stopped = True
            break
    assert stopped
    # Additional fixed-baseline draws happen after the adaptive decision.
    while len(gens) < 10:
        gens.append(call_one(q, 'gen', len(gens), cli))
    return q['id']

def verify_frozen():
    manifest = json.loads((CHECK/'冻结清单.json').read_text(encoding='utf-8'))
    for file, key in [(CHECK/'题库.json', 'bank_sha256'), (ROOT/'实验方案.md', 'protocol_sha256')]:
        if sha(file.read_text(encoding='utf-8')) != manifest[key]:
            raise RuntimeError(f'Frozen file changed: {file}')

def analyse(require_complete=False):
    verify_frozen()
    bank = json.loads((CHECK/'题库.json').read_text(encoding='utf-8'))
    rows = []
    for q in bank:
        records = load_records(q['id'])
        if not all(('gen', i) in records for i in range(10)):
            continue
        gens = [records[('gen', i)] for i in range(10)]
        if any(r['returncode'] or r['tool_events'] or r['completed_turns'] != 1 for r in gens):
            continue
        row = dict(id=q['id'], topic=q['topic'], gold=q['gold'],
                   generated_answers=[r['answer'] for r in gens], fixed={})
        for k in [1, 3, 5, 10]:
            answer = best(gens[:k])[0]
            row['fixed'][str(k)] = dict(answer=answer, display_answer=display_answer(gens[:k],answer),
                                       correct=answer == norm(q['gold']), calls=k)
        available_reviews = []
        for j in range(3):
            review = records.get(('review', j))
            if review is None or review['returncode'] or review['tool_events'] or review['completed_turns'] != 1:
                break
            available_reviews.append(review)
        replay = replay_method(gens, available_reviews)
        if replay is None:
            continue
        method, review_records = replay
        method['correct'] = method['answer'] == norm(q['gold'])
        method['display_answer'] = display_answer(gens[:method['calls']-len(review_records)]+review_records,method['answer'])
        row['method'] = method
        row['reviews'] = [dict(style=r['style'], answer=r['answer']) for r in review_records]
        row['all_ten_wrong'] = all(r['answer'] != norm(q['gold']) for r in gens)
        wrong = [r['answer'] for r in gens if r['answer'] is not None and r['answer'] != norm(q['gold'])]
        row['dominant_wrong_count'] = max([wrong.count(a) for a in set(wrong)], default=0)
        rows.append(row)
    if require_complete and len(rows) != 20:
        raise RuntimeError(f'Only {len(rows)}/20 complete problems; no final report allowed')
    def metric(method, k=None):
        values = [r['method'] if method else r['fixed'][str(k)] for r in rows]
        return dict(n=len(values), correct=sum(v['correct'] for v in values),
                    accuracy=sum(v['correct'] for v in values)/len(values) if values else None,
                    mean_calls=sum(v['calls'] for v in values)/len(values) if values else None)
    summary = dict(status='complete' if len(rows) == 20 else 'incomplete', model=MODEL,
                   n=len(rows), fixed={str(k): metric(False, k) for k in [1, 3, 5, 10]},
                   method=metric(True), all_ten_wrong=[r['id'] for r in rows if r['all_ten_wrong']],
                   method_gains_vs_single=[r['id'] for r in rows if not r['fixed']['1']['correct'] and r['method']['correct']],
                   method_losses_vs_single=[r['id'] for r in rows if r['fixed']['1']['correct'] and not r['method']['correct']],
                   false_early_stops=[r['id'] for r in rows if not r['method']['correct'] and r['method']['stop']=='verified'],
                   reversals={f'{a}->{b}': [r['id'] for r in rows if r['fixed'][str(a)]['correct']
                                              and not r['fixed'][str(b)]['correct']]
                              for a, b in [(1, 3), (3, 5), (5, 10)]},
                   rows=rows)
    dump(CHECK/'实验结果.json', summary)
    # Raw archive integrity; operational inputs are preserved exactly.
    hashes = {}
    for path in sorted(DATA.rglob('*')):
        if path.is_file():
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    hash_path = CHECK/'原始记录校验值.json'
    if hash_path.exists():
        previous = json.loads(hash_path.read_text(encoding='utf-8'))
        for relative, digest in previous.items():
            if hashes.get(relative) != digest:
                raise RuntimeError(f'Original record changed or disappeared: {relative}')
    dump(hash_path, hashes)
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, ensure_ascii=False, indent=2))
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--analyse', action='store_true')
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.run:
        verify_frozen()
        cli = shutil.which('codex')
        if not cli:
            raise RuntimeError('codex CLI missing')
        (CHECK/'isolated').mkdir(exist_ok=True)
        bank = json.loads((CHECK/'题库.json').read_text(encoding='utf-8'))[:args.limit]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = [pool.submit(run_question, q, cli) for q in bank]
            for job in concurrent.futures.as_completed(jobs):
                print('Completed question:', job.result(), flush=True)
        analyse(require_complete=args.require_complete)
    if args.analyse:
        analyse(require_complete=args.require_complete)

if __name__ == '__main__':
    main()
