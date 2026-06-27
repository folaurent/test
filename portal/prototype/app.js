/* =====================================================================
   Automation Portal — interactive prototype. Mock data, no backend.
   Visual spec for the developer.
   ===================================================================== */

// ---------------- Mock data ----------------
const STATUS_LABEL = { success: 'Success', running: 'Running', queued: 'Queued', error: 'Error' };

const automations = [
  {
    slug: 'enrich-leads', icon: '🧲', name: 'Lead enrichment',
    desc: "Every new form lead is enriched (company, role, LinkedIn) then pushed to the CRM.",
    trigger: 'event', triggerLabel: 'New lead received (website form)',
    config: [
      { label: 'Lead source webhook', type: 'text', value: 'https://hooks.portal.app/in/enrich-leads/ax82f', hint: 'Paste this URL into your form — provided by the agency.' },
      { label: 'Destination CRM', type: 'select', options: ['HubSpot', 'Pipedrive', 'Salesforce'], value: 'HubSpot' },
      { label: 'Notify on Slack', type: 'select', options: ['Yes', 'No'], value: 'Yes' },
    ],
    enabled: true, last: '12 min ago', runs7: 48,
  },
  {
    slug: 'invoice-reminders', icon: '📨', name: 'Payment reminders',
    desc: "Automatically emails reminders for overdue invoices at D+3, D+7 and D+14.",
    trigger: 'event', triggerLabel: 'Overdue invoice detected (Stripe)',
    config: [
      { label: 'Connected Stripe account', type: 'text', value: 'acct_1Q…7zP', hint: 'Connection managed by the agency.' },
      { label: 'Email tone', type: 'select', options: ['Friendly', 'Direct', 'Firm'], value: 'Friendly' },
    ],
    enabled: true, last: '2 h ago', runs7: 11,
  },
  {
    slug: 'slack-new-sale', icon: '🔔', name: 'New sale alert',
    desc: "Posts a Slack message on every successful payment, with amount and customer.",
    trigger: 'event', triggerLabel: 'Successful payment (Stripe)',
    config: [
      { label: 'Slack channel', type: 'text', value: '#sales' },
      { label: 'Minimum amount ($)', type: 'text', value: '0' },
    ],
    enabled: true, last: '38 min ago', runs7: 27,
  },
  {
    slug: 'weekly-report', icon: '📊', name: 'Weekly report',
    desc: "Generates and emails a PDF recap of the week's sales and leads every Monday.",
    trigger: 'event', triggerLabel: 'Every Monday at 8:00 AM',
    config: [
      { label: 'Recipients', type: 'text', value: 'leadership@client.com' },
      { label: 'Send day', type: 'select', options: ['Monday', 'Friday'], value: 'Monday' },
    ],
    enabled: false, last: 'never', runs7: 0,
  },
  {
    slug: 'review-request', icon: '⭐', name: 'Review request',
    desc: "Sends a Google review request 3 days after an order is delivered.",
    trigger: 'event', triggerLabel: 'Order delivered',
    config: [
      { label: 'Delay (days)', type: 'text', value: '3' },
      { label: 'Review link', type: 'text', value: 'https://g.page/r/…/review' },
    ],
    enabled: true, last: '5 h ago', runs7: 9,
  },
  {
    slug: 'lead-routing', icon: '🚦', name: 'Lead routing',
    desc: "Assigns each incoming lead to the right rep based on region and industry.",
    trigger: 'event', triggerLabel: 'New qualified lead',
    config: [
      { label: 'Routing rule', type: 'select', options: ['Round-robin', 'By region', 'By industry'], value: 'By region' },
    ],
    enabled: true, last: '1 h ago', runs7: 34,
  },
];

const runs = [
  { id: 'run_9f3a2', auto: 'enrich-leads', name: 'Lead enrichment', status: 'success', when: 'Today, 2:22 PM', detail: 'Lead "Marie Dubois" enriched → HubSpot' },
  { id: 'run_9f2b8', auto: 'slack-new-sale', name: 'New sale alert', status: 'success', when: 'Today, 1:48 PM', detail: 'Sale $249 → #sales' },
  { id: 'run_9f1c1', auto: 'enrich-leads', name: 'Lead enrichment', status: 'running', when: 'Today, 2:25 PM', detail: 'Lead "Karim B." in progress…' },
  { id: 'run_9e0d4', auto: 'invoice-reminders', name: 'Payment reminders', status: 'success', when: 'Today, 12:10 PM', detail: '3 invoices reminded' },
  { id: 'run_9d8e7', auto: 'lead-routing', name: 'Lead routing', status: 'error', when: 'Today, 11:02 AM', detail: 'No rep available for region "South"' },
  { id: 'run_9c5f0', auto: 'review-request', name: 'Review request', status: 'success', when: 'Yesterday, 6:30 PM', detail: 'Request sent to 4 customers' },
  { id: 'run_9b3a9', auto: 'enrich-leads', name: 'Lead enrichment', status: 'success', when: 'Yesterday, 4:14 PM', detail: 'Lead "ACME Corp" enriched' },
  { id: 'run_9a1b2', auto: 'slack-new-sale', name: 'New sale alert', status: 'queued', when: 'Yesterday, 3:50 PM', detail: 'Awaiting processing' },
];

