from __future__ import annotations
import argparse, json, random
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import GroupShuffleSplit
from src.watermeter.digit_model import TinyDigitCNN

SEED=42
def seed_all(seed=SEED):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

def crop_five_digits(image_path, profile, overlap=0.08):
    image=cv2.imread(str(image_path))
    if image is None: raise ValueError(f"Cannot read image: {image_path}")
    h,w=image.shape[:2]; x1,y1,x2,y2=profile["integer_register_roi"]
    roi=image[int(y1*h):int(y2*h),int(x1*w):int(x2*w)]
    if roi.size==0: raise ValueError(f"Empty register ROI for {image_path}")
    rh,rw=roi.shape[:2]; cell=rw/5.0; crops=[]
    for i in range(5):
        left=max(0,int(i*cell-overlap*cell))
        right=min(rw,int((i+1)*cell+overlap*cell))
        digit=roi[:,left:right]
        digit=cv2.cvtColor(digit,cv2.COLOR_BGR2GRAY)
        digit=cv2.resize(digit,(32,48),interpolation=cv2.INTER_AREA)
        digit=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(4,4)).apply(digit)
        crops.append(digit)
    return crops

class MeterDigitDataset(Dataset):
    def __init__(self, frame, profile):
        self.samples=[]
        for row in frame.to_dict("records"):
            labels=[int(row[f"digit_{i}"]) for i in range(1,6)]
            crops=crop_five_digits(row["image_path"],profile)
            self.samples.extend((crop,label) for crop,label in zip(crops,labels))
    def __len__(self): return len(self.samples)
    def __getitem__(self,index):
        image,label=self.samples[index]
        x=torch.from_numpy(image.astype(np.float32)/255.0).unsqueeze(0)
        # Mild illumination/contrast perturbation; geometry remains fixed.
        if self.training and random.random()<0.5:
            x=torch.clamp((x-0.5)*random.uniform(0.85,1.15)+0.5,0,1)
        return x,torch.tensor(label,dtype=torch.long)

def split_frame(df):
    if "split" in df.columns and df["split"].fillna("").astype(str).str.len().gt(0).all():
        return (df[df.split=="train"],df[df.split=="val"],df[df.split=="test"])
    groups=df["meter_id"].astype(str) if "meter_id" in df else df["image_path"].astype(str)
    if groups.nunique()<3:
        raise SystemExit("Need at least 3 distinct meter_id groups for train/validation/test without meter leakage. Prefer many more.")
    train_idx=next(GroupShuffleSplit(n_splits=1,test_size=0.30,random_state=SEED).split(df,groups=groups))
    temp=df.iloc[temp_idx]; temp_groups=groups.iloc[temp_idx]
    val_rel,test_rel=next(GroupShuffleSplit(n_splits=1,test_size=0.50,random_state=SEED).split(temp,groups=temp_groups))
    return df.iloc[train_idx],temp.iloc[val_rel],temp.iloc[test_rel]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",required=True); ap.add_argument("--profile",required=True)
    ap.add_argument("--epochs",type=int,default=40); ap.add_argument("--batch-size",type=int,default=64)
    ap.add_argument("--out",default="models/digit_cnn")
    a=ap.parse_args(); seed_all()
    df=pd.read_csv(a.csv).dropna(subset=[f"digit_{i}" for i in range(1,6)]).copy()
    if len(df)<10: raise SystemExit("Need at least 10 fully labeled meter images; preferably hundreds/thousands across many physical meters.")
    for c in [f"digit_{i}" for i in range(1,6)]:
        df[c]=df[c].astype(int)
        if not df[c].between(0,9).all(): raise ValueError(f"{c} must contain only digits 0..9")
    profile=json.loads(Path(a.profile).read_text(encoding="utf-8"))
    train_df,val_df,test_df=split_frame(df)
    if min(len(train_df),len(val_df),len(test_df))==0:
        raise SystemExit("Group split produced an empty partition. Add more distinct meter_id values or supply explicit split values.")
    train_ds=MeterDigitDataset(train_df,profile); train_ds.training=True
    val_ds=MeterDigitDataset(val_df,profile); val_ds.training=False
    test_ds=MeterDigitDataset(test_df,profile); test_ds.training=False
    device="cuda" if torch.cuda.is_available() else "cpu"
    train_loader=DataLoader(train_ds,batch_size=a.batch_size,shuffle=True)
    val_loader=DataLoader(val_ds,batch_size=a.batch_size)
    test_loader=DataLoader(test_ds,batch_size=a.batch_size)
    model=TinyDigitCNN().to(device); optimizer=torch.optim.AdamW(model.parameters(),lr=1e-3)
    criterion=nn.CrossEntropyLoss(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    best=0.0
    for epoch in range(1,a.epochs+1):
        model.train(); total=correct=loss_sum=0
        for x,y in train_loader:
            x,y=x.to(device),y.to(device); optimizer.zero_grad()
            logits=model(x); loss=criterion(logits,y); loss.backward(); optimizer.step()
            loss_sum+=loss.item()*len(y); correct+=(logits.argmax(1)==y).sum().item(); total+=len(y)
        model.eval(); vcorrect=vtotal=0
        with torch.no_grad():
            for x,y in val_loader:
                x,y=x.to(device),y.to(device); vcorrect+=(model(x).argmax(1)==y).sum().item(); vtotal+=len(y)
        val_acc=vcorrect/max(1,vtotal)
        print(f"epoch={epoch:03d} train_loss={loss_sum/max(1,total):.4f} train_acc={correct/max(1,total):.4f} val_acc={val_acc:.4f}")
        if val_acc>best:
            best=val_acc
            torch.save({"model_state":model.cpu().state_dict(),"val_accuracy":best,"input_shape":[1,1,48,32],"profile":profile},out/"best.pt")
            model.to(device)
    model.load_state_dict(torch.load(out/"best.pt",map_location=device,weights_only=True)["model_state"])
    model.eval(); correct=total=0
    with torch.no_grad():
        for x,y in test_loader:
            pred=model(x.to(device)).argmax(1).cpu(); correct+=(pred==y).sum().item(); total+=len(y)
    # Also report full five-digit exact match, reconstructed in image-row order.
    full_exact=0; wheel_correct=np.zeros(5,dtype=np.int64); wheel_total=np.zeros(5,dtype=np.int64)
    with torch.no_grad():
        for row in test_df.to_dict("records"):
            truth="".join(str(int(row[f"digit_{i}"])) for i in range(1,6))
            crops=crop_five_digits(row["image_path"],profile)
            x=torch.from_numpy(np.stack(crops).astype(np.float32)/255.0)[:,None,:,:].to(device)
            # Match training preprocessing: CLAHE was already applied in crop_five_digits.
            pred_values=model(x).argmax(1).cpu().tolist()
            pred="".join(str(int(v)) for v in pred_values)
            truth_values=[int(row[f"digit_{i}"]) for i in range(1,6)]
            for j,(pv,tv) in enumerate(zip(pred_values,truth_values)):
                wheel_correct[j]+=int(pv==tv); wheel_total[j]+=1
            full_exact += int(pred==truth)
    metrics={"test_digit_accuracy":correct/max(1,total),"test_digit_count":total,
             "test_full_register_exact_match":full_exact/max(1,len(test_df)),
             "test_full_register_count":len(test_df),
             "per_wheel_accuracy":{f"wheel_{i+1}":float(wheel_correct[i]/max(1,wheel_total[i])) for i in range(5)},
             "best_val_accuracy":best,
             "train_images":len(train_df),"val_images":len(val_df),"test_images":len(test_df),
             "split_unit":"meter_id","device":device}
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
