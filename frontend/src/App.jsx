import React, { useCallback, useEffect, useMemo, useState } from "react";
import RecognitionWorkbench from "./RecognitionWorkbench.jsx";
import {
  Activity, AlertTriangle, Aperture, ArrowDownRight, ArrowUpRight, Bell, Check,
  ChevronRight, CircleHelp, Clock3, Command, Cpu, Download, Droplets, Gauge,
  LayoutDashboard, Menu, MoreHorizontal, Play, Radio, RefreshCw, Search,
  Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Wifi, WifiOff, X, Zap, Sun, Moon, Languages
} from "lucide-react";

const API = "http://127.0.0.1:8000/api";
const fmt = (n) => Number.isFinite(n) ? n.toFixed(4) : "— — — —";
const initialCalibration = (camera) => camera?.calibration || null;
const tr = (lang, en, ar) => lang === "ar" ? ar : en;

function Metric({ icon: Icon, label, value, detail, tone = "mint" }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18}/></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div><div className="metric-spark"><Activity size={26}/></div></div>;
}

function CameraCard({ camera, frameTick, frameSourceId, onTrigger, onConfigure, busy, lang }) {
  const online = camera.online;
  const result = camera.result;
  const reading = result?.candidate_reading_m3;
  const t = (en, ar) => tr(lang, en, ar);
  return <article className={`camera-card ${online ? "is-online" : "is-offline"}`}>
    <div className="camera-card-top">
      <div className="camera-identity"><div className="camera-index">{camera.id.replace("cam_", "")}</div><div><h3>{camera.name || camera.id}</h3><span>{camera.meter_id || t("METER STATION","محطة العداد")} <i>•</i> <a className="camera-stream-link" href={camera.stream_url} target="_blank" rel="noreferrer" title={t("Open direct MJPEG stream","فتح رابط البث المباشر")}>{camera.ip_label}</a></span></div></div>
      <div className={`status-pill ${online ? "online" : "offline"}`}><span/>{online ? t("LIVE","مباشر") : t("OFFLINE","غير متصل")}</div>
    </div>
    <div className="feed-wrap">
      {online ? <img src={`${API}/cameras/${frameSourceId || camera.id}/frame?t=${frameTick}`} alt={`${camera.name} live meter feed`} /> :
        <div className="feed-placeholder"><WifiOff size={25}/><strong>{t("Signal unavailable","الإشارة غير متاحة")}</strong><span>{camera.last_error || t("Waiting for camera stream","في انتظار بث الكاميرا")}</span></div>}
      <div className="feed-overlay"><span className="rec-dot"/> {t("LIVE MONITOR","مراقبة مباشرة")}</div>
      <div className="feed-corner"><Aperture size={15}/> MJPEG</div>
    </div>
    <div className="reading-row"><div><span className="eyebrow">{t("LATEST REGISTER VALUE","آخر قراءة للعداد")}</span><div className="reading-value">{fmt(reading)} <small>m³</small></div></div><div className={`result-state ${result?.status === "experimental_candidate" ? "review-ok" : "review"}`}>{result?.status === "experimental_candidate" ? <Check size={13}/> : <AlertTriangle size={13}/>} {result ? (result.status === "experimental_candidate" ? t("Candidate","قراءة مرشحة") : t("Review","تحتاج مراجعة")) : t("Not read","لم تتم القراءة")}</div></div>
    <div className="camera-meta"><span><Gauge size={13}/> {t("Register","الأرقام")} <b>{result?.integer_digits || "— — — — —"}</b></span><span><Activity size={13}/> OCR <b>{result ? Math.round(result.ocr_confidence * 100) + "%" : "—"}</b></span></div>
    <div className="card-actions"><button className="btn-primary" onClick={() => onTrigger(camera.id)} disabled={!online || busy}>{busy ? <RefreshCw className="spin" size={15}/> : <Play size={14} fill="currentColor"/>}{busy ? t("ANALYZING","جارٍ التحليل") : t("TRIGGER READ","ابدأ القراءة")}</button><button className="btn-icon" onClick={() => onConfigure(camera)} title={t("Configure station","إعداد الكاميرا")}><SlidersHorizontal size={16}/></button><button className="btn-icon" onClick={() => result && downloadResult(camera)} title={t("Export result","تصدير النتيجة")} disabled={!result}><Download size={16}/></button></div>
  </article>;
}

