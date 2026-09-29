import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, BrainCircuit, Building2, Check, ChevronRight, CircleHelp, Database, FileText, LayoutDashboard, LoaderCircle, Mail, MessageSquare, Plus, RefreshCw, Search, Sparkles, Target, Users, X } from 'lucide-react';
import { api, API_DOCS_URL } from './api';

const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
const date = value => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const initials = name => name.split(' ').map(word => word[0]).slice(0, 2).join('');

function Busy({ children }) { return <span className="busy"><LoaderCircle size={15} className="spin" />{children}</span>; }
function Empty({ children }) { return <div className="empty"><Database size={25} /><p>{children}</p></div>; }

function Dialog({ kind, onClose, onSubmit, busy, error }) {
  const dialog = useRef(null);
  useEffect(() => { dialog.current.showModal(); }, []);
  async function submit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    if (kind === 'deal') data.value = Number(data.value);
    else data.occurred_at = new Date(data.occurred_at).toISOString();
    await onSubmit(data);
  }
  const localNow = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  return <dialog ref={dialog} onCancel={event => { event.preventDefault(); if (!busy) onClose(); }} aria-labelledby="dialog-title">
    <div className="dialog-heading"><div><span className="eyebrow">CAPTURE THE CONTEXT</span><h2 id="dialog-title">{kind === 'deal' ? 'Create a deal' : 'Log an interaction'}</h2></div><button className="icon-button" aria-label="Close dialog" disabled={busy} onClick={onClose}><X size={20} /></button></div>
    <form onSubmit={submit}>
      {kind === 'deal' ? <>
        <label>Company<input name="company" required maxLength={120} autoFocus placeholder="e.g. Acme Systems" /></label>
        <div className="form-row"><label>Contact<input name="contact" required maxLength={120} /></label><label>Role<input name="role" maxLength={120} /></label></div>
        <label>Deal title<input name="title" required maxLength={200} /></label>
        <div className="form-row"><label>Value (USD)<input type="number" name="value" min="0" max="1000000000" step="0.01" defaultValue="0" required /></label><label>Stage<select name="stage">{['Discovery', 'Evaluation', 'Proposal', 'Negotiation', 'Won', 'Lost'].map(x => <option key={x}>{x}</option>)}</select></label></div>
        <label>Current context<textarea name="summary" rows={3} maxLength={4000} /></label>
      </> : <>
        <label>Title<input name="title" required maxLength={200} autoFocus placeholder="What was the conversation about?" /></label>
        <div className="form-row"><label>Channel<select name="channel">{['Call', 'Email', 'Meeting', 'Note'].map(x => <option key={x}>{x}</option>)}</select></label><label>Occurred at<input type="datetime-local" name="occurred_at" required defaultValue={localNow} /></label></div>
        <label>Conversation notes<textarea name="content" required minLength={3} maxLength={12000} rows={6} placeholder="Capture concerns, requirements, preferences, and agreed next steps…" /></label>
        <p className="form-note"><Database size={16} />Saved to the deal, then sent to Hindsight. Failed memory delivery can be retried.</p>
      </>}
      {error && <div role="alert" className="alert error">{error}</div>}
      <div className="dialog-footer"><button type="button" className="secondary" disabled={busy} onClick={onClose}>Cancel</button><button className="primary" disabled={busy}>{busy ? <Busy>Saving…</Busy> : kind === 'deal' ? 'Create deal' : 'Save interaction'}</button></div>
    </form>
  </dialog>;
}

