from __future__ import annotations
import argparse
from pathlib import Path
import torch
from src.watermeter.digit_model import TinyDigitCNN

p=argparse.ArgumentParser()
p.add_argument("--checkpoint",required=True); p.add_argument("--out",required=True)
a=p.parse_args()
ckpt=torch.load(a.checkpoint,map_location="cpu",weights_only=True)
model=TinyDigitCNN(); model.load_state_dict(ckpt["model_state"]); model.eval()
out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
dummy=torch.zeros(1,1,48,32)
torch.onnx.export(model,dummy,str(out),input_names=["digit_image"],output_names=["logits"],
                  dynamic_axes={"digit_image":{0:"batch"},"logits":{0:"batch"}},
                  opset_version=13,dynamo=False)
print(f"Exported ONNX: {out}")