const clients = [
  { id: 'org_acme', name: 'ACME Studio', plan: 'Pro', active: 5, members: 3, status: 'Active' },
  { id: 'org_bloom', name: 'Bloom & Co', plan: 'Starter', active: 2, members: 1, status: 'Active' },
  { id: 'org_nova', name: 'Nova Realty', plan: 'Pro', active: 6, members: 4, status: 'Active' },
  { id: 'org_zest', name: 'Zest Fitness', plan: 'Starter', active: 1, members: 2, status: 'Onboarding' },
];

// ---------------- Outreach engine (OpenOutreach-powered) mock data ----------------
const outreach = {
  campaign: {
    name: 'Q3 — Outbound to RevOps leaders',
    status: 'running',           // running | paused | draft
    product: 'We sell an AI workflow platform that lets B2B teams automate lead gen and outreach without engineers.',
    titles: ['Head of Sales', 'VP Sales', 'RevOps Lead', 'Head of Growth'],
    industries: ['SaaS', 'Fintech', 'B2B Services'],
    sizes: '11–200 employees',
    locations: ['United States', 'United Kingdom', 'Germany'],
    keywords: ['product-led growth', 'outbound', 'sales automation'],
    channels: { linkedin: true, email: true },
    tone: 'Friendly',
    connectNote: "Hi {{first_name}} — loved your take on {{topic}}. We help {{industry}} teams automate outbound. Open to connect?",
    emailOpener: "Hi {{first_name}}, noticed {{company}} is scaling its GTM. We help teams like yours book more meetings without adding headcount — worth a quick look?",
    followups: 3,
    liPerDay: 25,
    emailPerDay: 60,
    strictness: 'Balanced',      // Broad | Balanced | Strict
  },
  funnel: [
    { stage: 'Discovered', count: 1240, color: '#8b5cf6' },
    { stage: 'Qualified',  count: 312,  color: '#6366f1' },
    { stage: 'Contacted',  count: 188,  color: '#2563eb' },
    { stage: 'Replied',    count: 47,   color: '#0ea5e9' },
    { stage: 'Meetings',   count: 12,   color: '#15a34a' },
  ],
  integrations: [
    { name: 'LinkedIn account', detail: 'marie@acme-studio.com', ok: true },
    { name: 'AI model', detail: 'Claude (Anthropic)', ok: true },
    { name: 'Email finder', detail: 'BetterContact', ok: true },
    { name: 'Sending mailbox', detail: 'outbound@acme-studio.com', ok: true },
  ],
  leads: [
    { id: 'ld_01', name: 'Sarah Chen', title: 'VP Sales', company: 'Datadog', loc: 'San Francisco', channel: 'LinkedIn', stage: 'Replied', score: 92 },
    { id: 'ld_02', name: 'Priya Nair', title: 'CMO', company: 'Figma', loc: 'London', channel: 'LinkedIn', stage: 'Meetings', score: 95 },
    { id: 'ld_03', name: 'Daniel Kim', title: 'RevOps Lead', company: 'Ramp', loc: 'New York', channel: 'Email', stage: 'Replied', score: 84 },
    { id: 'ld_04', name: 'Tom Becker', title: 'Head of Growth', company: 'Notion', loc: 'Berlin', channel: 'Email', stage: 'Contacted', score: 87 },
    { id: 'ld_05', name: 'Lena Vogt', title: 'Founder', company: 'Pitch', loc: 'Berlin', channel: 'LinkedIn', stage: 'Contacted', score: 78 },
    { id: 'ld_06', name: 'Marco Rossi', title: 'Sales Director', company: 'Stripe', loc: 'Milan', channel: 'Email', stage: 'Qualified', score: 81 },
    { id: 'ld_07', name: 'Aisha Khan', title: 'VP Marketing', company: 'Miro', loc: 'Amsterdam', channel: 'LinkedIn', stage: 'Qualified', score: 76 },
    { id: 'ld_08', name: 'Hugo Martin', title: 'CEO', company: 'Lemlist', loc: 'Paris', channel: 'Email', stage: 'Discovered', score: 70 },
  ],
  thread: [
    { who: 'ai', t: '2 days ago', text: "Hi Sarah — loved your talk on product-led sales. We help SaaS teams automate outbound without adding headcount. Open to connect?" },
    { who: 'them', t: '1 day ago', text: "Thanks! Sure — what does it actually do?" },
    { who: 'ai', t: '1 day ago', text: "It finds and qualifies prospects matching your ICP, then runs personalized LinkedIn + email sequences. Teams book ~30% more meetings. Worth a 15-min look this week?" },
    { who: 'them', t: '4 h ago', text: "Could be interesting. Send me a time." },
  ],
};
const STAGE_BADGE = { Discovered: 'muted', Qualified: 'queued', Contacted: 'running', Replied: 'running', Meetings: 'success' };

// ---------------- State ----------------
let role = 'client';          // 'client' | 'agency'
let route = '#/';