export default function App() {
  const [deals, setDeals] = useState([]);
  const [selected, setSelected] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All deals');
  const [tab, setTab] = useState('overview');
  const [query, setQuery] = useState('What should I know before the next customer conversation?');
  const [memories, setMemories] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [working, setWorking] = useState('');
  const [notice, setNotice] = useState(null);
  const [dialog, setDialog] = useState(null);
  const [dialogError, setDialogError] = useState('');
  const selectionVersion = useRef(0);
  const deal = deals.find(item => item.id === selected);

  async function load() {
    setLoading(true); setLoadError('');
    try {
      const [records, status] = await Promise.all([api('/deals'), api('/health')]);
      setDeals(records); setHealth(status); setSelected(id => id || records[0]?.id || null);
    } catch (error) { setLoadError(error.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  function selectDeal(id) {
    selectionVersion.current += 1;
    setSelected(id); setMemories(null); setIntelligence(null); setNotice(null); setTab('overview'); setWorking('');
  }
  async function refreshDeal(id) {
    const updated = await api(`/deals/${id}`);
    setDeals(current => current.map(item => item.id === id ? updated : item));
  }
  async function run(action) {
    const id = selected, version = selectionVersion.current;
    setWorking(action); setNotice(null);
    try {
      const path = action === 'sync' ? 'memory/sync' : action === 'recall' ? 'memory/recall' : 'intelligence';
      const data = await api(`/deals/${id}/${path}`, action === 'sync' ? {} : { query });
      if (version !== selectionVersion.current) return;
      if (action === 'sync') {
        await refreshDeal(id);
        if (version !== selectionVersion.current) return;
        setNotice({ error: !!data.error, text: data.error || `${data.retained} interaction(s) retained. ${data.remaining} remaining.` });
        setMemories(null); setIntelligence(null);
      } else if (action === 'recall') { setMemories(data.memories); }
      else { setIntelligence(data); setMemories(data.memories); }
    } catch (error) { if (version === selectionVersion.current) setNotice({ error: true, text: error.message }); }
    finally { if (version === selectionVersion.current) setWorking(''); }
  }
  async function save(data) {
    setWorking('save'); setDialogError('');
    try {
      if (dialog === 'deal') {
        const created = await api('/deals', data);
        setDeals(current => [...current, created]); selectDeal(created.id);
      } else {
        const interaction = await api(`/deals/${selected}/interactions`, data);
        await refreshDeal(selected); setMemories(null); setIntelligence(null);
        setNotice({ error: interaction.memory_status !== 'retained', text: interaction.memory_status === 'retained' ? 'Interaction saved and retained in Hindsight.' : `Interaction saved. ${interaction.memory_error}` });
      }
      setDialog(null);
    } catch (error) { setDialogError(error.message); }
    finally { setWorking(''); }
  }
  const visible = deals.filter(item => `${item.company} ${item.contact} ${item.title}`.toLowerCase().includes(search.toLowerCase()) && (filter === 'All deals' || item.stage === filter));
  const retained = deal?.interactions.filter(item => item.memory_status === 'retained').length || 0;
  const total = deals.reduce((sum, item) => sum + (['Won', 'Lost'].includes(item.stage) ? 0 : item.value), 0);

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={event => event.preventDefault()}><span className="brand-mark"><BrainCircuit size={24} /></span>DealMind<span className="brand-dot">.</span></a>
      <div className="workspace"><span className="workspace-icon">D</span><div>Sales workspace<small>Personal workspace</small></div><ChevronRight size={15} /></div>
      <span className="nav-label">WORKSPACE</span>
      <button className={`nav-item ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}><LayoutDashboard size={18} />Deal overview<span>{deals.length}</span></button>
      <button className={`nav-item ${tab === 'memory' ? 'active' : ''}`} onClick={() => setTab('memory')}><BrainCircuit size={18} />Memory & intelligence</button>
      <div className="sidebar-bottom"><div className="memory-note"><span className="tiny-icon"><Database size={18} /></span><strong>Every conversation counts.</strong><p>Turn yesterday’s context into a better next conversation.</p><span>Powered by Hindsight <ArrowUpRight size={13} /></span></div><div className="profile"><span className="avatar">SR</span><div>Sales representative<small>Local demo workspace</small></div></div></div>
    </aside>

    <main>
      <header className="topbar"><div>Workspace <ChevronRight size={14} /><strong>{tab === 'overview' ? 'Deal overview' : 'Memory & intelligence'}</strong></div><a href={API_DOCS_URL} target="_blank" rel="noreferrer"><CircleHelp size={17} /> API docs</a></header>
      <div className="page">
        <div className="page-heading"><div><span className="eyebrow">YOUR PIPELINE, WITH CONTEXT</span><h1>{tab === 'overview' ? 'Good deals start with a good memory.' : 'Connect the dots before your next call.'}</h1><p>Know what matters. Remember what was said. Move the conversation forward.</p></div><button className="primary" onClick={() => { setDialogError(''); setDialog('deal'); }} disabled={!!working}><Plus size={17} />New deal</button></div>
        <section className="metrics" aria-label="Pipeline summary"><div><span>Active pipeline <Target size={16} /></span><strong>{money(total)}</strong><small>Across open opportunities</small></div><div><span>Customer relationships <Building2 size={16} /></span><strong>{deals.length.toString().padStart(2, '0')}</strong><small>Every detail in one place</small></div><div><span>Captured interactions <MessageSquare size={16} /></span><strong>{deals.reduce((sum, item) => sum + item.interactions.length, 0).toString().padStart(2, '0')}</strong><small>Context worth remembering</small></div><div className="status-metric"><span>Memory layer <Database size={16} /></span><strong><i className={health?.memory_configured ? 'dot green' : 'dot amber'} />{health?.memory_configured ? 'Configured' : 'Setup needed'}</strong><small>{health?.memory_configured ? 'Hindsight · connection checked on use' : 'Connect Hindsight to activate memory'}</small></div></section>
        {loadError && <div className="alert error" role="alert">{loadError}<button onClick={load}>Retry loading</button></div>}
        {loading ? <div className="loading-page"><Busy>Loading your workspace…</Busy></div> : <div className="workbench">
          <section className="deal-list panel"><div className="panel-title"><h2>Your deals <span className="count">{deals.length}</span></h2><Users size={17} /></div><label className="search-box"><Search size={16} /><input aria-label="Search deals" placeholder="Search companies or contacts" value={search} onChange={event => setSearch(event.target.value)} /></label><div className="list-filter"><span>OPPORTUNITIES</span><select aria-label="Filter by stage" value={filter} onChange={event => setFilter(event.target.value)}>{['All deals', 'Discovery', 'Evaluation', 'Proposal', 'Negotiation', 'Won', 'Lost'].map(item => <option key={item}>{item}</option>)}</select></div>
            {visible.map((item, index) => <button key={item.id} className={`deal-card ${item.id === selected ? 'selected' : ''}`} onClick={() => selectDeal(item.id)}><div className="deal-card-top"><span className={`company-icon tone-${index % 3}`}>{initials(item.company)}</span><span><strong>{item.company}</strong><small>{item.contact}</small></span><ChevronRight size={16} /></div><p>{item.title}</p><div className="deal-card-bottom"><span className={`stage stage-${item.stage.toLowerCase()}`}>{item.stage}</span><b>{money(item.value)}</b></div></button>)}
            {!visible.length && <Empty>No deals match. Try another search or create a deal.</Empty>}<div className="list-footer"><span className="dot green" />Stored locally · built for your next conversation</div>
          </section>

          {!deal ? <section className="panel"><Empty>Select or create a deal to get started.</Empty></section> : <div className="detail-column">
            <section className="deal-detail panel"><div className="detail-top"><div className="company-heading"><span className="company-icon large">{initials(deal.company)}</span><div><div className="company-title"><h2>{deal.company}</h2><span className={`stage stage-${deal.stage.toLowerCase()}`}>{deal.stage}</span></div><p>{deal.title}</p></div></div><strong className="deal-value">{money(deal.value)}<small>Annual deal value</small></strong></div><p className="deal-summary">{deal.summary || 'Add an interaction to start building customer context.'}</p><div className="contact-row"><span className="avatar small">{initials(deal.contact)}</span><strong>{deal.contact}</strong><span>{deal.role}</span>{deal.industry && <span className="industry">{deal.industry}</span>}</div></section>
            <section className="memory-flow"><span><i>1</i>Capture interactions</span><ArrowRight size={15} /><span><i>2</i>Retain in Hindsight</span><ArrowRight size={15} /><span><i>3</i>Recall & act</span></section>
            {notice && <div className={`alert ${notice.error ? 'error' : 'success'}`} role={notice.error ? 'alert' : 'status'}>{notice.text}</div>}
            {tab === 'overview' && <section className="panel history"><div className="panel-title"><div><h2><MessageSquare size={18} />Interaction history <span className="count">{deal.interactions.length}</span></h2><p>The conversations behind the opportunity.</p></div><button className="secondary" disabled={!!working} onClick={() => { setDialogError(''); setDialog('interaction'); }}><Plus size={15} />Log interaction</button></div>
              <div className="timeline">{deal.interactions.map(item => <article key={item.id} className="interaction"><div className="timeline-icon">{item.channel === 'Email' ? <Mail size={15} /> : <MessageSquare size={15} />}</div><div><div className="interaction-meta"><span>{item.channel}</span><span>{date(item.occurred_at)}</span></div><h3>{item.title}</h3><p>{item.content}</p><span className={`memory-state ${item.memory_status}`} title={item.memory_error || ''}>{item.memory_status === 'retained' ? <Check size={12} /> : <Database size={12} />}{item.memory_status === 'retained' ? 'Retained in Hindsight' : item.memory_status === 'failed' ? 'Memory delivery failed · retry sync' : 'Pending memory sync'}</span></div></article>)}</div>
              {!deal.interactions.length && <Empty>No conversations yet. Log your first interaction to build the deal’s memory.</Empty>}
            </section>}
            <section className="panel memory-panel"><div className="panel-title"><div><h2><BrainCircuit size={19} />Relevant memory <span className="hindsight-badge">HINDSIGHT</span></h2><p>Bring earlier requirements and concerns back into view.</p></div><button className="secondary" disabled={!!working} onClick={() => run('sync')}>{working === 'sync' ? <Busy>Syncing…</Busy> : <><RefreshCw size={14} />Sync {deal.interactions.length - retained} pending</>}</button></div>
              <div className="memory-progress"><span>{retained} of {deal.interactions.length} interactions retained</span><div><i style={{ width: `${deal.interactions.length ? retained / deal.interactions.length * 100 : 0}%` }} /></div></div>
              <form className="query-form" onSubmit={event => { event.preventDefault(); run('recall'); }}><label htmlFor="memory-query">What would you like to recall?</label><div><input id="memory-query" value={query} onChange={event => setQuery(event.target.value)} required minLength={3} maxLength={2000} /><button className="secondary" disabled={!!working || query.trim().length < 3}>{working === 'recall' ? <Busy>Recalling…</Busy> : <><Search size={15} />Recall</>}</button></div></form>
              {memories === null ? <Empty>Sync your interactions, then recall the context you need. Only actual Hindsight results appear here.</Empty> : memories.length === 0 ? <Empty>No memories returned. Check setup, sync interactions, or broaden your question.</Empty> : <div className="memory-results">{memories.map(item => <article key={item.id}><span className="memory-type"><Database size={13} />{item.type}</span><p>{item.text}</p><small>Memory {item.id}{item.document_id ? ` · Source ${item.document_id}` : ''}</small></article>)}</div>}
            </section>
            <section className="panel intelligence-panel"><div className="panel-title"><div><h2><Sparkles size={19} />Sales intelligence</h2><p>Turn recalled context into a more thoughtful follow-up.</p></div><button className="primary" disabled={!!working || query.trim().length < 3} onClick={() => run('intelligence')}>{working === 'intelligence' ? <Busy>Preparing…</Busy> : <><Sparkles size={15} />Prepare brief</>}</button></div>
              {!intelligence ? <div className="brief-placeholder"><span><FileText size={27} /></span><div><h3>Your next conversation, with the full picture.</h3><p>Prepare a brief from current deal information and relevant historical memory.</p></div></div> : <>
                <div className="brief-label"><span className={intelligence.mode === 'hindsight' ? 'ai-label' : 'demo-label'}>{intelligence.mode === 'hindsight' ? 'AI brief · Hindsight reflection' : 'Rules-based development brief'}</span><small>{date(intelligence.generated_at)}</small></div>
                {intelligence.warning && <div className="alert warning" role="status">{intelligence.warning}</div>}<div className="brief-text">{intelligence.brief}</div><div className="next-actions"><h3><Target size={17} />Suggested follow-up checks</h3><p>Rules-based suggestions from the available evidence. Confirm before acting.</p>{intelligence.next_actions.map((action, index) => <div key={index}><span>{index + 1}</span><p>{action}</p></div>)}</div>
              </>}
            </section>
          </div>}
        </div>}
        <footer>DealMind <span>Remember the details. Build the relationship.</span><span>Fictional sample data · USD</span></footer>
      </div>
    </main>
    {dialog && <Dialog kind={dialog} onClose={() => setDialog(null)} onSubmit={save} busy={working === 'save'} error={dialogError} />}
  </div>;
}
