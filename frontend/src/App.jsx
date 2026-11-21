import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, Aperture, ArrowDownRight, ArrowUpRight, Bell, Check,
  ChevronRight, CircleHelp, Clock3, Command, Cpu, Download, Droplets, Gauge,
  LayoutDashboard, Menu, MoreHorizontal, Play, Radio, RefreshCw, Search,
  Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Wifi, WifiOff, X, Zap
} from "lucide-react";

const API = "http://127.0.0.1:8000/api";
const fmt = (n) => Number.isFinite(n) ? n.toFixed(4) : "— — — —";
const initialCalibration = (camera) => camera?.calibration || null;

function Metric({ icon: Icon, label, value, detail, tone = "mint" }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18}/></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div><div className="metric-spark"><Activity size={26}/></div></div>;
}

function CameraCard({ camera, frameTick, onTrigger, onConfigure, busy }) {
  const online = camera.online;
  const result = camera.result;
  const reading = result?.candidate_reading_m3;
  return <article className={`camera-card ${online ? "is-online" : "is-offline"}`}>
    <div className="camera-card-top">
      <div className="camera-identity"><div className="camera-index">{camera.id.replace("cam_", "")}</div><div><h3>{camera.name || camera.id}</h3><span>{camera.meter_id || "METER STATION"} <i>•</i> {camera.ip_label}</span></div></div>
      <div className={`status-pill ${online ? "online" : "offline"}`}><span/>{online ? "LIVE" : "OFFLINE"}</div>
    </div>
    <div className="feed-wrap">
      {online ? <img src={`${API}/cameras/${camera.id}/frame?t=${frameTick}`} alt={`${camera.name} live meter feed`} /> :
        <div className="feed-placeholder"><WifiOff size={25}/><strong>Signal unavailable</strong><span>{camera.last_error || "Waiting for camera stream"}</span></div>}
      <div className="feed-overlay"><span className="rec-dot"/> LIVE MONITOR</div>
      <div className="feed-corner"><Aperture size={15}/> MJPEG</div>
    </div>
    <div className="reading-row"><div><span className="eyebrow">LATEST REGISTER VALUE</span><div className="reading-value">{fmt(reading)} <small>m³</small></div></div><div className={`result-state ${result?.status === "experimental_candidate" ? "review-ok" : "review"}`}>{result?.status === "experimental_candidate" ? <Check size={13}/> : <AlertTriangle size={13}/>} {result ? (result.status === "experimental_candidate" ? "Candidate" : "Review") : "Not read"}</div></div>
    <div className="camera-meta"><span><Gauge size={13}/> Register <b>{result?.integer_digits || "— — — — —"}</b></span><span><Activity size={13}/> OCR <b>{result ? Math.round(result.ocr_confidence * 100) + "%" : "—"}</b></span></div>
    <div className="card-actions"><button className="btn-primary" onClick={() => onTrigger(camera.id)} disabled={!online || busy}>{busy ? <RefreshCw className="spin" size={15}/> : <Play size={14} fill="currentColor"/>}{busy ? "ANALYZING" : "TRIGGER READ"}</button><button className="btn-icon" onClick={() => onConfigure(camera)} title="Configure station"><SlidersHorizontal size={16}/></button><button className="btn-icon" onClick={() => result && downloadResult(camera)} title="Export result" disabled={!result}><Download size={16}/></button></div>
  </article>;
}

function downloadResult(camera) {
  const blob = new Blob([JSON.stringify(camera.result, null, 2)], {type:"application/json"});
  const url = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = url; a.download = `${camera.id}-reading.json`; a.click(); URL.revokeObjectURL(url);
}

