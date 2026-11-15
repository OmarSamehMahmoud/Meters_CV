import argparse,json
from pathlib import Path
from .pipeline import run_pipeline

def main():
    ap=argparse.ArgumentParser(description="Mechanical water meter CV baseline")
    ap.add_argument("--image",required=True)
    ap.add_argument("--profile",default="configs/meter_profile.example.json")
    ap.add_argument("--out",default="runs/result.json")
    args=ap.parse_args()
    result=run_pipeline(args.image,args.profile)
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
