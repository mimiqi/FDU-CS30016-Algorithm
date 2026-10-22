"""Exact Hash + independent random-hyperplane LSH, with offline-only ground truth."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import csv, hashlib, json, math, platform, time
import numpy as np
from threadpoolctl import threadpool_limits, threadpool_info
from prepare import sha, save

TAU=0.8
SEEDS=[20261022,20261023,20261024]
CONFIGS=[(12,46),(8,46),(16,46),(12,23),(12,92)]

def probability(s,k,L):
    p=1-math.acos(s)/math.pi
    return -math.expm1(L*math.log1p(-p**k))

def parameter_design():
    rows=[]
    for k in range(1,25):
        p=1-math.acos(TAU)/math.pi
        L=math.ceil(math.log(.05)/math.log1p(-p**k))
        rows.append({'k':k,'L':L,'near':probability(.8,k,L),'far':probability(.2,k,L)})
    selected=next(r for r in rows if r['far']<=.05)
    assert (selected['k'],selected['L'])==(12,46)
    return rows

class ExactHash:
    def __init__(self,texts,digest=None):
        self.texts=texts
        self.digest=digest or (lambda text:hashlib.sha256(text.encode('utf-8')).digest())
        self.table={}
        for i,text in enumerate(texts):
            self.table.setdefault(self.digest(text),[]).append(i)
    def query(self,text):
        return np.asarray([i for i in self.table.get(self.digest(text),()) if self.texts[i]==text],dtype=np.uint32)
    def memory(self):
        # Only the index, excluding shared source strings and the function object.
        return (sys.getsizeof(self.table)+sum(sys.getsizeof(k)+sys.getsizeof(v)+
                sum(sys.getsizeof(i) for i in v) for k,v in self.table.items()))

class HyperplaneLSH:
    def __init__(self,X,k=12,L=46,seed=SEEDS[0]):
        self.k,self.L,self.N,self.d=k,L,len(X),X.shape[1]
        # A fixed larger independent bank makes the ablations and scale series comparable.
        bank=np.random.default_rng(seed).normal(size=(92,16,self.d)).astype(np.float32)
        self.R=bank[:L,:k].copy().reshape(L*k,self.d)
        self.weights=(np.uint32(1)<<np.arange(k,dtype=np.uint32))
        self.offsets=[]; self.ids=[]
        for t in range(L):
            bits=(X@self.R[t*k:(t+1)*k].T>=0)
            codes=(bits*self.weights).sum(axis=1,dtype=np.uint32)
            counts=np.bincount(codes,minlength=1<<k)
            offsets=np.empty((1<<k)+1,np.uint32); offsets[0]=0
            np.cumsum(counts,out=offsets[1:])
            self.offsets.append(offsets)
            self.ids.append(np.argsort(codes,kind='stable').astype(np.uint32))
    def candidates(self,u):
        codes=((self.R@u>=0).reshape(self.L,self.k)*self.weights).sum(axis=1,dtype=np.uint32)
        buckets=[self.ids[t][int(self.offsets[t][c]):int(self.offsets[t][c+1])] for t,c in enumerate(codes)]
        return np.unique(np.concatenate(buckets))
    def memory(self):
        arrays=[self.R,self.weights]+self.offsets+self.ids
        return {'payload_bytes':sum(a.nbytes for a in arrays),
                'container_bytes':sum(sys.getsizeof(a)-a.nbytes if a.flags.owndata else sys.getsizeof(a) for a in arrays)+sys.getsizeof(self.offsets)+sys.getsizeof(self.ids),
                'planes_bytes':self.R.nbytes,'offsets_bytes':sum(a.nbytes for a in self.offsets),
                'posting_bytes':sum(a.nbytes for a in self.ids)}

def brute(X,u):
    return np.flatnonzero(X@u>=TAU).astype(np.uint32)

def reuse(text,u,X,exact,index):
    hits=exact.query(text)
    if len(hits):
        return hits,np.empty(0,np.uint32),'exact'
    C=index.candidates(u)
    return C[X[C]@u>=TAU],C,'semantic'

def summarize(rows):
    active=[r for r in rows if r['truth_count']]
    return {'queries':len(rows),'nonempty_truth':len(active),'empty_truth':len(rows)-len(active),
            'macro_recall':float(np.mean([r['hits']/r['truth_count'] for r in active])) if active else None,
            'micro_recall':sum(r['hits'] for r in active)/sum(r['truth_count'] for r in active) if active else None,
            'reuse_hit_rate_nonempty':sum(r['hits']>0 for r in active)/len(active) if active else None,
            'mean_candidates':float(np.mean([r['candidates'] for r in rows])),
            'p95_candidates':float(np.percentile([r['candidates'] for r in rows],95)),
            'candidate_ratio':float(np.mean([r['candidates']/r['N'] for r in rows])),
            'mean_truth':float(np.mean([r['truth_count'] for r in rows])),
            'mean_false_candidates':float(np.mean([r['candidates']-r['hits'] for r in rows]))}

def timings(methods,Q,rounds=5):
    for method in methods.values():
        for i in range(min(20,Q)): method(i)
    measurements={name:[] for name in methods}
    for r in range(rounds):
        names=list(methods)
        names=names[r%len(names):]+names[:r%len(names)]
        for i in range(Q):
            for name in names:
                start=time.perf_counter_ns(); methods[name](i)
                measurements[name].append((time.perf_counter_ns()-start)/1e6)
    return {name:{'mean_ms':float(np.mean(v)),'median_ms':float(np.median(v)),
                   'p95_ms':float(np.percentile(v,95)),'samples':len(v)} for name,v in measurements.items()}

def evaluate(X,U,texts,query_texts,k,L,seed,save_trace=False):
    exact=ExactHash(texts)
    start=time.perf_counter(); index=HyperplaneLSH(X,k,L,seed); build=time.perf_counter()-start
    rows=[]; trace=[]
    for i,(u,text) in enumerate(zip(U,query_texts)):
        G=brute(X,u)
        found,C,path=reuse(text,u,X,exact,index)
        assert path=='semantic' and np.all(np.isin(found,G))
        expected=np.intersect1d(C,G)
        assert np.array_equal(found,expected)
        rows.append({'query':i,'N':len(X),'truth_count':len(G),'candidates':len(C),'hits':len(found)})
        if save_trace:
            trace.append({'query':i,'truth':G.tolist(),'candidates':C.tolist(),'returned':found.tolist()})
    result={'k':k,'L':L,'seed':seed,'N':len(X),'summary':summarize(rows),'build_seconds':build,
            'lsh_memory':index.memory(),'projection_dots_per_query':k*L,
            'theory_near':probability(.8,k,L),'theory_far':probability(.2,k,L),'per_query':rows}
    return result,trace,exact,index

def run():
    manifest=json.loads((ROOT/'数据/划分.json').read_text(encoding='utf-8'))
    metadata=json.loads((ROOT/'验证/向量元数据.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'.cache/embeddings.npy')==metadata['sha256']
    E=np.load(ROOT/'.cache/embeddings.npy',allow_pickle=False)
    N=len(manifest['history']); X=E[:N]; U=E[N:]
    texts=[r['text'] for r in manifest['history']]
    query_texts=[r['text'] for r in manifest['semantic_queries']]
    assert len(U)==300 and not set(texts)&set(query_texts)
    results=[]
    for k,L in CONFIGS:
        seeds=SEEDS if (k,L)==(12,46) else SEEDS[:1]
        for seed in seeds:
            main=(k,L,seed)==(12,46,SEEDS[0])
            result,trace,exact,index=evaluate(X,U,texts,query_texts,k,L,seed,main)
            if main:
                save(ROOT/'验证/主实验逐查询.json',trace)
                semantic_time=timings({'Brute-force':lambda i:brute(X,U[i]),
                    'Exact Hash Only':lambda i:exact.query(query_texts[i]),
                    'Hash + LSH':lambda i:reuse(query_texts[i],U[i],X,exact,index)},len(U))
                exact_ids=manifest['exact_ids']
                exact_time=timings({'Brute-force':lambda j:brute(X,X[exact_ids[j]]),
                    'Exact Hash Only':lambda j:exact.query(texts[exact_ids[j]]),
                    'Hash + LSH':lambda j:reuse(texts[exact_ids[j]],None,X,exact,index)},len(exact_ids))
                for i in exact_ids:
                    found,C,path=reuse(texts[i],None,X,exact,index)
                    assert path=='exact' and i in found and len(C)==0
                main_memory={'vectors_bytes':X.nbytes,'raw_text_utf8_bytes':sum(len(t.encode('utf-8')) for t in texts),
                             'raw_text_python_bytes':sys.getsizeof(texts)+sum(sys.getsizeof(t) for t in texts),
                             'exact_index_bytes':exact.memory(),'lsh':index.memory()}
                baseline={'Brute-force':{'macro_recall':1.0,'candidate_ratio':1.0,'mean_candidates':N},
                          'Exact Hash Only':{'macro_recall':0.0,'candidate_ratio':0.0,'mean_candidates':0}}
            results.append(result)
            print(json.dumps({key:result[key] for key in ['k','L','seed','summary']},ensure_ascii=False),flush=True)
    scales=[]
    for n in [2000,5000,N]:
        if n==N:
            result=results[0]
        else:
            result,_,_,_=evaluate(X[:n],U,texts[:n],query_texts,12,46,SEEDS[0])
        scales.append({key:value for key,value in result.items() if key!='per_query'})
    output={'status':'complete','tau':TAU,'N':N,'d':X.shape[1],'semantic_queries':len(U),'exact_queries':100,
            'seed':SEEDS[0],'parameter_design':parameter_design(),'main':results[0],
            'baselines':baseline,'semantic_timing':semantic_time,'exact_timing':exact_time,
            'exact_hit_rate':1.0,'exact_vector_comparisons':0,'memory':main_memory,
            'configurations':results,'scales':scales,'threadpools':threadpool_info(),
            'timing_scope':'Precomputed query vector; SHA256, buckets, dedup and cosine included; BLAS=1 thread; 5 rounds after warmup.',
            'source_hashes':{name:sha(ROOT/name) for name in ['实验方案.md','数据/划分.json','验证/向量元数据.json','验证/主实验逐查询.json']}}
    save(ROOT/'验证/实验结果.json',output)
    save(ROOT/'验证/运行源码校验.json',{f'验证/{name}':sha(ROOT/'验证'/name) for name in ['prepare.py','experiment.py']})
    print('Experiment complete',flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=1):run()
