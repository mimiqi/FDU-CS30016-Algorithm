"""Download public artifacts and encode BANKING77 on CPU. No training or paid API."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps'))
import argparse, csv, hashlib, importlib.metadata, json, os, platform, time, urllib.request
import numpy as np

CACHE = ROOT / '.cache'
DATA = ROOT / '数据'
OUT = ROOT / '验证'
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DATA_REV = '9d081458ff52e53cf7e848f414e6e9344e4e6696'
SEED = 20261022

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def fetch(url, path):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print('Downloading', path.name, flush=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'BHW4-course-experiment/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r, path.with_suffix(path.suffix+'.part').open('wb') as f:
        while chunk := r.read(1024*1024):
            f.write(chunk)
    path.with_suffix(path.suffix+'.part').replace(path)

def prepare():
    DATA.mkdir(exist_ok=True)
    source_file = DATA / '来源与校验.json'
    sources = json.loads(source_file.read_text(encoding='utf-8')) if source_file.exists() else {}
    for split, expected in [('train','b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b'),('test','d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d')]:
        url = f'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{DATA_REV}/banking_data/{split}.csv'
        path = DATA / f'{split}.csv'
        fetch(url, path)
        assert sha(path) == expected, f'Unexpected dataset hash: {split}'
        sources[split] = {'url':url, 'sha256':sha(path)}
    fetch('https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/LICENSE', DATA/'LICENSE-BANKING77')
    if 'model_revision' not in sources:
        with urllib.request.urlopen(f'https://huggingface.co/api/models/{MODEL}', timeout=60) as r:
            sources['model_revision'] = json.load(r)['sha']
    sources['model_id'] = MODEL
    for name in ['onnx/model_quint8_avx2.onnx', 'tokenizer.json', 'config.json', 'sentence_bert_config.json', '1_Pooling/config.json']:
        url = f"https://huggingface.co/{MODEL}/resolve/{sources['model_revision']}/{name}"
        path = CACHE/'model'/name
        fetch(url, path)
        info = {'url':url,'sha256':sha(path),'bytes':path.stat().st_size}
        if name in sources:
            assert sources[name]['sha256'] == info['sha256'], f'Model file changed: {name}'
        sources[name] = info
    save(source_file,sources)
    def read(split):
        with (DATA/f'{split}.csv').open(encoding='utf-8', newline='') as f:
            return [{'source_row':i,'text':r['text'],'category':r['category']} for i,r in enumerate(csv.DictReader(f))]
    train,test = read('train'),read('test')
    def unique(rows):
        seen=set(); result=[]
        for row in rows:
            if row['text'] not in seen:
                seen.add(row['text']); result.append(row)
        return result
    history=unique(train)
    rng=np.random.default_rng(SEED)
    history=[history[i] for i in rng.permutation(len(history))]
    seen={r['text'] for r in history}
    eligible=unique([r for r in test if r['text'] not in seen])
    semantic=[eligible[i] for i in rng.choice(len(eligible),300,replace=False)]
    exact_ids=rng.choice(len(history),100,replace=False).tolist()
    manifest={'seed':SEED,'history':history,'semantic_queries':semantic,'exact_ids':exact_ids,
              'train_rows':len(train),'test_rows':len(test),'eligible_test_unique':len(eligible)}
    save(DATA/'划分.json',manifest)
    return manifest,sources

def encode(manifest,sources):
    import onnxruntime as ort
    from tokenizers import Tokenizer
    texts=[r['text'] for r in manifest['history']+manifest['semantic_queries']]
    text_hash=hashlib.sha256(json.dumps(texts,ensure_ascii=False).encode()).hexdigest()
    embedding_path=CACHE/'embeddings.npy'
    metadata_path=OUT/'向量元数据.json'
    if embedding_path.exists() and metadata_path.exists():
        old=json.loads(metadata_path.read_text(encoding='utf-8'))
        assert old['texts_sha256']==text_hash and old['sha256']==sha(embedding_path)
        assert old['model_revision']==sources['model_revision']
        print('Reusing verified embeddings',flush=True); return
    tok=Tokenizer.from_file(str(CACHE/'model/tokenizer.json'))
    tok.enable_truncation(max_length=256)
    tok.no_padding()
    encoded=tok.encode_batch(texts)
    order=sorted(range(len(encoded)),key=lambda i:len(encoded[i].ids))
    opt=ort.SessionOptions(); opt.intra_op_num_threads=4; opt.inter_op_num_threads=1
    session=ort.InferenceSession(str(CACHE/'model/onnx/model_quint8_avx2.onnx'),sess_options=opt,providers=['CPUExecutionProvider'])
    embeddings=np.empty((len(texts),384),dtype=np.float32)
    input_names={x.name for x in session.get_inputs()}
    print('ONNX inputs:',sorted(input_names),'outputs:',[x.name for x in session.get_outputs()],flush=True)
    start=time.perf_counter()
    for pos in range(0,len(order),32):
        ids=order[pos:pos+32]; width=max(len(encoded[i].ids) for i in ids)
        input_ids=np.zeros((len(ids),width),np.int64)
        mask=np.zeros_like(input_ids); types=np.zeros_like(input_ids)
        for j,i in enumerate(ids):
            n=len(encoded[i].ids); input_ids[j,:n]=encoded[i].ids
            mask[j,:n]=1; types[j,:n]=encoded[i].type_ids
        feeds={k:v for k,v in {'input_ids':input_ids,'attention_mask':mask,'token_type_ids':types}.items() if k in input_names}
        output=session.run(None,feeds)[0]
        pooled=(output*mask[...,None]).sum(axis=1)/mask.sum(axis=1,keepdims=True)
        pooled=pooled/np.linalg.norm(pooled,axis=1,keepdims=True)
        embeddings[ids]=pooled.astype(np.float32)
        if pos%1024==0:
            print(f'Encoded {min(pos+32,len(texts))}/{len(texts)}, {time.perf_counter()-start:.1f}s',flush=True)
    elapsed=time.perf_counter()-start
    assert np.isfinite(embeddings).all()
    assert np.max(np.abs(np.linalg.norm(embeddings,axis=1)-1))<1e-5
    np.save(embedding_path,embeddings,allow_pickle=False)
    versions={p:importlib.metadata.version(p) for p in ['numpy','onnxruntime','tokenizers','threadpoolctl']}
    save(metadata_path,{'model':MODEL,'model_revision':sources['model_revision'], 'export':'onnx/model_quint8_avx2.onnx',
         'pooling':'attention-mask mean + L2 normalization','max_tokens':256,'dtype':'float32','shape':list(embeddings.shape),
         'texts_sha256':text_hash,'sha256':sha(embedding_path),'bytes':embeddings.nbytes,'encode_seconds':elapsed,
         'batch_size':32,'onnx_threads':4,'versions':versions,'python':sys.version,'platform':platform.platform(),
         'processor':platform.processor(),'logical_cpus':os.cpu_count(),'seed':SEED})
    print('Embeddings saved',embeddings.shape,f'{elapsed:.2f}s',flush=True)

if __name__=='__main__':
    manifest,sources=prepare()
    encode(manifest,sources)
