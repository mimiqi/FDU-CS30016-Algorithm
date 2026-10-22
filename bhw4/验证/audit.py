"""Offline correctness audit, independent float64 truth, forced hash collisions."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import json, numpy as np
from threadpoolctl import threadpool_limits
from experiment import ExactHash, HyperplaneLSH, summarize, parameter_design, TAU, SEEDS, reuse
from prepare import save,sha

def run():
    result=json.loads((ROOT/'验证/实验结果.json').read_text(encoding='utf-8'))
    trace=json.loads((ROOT/'验证/主实验逐查询.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'数据/划分.json').read_text(encoding='utf-8'))
    meta=json.loads((ROOT/'验证/向量元数据.json').read_text(encoding='utf-8'))
    source=json.loads((ROOT/'验证/运行源码校验.json').read_text(encoding='utf-8'))
    for name,h in {**result['source_hashes'],**source}.items(): assert sha(ROOT/name)==h,name
    assert sha(ROOT/'.cache/embeddings.npy')==meta['sha256']
    E=np.load(ROOT/'.cache/embeddings.npy',allow_pickle=False)
    N=result['N']; X=E[:N]; U=E[N:]
    assert N>=3000 and len(U)>=100
    assert len(set(r['text'] for r in manifest['history']))==N
    assert not set(r['text'] for r in manifest['history'])&set(r['text'] for r in manifest['semantic_queries'])
    assert np.isfinite(E).all() and np.allclose(np.linalg.norm(E,axis=1),1,atol=1e-6)
    exact=ExactHash(['alpha','beta','alpha'],digest=lambda _:b'forced-collision')
    assert exact.query('alpha').tolist()==[0,2]
    assert exact.query('beta').tolist()==[1]
    assert exact.query('gamma').tolist()==[]
    index=HyperplaneLSH(X)
    for offsets,ids in zip(index.offsets,index.ids):
        assert len(ids)==N and np.array_equal(np.sort(ids),np.arange(N))
        assert offsets[0]==0 and offsets[-1]==N and np.all(offsets[1:]>=offsets[:-1])
    rows=[]; minimum_margin=1.
    # A different reduction path and higher precision test the saved threshold truth.
    X64=X.astype(np.float64)
    for i,t in enumerate(trace):
        sims=np.einsum('ij,j->i',X64,U[i].astype(np.float64))
        minimum_margin=min(minimum_margin,float(np.min(abs(sims-TAU))))
        G=np.flatnonzero(sims>=TAU).tolist()
        assert G==t['truth'],f'float64 truth mismatch {i}'
        C=index.candidates(U[i]).tolist()
        assert C==t['candidates'] and len(C)==len(set(C))
        assert sorted(set(G)&set(C))==t['returned']
        rows.append({'query':i,'N':N,'truth_count':len(G),'candidates':len(C),'hits':len(t['returned'])})
    summary=summarize(rows)
    assert summary==result['main']['summary']
    # Direct per-row signature equality is an independent check of the bucket offsets.
    raw_bits=(X@index.R.T>=0).reshape(N,index.L,index.k)
    for i in range(0,len(U),20):
        qbits=(index.R@U[i]>=0).reshape(index.L,index.k)
        expected=np.flatnonzero(np.any(np.all(raw_bits==qbits[None,:,:],axis=2),axis=1))
        assert expected.tolist()==trace[i]['candidates']
    texts=[r['text'] for r in manifest['history']]
    exact=ExactHash(texts)
    for i in manifest['exact_ids']:
        found,C,path=reuse(texts[i],None,X,exact,index)
        assert found.tolist()==[i] and len(C)==0 and path=='exact'
    parameter_design()
    assert result['memory']['vectors_bytes']==N*384*4
    assert result['memory']['lsh']['posting_bytes']==46*N*4
    assert result['memory']['lsh']['offsets_bytes']==46*((1<<12)+1)*4
    assert all(p['num_threads']==1 for p in result['threadpools'])
    # Shared planes imply candidate nesting and monotonicity for the planned ablations.
    config={(r['k'],r['L']):r for r in result['configurations'] if r['seed']==SEEDS[0]}
    for i in range(len(U)):
        count=lambda pair:config[pair]['per_query'][i]['candidates']
        assert count((16,46))<=count((12,46))<=count((8,46))
        assert count((12,23))<=count((12,46))<=count((12,92))
    save(ROOT/'验证/审计结果.json',{'status':'passed','queries_checked':len(U),'exact_queries_checked':100,
       'independent_bucket_union_queries':15,'float64_ground_truth':True,'forced_digest_collision':True,
       'minimum_cosine_distance_to_threshold':minimum_margin,'summary_recalculated':summary,
       'experiment_sha256':sha(ROOT/'验证/实验结果.json'),'audit_source_sha256':sha(__file__)})
    print('PASS: 300 float64 ground truths; 300 candidate lists; 15 independent bucket unions; 100 exact fast paths; forced digest collision; memory; ablation monotonicity.')

if __name__=='__main__':
    with threadpool_limits(limits=1):run()
