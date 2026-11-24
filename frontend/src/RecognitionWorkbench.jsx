import React, { useEffect, useMemo, useState } from "react";
import { Aperture, CheckCircle2, CircleAlert, Crosshair, Gauge, RefreshCw, Save, ScanLine, SlidersHorizontal, Sparkles, Target, Zap } from "lucide-react";

const API = "http://127.0.0.1:8000/api";
const n = (v) => Number(v ?? 0);
const fmt = (v) => Number.isFinite(Number(v)) ? Number(v).toFixed(3) : "—";

export default function RecognitionWorkbench({ lang="en", onToast=()=>{} }) {
  const ar = lang === "ar";
  const t = (en, a) => ar ? a : en;
  const [channels,setChannels] = useState([]);
  const [channel,setChannel] = useState("cam_01");
  const [cal,setCal] = useState(null);
  const [dialIndex,setDialIndex] = useState(0);
  const [frameTick,setFrameTick] = useState(Date.now());
  const [busy,setBusy] = useState(false);
  const [saving,setSaving] = useState(false);
  const [result,setResult] = useState(null);
  const [alignment,setAlignment] = useState(null);
  const [savingReference,setSavingReference] = useState(false);
  const [error,setError] = useState("");
  const selected = channels.find(c=>c.id===channel);
  const dial = cal?.dials?.[dialIndex];

  useEffect(()=>{let alive=true;fetch(API+"/overview").then(r=>r.json()).then(d=>{if(alive){setChannels(d.channels||[]);if(d.channels?.length)setChannel(d.channels[0].id)}}).catch(()=>setError("API is not reachable"));return()=>{alive=false}},[]);
  useEffect(()=>{let alive=true;setCal(null);fetch(`${API}/cameras/${channel}/calibration`).then(r=>r.ok?r.json():Promise.reject(new Error("Calibration unavailable"))).then(d=>{if(alive)setCal(d)}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[channel]);
  useEffect(()=>{const id=setInterval(()=>setFrameTick(Date.now()),700);return()=>clearInterval(id)},[]);
  useEffect(()=>{let alive=true;fetch(`${API}/cameras/${channel}/alignment`).then(r=>r.ok?r.json():Promise.reject(new Error("Alignment status unavailable"))).then(d=>{if(alive)setAlignment(d)}).catch(()=>{if(alive)setAlignment(null)});return()=>{alive=false}},[channel]);
  const updateRoi=(i,v)=>setCal(c=>({...c,roi:c.roi.map((x,j)=>j===i?Number(v):x)}));
  const updateDial=(key,v)=>setCal(c=>({...c,dials:c.dials.map((d,i)=>i!==dialIndex?d:key==="radius"?{...d,radius:Number(v)}:{...d,center:d.center.map((x,j)=>j===(key==="cx"?0:1)?Number(v):x)})}));
  const save=async()=>{if(!cal)return;setSaving(true);setError("");try{const r=await fetch(`${API}/cameras/${channel}/calibration`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({roi:cal.roi,dials:cal.dials})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Save failed");onToast(t("Calibration saved for "+channel,"تم حفظ معايرة "+channel))}catch(e){setError(e.message)}finally{setSaving(false)}};
  const run=async()=>{setBusy(true);setError("");try{const r=await fetch(`${API}/cameras/${channel}/trigger`,{method:"POST"});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Recognition failed");setResult(d)}catch(e){setError(e.message)}finally{setBusy(false)}};
  const saveReference=async()=>{setSavingReference(true);setError("");try{const r=await fetch(`${API}/cameras/${channel}/alignment/reference`,{method:"POST"});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not save reference");setAlignment({configured:true,status:"reference_ready",reference_size:d.reference_size});onToast(t("Reference frame saved for "+channel,"تم حفظ الصورة المرجعية "+channel));setResult(null)}catch(e){setError(e.message)}finally{setSavingReference(false)}};
  const roi=cal?.roi||[0,0,0,0];
  const frameUrl=`${API}/cameras/${channel}/aligned-frame?t=${frameTick}`;
  const resultValue=result?.candidate_reading_m3;
  return <section className="workbench">
    <div className="workbench-heading"><div><div className="overline"><span/> {t("METER INTELLIGENCE / CONFIGURATION","ذكاء العدادات / الإعداد")}</div><h1>{t("Recognition Workbench","معمل التعرف")}<span>.</span></h1><p>{t("Calibrate the measurement regions, inspect the live frame and trigger the current local recognition pipeline.","اضبط مناطق القياس، وافحص الصورة المباشرة، وشغّل مسار التعرف المحلي الحالي.")}</p></div><div className="workbench-channel"><label>{t("ACTIVE STATION","المحطة النشطة")}</label><select value={channel} onChange={e=>{setChannel(e.target.value);setResult(null)}}>{channels.map(c=><option key={c.id} value={c.id}>{c.name||c.id} · {c.meter_id||c.id}</option>)}</select></div></div>
    <div className="pipeline-strip">{[[ScanLine,"01","Image Capture"],[Crosshair,"02","Geometry Calibration"],[Aperture,"03","ROI Extraction"],[Sparkles,"04","Recognition"],[CheckCircle2,"05","Validation"]].map(([Icon,num,label],i)=><div className={`pipeline-step ${i<3?"available":"experimental"}`} key={num}><Icon size={16}/><b>{num}</b><span>{t(label,["التقاط الصورة","معايرة الهندسة","استخراج المناطق","التعرف","التحقق"][i])}</span></div>)}</div>
    <div className="workbench-grid">
      <div className="workbench-panel preview-panel"><div className="panel-title"><div><span className="eyebrow">{t("LIVE FRAME","الصورة المباشرة")}</span><h3>{selected?.name||channel}</h3></div><span className={selected?.online?"wb-status online":"wb-status"}>{selected?.online?t("STREAM ONLINE","البث متصل"):t("NO SIGNAL","لا توجد إشارة")}</span></div>
        <div className="meter-preview">{selected?.online?<img src={frameUrl} alt="Live meter frame"/>:<div className="preview-empty"><Aperture size={28}/>{t("Waiting for a camera frame","في انتظار صورة الكاميرا")}</div>}
          {cal&&<><div className="roi-outline" style={{left:(roi[0]*100)+"%",top:(roi[1]*100)+"%",width:((roi[2]-roi[0])*100)+"%",height:((roi[3]-roi[1])*100)+"%"}}><span>DIGIT REGISTER ROI</span></div>{cal.dials.map((d,i)=><div key={d.name} className={`dial-outline ${i===dialIndex?"selected":""}`} style={{left:(d.center[0]*100)+"%",top:(d.center[1]*100)+"%",width:(d.radius*200)+"%",height:(d.radius*200)+"%"}}><span>{d.name}</span></div>)}</>}
        </div>
        <div className="alignment-status"><span className={alignment?.configured?"alignment-dot ready":"alignment-dot"}/><b>{t("REFERENCE ALIGNMENT","محاذاة الصورة المرجعية")}</b><span>{alignment?.configured?t("Reference saved · auto-align on trigger","تم حفظ المرجع · محاذاة تلقائية عند التشغيل"):t("Not configured · save current frame first","غير مفعّلة · احفظ الصورة الحالية أولاً")}</span></div><div className="preview-legend"><span><i className="legend-digit"/> {t("Digit register","منطقة الأرقام")}</span><span><i className="legend-dial"/> {t("Analog dial ROIs","مناطق المؤشرات")}</span></div>
        <div className="preview-actions"><button className="btn-secondary" onClick={saveReference} disabled={!selected?.online||savingReference}>{savingReference?<RefreshCw className="spin" size={14}/>:<Target size={14}/>} {savingReference?t("SAVING…","جارٍ الحفظ…"):t("SET REFERENCE","حفظ صورة مرجعية")}</button><button className="btn-primary" onClick={run} disabled={!selected?.online||busy}>{busy?<RefreshCw className="spin" size={15}/>:<Zap size={15}/>} {busy?t("RUNNING…","جارٍ التحليل…"):t("RUN RECOGNITION","تشغيل التعرف")}</button><button className="btn-secondary" onClick={()=>setFrameTick(Date.now())}><RefreshCw size={14}/>{t("Refresh frame","تحديث الصورة")}</button></div>
      </div>
      <div className="workbench-panel calibration-panel"><div className="panel-title"><div><span className="eyebrow">{t("PER-METER GEOMETRY","هندسة كل عداد")}</span><h3>{t("ROI Calibration","معايرة مناطق القياس")}</h3></div><SlidersHorizontal size={18}/></div>
        {!cal?<div className="preview-empty">{t("Loading calibration…","جارٍ تحميل المعايرة…")}</div>:<>
        <div className="cal-group"><h4><Target size={15}/> {t("Digit register region","منطقة أرقام العداد")}</h4>{[["Left",0],["Top",1],["Right",2],["Bottom",3]].map(([label,i])=><label className="wb-range" key={label}><span>{t(label,["يسار","أعلى","يمين","أسفل"][i])}</span><input type="range" min="0" max="1" step=".001" value={roi[i]} onChange={e=>updateRoi(i,e.target.value)}/><output>{fmt(roi[i])}</output></label>)}</div>
        <div className="cal-group"><h4><Gauge size={15}/> {t("Analog pointer regions","مناطق المؤشرات التناظرية")}</h4><div className="dial-tabs">{cal.dials.map((d,i)=><button key={d.name} className={i===dialIndex?"active":""} onClick={()=>setDialIndex(i)}>{d.name}</button>)}</div>{dial&&[["cx","Center X",dial.center[0]],["cy","Center Y",dial.center[1]],["radius","Radius",dial.radius]].map(([key,label,value])=><label className="wb-range" key={key}><span>{t(label,{"Center X":"المركز X","Center Y":"المركز Y","Radius":"نصف القطر"}[label])}</span><input type="range" min="0" max={key === "radius" ? 0.2 : 1} step=".001" value={n(value)} onChange={e=>updateDial(key,e.target.value)}/><output>{fmt(value)}</output></label>)}</div>
        <div className="calibration-actions"><button className="btn-primary" onClick={save} disabled={saving}><Save size={15}/>{saving?t("SAVING…","جارٍ الحفظ…"):t("SAVE CALIBRATION","حفظ المعايرة")}</button></div></>}
      </div>
    </div>
    <div className="workbench-bottom">
      <div className="workbench-panel result-panel"><div className="panel-title"><div><span className="eyebrow">{t("LATEST INFERENCE","آخر نتيجة استدلال")}</span><h3>{t("Reading candidate","القراءة المرشحة")}</h3></div><span className="experimental-tag">EXPERIMENTAL</span></div><div className="candidate-value">{resultValue!=null?Number(resultValue).toFixed(4):"— — — —"} <small>m³</small></div><div className="result-details"><span>{t("Integer digits","الأرقام الصحيحة")} <b>{result?.integer_digits||"—"}</b></span><span>{t("OCR confidence","ثقة OCR")} <b>{result?Math.round(result.ocr_confidence*100)+"%":"—"}</b></span><span>{t("Status","الحالة")} <b>{result?.status||t("Not run","لم يتم التشغيل")}</b></span><span>{t("Alignment","المحاذاة")} <b>{result?.alignment?.status||"—"}{result?.alignment?.inliers?` · ${result.alignment.inliers} inliers`:""}</b></span></div>{result?.warning&&<p className="warning-copy"><CircleAlert size={14}/>{result.warning}</p>}</div>
      <div className="workbench-panel method-panel"><div className="panel-title"><div><span className="eyebrow">{t("CURRENT IMPLEMENTATION","التنفيذ الحالي")}</span><h3>{t("Processing notes","ملاحظات المعالجة")}</h3></div></div><ul><li>{t("Digit recognition: EasyOCR on the configured register ROI.","التعرف على الأرقام: EasyOCR على منطقة الأرقام المحددة.")}</li><li>{t("Pointer estimation: red-pixel segmentation and dial geometry.","تقدير المؤشر: فصل البكسلات الحمراء وهندسة المؤشر.")}</li><li>{t("Reference alignment: ORB feature matching + RANSAC similarity transform; requires a saved reference frame.","محاذاة المرجع: مطابقة ORB وتحويل هندسي باستخدام RANSAC؛ تتطلب حفظ صورة مرجعية.")}</li><li>{t("Trained meter-specific recognition models are not active yet.","النماذج المدربة الخاصة بالعدادات لم تُفعّل بعد.")}</li></ul><div className="method-foot">{t("No fabricated readings · local CPU processing","لا توجد قراءات وهمية · معالجة محلية بالمعالج")}</div></div>
    </div>
    {error&&<div className="wb-error"><CircleAlert size={15}/>{error}</div>}
  </section>;
}
