import argparse,json
from pathlib import Path
from .pipeline import run_pipeline
from .digit_inference import predict_five_digits

def main():
    ap=argparse.ArgumentParser(description="Mechanical water meter CV baseline")
    ap.add_argument("--image",required=True)
    ap.add_argument("--profile",default="configs/meter_profile.example.json")
    ap.add_argument("--checkpoint",default=None,help="Optional trained TinyDigitCNN checkpoint")
    ap.add_argument("--out",default="runs/result.json")
    args=ap.parse_args()
    result=run_pipeline(args.image,args.profile)
    if args.checkpoint:
        import json as _json
        profile=_json.loads(Path(args.profile).read_text(encoding="utf-8"))
        digit_result=predict_five_digits(args.image,profile,args.checkpoint)
        result.update(digit_result)
        if result["mean_digit_confidence"]>=0.90:
            result["quality_flags"]=[f for f in result["quality_flags"] if f!="digit_model_not_trained"]
        else:
            result["quality_flags"].append("digit_confidence_below_acceptance_threshold")
    result["status"]="needs_review"
    result["reading_m3"]=None
    result["quality_flags"].append("dial_calibration_and_full_reading_logic_not_validated")
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