function CalibrationDrawer({ camera, onClose, onSave }) {
  const [roi, setRoi] = useState([0.18,0.35,0.82,0.67]);
  const [dials, setDials] = useState([]);
  const [saving, setSaving] = useState(false);
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
    <div className="drawer-head"><div><span className="eyebrow">STATION CONFIGURATION</span><h2>{camera.name}</h2><p>Independent geometry calibration</p></div><button className="btn-icon" onClick={onClose}><X size={18}/></button></div>
    <div className="drawer-section"><h4><Aperture size={15}/> Register window · ROI</h4><p>Normalized coordinates from 0 to 1.</p>{["Left","Top","Right","Bottom"].map((label,i)=><label className="range-row" key={label}><span>{label}</span><input type="range" min="0" max="1" step=".001" value={roi[i]} onChange={e=>setRoi(prev=>prev.map((v,j)=>j===i?Number(e.target.value):v))}/><output>{roi[i].toFixed(3)}</output></label>)}</div>
    <div className="drawer-section"><h4><Gauge size={15}/> Rotary dial geometry</h4>{dials.map((dial,i)=><div className="dial-config" key={dial.name}><strong>{dial.name}</strong>{[{key:"cx",label:"Center X",value:dial.center?.[0]},{key:"cy",label:"Center Y",value:dial.center?.[1]},{key:"radius",label:"Radius",value:dial.radius}].map(item=><label className="range-row" key={item.key}><span>{item.label}</span><input type="range" min="0" max={item.key==="radius" ? ".2" : "1"} step=".001" value={item.value ?? 0} onChange={e=>updateDial(i,item.key,e.target.value)}/><output>{Number(item.value ?? 0).toFixed(3)}</output></label>)}</div>)}</div>
    <div className="drawer-note"><AlertTriangle size={16}/> Calibration is stored in the running API process. Save your configuration before restarting the backend.</div>
    <div className="drawer-footer"><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" onClick={save} disabled={saving || dials.length !== 4}>{saving ? "SAVING…" : "SAVE CALIBRATION"}</button></div>
  </aside></div>;
}