// ---------------- Helpers ----------------
const $ = (s, r = document) => r.querySelector(s);
const badge = (status, label) => `<span class="badge ${status}"><span class="bd"></span>${label || STATUS_LABEL[status]}</span>`;
const findAuto = (slug) => automations.find(a => a.slug === slug);

function nav(items) {
  return items.map(i =>
    `<a href="${i.href}" class="${route === i.href || (i.match && route.startsWith(i.match)) ? 'active' : ''}">
       <span class="ic">${i.ic}</span>${i.label}</a>`).join('');
}

// ---------------- Shell ----------------
function clientShell(inner) {
  return `
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">A</div>
        <div><div class="name">Automate</div><div class="sub">Client workspace</div></div>
      </div>
      <nav class="nav">
        ${nav([
          { href: '#/', ic: '◧', label: 'Dashboard' },
          { href: '#/outreach', ic: '🎯', label: 'Outreach', match: '#/outreach' },
          { href: '#/runs', ic: '≣', label: 'Activity', match: '#/run' },
          { href: '#/settings', ic: '⚙', label: 'Settings' },
        ])}
      </nav>
      <div class="sidebar-foot">
        <div class="userchip"><div class="av">MD</div>
          <div class="meta"><b>Marie Dubois</b><span>ACME Studio</span></div></div>
      </div>
    </aside>
    <div class="main">
      <div class="topbar">
        <div class="org"><span class="dot"></span> ACME Studio</div>
        <div class="actions">
          <button class="btn btn-sm">Help</button>
          <button class="btn btn-sm btn-primary">+ Request automation</button>
        </div>
      </div>
      <div class="content">${inner}</div>
    </div>
  </div>`;
}

function agencyShell(inner) {
  return `
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">A</div>
        <div><div class="name">Automate</div><div class="sub">Agency console</div></div>
      </div>
      <nav class="nav">
        ${nav([
          { href: '#/', ic: '◧', label: 'Overview' },
          { href: '#/clients', ic: '👥', label: 'Clients', match: '#/client' },
          { href: '#/catalog', ic: '⚡', label: 'Catalog', match: '#/catalog' },
          { href: '#/runs', ic: '≣', label: 'Activity' },
        ])}
      </nav>
      <div class="sidebar-foot">
        <div class="userchip"><div class="av">LF</div>
          <div class="meta"><b>L. Fournier</b><span>Agency · Owner</span></div></div>
      </div>
    </aside>
    <div class="main">
      <div class="topbar">
        <div class="org"><span class="dot"></span> Agency console — 4 clients</div>
        <div class="actions">
          <button class="btn btn-sm btn-primary">+ New client</button>
        </div>
      </div>
      <div class="content">${inner}</div>
    </div>
  </div>`;
}

// ---------------- Client views ----------------
function clientDashboard() {
  const active = automations.filter(a => a.enabled).length;
  const cards = automations.map(a => `
    <div class="card auto-card" data-link="#/automation/${a.slug}">
      <div class="top">
        <div style="display:flex;gap:13px;align-items:flex-start">
          <div class="auto-icon">${a.icon}</div>
          <div><h3>${a.name}</h3></div>
        </div>
        <label class="toggle" onclick="event.stopPropagation()">
          <input type="checkbox" ${a.enabled ? 'checked' : ''} data-toggle="${a.slug}"><span class="track"></span>
        </label>
      </div>
      <div class="desc">${a.desc}</div>
      <div class="foot">
        ${a.enabled ? badge('success', 'Active') : badge('muted', 'Inactive')}
        <span class="last">Last run: ${a.last}</span>
      </div>
    </div>`).join('');

  return `
    <div class="page-head">
      <h1>Welcome back, Marie 👋</h1>
      <p>Here are the automations running on your ACME Studio workspace.</p>
    </div>
    <div class="stats">
      <div class="stat"><div class="label">Active automations</div><div class="num">${active}</div><div class="delta flat">of ${automations.length} available</div></div>
      <div class="stat"><div class="label">Runs (7 days)</div><div class="num">129</div><div class="delta">+18% vs last week</div></div>
      <div class="stat"><div class="label">Success rate</div><div class="num">98.4%</div><div class="delta flat">2 errors</div></div>
      <div class="stat"><div class="label">Est. time saved</div><div class="num">~6 h</div><div class="delta flat">this week</div></div>
    </div>
    <div class="section-title">Featured — interactive automation</div>
    <div class="card feature-card" data-link="#/outreach">
      <div class="feature-glow"></div>
      <div class="feature-main">
        <div class="auto-icon" style="width:52px;height:52px;font-size:26px;background:rgba(255,255,255,.16);border-color:rgba(255,255,255,.25)">🎯</div>
        <div>
          <h3>Outreach Engine <span class="chip-live">● Live</span></h3>
          <p>AI-driven LinkedIn &amp; email prospecting. Set your ideal customer, launch, and watch meetings land. Powered by your private OpenOutreach workflow.</p>
          <div class="feature-stats">
            <span><b>1,240</b> discovered</span><i></i>
            <span><b>188</b> contacted</span><i></i>
            <span><b>47</b> replied</span><i></i>
            <span><b>12</b> meetings</span>
          </div>
        </div>
      </div>
      <button class="btn feature-btn">Open campaign →</button>
    </div>

    <div class="section-title">Your automations</div>
    <div class="grid">${cards}</div>`;
}

