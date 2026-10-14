"""Integrity and adversarial control-flow tests, without model calls."""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import experiment as e

def strict_norm(raw):
    # Retains integer-token boundaries: "1 23" differs from "12 3".
    return '\n'.join(' '.join(re.findall(r'-?\d+|True|False|[^\s]', line))
                     for line in raw.strip('\r\n').splitlines())

def record(a, style, kind='gen', index=0):
    return dict(answer=a, style=style, kind=kind, index=index)

def test_controller():
    # Agreement between one strategy repeated twice must not trigger a stop.
    assert not e.stage_decision([record('A','s'), record('A','s'), record('B','t')],
                                [record('A','v','review')])[0]
    # Two distinct generator strategies plus independent matching check can stop.
    assert e.stage_decision([record('A','s'), record('A','t'), record('B','u')],
                           [record('A','v','review')])[0]
    # A dissenting check forces more sampling, regardless of majority size.
    assert not e.stage_decision([record('A',str(i)) for i in range(3)],
                                [record('B','v','review')])[0]
    # No unique generator leader: cannot stop.
    assert not e.stage_decision([record('A','s'),record('B','t'),record(None,'u')],
                                [record('A','v','review')])[0]
    # Generator tie uses first occurrence; final tie prefers blind verification.
    tied = [record('A','s',index=0),record('B','v','review',0)]
    assert e.best(tied)[0] == 'A'
    assert e.best(tied, reviews_first=True)[0] == 'B'
    assert e.best([record(None,'s')])[0] is None
    assert e.parse('{"answer":"0 [1, 2]\\n3","reason":"x"}') == e.norm('0 [1, 2]\n3')
    assert e.parse('not json') is None
    # Stage-10 fallback must use all 10 responses, even if latest checker matches
    # the generator leader. Earlier checkers can change the final vote tie.
    gens=[record(a,str(i),index=i) for i,a in enumerate('AABBABA')]
    reviews=[record(a,'v','review',i) for i,a in enumerate('BBA')]
    result,used=e.replay_method(gens,reviews)
    assert result['calls']==10 and result['answer']=='B' and result['stop']=='budget'

def main():
    test_controller()
    e.verify_frozen()
    summary = e.analyse(require_complete=True)
    bank = json.loads((e.CHECK/'题库.json').read_text(encoding='utf-8'))
    frozen_hashes = json.loads((e.CHECK/'原始记录校验值.json').read_text(encoding='utf-8'))
    records_count = 0
    format_failures = 0
    usage = dict(input_tokens=0, cached_input_tokens=0, output_tokens=0, reasoning_output_tokens=0)
    token_collisions = []
    for q in bank:
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(compile(q['program'],q['id'],'exec'), {})
        assert capture.getvalue().rstrip('\n') == q['gold'], q['id']
        records = e.load_records(q['id'])
        normal_forms = {e.norm(q['gold']): strict_norm(q['gold'])}
        for (kind,index), r in records.items():
            records_count += 1
            assert r['requested_model'] == e.MODEL and r['reasoning_effort'] == 'low'
            assert not r['tool_events'] and r['returncode'] == 0 and r['completed_turns'] == 1
            prefix = e.DATA/q['id']/f'{kind}_{index+1:02}'
            inp = prefix.with_suffix('.input.txt').read_text(encoding='utf-8')
            assert inp == e.prompt(q,kind,index)
            assert e.sha(inp) == r['prompt_sha256']
            assert e.sha(r['raw']) == r['raw_sha256']
            assert r['answer'] == e.parse(r['raw'])
            events=[json.loads(line) for line in prefix.with_suffix('.events.jsonl').read_text(encoding='utf-8').splitlines()
                    if line.startswith('{')]
            completed_items=[v['item'] for v in events if v.get('type')=='item.completed']
            assert all(v['type'] in ('agent_message','reasoning') for v in completed_items)
            assert sum(v['type']=='agent_message' for v in completed_items)==1
            assert sum(v.get('type')=='turn.started' for v in events)==1
            assert sum(v.get('type')=='thread.started' for v in events)==1
            if r['answer'] is None:
                format_failures += 1
            else:
                cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', r['raw'].strip())
                original = json.loads(cleaned)['answer']
                strict = strict_norm(original)
                if r['answer'] in normal_forms and normal_forms[r['answer']] != strict:
                    token_collisions.append([q['id'],kind,index])
                normal_forms[r['answer']] = strict
            for u in r['usage']:
                for key in usage:
                    usage[key] += u.get(key,0)
        row = next(row for row in summary['rows'] if row['id'] == q['id'])
        assert row['method']['calls'] in (4,7,10)
    assert not token_collisions, 'Whitespace normalization merged distinct token sequences'
    for relative, digest in frozen_hashes.items():
        assert hashlib.sha256((e.ROOT/relative).read_bytes()).hexdigest() == digest
    assert records_count == 200 + sum(len(row['reviews']) for row in summary['rows'])
    result = dict(status='passed', questions=20, physical_model_calls=records_count,
                  tools_used_by_respondents=0, format_failures=format_failures,
                  hash_checked_files=len(frozen_hashes), token_boundary_collisions=0,
                  controller_tests='passed', gold_reexecution='passed', usage=usage,
                  method_call_distribution={str(k):sum(r['method']['calls']==k for r in summary['rows'])
                                            for k in (4,7,10)})
    e.dump(e.CHECK/'完整性审计.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