export default function App() {
  const [data, setData] = useState({channels:[],online_channels:0,total_channels:8,unique_streams:0});
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

  const refresh = useCallback(async () => {
    try { const res = await fetch(`${API}/overview`); if (!res.ok) throw new Error(); setData(await res.json()); setApiOnline(true); }
    catch { setApiOnline(false); }
  }, []);
  useEffect(() => { refresh(); const a=setInterval(refresh,1500); const b=setInterval(()=>setFrameTick(Date.now()),850); return ()=>{clearInterval(a);clearInterval(b)}; },[refresh]);
  useEffect(() => { if(!toast) return; const t=setTimeout(()=>setToast(""),3200); return ()=>clearTimeout(t); },[toast]);

  const trigger = async (id) => {
    setBusy(p=>({...p,[id]:true}));
    try { const res=await fetch(`${API}/cameras/${id}/trigger`,{method:"POST"}); const body=await res.json(); if(!res.ok) throw new Error(body.detail || "Trigger failed"); setToast(`${id.toUpperCase()} analysis completed`); await refresh(); }
    catch(e){setToast(e.message)}
    finally{setBusy(p=>({...p,[id]:false}))}
  };
  const triggerAll = async () => {
    setBatchBusy(true);
    try {const res=await fetch(`${API}/trigger-all`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({workers})});const body=await res.json();if(!res.ok)throw new Error(body.detail||"Batch failed");setToast(`Batch finished · ${body.processed} channels processed`);await refresh();}
    catch(e){setToast(e.message)} finally{setBatchBusy(false)}
  };
  const saveCalibration = async (id, calibration) => {
    const res=await fetch(`${API}/cameras/${id}/calibration`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(calibration)});
    const body=await res.json();if(!res.ok)throw new Error(body.detail||"Could not save calibration");setToast("Station calibration saved");
  };

  const channels = useMemo(()=>data.channels.filter(c=>(filter==="all" || (filter==="online" ? c.online : !c.online)) && `${c.name} ${c.meter_id} ${c.ip_label}`.toLowerCase().includes(query.toLowerCase())),[data.channels,filter,query]);
  const completed = data.channels.filter(c=>c.result).length;
  const candidate = data.channels.filter(c=>c.result?.status==="experimental_candidate").length;

  return <div className="app-shell">
    <aside className={`sidebar ${navOpen?"nav-open":""}`}>
      <div className="brand"><div className="brand-mark"><Droplets size={22}/></div><div><b>WATERMETER<span>VISION</span></b><small>EDGE INTELLIGENCE</small></div><button className="mobile-close" onClick={()=>setNavOpen(false)}><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <button className="nav-item active"><LayoutDashboard size={17}/> Control Center <span className="nav-count">08</span></button>
      <button className="nav-item" onClick={()=>setToast("Station history will be enabled with persistent storage.")}><Clock3 size={17}/> Reading History</button>
      <button className="nav-item" onClick={()=>setToast("Network configuration is managed in configs/camera_channels.json.")}><Radio size={17}/> Camera Network</button>
      <button className="nav-item" onClick={()=>setToast("System settings are available in the backend configuration.")}><Settings2 size={17}/> System Settings</button>
      <div className="sidebar-bottom"><div className="edge-status"><span className={apiOnline?"pulse-dot":"pulse-dot danger"}/><div><b>{apiOnline?"EDGE NODE ONLINE":"API DISCONNECTED"}</b><small>LOCAL PROCESSING NODE</small></div></div><div className="sidebar-foot">WATERVISION CONSOLE <span>v1.0.0</span></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" onClick={()=>setNavOpen(true)}><Menu size={19}/></button><div className="breadcrumb">Workspace <ChevronRight size={14}/> <b>Control Center</b></div></div><div className="topbar-right"><div className="local-chip"><ShieldCheck size={14}/> LOCAL NETWORK <i/></div><button className="icon-button" onClick={refresh} title="Refresh"><RefreshCw size={17}/></button><button className="icon-button" onClick={()=>setToast("No new alerts.")} title="Notifications"><Bell size={17}/></button><div className="avatar">WM</div></div></header>

      <div className="content">
        <section className="hero"><div className="hero-copy"><div className="overline"><span/> INDUSTRIAL METER INTELLIGENCE <span className="overline-line"/></div><h1>Meter Operations<span>.</span><br/><em>At a glance.</em></h1><p>Real-time visibility across your meter network. Capture, analyze and monitor every station from one local control plane.</p><div className="hero-actions"><button className="btn-primary hero-trigger" onClick={triggerAll} disabled={batchBusy || !apiOnline}><Zap size={16} fill="currentColor"/>{batchBusy?"PROCESSING ALL STATIONS":"TRIGGER ALL STATIONS"}</button><span className="hero-caption"><Wifi size={14}/> PRIVATE LAN <b>•</b> NO CLOUD</span></div></div><div className="hero-visual"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-core"><Droplets size={35}/><span>EDGE<br/>VISION</span></div><div className="orbit-node node-a"><Radio size={15}/></div><div className="orbit-node node-b"><Gauge size={15}/></div><div className="orbit-node node-c"><Cpu size={15}/></div><div className="hero-visual-label">8 STATIONS <b>·</b> 1 CONTROL PLANE</div></div><div className="hero-index">01 <span>/ 08</span></div></section>

        <section className="metrics-grid"><Metric icon={Radio} label="CAMERAS ONLINE" value={`${String(data.online_channels||0).padStart(2,"0")} / 08`} detail="Live signal detected" tone="mint"/><Metric icon={Gauge} label="READINGS CAPTURED" value={String(completed).padStart(2,"0")} detail="Triggered this session" tone="blue"/><Metric icon={ShieldCheck} label="CANDIDATES" value={String(candidate).padStart(2,"0")} detail="Require verification" tone="violet"/><Metric icon={Cpu} label="PROCESSING MODE" value="CPU / LOCAL" detail={`${data.unique_streams||0} unique stream(s)`} tone="amber"/></section>

        <section className="section-heading"><div><div className="overline">NETWORK OVERVIEW</div><h2>Camera stations <span className="count-tag">{data.total_channels||8} CHANNELS</span></h2><p>Monitor live feeds and trigger meter recognition on demand.</p></div><div className="heading-actions"><div className="search-box"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search stations…"/><Command size={13}/></div><button className="btn-secondary compact" onClick={refresh}><RefreshCw size={14}/> Refresh</button></div></section>
        <div className="filter-row"><div className="filter-tabs">{[["all","All stations"],["online","Online"],["offline","Offline"]].map(([v,label])=><button key={v} className={filter===v?"selected":""} onClick={()=>setFilter(v)}>{label}<span>{v==="all"?data.channels.length:data.channels.filter(c=>v==="online"?c.online:!c.online).length}</span></button>)}</div><div className="worker-control"><span>PARALLEL WORKERS</span><select value={workers} onChange={e=>setWorkers(Number(e.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={4}>4</option><option value={8}>8</option></select><span className="worker-info" title="OCR access is serialized for stability"><CircleHelp size={14}/></span></div></div>

        <section className="camera-grid">{channels.map(camera=><CameraCard key={camera.id} camera={camera} frameTick={frameTick} busy={busy[camera.id] || batchBusy} onTrigger={trigger} onConfigure={setSelected}/>)}</section>
        {channels.length===0 && <div className="empty-state">No stations match your search.</div>}
        <footer className="page-footer"><span>WATERMETERVISION <b>·</b> LOCAL-FIRST EDGE PLATFORM</span><span><span className={apiOnline?"pulse-dot":"pulse-dot danger"}/> {apiOnline?"API CONNECTED":"WAITING FOR API"} <b>·</b> EXPERIMENTAL CV OUTPUT</span></footer>
      </div>
    </main>
    {selected && <CalibrationDrawer camera={selected} onClose={()=>setSelected(null)} onSave={saveCalibration}/>}
    {toast && <div className="toast"><Sparkles size={16}/>{toast}<button onClick={()=>setToast("")}><X size={14}/></button></div>}
  </div>;
}