// ---------------- Outreach engine views ----------------
function outreachTabs(active) {
  const tabs = [
    { id: 'overview', label: 'Pipeline', href: '#/outreach' },
    { id: 'setup', label: 'Targeting & criteria', href: '#/outreach/setup' },
    { id: 'leads', label: 'Leads', href: '#/outreach/leads' },
    { id: 'inbox', label: 'Inbox', href: '#/outreach/inbox' },
  ];
  return `<div class="subtabs">${tabs.map(t =>
    `<a href="${t.href}" class="subtab ${t.id === active ? 'active' : ''}">${t.label}</a>`).join('')}</div>`;
}

function outreachHead() {
  const c = outreach.campaign;
  const status = c.status === 'running'
    ? badge('success', 'Running') : c.status === 'paused' ? badge('queued', 'Paused') : badge('muted', 'Draft');
  return `
    <div class="breadcrumb"><a href="#/">Dashboard</a> <span>/</span> <span>Outreach Engine</span></div>
    <div class="page-head" style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px">
      <div style="display:flex;gap:14px;align-items:center">
        <div class="auto-icon" style="width:50px;height:50px;font-size:25px">🎯</div>
        <div><h1>${c.name}</h1><p>AI LinkedIn &amp; email outreach · ${status}</p></div>
      </div>
      <div class="actions" style="display:flex;gap:10px">
        <button class="btn">${c.status === 'running' ? '❚❚ Pause' : '▶ Resume'}</button>
        <button class="btn btn-primary" data-link="#/outreach/setup">Edit criteria</button>
      </div>
    </div>`;
}

function outreachOverview() {
  const max = Math.max(...outreach.funnel.map(f => f.count));
  const funnel = outreach.funnel.map(f => `
    <div class="funnel-row">
      <div class="funnel-label">${f.stage}</div>
      <div class="funnel-bar-wrap">
        <div class="funnel-bar" style="width:${Math.max(8, f.count / max * 100)}%;background:${f.color}"></div>
      </div>
      <div class="funnel-count">${f.count.toLocaleString()}</div>
    </div>`).join('');

  const recent = outreach.leads.slice(0, 5).map(l => `
    <tr data-link="#/outreach/lead/${l.id}">
      <td><div class="lead-name"><span class="av-sm">${l.name.split(' ').map(x => x[0]).join('')}</span><div><b>${l.name}</b><span>${l.title} · ${l.company}</span></div></div></td>
      <td>${l.channel === 'LinkedIn' ? '🔗 LinkedIn' : '✉️ Email'}</td>
      <td>${badge(STAGE_BADGE[l.stage], l.stage)}</td>
      <td><div class="score"><div class="score-bar" style="width:${l.score}%"></div></div><span class="score-num">${l.score}</span></td>
    </tr>`).join('');

  return outreachHead() + outreachTabs('overview') + `
    <div class="stats" style="margin-top:22px">
      <div class="stat"><div class="label">Prospects discovered</div><div class="num">1,240</div><div class="delta">+96 today</div></div>
      <div class="stat"><div class="label">Messages sent (7d)</div><div class="num">188</div><div class="delta">LinkedIn + email</div></div>
      <div class="stat"><div class="label">Reply rate</div><div class="num">25%</div><div class="delta">+4 pts</div></div>
      <div class="stat"><div class="label">Meetings booked</div><div class="num">12</div><div class="delta">3 this week</div></div>
    </div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Pipeline</h2>
        <div class="panel-sub">How prospects move from discovery to a booked meeting.</div>
        <div class="funnel">${funnel}</div>
      </div>
      <div class="panel">
        <h2>Daily activity</h2>
        <div class="panel-sub">Within your safety limits.</div>
        <div class="kv"><span class="k">LinkedIn requests</span><span class="v">18 / ${outreach.campaign.liPerDay}</span></div>
        <div class="kv"><span class="k">Emails sent</span><span class="v">42 / ${outreach.campaign.emailPerDay}</span></div>
        <div class="kv"><span class="k">Follow-ups queued</span><span class="v">23</span></div>
        <div class="kv"><span class="k">Awaiting reply</span><span class="v">141</span></div>
      </div>
    </div>
    <div class="section-title">Latest leads</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Lead</th><th>Channel</th><th>Stage</th><th>Fit score</th></tr></thead>
      <tbody>${recent}</tbody>
    </table></div>`;
}

function tagInput(label, items, hint) {
  return `
    <div class="field">
      <label>${label}</label>
      <div class="tags-input">
        ${items.map(t => `<span class="tag-pill">${t}<span class="x">×</span></span>`).join('')}
        <input class="tag-add" placeholder="Type and press Enter…" />
      </div>
      ${hint ? `<div class="hint">${hint}</div>` : ''}
    </div>`;
}

function seg(label, options, active) {
  return `
    <div class="field"><label>${label}</label>
      <div class="seg">${options.map(o => `<button class="${o === active ? 'active' : ''}">${o}</button>`).join('')}</div>
    </div>`;
}

