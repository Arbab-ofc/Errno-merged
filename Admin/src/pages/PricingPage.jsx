import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";

const inr = (value) => value == null ? "Not configured" : `₹${Number(value).toLocaleString("en-IN")}`;

export function PricingPage() {
  const { user, admin } = useAuth();
  const [durations, setDurations] = useState(null);
  const [settings, setSettings] = useState(null);
  const [presence, setPresence] = useState(null);
  const [audit, setAudit] = useState([]);
  const [timeRules, setTimeRules] = useState([]);
  const [demandRules, setDemandRules] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [areas, setAreas] = useState([]);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canWrite = admin?.permissions?.includes("pricing.write");
  const canActivate = admin?.permissions?.includes("pricing.activate");
  const settingValues = settings?.draft?.values || settings || {};
  const refresh = useCallback(async () => {
    try {
      setError("");
      const [d, s, p, a, t, m, b, ar] = await Promise.all([api.pricingDurations(user), api.pricingSettings(user), api.presenceSummary(user), api.pricingAudit(user, { limit: 30 }), api.pricingTimeRules(user), api.pricingDemandRules(user), api.pricingBookings(user, { limit: 50 }), api.pricingAreas(user)]);
      setDurations(d); setSettings(s); setPresence(p); setAudit(a.items || []); setTimeRules(t); setDemandRules(m); setBookings(b.items || []); setAreas(ar);
    } catch (e) { setError(e.message); }
  }, [user]);
  useEffect(() => { refresh(); const timer = setInterval(refresh, 30000); return () => clearInterval(timer); }, [refresh]);

  async function saveDuration(row, form) {
    setBusy(true);
    try {
      await api.updatePricingDuration(user, row.duration_hours, {
        base_price: form.get("base") || null,
        maximum_price: form.get("maximum") || null, enabled: false,
        effective_from: form.get("from") ? new Date(form.get("from")).toISOString() : null,
        effective_until: form.get("until") ? new Date(form.get("until")).toISOString() : null,
      }); await refresh();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function activate(hours) {
    if (!window.confirm(`Activate the reviewed ${hours}-hour pricing version? This changes quotes for future bookings.`)) return;
    setBusy(true); try { await api.activatePricingDuration(user, hours); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function saveSettings(form) {
    setBusy(true);
    try { await api.updatePricingSettings(user, {
      commission_rate: form.get("commission") === "" ? undefined : Number(form.get("commission")) / 100,
      quote_ttl_seconds: form.get("ttl") === "" ? undefined : Number(form.get("ttl")),
      heartbeat_interval_seconds: form.get("heartbeat") === "" ? undefined : Number(form.get("heartbeat")),
      presence_ttl_seconds: form.get("presenceTtl") === "" ? undefined : Number(form.get("presenceTtl")),
      combined_multiplier_cap: form.get("cap") === "" ? undefined : Number(form.get("cap")),
      default_timezone: form.get("timezone") || undefined,
      rounding_policy: form.get("rounding") || undefined,
      surge_enabled: form.get("surge") === "on",
      time_pricing_enabled: form.get("time") === "on",
      demand_pricing_enabled: form.get("demand") === "on",
    }); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function addTimeRule(form) {
    setBusy(true); try { await api.createPricingTimeRule(user, { name: form.get("name"), start_time: form.get("start"), end_time: form.get("end"), timezone: form.get("timezone"), multiplier: Number(form.get("multiplier")), effective_from: form.get("effective") ? new Date(form.get("effective")).toISOString() : null, enabled: false }); await refresh(); form.reset(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function addDemandRule(form) {
    setBusy(true); try { await api.createPricingDemandRule(user, { name: form.get("name"), demand_level: form.get("level"), minimum_demand_ratio: form.get("minimum") === "" ? null : Number(form.get("minimum")), maximum_demand_ratio: form.get("maximum") === "" ? null : Number(form.get("maximum")), availability_thresholds: form.get("zero") === "on" ? { zero_available_workers: true } : {}, multiplier: Number(form.get("multiplier")), effective_from: form.get("effective") ? new Date(form.get("effective")).toISOString() : null, enabled: false }); await refresh(); form.reset(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function activateRule(fn, id) { if (!window.confirm("Activate this reviewed pricing rule?")) return; setBusy(true); try { await fn(user,id); await refresh(); } catch(e) { setError(e.message); } finally { setBusy(false); } }
  async function runPreview(form) {
    setBusy(true); setPreview(null); setError("");
    try { setPreview(await api.previewPricing(user, {
      duration_hours: Number(form.get("duration")), service_start_at: new Date(form.get("serviceTime")).toISOString(),
      area_id: form.get("areaId") || null, use_draft_configuration: form.get("configurationSource") === "draft",
      scenario_time_multiplier: form.get("timeMultiplier") === "" ? null : Number(form.get("timeMultiplier")),
      scenario_demand_multiplier: form.get("demandMultiplier") === "" ? null : Number(form.get("demandMultiplier")),
    })); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function updateTimeRule(id, form) {
    setBusy(true); try { await api.updatePricingTimeRule(user,id,{ name:form.get("name"), start_time:form.get("start"), end_time:form.get("end"), timezone:form.get("timezone"), multiplier:Number(form.get("multiplier")), enabled:false }); await refresh(); }
    catch(e) { setError(e.message); } finally { setBusy(false); }
  }
  async function updateDemandRule(id, form) {
    setBusy(true); try { await api.updatePricingDemandRule(user,id,{ name:form.get("name"), demand_level:form.get("level"), minimum_demand_ratio:form.get("minimum") === "" ? null : Number(form.get("minimum")), maximum_demand_ratio:form.get("maximum") === "" ? null : Number(form.get("maximum")), multiplier:Number(form.get("multiplier")), enabled:false }); await refresh(); }
    catch(e) { setError(e.message); } finally { setBusy(false); }
  }
  async function addAreaRule(form) {
    setBusy(true); try { await api.createPricingArea(user,{area_key:form.get("area"),duration_hours:Number(form.get("duration")),base_price:form.get("base")===""?null:Number(form.get("base")),maximum_price:form.get("maximum")===""?null:Number(form.get("maximum")),time_rule_id:form.get("timeRule")||null,demand_rule_id:form.get("demandRule")||null,effective_from:form.get("effective")?new Date(form.get("effective")).toISOString():null}); await refresh(); form.reset(); }
    catch(e){setError(e.message);} finally{setBusy(false);}
  }
  async function updateAreaRule(id,form) {
    setBusy(true); try { await api.updatePricingArea(user,id,{area_key:form.get("area"),base_price:form.get("base")===""?null:Number(form.get("base")),maximum_price:form.get("maximum")===""?null:Number(form.get("maximum")),time_rule_id:form.get("timeRule")||null,demand_rule_id:form.get("demandRule")||null}); await refresh(); }
    catch(e){setError(e.message);} finally{setBusy(false);}
  }
  async function activateArea(id) { if(!window.confirm("Activate this area pricing override?"))return; setBusy(true); try{await api.activatePricingArea(user,id);await refresh();}catch(e){setError(e.message);}finally{setBusy(false);} }
  async function activateSettings() { if(!window.confirm("Activate these reviewed global pricing settings for future quotes?"))return; setBusy(true); try{await api.activatePricingSettings(user);await refresh();}catch(e){setError(e.message);}finally{setBusy(false);} }

  if (error && !durations) return <><PageHeader title="Pricing Management" description="Backend controlled pricing, payout and live presence." onRefresh={refresh} /><StatePanel title="Pricing data is unavailable" detail={error} actionLabel="Retry" onAction={refresh} /></>;
  return <>
    <PageHeader title="Pricing Management" description="Configure commercial rates, review pricing versions and monitor live platform presence." onRefresh={refresh} refreshing={busy} />
    {error && <div role="alert" className="inline-error">{error}</div>}
    <section className="metric-grid live-metrics" aria-label="Live user presence">
      {[["ONLINE WORKERS", presence?.online_workers], ["ONLINE RECRUITERS", presence?.online_recruiters], ["AVAILABLE WORKERS", presence?.available_workers], ["REGISTERED WORKERS", presence?.registered_workers], ["REGISTERED RECRUITERS", presence?.registered_recruiters]].map(([label, value]) => <article className="metric-panel" key={label}><div className="metric-panel-top"><span>{label}</span></div><strong>{value == null ? "—" : value}</strong><small>{presence?.last_updated_at ? `Updated ${new Date(presence.last_updated_at).toLocaleTimeString()}` : "Waiting for live API data"}</small></article>)}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Time based rules</h2><p>Time bands use the configured pricing timezone and support bands that cross midnight.</p></div></div>
      {timeRules.map((r)=><div className="recent-row rule-row" key={r.id}><div><b>{r.name} · {String(r.start_time).slice(0,5)}–{String(r.end_time).slice(0,5)} · {r.multiplier}×</b><small>{r.timezone} · {r.enabled ? "Active" : "Draft"} · {r.effective_from ? new Date(r.effective_from).toLocaleString() : "No effective date"}</small></div><details><summary>Edit</summary><form className="rule-form" action={(f)=>updateTimeRule(r.id,f)}><input name="name" required defaultValue={r.name}/><input name="start" type="time" required defaultValue={String(r.start_time).slice(0,5)}/><input name="end" type="time" required defaultValue={String(r.end_time).slice(0,5)}/><input name="timezone" required defaultValue={r.timezone}/><input name="multiplier" type="number" min="0.01" max="10" step="0.01" required defaultValue={r.multiplier}/><button disabled={busy}>Save draft</button></form></details>{canActivate && !r.enabled && <button className="pricing-action" onClick={()=>activateRule(api.activatePricingTimeRule,r.id)}>Activate</button>}{canWrite && r.enabled && <button className="pricing-action" onClick={()=>api.updatePricingTimeRule(user,r.id,{enabled:false}).then(refresh).catch(e=>setError(e.message))}>Deactivate</button>}</div>)}
      {canWrite && <form className="rule-form" action={addTimeRule}><input name="name" required placeholder="Band name"/><input name="start" type="time" required/><input name="end" type="time" required/><input name="timezone" required defaultValue={settings?.default_timezone ?? ""} placeholder="IANA timezone"/><input name="multiplier" type="number" min="0.01" max="10" step="0.01" required placeholder="Multiplier"/><input name="effective" type="datetime-local" required/><button disabled={busy}>Add draft band</button></form>}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Demand rules</h2><p>Demand ratio is open jobs divided by currently available, online workers. Zero supply requires an explicit rule.</p></div></div>
      {demandRules.map((r)=><div className="recent-row rule-row" key={r.id}><div><b>{r.name} · {r.demand_level} · {r.multiplier}×</b><small>Ratio {r.minimum_demand_ratio ?? "−∞"} to {r.maximum_demand_ratio ?? "∞"} · {r.enabled ? "Active" : "Draft"}</small></div><details><summary>Edit</summary><form className="rule-form" action={(f)=>updateDemandRule(r.id,f)}><input name="name" required defaultValue={r.name}/><input name="level" required defaultValue={r.demand_level}/><input name="minimum" type="number" min="0" step="0.01" defaultValue={r.minimum_demand_ratio ?? ""} placeholder="Min ratio"/><input name="maximum" type="number" min="0" step="0.01" defaultValue={r.maximum_demand_ratio ?? ""} placeholder="Max ratio"/><input name="multiplier" type="number" min="0.01" max="10" step="0.01" required defaultValue={r.multiplier}/><button disabled={busy}>Save draft</button></form></details>{canActivate && !r.enabled && <button className="pricing-action" onClick={()=>activateRule(api.activatePricingDemandRule,r.id)}>Activate</button>}{canWrite && r.enabled && <button className="pricing-action" onClick={()=>api.updatePricingDemandRule(user,r.id,{enabled:false}).then(refresh).catch(e=>setError(e.message))}>Deactivate</button>}</div>)}
      {canWrite && <form className="rule-form" action={addDemandRule}><input name="name" required placeholder="Rule name"/><input name="level" required placeholder="Demand level"/><input name="minimum" type="number" min="0" step="0.01" placeholder="Minimum jobs/worker"/><input name="maximum" type="number" min="0" step="0.01" placeholder="Maximum jobs/worker"/><input name="multiplier" type="number" min="0.01" max="10" step="0.01" required placeholder="Multiplier"/><input name="effective" type="datetime-local" required/><label><input type="checkbox" name="zero"/> Applies when no workers are available</label><button disabled={busy}>Add draft demand rule</button></form>}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Duration pricing</h2><p>Reference maximums are not approved prices. Draft rows stay inactive until approved.</p></div></div>
      {!durations ? <p>Loading pricing configuration…</p> : <div className="pricing-table-wrap"><table className="pricing-table"><thead><tr><th>Duration</th><th>Base price</th><th>Maximum price</th><th>Approval</th><th>Effective from</th><th>Actions</th></tr></thead><tbody>{durations.map((row) => <tr key={row.duration_hours}><td>{row.duration_hours} hour{row.duration_hours > 1 ? "s" : ""}</td><td colSpan="5"><form className="pricing-row" action={(form) => saveDuration(row, form)}><label><span className="sr-only">Base price</span><input name="base" aria-label={`${row.duration_hours} hour base`} type="number" min="0" step="0.01" defaultValue={row.base_price ?? ""} placeholder="Set base" disabled={!canWrite} /></label><label><span className="sr-only">Maximum price</span><input name="maximum" aria-label={`${row.duration_hours} hour maximum`} type="number" min="0" step="0.01" defaultValue={row.maximum_price ?? ""} placeholder={inr(row.maximum_price)} disabled={!canWrite} /></label><span>{row.approval_status}{row.enabled ? " · active" : " · inactive"}</span><label><span className="sr-only">Effective from</span><input aria-label="Effective start date" name="from" type="datetime-local" disabled={!canWrite} /></label><label><span className="sr-only">Effective until</span><input aria-label="Effective end date" name="until" type="datetime-local" disabled={!canWrite} /></label><div className="pricing-actions">{canWrite && <button type="submit" disabled={busy}>Save draft</button>}{canActivate && <button type="button" disabled={busy || row.approval_status !== "draft"} onClick={() => activate(row.duration_hours)}>Review & activate</button>}</div></form></td></tr>)}</tbody></table></div>}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Global pricing settings</h2><p>Rates remain unset until an administrator configures and saves them.</p></div></div>
      <form className="pricing-settings" action={saveSettings}><label>ERRNO commission (%)<input name="commission" type="number" min="0" max="100" step="0.01" defaultValue={settingValues.commission_rate == null ? "" : Number(settingValues.commission_rate) * 100} disabled={!canWrite} /></label><label>Quote validity (seconds)<input name="ttl" type="number" min="1" defaultValue={settingValues.quote_ttl_seconds ?? ""} disabled={!canWrite} /></label><label>Heartbeat interval (seconds)<input name="heartbeat" type="number" min="15" max="3600" defaultValue={settingValues.heartbeat_interval_seconds ?? ""} disabled={!canWrite} /></label><label>Presence expiry (seconds)<input name="presenceTtl" type="number" min="30" defaultValue={settingValues.presence_ttl_seconds ?? ""} disabled={!canWrite} /></label><label>Combined multiplier cap<input name="cap" type="number" min="0.01" step="0.01" defaultValue={settingValues.combined_multiplier_cap ?? ""} disabled={!canWrite} /></label><label>Pricing timezone<input name="timezone" defaultValue={settingValues.default_timezone ?? ""} placeholder="IANA timezone" disabled={!canWrite} /></label><label>Rounding policy<select name="rounding" defaultValue={settingValues.rounding_policy ?? ""} disabled={!canWrite}><option value="">Not configured</option><option value="half_up">Nearest rupee (half up)</option><option value="up">Round up</option><option value="down">Round down</option></select></label><label><input type="checkbox" name="surge" defaultChecked={settingValues.surge_enabled ?? false} disabled={!canWrite} /> Surge enabled</label><label><input type="checkbox" name="time" defaultChecked={settingValues.time_pricing_enabled ?? false} disabled={!canWrite} /> Time pricing enabled</label><label><input type="checkbox" name="demand" defaultChecked={settingValues.demand_pricing_enabled ?? false} disabled={!canWrite} /> Demand pricing enabled</label>{canWrite && <button disabled={busy}>Save settings draft</button>}{canActivate && settings?.draft && <button type="button" disabled={busy} onClick={activateSettings}>Activate settings v{settings.draft.version}</button>}</form>
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Pricing preview</h2><p>Uses the backend pricing engine. Draft mode previews saved, inactive configuration without activating it.</p></div></div>
      <form className="rule-form" action={runPreview}><select name="duration" required defaultValue=""><option value="" disabled>Select duration</option>{durations?.map((d)=><option key={d.duration_hours} value={d.duration_hours}>{d.duration_hours} hours</option>)}</select><input name="serviceTime" type="datetime-local" required/><input name="areaId" placeholder="Existing shop/job address (optional)"/><select aria-label="Configuration to preview" name="configurationSource" defaultValue={settings?.draft ? "draft" : "active"}><option value="draft" disabled={!settings?.draft}>Saved draft</option><option value="active">Active configuration</option></select><input name="timeMultiplier" type="number" min="0.01" max="10" step="0.01" placeholder="Time scenario multiplier (optional)"/><input name="demandMultiplier" type="number" min="0.01" max="10" step="0.01" placeholder="Demand scenario multiplier (optional)"/><button disabled={busy}>Calculate preview</button></form>
      {preview && <div className="pricing-preview-grid">{[["Base price",preview.base_price],["Time multiplier",`${preview.time_multiplier}×`],["Demand multiplier",`${preview.demand_multiplier}×`],["Raw price",preview.raw_price],["Maximum price",preview.maximum_price],["Final customer payable",preview.final_service_charge],["ERRNO commission",preview.commission_amount],["Worker payout",preview.worker_payout_amount],["Expires",new Date(preview.expires_at).toLocaleString()],["Version",preview.pricing_version]].map(([k,v])=><div key={k}><small>{k}</small><b>{v}</b></div>)}</div>}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Area pricing overrides</h2><p>Uses the existing canonical address string as the normalized area key. Missing overrides fall back to duration and global time/demand rules.</p></div></div>
      {areas.map((r)=><div className="recent-row rule-row" key={r.id}><div><b>{r.area_key} · {r.duration_hours}h · {r.approval_status}{r.enabled?" · active":""}</b><small>Base {inr(r.base_price)} · maximum {inr(r.maximum_price)} · time rule {r.time_rule_id||"global"} · demand rule {r.demand_rule_id||"global"}</small></div><details><summary>Edit</summary><form className="rule-form" action={(f)=>updateAreaRule(r.id,f)}><input name="area" required defaultValue={r.area_key}/><input name="base" type="number" min="0" step="0.01" defaultValue={r.base_price??""} placeholder="Base override"/><input name="maximum" type="number" min="0" step="0.01" defaultValue={r.maximum_price??""} placeholder="Maximum override"/><select name="timeRule" defaultValue={r.time_rule_id??""}><option value="">Global time rules</option>{timeRules.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><select name="demandRule" defaultValue={r.demand_rule_id??""}><option value="">Global demand rules</option>{demandRules.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><button disabled={busy}>Save draft</button></form></details>{canActivate&&!r.enabled&&<button className="pricing-action" onClick={()=>activateArea(r.id)}>Activate</button>}</div>)}
      {canWrite&&<form className="rule-form" action={addAreaRule}><input name="area" required placeholder="Existing canonical shop/job address"/><select name="duration" required defaultValue=""><option value="" disabled>Duration</option>{durations?.map(d=><option key={d.duration_hours} value={d.duration_hours}>{d.duration_hours}h</option>)}</select><input name="base" type="number" min="0" step="0.01" placeholder="Base override (optional)"/><input name="maximum" type="number" min="0" step="0.01" placeholder="Maximum override (optional)"/><select name="timeRule"><option value="">Global time rules</option>{timeRules.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><select name="demandRule"><option value="">Global demand rules</option>{demandRules.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><input name="effective" type="datetime-local" required/><button disabled={busy}>Add area draft</button></form>}
    </section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Booking financial breakdown</h2><p>Persisted quote snapshots only. Historical jobs without snapshots are omitted.</p></div></div><div className="pricing-table-wrap"><table className="pricing-table"><thead><tr><th>Job ID</th><th>Duration</th><th>Base</th><th>Multipliers</th><th>Final charge</th><th>Commission</th><th>Worker payout</th><th>Version</th><th>Quote / confirm</th></tr></thead><tbody>{bookings.map((b)=><tr key={b.job_id}><td>{b.job_id}</td><td>{b.duration_hours}h</td><td>{inr(b.base_price)}</td><td>{b.time_multiplier}× / {b.demand_multiplier}×</td><td>{inr(b.final_service_charge)}</td><td>{inr(b.commission_amount)}</td><td>{inr(b.worker_payout_amount)}</td><td>{b.pricing_version}</td><td>{new Date(b.created_at).toLocaleString()} / {b.confirmed_at ? new Date(b.confirmed_at).toLocaleString() : "—"}</td></tr>)}</tbody></table></div></section>
    <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Pricing audit history</h2><p>Recent draft changes and activations</p></div></div>{audit.length ? audit.map((item) => <div className="recent-row" key={item.id}><div><b>{item.action} · {item.entity_type}</b><small>{item.admin_user_id} · version {item.pricing_version}</small></div><time>{new Date(item.created_at).toLocaleString()}</time></div>) : <p>No pricing changes recorded.</p>}</section>
  </>;
}
