from __future__ import annotations
import json, time
import numpy as np, pandas as pd, torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from ml.common import build_vocab, encode_texts, labels_to_ids, load_splits, set_seed
from ml.config import CFG, DATA_RAW, LABEL_ORDER, TABLES_DIR
from ml.models import SEQUENCE_MODEL_NAMES, TfidfMLP, create_sequence_model

def sample_train(df):
    parts=[]
    for _,g in df.groupby('Dialogue_Act'):
        n=max(1,min(len(g),int(round(CFG.train_sample_size*len(g)/len(df)))))
        parts.append(g.sample(n,random_state=CFG.seed))
    return pd.concat(parts,ignore_index=True).sample(frac=1,random_state=CFG.seed).reset_index(drop=True)

def main():
    set_seed()
    df=sample_train(load_splits(DATA_RAW)['train'])
    y=labels_to_ids(df.Dialogue_Act)
    weights=torch.tensor(compute_class_weight(class_weight='balanced',classes=np.arange(len(LABEL_ORDER)),y=y),dtype=torch.float32)
    rows=[]
    vec=TfidfVectorizer(max_features=CFG.tfidf_features,ngram_range=(1,2),min_df=2,sublinear_tf=True)
    X=vec.fit_transform(df.Utterance)
    model=TfidfMLP(X.shape[1],len(LABEL_ORDER),hidden_dim=128,dropout=.3)
    opt=torch.optim.Adam(model.parameters(),lr=CFG.learning_rate); lossf=nn.CrossEntropyLoss(weight=weights)
    idx=np.arange(len(y)); rng=np.random.default_rng(CFG.seed); t=time.perf_counter()
    for _ in range(CFG.epochs):
        rng.shuffle(idx)
        for start in range(0,len(idx),CFG.batch_size):
            bi=idx[start:start+CFG.batch_size]; xb=torch.tensor(X[bi].toarray(),dtype=torch.float32); yb=torch.tensor(y[bi])
            opt.zero_grad(); loss=lossf(model(xb),yb); loss.backward(); opt.step()
    rows.append({'modelo':'MLP-TFIDF','tiempo_entrenamiento_seg':time.perf_counter()-t})
    vocab=build_vocab(df.Utterance); Xseq=torch.tensor(encode_texts(df.Utterance,vocab)); Y=torch.tensor(y)
    loader=DataLoader(TensorDataset(Xseq,Y),batch_size=CFG.batch_size,shuffle=True)
    for name in SEQUENCE_MODEL_NAMES:
        model=create_sequence_model(name,len(vocab),len(LABEL_ORDER)); opt=torch.optim.Adam(model.parameters(),lr=CFG.learning_rate); lossf=nn.CrossEntropyLoss(weight=weights)
        t=time.perf_counter()
        for _ in range(CFG.epochs):
            for xb,yb in loader:
                opt.zero_grad(); loss=lossf(model(xb),yb); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5); opt.step()
        rows.append({'modelo':name,'tiempo_entrenamiento_seg':time.perf_counter()-t})
        print(rows[-1],flush=True)
    out=pd.DataFrame(rows)
    out.to_csv(TABLES_DIR/'tiempos_entrenamiento_repeticion.csv',index=False)
    comp=pd.read_csv(TABLES_DIR/'comparacion_modelos.csv').drop(columns=['tiempo_entrenamiento_seg'],errors='ignore').merge(out,on='modelo',how='left')
    cols=['modelo','accuracy','precision_macro','recall_macro','f1_macro','f1_weighted','roc_auc_macro_ovr','tiempo_entrenamiento_seg','tiempo_inferencia_seg','milisegundos_por_registro','tamano_modelo_mb','parametros','epocas']
    comp=comp[cols].sort_values(['f1_macro','accuracy'],ascending=False)
    comp.to_csv(TABLES_DIR/'comparacion_modelos.csv',index=False)
    print(out.to_string(index=False))
if __name__=='__main__': main()