function outreachSetup() {
  const c = outreach.campaign;
  const integ = outreach.integrations.map(i => `
    <div class="integ-chip"><span class="dot ${i.ok ? 'ok' : 'off'}"></span><div><b>${i.name}</b><span>${i.detail}</span></div>${i.ok ? '<span class="integ-ok">✓</span>' : ''}</div>`).join('');

  return outreachHead() + outreachTabs('setup') + `
    <div class="detail-grid" style="margin-top:22px">
      <div style="display:flex;flex-direction:column;gap:18px">

        <div class="panel">
          <h2>1 · What you sell</h2>
          <div class="panel-sub">The AI uses this to write search queries and personalize every message.</div>
          <div class="field"><label>Campaign name</label><input value="${c.name}"></div>
          <div class="field"><label>Product / offer description</label><textarea rows="3">${c.product}</textarea>
            <div class="hint">Be specific about the outcome you deliver and to whom.</div></div>
        </div>

        <div class="panel">
          <h2>2 · Ideal customer profile (ICP)</h2>
          <div class="panel-sub">Who should we target? These are your search criteria.</div>
          ${tagInput('Job titles', c.titles, 'The roles you want to reach.')}
          ${tagInput('Industries', c.industries)}
          <div class="field"><label>Company size</label>
            <select><option>1–10 employees</option><option selected>11–200 employees</option><option>201–1000 employees</option><option>1000+ employees</option></select></div>
          ${tagInput('Locations', c.locations)}
          ${tagInput('Keywords (in profile / company)', c.keywords)}
          ${seg('Qualification strictness', ['Broad', 'Balanced', 'Strict'], c.strictness)}
        </div>

        <div class="panel">
          <h2>3 · Channels &amp; messaging</h2>
          <div class="panel-sub">How we reach out. The AI personalizes each message per prospect.</div>
          <div class="channel-cards">
            <div class="channel-card ${c.channels.linkedin ? 'on' : ''}">
              <div class="cc-top"><span>🔗 LinkedIn</span>
                <label class="toggle"><input type="checkbox" ${c.channels.linkedin ? 'checked' : ''}><span class="track"></span></label></div>
              <p>Connection requests + DMs</p>
            </div>
            <div class="channel-card ${c.channels.email ? 'on' : ''}">
              <div class="cc-top"><span>✉️ Email</span>
                <label class="toggle"><input type="checkbox" ${c.channels.email ? 'checked' : ''}><span class="track"></span></label></div>
              <p>Cold email + follow-ups</p>
            </div>
          </div>
          ${seg('Tone of voice', ['Friendly', 'Professional', 'Direct'], c.tone)}
          <div class="field"><label>LinkedIn connection note</label><textarea rows="2">${c.connectNote}</textarea>
            <div class="hint">Variables: <span class="var">{{first_name}}</span> <span class="var">{{company}}</span> <span class="var">{{industry}}</span> <span class="var">{{topic}}</span></div></div>
          <div class="field"><label>Email opener</label><textarea rows="3">${c.emailOpener}</textarea></div>
          <div class="field"><label>Number of follow-ups</label>
            <select><option ${c.followups===2?'selected':''}>2</option><option ${c.followups===3?'selected':''}>3</option><option ${c.followups===4?'selected':''}>4</option></select></div>
        </div>

        <div class="panel">
          <h2>4 · Safety limits</h2>
          <div class="panel-sub">Daily caps that keep your accounts safe. Recommended ranges shown.</div>
          <div class="field"><label>LinkedIn requests / day <b class="rangeval">${c.liPerDay}</b></label>
            <input type="range" min="5" max="40" value="${c.liPerDay}" class="range"><div class="hint">Recommended: 20–30</div></div>
          <div class="field"><label>Emails / day <b class="rangeval">${c.emailPerDay}</b></label>
            <input type="range" min="10" max="150" value="${c.emailPerDay}" class="range"><div class="hint">Recommended: 40–80</div></div>
        </div>
      </div>

      <div style="display:flex;flex-direction:column;gap:18px">
        <div class="panel launch-panel">
          <h2>Launch</h2>
          <div class="panel-sub">Triggers your private OpenOutreach workflow with these criteria.</div>
          <div class="kv"><span class="k">Target roles</span><span class="v">${c.titles.length}</span></div>
          <div class="kv"><span class="k">Channels</span><span class="v">${[c.channels.linkedin && 'LinkedIn', c.channels.email && 'Email'].filter(Boolean).join(' + ')}</span></div>
          <div class="kv"><span class="k">Est. new prospects / wk</span><span class="v">~250</span></div>
          <button class="btn btn-primary" style="width:100%;justify-content:center;margin-top:16px;padding:12px">🚀 Launch campaign</button>
          <button class="btn" style="width:100%;justify-content:center;margin-top:10px">Save as draft</button>
          <div class="hint" style="text-align:center;margin-top:12px">Sends a signed request to n8n → OpenOutreach.</div>
        </div>
        <div class="panel">
          <h2>Connections</h2>
          <div class="panel-sub">Managed with your agency. All set before launch.</div>
          ${integ}
        </div>
      </div>
    </div>`;
}

