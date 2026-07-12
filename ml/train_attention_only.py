from __future__ import annotations
import json
import pandas as pd
from ml.common import load_splits, set_seed
from ml.config import CFG, DATA_RAW, MODELS_DIR
from ml.train_all import train_sequence

set_seed()
splits=load_splits(DATA_RAW)
train_df=splits['train']
parts=[]
for label, group in train_df.groupby('Dialogue_Act'):
    count=max(1,min(len(group),int(round(CFG.train_sample_size*len(group)/len(train_df)))))
    parts.append(group.sample(count,random_state=CFG.seed))
train_sample=pd.concat(parts,ignore_index=True).sample(frac=1,random_state=CFG.seed).reset_index(drop=True)
vocab=json.loads((MODELS_DIR/'vocab.json').read_text(encoding='utf-8'))
row,_=train_sequence('BiLSTM-Atencion',train_sample,splits['dev'],splits['test'],vocab)
print(row)