function downloadResult(camera) {
  const blob = new Blob([JSON.stringify(camera.result, null, 2)], {type:"application/json"});
  const url = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = url; a.download = `${camera.id}-reading.json`; a.click(); URL.revokeObjectURL(url);
}

function CalibrationDrawer({ camera, onClose, onSave, lang }) {
  const [roi, setRoi] = useState([0.18,0.35,0.82,0.67]);
  const [dials, setDials] = useState([]);
  const [saving, setSaving] = useState(false);
  const t = (en, ar) => tr(lang, en, ar);
  useEffect(() => {
    let active = true;
    fetch(`${API}/cameras/${camera.id}/calibration`).then(r => r.ok ? r.json() : null).then(data => {
      if (active && data) { setRoi(data.roi); setDials(data.dials); }
    }).catch(() => {});
    return () => { active = false; };
  }, [camera.id]);
  const updateDial = (index, key, value) => setDials(prev => prev.map((d,i) => i !== index ? d : key === "radius" ? {...d, radius:Number(value)} : {...d, center:d.center.map((v,j)=>j === (key === "cx" ? 0 : 1) ? Number(value) : v)}));
  const save = async () => {
    setSaving(true);
    try { await onSave(camera.id, {roi, dials}); onClose(); } finally { setSaving(false); }
  };
  return <div className="drawer-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}><aside className="calibration-drawer">
    <div className="drawer-head"><div><span className="eyebrow">{t("STATION CONFIGURATION","إعداد المحطة")}</span><h2>{camera.name}</h2><p>{t("Independent geometry calibration","معايرة مستقلة لأبعاد العداد")}</p></div><button className="btn-icon" onClick={onClose}><X size={18}/></button></div>
    <div className="drawer-section"><h4><Aperture size={15}/> {t("Register window · ROI","منطقة قراءة العداد · ROI")}</h4><p>{t("Normalized coordinates from 0 to 1.","إحداثيات نسبية من 0 إلى 1.")}</p>{[t("Left","يسار"),t("Top","أعلى"),t("Right","يمين"),t("Bottom","أسفل")].map((label,i)=><label className="range-row" key={label}><span>{label}</span><input type="range" min="0" max="1" step=".001" value={roi[i]} onChange={e=>setRoi(prev=>prev.map((v,j)=>j===i?Number(e.target.value):v))}/><output>{roi[i].toFixed(3)}</output></label>)}</div>
    <div className="drawer-section"><h4><Gauge size={15}/> {t("Rotary dial geometry","إعدادات البكرات")}</h4>{dials.map((dial,i)=><div className="dial-config" key={dial.name}><strong>{dial.name}</strong>{[{key:"cx",label:t("Center X","المركز X"),value:dial.center?.[0]},{key:"cy",label:t("Center Y","المركز Y"),value:dial.center?.[1]},{key:"radius",label:t("Radius","نصف القطر"),value:dial.radius}].map(item=><label className="range-row" key={item.key}><span>{item.label}</span><input type="range" min="0" max={item.key==="radius" ? ".2" : "1"} step=".001" value={item.value ?? 0} onChange={e=>updateDial(i,item.key,e.target.value)}/><output>{Number(item.value ?? 0).toFixed(3)}</output></label>)}</div>)}</div>
    <div className="drawer-note"><AlertTriangle size={16}/> {t("Calibration is saved locally in data/meter_calibrations.json and survives backend restarts.","يتم حفظ المعايرة محليًا في data/meter_calibrations.json وتظل محفوظة بعد إعادة تشغيل الخادم.")}</div>
    <div className="drawer-footer"><button className="btn-secondary" onClick={onClose}>{t("Cancel","إلغاء")}</button><button className="btn-primary" onClick={save} disabled={saving || dials.length !== 4}>{saving ? t("SAVING…","جارٍ الحفظ…") : t("SAVE CALIBRATION","حفظ المعايرة")}</button></div>
  </aside></div>;
}