function outreachLeads() {
  const rows = outreach.leads.map(l => `
    <tr data-link="#/outreach/lead/${l.id}">
      <td><div class="lead-name"><span class="av-sm">${l.name.split(' ').map(x => x[0]).join('')}</span><div><b>${l.name}</b><span>${l.title}</span></div></div></td>
      <td>${l.company}</td>
      <td>${l.loc}</td>
      <td>${l.channel === 'LinkedIn' ? '🔗 LinkedIn' : '✉️ Email'}</td>
      <td>${badge(STAGE_BADGE[l.stage], l.stage)}</td>
      <td><div class="score"><div class="score-bar" style="width:${l.score}%"></div></div><span class="score-num">${l.score}</span></td>
    </tr>`).join('');
  return outreachHead() + outreachTabs('leads') + `
    <div class="table-wrap" style="margin-top:22px"><table>
      <thead><tr><th>Lead</th><th>Company</th><th>Location</th><th>Channel</th><th>Stage</th><th>Fit score</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function outreachLead(id) {
  const l = outreach.leads.find(x => x.id === id) || outreach.leads[0];
  const thread = outreach.thread.map(m => `
    <div class="msg ${m.who === 'ai' ? 'out' : 'in'}">
      <div class="msg-meta">${m.who === 'ai' ? 'AI (you)' : l.name.split(' ')[0]} · ${m.t}</div>
      <div class="bubble">${m.text}</div>
    </div>`).join('');
  return outreachHead() + outreachTabs('inbox') + `
    <div class="breadcrumb" style="margin-top:18px"><a href="#/outreach/leads">Leads</a> <span>/</span> <span>${l.name}</span></div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Conversation</h2>
        <div class="panel-sub">AI-managed thread on ${l.channel}. Jump in anytime.</div>
        <div class="thread">${thread}</div>
        <div class="composer">
          <input placeholder="Write a message or let the AI follow up…" />
          <button class="btn btn-primary btn-sm">Send</button>
        </div>
        <div class="hint" style="margin-top:10px">⚡ Next AI follow-up scheduled in 2 days if no reply.</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:18px">
        <div class="panel">
          <h2>${l.name}</h2>
          <div class="panel-sub">${l.title} · ${l.company}</div>
          <div class="kv"><span class="k">Location</span><span class="v">${l.loc}</span></div>
          <div class="kv"><span class="k">Channel</span><span class="v">${l.channel}</span></div>
          <div class="kv"><span class="k">Stage</span><span class="v">${badge(STAGE_BADGE[l.stage], l.stage)}</span></div>
          <div class="kv"><span class="k">Fit score</span><span class="v">${l.score}/100</span></div>
          <a href="#" class="btn btn-sm" style="width:100%;justify-content:center;margin-top:14px">🔗 View LinkedIn profile</a>
        </div>
        <div class="panel">
          <h2>Why qualified</h2>
          <div class="panel-sub">AI assessment.</div>
          <p style="font-size:13px;color:var(--text-soft);line-height:1.55">Strong ICP match: ${l.title} at a ${'mid-market SaaS'} company in a target region. Recently posted about scaling outbound — high intent signal.</p>
        </div>
      </div>
    </div>`;
}

function clientAutomation(slug) {
  const a = findAuto(slug);
  if (!a) return `<p>Not found. <a href="#/">Back</a></p>`;
  const fields = a.config.map(f => {
    const input = f.type === 'select'
      ? `<select>${f.options.map(o => `<option ${o === f.value ? 'selected' : ''}>${o}</option>`).join('')}</select>`
      : `<input value="${f.value}" />`;
    return `<div class="field"><label>${f.label}</label>${input}${f.hint ? `<div class="hint">${f.hint}</div>` : ''}</div>`;
  }).join('');

  const recent = runs.filter(r => r.auto === slug).slice(0, 4).map(r => `
    <div class="kv"><span class="k">${r.when}</span><span class="v">${badge(r.status)}</span></div>`).join('')
    || '<div class="kv"><span class="k">No runs yet</span></div>';

  return `
    <div class="breadcrumb"><a href="#/">Dashboard</a> <span>/</span> <span>${a.name}</span></div>
    <div class="page-head" style="display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;gap:14px;align-items:center">
        <div class="auto-icon" style="width:54px;height:54px;font-size:26px">${a.icon}</div>
        <div><h1>${a.name}</h1><p>${a.desc}</p></div>
      </div>
      <label class="toggle" style="transform:scale(1.15)">
        <input type="checkbox" ${a.enabled ? 'checked' : ''} data-toggle="${a.slug}"><span class="track"></span>
      </label>
    </div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Configuration</h2>
        <div class="panel-sub">Settings specific to your workspace. Editable anytime.</div>
        ${fields}
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary">Save changes</button>
          <button class="btn">Run a test</button>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:18px">
        <div class="panel">
          <h2>Trigger</h2>
          <div class="panel-sub">This automation runs automatically.</div>
          <div class="trigger-note"><span class="ic">⚡</span><div><b>${a.triggerLabel}</b><br>No clicks needed — it fires whenever the event happens.</div></div>
        </div>
        <div class="panel">
          <h2>Recent runs</h2>
          <div class="panel-sub">Status of the latest triggers.</div>
          ${recent}
          <a href="#/runs" class="btn btn-sm" style="margin-top:12px;width:100%;justify-content:center">View full activity</a>
        </div>
      </div>
    </div>`;
}

function runsView(isAgency) {
  const rows = runs.map(r => `
    <tr data-link="#/run/${r.id}">
      <td><span class="mono">${r.id}</span></td>
      ${isAgency ? '<td>ACME Studio</td>' : ''}
      <td><b>${r.name}</b></td>
      <td>${r.detail}</td>
      <td>${r.when}</td>
      <td>${badge(r.status)}</td>
    </tr>`).join('');
  return `
    <div class="page-head"><h1>Activity</h1><p>History of triggers${isAgency ? ' — all clients' : ''} (simple status).</p></div>
    <div class="table-wrap"><table>
      <thead><tr>
        <th>ID</th>${isAgency ? '<th>Client</th>' : ''}<th>Automation</th><th>Detail</th><th>When</th><th>Status</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function runDetail(id) {
  const r = runs.find(x => x.id === id) || runs[0];
  return `
    <div class="breadcrumb"><a href="#/runs">Activity</a> <span>/</span> <span class="mono">${r.id}</span></div>
    <div class="page-head"><h1>${r.name}</h1><p>${r.detail}</p></div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Run detail</h2>
        <div class="panel-sub">Simplified view — no technical logs on the client side.</div>
        <div class="kv"><span class="k">Status</span><span class="v">${badge(r.status)}</span></div>
        <div class="kv"><span class="k">Triggered</span><span class="v">${r.when}</span></div>
        <div class="kv"><span class="k">Source</span><span class="v">External event → n8n</span></div>
        <div class="kv"><span class="k">Duration</span><span class="v">${r.status === 'running' ? '—' : '1.8 s'}</span></div>
        <div class="kv"><span class="k">Result</span><span class="v">${r.detail}</span></div>
      </div>
      <div class="panel">
        <h2>Automation</h2>
        <div class="panel-sub">Applied settings.</div>
        <div class="pill-row"><span class="tag">${r.name}</span><span class="tag">Event-driven</span></div>
        <a href="#/automation/${r.auto}" class="btn btn-sm" style="margin-top:16px;width:100%;justify-content:center">Open automation</a>
      </div>
    </div>`;
}

function clientSettings() {
  return `
    <div class="page-head"><h1>Settings</h1><p>Profile and sign-in for your workspace.</p></div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Profile</h2><div class="panel-sub">Organization details.</div>
        <div class="field"><label>Organization name</label><input value="ACME Studio"></div>
        <div class="field"><label>Contact email</label><input value="marie@acme-studio.com"></div>
        <button class="btn btn-primary">Save changes</button>
      </div>
      <div class="panel">
        <h2>Sign-in</h2><div class="panel-sub">Account security.</div>
        <div class="trigger-note"><span class="ic">✉️</span><div><b>Magic-link sign-in</b><br>No password: you receive a sign-in link by email.</div></div>
      </div>
    </div>`;
}

// ---------------- Agency views ----------------
function agencyOverview() {
  const rows = clients.map(c => `
    <tr data-link="#/client/${c.id}">
      <td><b>${c.name}</b></td>
      <td><span class="tag">${c.plan}</span></td>
      <td>${c.active} active</td>
      <td>${c.members} member${c.members > 1 ? 's' : ''}</td>
      <td>${c.status === 'Active' ? badge('success', 'Active') : badge('queued', 'Onboarding')}</td>
    </tr>`).join('');
  return `
    <div class="page-head"><h1>Overview</h1><p>Activity across all your clients and their automations.</p></div>
    <div class="stats">
      <div class="stat"><div class="label">Clients</div><div class="num">4</div><div class="delta">+1 this month</div></div>
      <div class="stat"><div class="label">Active automations</div><div class="num">14</div><div class="delta flat">all clients</div></div>
      <div class="stat"><div class="label">Runs (24 h)</div><div class="num">312</div><div class="delta">+6%</div></div>
      <div class="stat"><div class="label">Errors (24 h)</div><div class="num">3</div><div class="delta warn">needs review</div></div>
    </div>
    <div class="section-title">Clients</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Client</th><th>Plan</th><th>Automations</th><th>Members</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function agencyClients() { return agencyOverview(); }

function agencyClientDetail(id) {
  const c = clients.find(x => x.id === id) || clients[0];
  const rows = automations.map(a => `
    <tr>
      <td><div style="display:flex;gap:10px;align-items:center"><span style="font-size:18px">${a.icon}</span><b>${a.name}</b></div></td>
      <td>${a.triggerLabel}</td>
      <td><span class="mono">…/${a.slug}/${id.slice(-4)}</span></td>
      <td><label class="toggle" onclick="event.stopPropagation()"><input type="checkbox" ${a.enabled ? 'checked' : ''}><span class="track"></span></label></td>
    </tr>`).join('');
  return `
    <div class="breadcrumb"><a href="#/clients">Clients</a> <span>/</span> <span>${c.name}</span></div>
    <div class="page-head"><h1>${c.name}</h1><p>${c.plan} plan · ${c.members} member(s). Enable and configure assigned automations.</p></div>
    <div class="panel" style="margin-bottom:18px">
      <h2>Automation assignment</h2>
      <div class="panel-sub">Choose what this client sees in their workspace. Each row has its own ingest token (maps n8n events → this client).</div>
      <div class="table-wrap" style="box-shadow:none"><table>
        <thead><tr><th>Automation</th><th>Trigger</th><th>Ingest token</th><th>Enabled</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
    </div>`;
}

function agencyCatalog() {
  const featured = `
    <tr data-link="#/outreach">
      <td><div style="display:flex;gap:10px;align-items:center"><span style="font-size:18px">🎯</span><b>Outreach Engine</b> <span class="tag" style="margin-left:4px">Interactive</span></div></td>
      <td><span class="mono">outreach-engine</span></td>
      <td>Client launches with criteria → n8n / OpenOutreach</td>
      <td>ICP + messaging + limits</td>
      <td>${badge('success', 'Published')}</td>
    </tr>`;
  const rows = featured + automations.map(a => `
    <tr data-link="#/automation/${a.slug}">
      <td><div style="display:flex;gap:10px;align-items:center"><span style="font-size:18px">${a.icon}</span><b>${a.name}</b></div></td>
      <td><span class="mono">${a.slug}</span></td>
      <td>${a.triggerLabel}</td>
      <td>${a.config.length} field(s)</td>
      <td>${badge('success', 'Published')}</td>
    </tr>`).join('');
  return `
    <div class="page-head" style="display:flex;justify-content:space-between;align-items:center">
      <div><h1>Catalog</h1><p>The automations you can assign to your clients.</p></div>
      <button class="btn btn-primary">+ New automation</button>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Name</th><th>Slug</th><th>Trigger</th><th>Config</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

// ---------------- Login (shared) ----------------
function loginView() {
  return `
  <div class="login-wrap">
    <div class="login-card">
      <div class="logo">A</div>
      <h1>Automation Portal</h1>
      <p>Sign in to access your automations.</p>
      <div class="field"><label>Work email</label><input placeholder="you@company.com" value="marie@acme-studio.com"></div>
      <button class="btn btn-primary" data-link="#/">Send me a sign-in link</button>
      <div class="magic">✉️ Passwordless sign-in — a magic link is emailed to you.</div>
    </div>
  </div>`;
}

// ---------------- Router ----------------
function render() {
  const app = $('#app');
  route = location.hash || '#/';

  if (route === '#/login') { app.innerHTML = loginView(); bind(); return; }

  let inner, shell;
  if (role === 'client') {
    if (route === '#/') inner = clientDashboard();
    else if (route === '#/outreach') inner = outreachOverview();
    else if (route === '#/outreach/setup') inner = outreachSetup();
    else if (route === '#/outreach/leads') inner = outreachLeads();
    else if (route === '#/outreach/inbox') inner = outreachLeads();
    else if (route.startsWith('#/outreach/lead/')) inner = outreachLead(route.split('/')[3]);
    else if (route.startsWith('#/automation/')) inner = clientAutomation(route.split('/')[2]);
    else if (route.startsWith('#/run/')) inner = runDetail(route.split('/')[2]);
    else if (route === '#/runs') inner = runsView(false);
    else if (route === '#/settings') inner = clientSettings();
    else inner = clientDashboard();
    shell = clientShell(inner);
  } else {
    if (route === '#/') inner = agencyOverview();
    else if (route === '#/clients') inner = agencyClients();
    else if (route.startsWith('#/client/')) inner = agencyClientDetail(route.split('/')[2]);
    else if (route === '#/catalog') inner = agencyCatalog();
    else if (route === '#/outreach') inner = outreachOverview();
    else if (route === '#/outreach/setup') inner = outreachSetup();
    else if (route === '#/outreach/leads' || route === '#/outreach/inbox') inner = outreachLeads();
    else if (route.startsWith('#/outreach/lead/')) inner = outreachLead(route.split('/')[3]);
    else if (route.startsWith('#/automation/')) inner = clientAutomation(route.split('/')[2]);
    else if (route.startsWith('#/run/')) inner = runDetail(route.split('/')[2]);
    else if (route === '#/runs') inner = runsView(true);
    else inner = agencyOverview();
    shell = agencyShell(inner);
  }
  app.innerHTML = shell;
  bind();
}

function bind() {
  document.querySelectorAll('[data-link]').forEach(el =>
    el.addEventListener('click', () => { location.hash = el.getAttribute('data-link'); }));
  document.querySelectorAll('[data-toggle]').forEach(el =>
    el.addEventListener('change', () => {
      const a = findAuto(el.getAttribute('data-toggle'));
      if (a) { a.enabled = el.checked; if (route === '#/' || route.startsWith('#/automation')) render(); }
    }));
}

// Role switch
document.querySelectorAll('.role-switch button').forEach(b =>
  b.addEventListener('click', () => {
    document.querySelectorAll('.role-switch button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    role = b.dataset.role;
    location.hash = '#/';
    render();
  }));

window.addEventListener('hashchange', render);
render();