export default function App() {
  const [data, setData] = useState({channels:[],online_channels:0,total_channels:8,unique_streams:0});
  const [lang, setLang] = useState(() => localStorage.getItem("wmv-language") || "en");
  const [theme, setTheme] = useState(() => localStorage.getItem("wmv-theme") || "dark");
  const t = (en, ar) => tr(lang, en, ar);
  useEffect(() => { localStorage.setItem("wmv-language", lang); document.documentElement.lang = lang; document.documentElement.dir = lang === "ar" ? "rtl" : "ltr"; }, [lang]);
  useEffect(() => { localStorage.setItem("wmv-theme", theme); document.documentElement.dataset.theme = theme; }, [theme]);
  const [apiOnline, setApiOnline] = useState(false);
  const [frameTick, setFrameTick] = useState(Date.now());
  const [busy, setBusy] = useState({});
  const [batchBusy, setBatchBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [toast, setToast] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [workers, setWorkers] = useState(4);
  const [navOpen, setNavOpen] = useState(false);
  const [activePage, setActivePage] = useState("overview");

  const refresh = useCallback(async () => {
    try { const res = await fetch(`${API}/overview`); if (!res.ok) throw new Error(); setData(await res.json()); setApiOnline(true); }
    catch { setApiOnline(false); }
  }, []);
  useEffect(() => { refresh(); const a=setInterval(refresh,1500); const b=setInterval(()=>setFrameTick(Date.now()),500); return ()=>{clearInterval(a);clearInterval(b)}; },[refresh]);
  useEffect(() => { if(!toast) return; const t=setTimeout(()=>setToast(""),3200); return ()=>clearTimeout(t); },[toast]);

  const trigger = async (id) => {
    setBusy(p=>({...p,[id]:true}));
    try { const res=await fetch(`${API}/cameras/${id}/trigger`,{method:"POST"}); const body=await res.json(); if(!res.ok) throw new Error(body.detail || "Trigger failed"); setToast(t(`${id.toUpperCase()} analysis completed`, `اكتمل تحليل ${id.toUpperCase()}`)); await refresh(); }
    catch(e){setToast(e.message)}
    finally{setBusy(p=>({...p,[id]:false}))}
  };
  const triggerAll = async () => {
    setBatchBusy(true);
    try {const res=await fetch(`${API}/trigger-all`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({workers})});const body=await res.json();if(!res.ok)throw new Error(body.detail||"Batch failed");setToast(t(`Batch finished · ${body.processed} channels processed`, `اكتملت المعالجة · ${body.processed} محطة`));await refresh();}
    catch(e){setToast(e.message)} finally{setBatchBusy(false)}
  };
  const saveCalibration = async (id, calibration) => {
    const res=await fetch(`${API}/cameras/${id}/calibration`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(calibration)});
    const body=await res.json();if(!res.ok)throw new Error(body.detail||"Could not save calibration");setToast(t("Station calibration saved","تم حفظ معايرة المحطة"));
  };

  const channels = useMemo(()=>data.channels.filter(c=>(filter==="all" || (filter==="online" ? c.online : !c.online)) && `${c.name} ${c.meter_id} ${c.ip_label}`.toLowerCase().includes(query.toLowerCase())),[data.channels,filter,query]);
  const completed = data.channels.filter(c=>c.result).length;
  const candidate = data.channels.filter(c=>c.result?.status==="experimental_candidate").length;

  return <div className="app-shell" data-theme={theme} dir={lang === "ar" ? "rtl" : "ltr"}>
    <aside className={`sidebar ${navOpen?"nav-open":""}`}>
      <div className="brand"><div className="brand-mark"><Droplets size={22}/></div><div><b>RAGURA WM<span>™</span></b><small>WATER METER INTELLIGENCE</small></div><button className="mobile-close" onClick={()=>setNavOpen(false)}><X size={18}/></button></div>
      <div className="workspace-label">{t("WORKSPACE","مساحة العمل")}</div>
      <button className={`nav-item ${activePage==="overview"?"active":""}`} onClick={()=>setActivePage("overview")}><LayoutDashboard size={17}/> {t("Overview","نظرة عامة")} <span className="nav-count">08</span></button>
      <button className={`nav-item ${activePage==="workbench"?"active":""}`} onClick={()=>{setActivePage("workbench");setNavOpen(false)}}><Aperture size={17}/> {t("Recognition Workbench","معمل التعرف")}</button>
      <button className="nav-item" onClick={()=>setToast(t("Station history will be enabled with persistent storage.","سيتم تفعيل سجل المحطات عند إضافة التخزين الدائم."))}><Clock3 size={17}/> {t("Reading History","سجل القراءات")}</button>
      <button className="nav-item" onClick={()=>setToast(t("Network configuration is managed in configs/camera_channels.json.","إعدادات الشبكة موجودة في configs/camera_channels.json."))}><Radio size={17}/> {t("Camera Network","شبكة الكاميرات")}</button>
      <button className="nav-item" onClick={()=>setToast(t("System settings are available in the backend configuration.","إعدادات النظام متاحة في إعدادات الخادم."))}><Settings2 size={17}/> {t("System Settings","إعدادات النظام")}</button>
      <div className="sidebar-bottom"><div className="edge-status"><span className={apiOnline?"pulse-dot":"pulse-dot danger"}/><div><b>{apiOnline?t("EDGE NODE ONLINE","وحدة المعالجة متصلة"):t("API DISCONNECTED","الخادم غير متصل")}</b><small>{t("LOCAL PROCESSING NODE","وحدة معالجة محلية")}</small></div></div><div className="sidebar-foot">{t("RAGURA WM CONSOLE","وحدة تحكم RAGURA WM")} <span>v1.0.0</span></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" onClick={()=>setNavOpen(true)}><Menu size={19}/></button><div className="breadcrumb">{t("Workspace","مساحة العمل")} <ChevronRight size={14}/> <b>{activePage==="workbench"?t("Recognition Workbench","معمل التعرف"):t("Overview","نظرة عامة")}</b></div></div><div className="topbar-right"><div className="local-chip"><ShieldCheck size={14}/> {t("LOCAL NETWORK","شبكة محلية")} <i/></div><button className="icon-button" onClick={refresh} title={t("Refresh","تحديث")}><RefreshCw size={17}/></button><button className="icon-button" onClick={()=>setTheme(v=>v==="dark"?"light":"dark")} title={t("Toggle theme","تغيير المظهر")}>{theme==="dark"?<Sun size={17}/>:<Moon size={17}/>}</button><button className="language-toggle" onClick={()=>setLang(v=>v==="en"?"ar":"en")} title={t("Switch language","تغيير اللغة")}><Languages size={15}/>{lang==="en"?"العربية":"English"}</button><button className="icon-button" onClick={()=>setToast(t("No new alerts.","لا توجد تنبيهات جديدة."))} title={t("Notifications","التنبيهات")}><Bell size={17}/></button><div className="avatar">RG</div></div></header>

      <div className="content">
        {activePage==="workbench" ? <RecognitionWorkbench lang={lang} onToast={setToast} /> : <>
        <section className="hero"><div className="hero-copy"><div className="overline"><span/> {t("INDUSTRIAL METER INTELLIGENCE","ذكاء قراءة العدادات الصناعية")} <span className="overline-line"/></div><h1>{t("Meter Operations","تشغيل العدادات")}<span>.</span><br/><em>{t("At a glance.","كل شيء أمامك.")}</em></h1><p>{t("Real-time visibility across your meter network. Capture, analyze and monitor every station from one local control plane.","تابع شبكة العدادات لحظيًا، والتقط الصور وحلل القراءات وراقب كل محطة من لوحة تحكم محلية واحدة.")}</p><div className="hero-actions"><button className="btn-primary hero-trigger" onClick={triggerAll} disabled={batchBusy || !apiOnline}><Zap size={16} fill="currentColor"/>{batchBusy?t("PROCESSING ALL STATIONS","جارٍ تحليل كل المحطات"):t("TRIGGER ALL STATIONS","تشغيل قراءة كل المحطات")}</button><span className="hero-caption"><Wifi size={14}/> {t("PRIVATE LAN","شبكة محلية خاصة")} <b>•</b> {t("NO CLOUD","بدون اتصال سحابي")}</span></div></div><div className="hero-visual"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-core"><Droplets size={35}/><span>EDGE<br/>VISION</span></div><div className="orbit-node node-a"><Radio size={15}/></div><div className="orbit-node node-b"><Gauge size={15}/></div><div className="orbit-node node-c"><Cpu size={15}/></div><div className="hero-visual-label">8 {t("STATIONS","محطات")} <b>·</b> 1 {t("CONTROL PLANE","لوحة تحكم")}</div></div><div className="hero-index">01 <span>/ 08</span></div></section>

        {data.mode === "demo_shared_stream" && <div className="demo-mode-banner"><div className="demo-mode-icon"><Radio size={17}/></div><div><strong>{t("SHARED CAMERA DEMO MODE","وضع تجربة كاميرا واحدة")}</strong><span>{t("All 8 meter channels display the live feed from ESP32-CAM · 192.168.137.201. Each channel keeps its own meter ID and calibration. Add the other cameras later by changing their stream URLs only.","كل قنوات العدادات الثمانية تعرض بث كاميرا ESP32 واحدة · 192.168.137.201. لكل قناة رقم عداد ومعايرة مستقلة. عند إضافة باقي الكاميرات سنغير روابط البث فقط.")}</span></div><a href="http://192.168.137.201/" target="_blank" rel="noreferrer">{t("CAMERA STATUS","حالة الكاميرا")} ↗</a></div>}
        <section className="metrics-grid"><Metric icon={Radio} label={t("CHANNELS RECEIVING VIDEO","قنوات تستقبل الفيديو")} value={`${String(data.online_channels||0).padStart(2,"0")} / 08`} detail={data.mode === "demo_shared_stream" ? t("8 channels · 1 physical camera","٨ قنوات · كاميرا فعلية واحدة") : t("Live signal detected","تم استقبال بث مباشر")} tone="mint"/><Metric icon={Gauge} label={t("READINGS CAPTURED","القراءات المسجلة")} value={String(completed).padStart(2,"0")} detail={t("Triggered this session","تم تشغيلها في هذه الجلسة")} tone="blue"/><Metric icon={ShieldCheck} label={t("CANDIDATES","قراءات مرشحة")} value={String(candidate).padStart(2,"0")} detail={t("Require verification","تحتاج إلى مراجعة")} tone="violet"/><Metric icon={Cpu} label={t("PROCESSING MODE","وضع المعالجة")} value={t("CPU / LOCAL","معالج محلي")} detail={data.mode === "demo_shared_stream" ? t("Shared ESP32-CAM demo stream","بث تجريبي مشترك من كاميرا ESP32") : `${data.unique_streams||0} unique stream(s)`} tone="amber"/></section>

        <section className="section-heading"><div><div className="overline">{t("NETWORK OVERVIEW","نظرة عامة على الشبكة")}</div><h2>{t("Camera stations","محطات الكاميرات")} <span className="count-tag">{data.total_channels||8} {t("CHANNELS","قنوات")}</span></h2><p>{t("Monitor live feeds and trigger meter recognition on demand.","راقب البث المباشر وابدأ التعرف على قراءة العداد عند الحاجة.")}</p></div><div className="heading-actions"><div className="search-box"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t("Search stations…","ابحث عن محطة…")}/><Command size={13}/></div><button className="btn-secondary compact" onClick={refresh}><RefreshCw size={14}/> {t("Refresh","تحديث")}</button></div></section>
        <div className="filter-row"><div className="filter-tabs">{[["all",t("All stations","كل المحطات")],["online",t("Online","متصلة")],["offline",t("Offline","غير متصلة")]].map(([v,label])=><button key={v} className={filter===v?"selected":""} onClick={()=>setFilter(v)}>{label}<span>{v==="all"?data.channels.length:data.channels.filter(c=>v==="online"?c.online:!c.online).length}</span></button>)}</div><div className="worker-control"><span>{t("PARALLEL WORKERS","مهام متوازية")}</span><select value={workers} onChange={e=>setWorkers(Number(e.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={4}>4</option><option value={8}>8</option></select><span className="worker-info" title={t("OCR access is serialized for stability","يتم تنظيم وصول OCR لضمان الاستقرار")}><CircleHelp size={14}/></span></div></div>

        <section className="camera-grid">{channels.map(camera=><CameraCard key={camera.id} camera={camera} frameTick={frameTick} frameSourceId={data.mode === "demo_shared_stream" ? "cam_01" : camera.id} busy={busy[camera.id] || batchBusy} onTrigger={trigger} onConfigure={setSelected} lang={lang}/>)}</section>
        {channels.length===0 && <div className="empty-state">{t("No stations match your search.","لا توجد محطات تطابق البحث.")}</div>}
        <footer className="page-footer"><span>RAGURA WM <b>·</b> {t("LOCAL-FIRST EDGE PLATFORM","منصة معالجة محلية")}</span><span><span className={apiOnline?"pulse-dot":"pulse-dot danger"}/> {apiOnline?t("API CONNECTED","الخادم متصل"):t("WAITING FOR API","في انتظار الخادم")} <b>·</b> {t("EXPERIMENTAL CV OUTPUT","نتائج رؤية حاسوبية تجريبية")}</span></footer>
        </>}
      </div>
    </main>
    {selected && <CalibrationDrawer camera={selected} onClose={()=>setSelected(null)} onSave={saveCalibration} lang={lang}/>}
    {toast && <div className="toast"><Sparkles size={16}/>{toast}<button onClick={()=>setToast("")}><X size={14}/></button></div>}
  </div>;
}
