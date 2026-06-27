/* =====================================================================
   Maquette Portail Automatisations — données fictives, aucun backend.
   Spec visuelle destinée au développeur.
   ===================================================================== */

// ---------------- Mock data ----------------
const STATUS_LABEL = { success: 'Réussi', running: 'En cours', queued: 'En file', error: 'Erreur' };

const automations = [
  {
    slug: 'enrich-leads', icon: '🧲', name: 'Enrichissement de leads',
    desc: "Chaque nouveau lead du formulaire est enrichi (entreprise, poste, LinkedIn) puis poussé dans le CRM.",
    trigger: 'event', triggerLabel: 'Nouveau lead reçu (formulaire site)',
    config: [
      { label: 'Webhook source des leads', type: 'text', value: 'https://hooks.portail.app/in/enrich-leads/ax82f', hint: "URL à coller dans votre formulaire — fournie par l'agence." },
      { label: 'CRM de destination', type: 'select', options: ['HubSpot', 'Pipedrive', 'Salesforce'], value: 'HubSpot' },
      { label: 'Notifier sur Slack', type: 'select', options: ['Oui', 'Non'], value: 'Oui' },
    ],
    enabled: true, last: 'il y a 12 min', runs7: 48,
  },
  {
    slug: 'invoice-reminders', icon: '📨', name: 'Relances de paiement',
    desc: "Relance automatiquement par email les factures impayées à J+3, J+7 et J+14.",
    trigger: 'event', triggerLabel: 'Facture en retard détectée (Stripe)',
    config: [
      { label: 'Compte Stripe connecté', type: 'text', value: 'acct_1Q…7zP', hint: 'Connexion gérée par l\'agence.' },
      { label: 'Modèle d\'email', type: 'select', options: ['Courtois', 'Direct', 'Ferme'], value: 'Courtois' },
    ],
    enabled: true, last: 'il y a 2 h', runs7: 11,
  },
  {
    slug: 'slack-new-sale', icon: '🔔', name: 'Alerte nouvelle vente',
    desc: "Poste un message dans Slack à chaque paiement réussi, avec le montant et le client.",
    trigger: 'event', triggerLabel: 'Paiement réussi (Stripe)',
    config: [
      { label: 'Canal Slack', type: 'text', value: '#ventes' },
      { label: 'Montant minimum (€)', type: 'text', value: '0' },
    ],
    enabled: true, last: 'il y a 38 min', runs7: 27,
  },
  {
    slug: 'weekly-report', icon: '📊', name: 'Rapport hebdomadaire',
    desc: "Génère et envoie chaque lundi un PDF récap des ventes et leads de la semaine.",
    trigger: 'event', triggerLabel: 'Tous les lundis à 8h00',
    config: [
      { label: 'Destinataires', type: 'text', value: 'direction@client.com' },
      { label: 'Jour d\'envoi', type: 'select', options: ['Lundi', 'Vendredi'], value: 'Lundi' },
    ],
    enabled: false, last: 'jamais', runs7: 0,
  },
  {
    slug: 'review-request', icon: '⭐', name: 'Demande d\'avis client',
    desc: "Envoie une demande d'avis Google 3 jours après une commande livrée.",
    trigger: 'event', triggerLabel: 'Commande livrée',
    config: [
      { label: 'Délai (jours)', type: 'text', value: '3' },
      { label: 'Lien d\'avis', type: 'text', value: 'https://g.page/r/…/review' },
    ],
    enabled: true, last: 'il y a 5 h', runs7: 9,
  },
  {
    slug: 'lead-routing', icon: '🚦', name: 'Routage des leads',
    desc: "Assigne chaque lead entrant au bon commercial selon la zone et le secteur.",
    trigger: 'event', triggerLabel: 'Nouveau lead qualifié',
    config: [
      { label: 'Règle de répartition', type: 'select', options: ['Round-robin', 'Par zone', 'Par secteur'], value: 'Par zone' },
    ],
    enabled: true, last: 'il y a 1 h', runs7: 34,
  },
];

const runs = [
  { id: 'run_9f3a2', auto: 'enrich-leads', name: 'Enrichissement de leads', status: 'success', when: "Aujourd'hui, 14:22", detail: 'Lead « Marie Dubois » enrichi → HubSpot' },
  { id: 'run_9f2b8', auto: 'slack-new-sale', name: 'Alerte nouvelle vente', status: 'success', when: "Aujourd'hui, 13:48", detail: 'Vente 249 € → #ventes' },
  { id: 'run_9f1c1', auto: 'enrich-leads', name: 'Enrichissement de leads', status: 'running', when: "Aujourd'hui, 14:25", detail: 'Lead « Karim B. » en cours…' },
  { id: 'run_9e0d4', auto: 'invoice-reminders', name: 'Relances de paiement', status: 'success', when: "Aujourd'hui, 12:10", detail: '3 factures relancées' },
  { id: 'run_9d8e7', auto: 'lead-routing', name: 'Routage des leads', status: 'error', when: "Aujourd'hui, 11:02", detail: 'Aucun commercial dispo pour la zone « Sud »' },
  { id: 'run_9c5f0', auto: 'review-request', name: 'Demande d\'avis client', status: 'success', when: 'Hier, 18:30', detail: 'Demande envoyée à 4 clients' },
  { id: 'run_9b3a9', auto: 'enrich-leads', name: 'Enrichissement de leads', status: 'success', when: 'Hier, 16:14', detail: 'Lead « ACME Corp » enrichi' },
  { id: 'run_9a1b2', auto: 'slack-new-sale', name: 'Alerte nouvelle vente', status: 'queued', when: 'Hier, 15:50', detail: 'En attente de traitement' },
];

const clients = [
  { id: 'org_acme', name: 'ACME Studio', plan: 'Pro', active: 5, members: 3, status: 'Actif' },
  { id: 'org_bloom', name: 'Bloom & Co', plan: 'Starter', active: 2, members: 1, status: 'Actif' },
  { id: 'org_nova', name: 'Nova Immobilier', plan: 'Pro', active: 6, members: 4, status: 'Actif' },
  { id: 'org_zest', name: 'Zest Fitness', plan: 'Starter', active: 1, members: 2, status: 'Onboarding' },
];

// ---------------- State ----------------
let role = 'client';          // 'client' | 'agency'
let route = '#/';

// ---------------- Helpers ----------------
const $ = (s, r = document) => r.querySelector(s);
const badge = (status) => `<span class="badge ${status}"><span class="bd"></span>${STATUS_LABEL[status]}</span>`;
const findAuto = (slug) => automations.find(a => a.slug === slug);

function nav(items) {
  return items.map(i => i.label === null
    ? `<div class="nav-label">${i.section}</div>`
    : `<a href="${i.href}" class="${route === i.href || (i.match && route.startsWith(i.match)) ? 'active' : ''}">
         <span class="ic">${i.ic}</span>${i.label}</a>`).join('');
}

// ---------------- Shell ----------------
function clientShell(inner) {
  return `
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">A</div>
        <div><div class="name">Portail Auto</div><div class="sub">Espace client</div></div>
      </div>
      <nav class="nav">
        ${nav([
          { href: '#/', ic: '◧', label: 'Tableau de bord' },
          { href: '#/runs', ic: '≣', label: 'Exécutions', match: '#/run' },
          { href: '#/settings', ic: '⚙', label: 'Paramètres' },
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
          <button class="btn btn-sm">Aide</button>
          <button class="btn btn-sm btn-primary">+ Demander une automatisation</button>
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
        <div><div class="name">Portail Auto</div><div class="sub">Console agence</div></div>
      </div>
      <nav class="nav">
        ${nav([
          { href: '#/', ic: '◧', label: 'Vue d\'ensemble' },
          { href: '#/clients', ic: '👥', label: 'Clients', match: '#/client' },
          { href: '#/catalog', ic: '⚡', label: 'Catalogue', match: '#/catalog' },
          { href: '#/runs', ic: '≣', label: 'Exécutions' },
        ])}
      </nav>
      <div class="sidebar-foot">
        <div class="userchip"><div class="av">LF</div>
          <div class="meta"><b>L. Fournier</b><span>Agence · Owner</span></div></div>
      </div>
    </aside>
    <div class="main">
      <div class="topbar">
        <div class="org"><span class="dot"></span> Console agence — 4 clients</div>
        <div class="actions">
          <button class="btn btn-sm btn-primary">+ Nouveau client</button>
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
        ${a.enabled ? badge('success').replace('Réussi', 'Active') : '<span class="badge muted"><span class="bd"></span>Inactive</span>'}
        <span class="last">Dernier : ${a.last}</span>
      </div>
    </div>`).join('');

  return `
    <div class="page-head">
      <h1>Bonjour Marie 👋</h1>
      <p>Voici les automatisations actives sur votre espace ACME Studio.</p>
    </div>
    <div class="stats">
      <div class="stat"><div class="label">Automatisations actives</div><div class="num">${active}</div><div class="delta">sur ${automations.length} disponibles</div></div>
      <div class="stat"><div class="label">Exécutions (7 j)</div><div class="num">129</div><div class="delta">+18% vs sem. préc.</div></div>
      <div class="stat"><div class="label">Réussite</div><div class="num">98,4%</div><div class="delta">2 erreurs</div></div>
      <div class="stat"><div class="label">Temps gagné estimé</div><div class="num">~6 h</div><div class="delta">cette semaine</div></div>
    </div>
    <div class="section-title">Vos automatisations</div>
    <div class="grid">${cards}</div>`;
}

function clientAutomation(slug) {
  const a = findAuto(slug);
  if (!a) return `<p>Introuvable. <a href="#/">Retour</a></p>`;
  const fields = a.config.map(f => {
    const input = f.type === 'select'
      ? `<select>${f.options.map(o => `<option ${o === f.value ? 'selected' : ''}>${o}</option>`).join('')}</select>`
      : `<input value="${f.value}" />`;
    return `<div class="field"><label>${f.label}</label>${input}${f.hint ? `<div class="hint">${f.hint}</div>` : ''}</div>`;
  }).join('');

  const recent = runs.filter(r => r.auto === slug).slice(0, 4).map(r => `
    <div class="kv"><span class="k">${r.when}</span><span class="v">${badge(r.status)}</span></div>`).join('')
    || '<div class="kv"><span class="k">Aucune exécution pour l\'instant</span></div>';

  return `
    <div class="breadcrumb"><a href="#/">Tableau de bord</a> <span>/</span> <span>${a.name}</span></div>
    <div class="page-head" style="display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;gap:14px;align-items:center">
        <div class="auto-icon" style="width:52px;height:52px;font-size:25px">${a.icon}</div>
        <div><h1>${a.name}</h1><p>${a.desc}</p></div>
      </div>
      <label class="toggle" style="transform:scale(1.15)">
        <input type="checkbox" ${a.enabled ? 'checked' : ''} data-toggle="${a.slug}"><span class="track"></span>
      </label>
    </div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Configuration</h2>
        <div class="panel-sub">Réglages propres à votre espace. Modifiables à tout moment.</div>
        ${fields}
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary">Enregistrer</button>
          <button class="btn">Lancer un test</button>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:18px">
        <div class="panel">
          <h2>Déclencheur</h2>
          <div class="panel-sub">Cette automatisation se lance automatiquement.</div>
          <div class="trigger-note"><span class="ic">⚡</span><div><b>${a.triggerLabel}</b><br>Aucun clic nécessaire — elle tourne dès qu'un événement survient.</div></div>
        </div>
        <div class="panel">
          <h2>Dernières exécutions</h2>
          <div class="panel-sub">Statut des derniers déclenchements.</div>
          ${recent}
          <a href="#/runs" class="btn btn-sm" style="margin-top:12px;width:100%;justify-content:center">Voir tout l'historique</a>
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
    <div class="page-head"><h1>Exécutions</h1><p>Historique des déclenchements${isAgency ? ' — tous clients' : ''} (statut simple).</p></div>
    <div class="table-wrap"><table>
      <thead><tr>
        <th>ID</th>${isAgency ? '<th>Client</th>' : ''}<th>Automatisation</th><th>Détail</th><th>Quand</th><th>Statut</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function runDetail(id) {
  const r = runs.find(x => x.id === id) || runs[0];
  return `
    <div class="breadcrumb"><a href="#/runs">Exécutions</a> <span>/</span> <span class="mono">${r.id}</span></div>
    <div class="page-head"><h1>${r.name}</h1><p>${r.detail}</p></div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Détail de l'exécution</h2>
        <div class="panel-sub">Vue simplifiée — pas de logs techniques côté client.</div>
        <div class="kv"><span class="k">Statut</span><span class="v">${badge(r.status)}</span></div>
        <div class="kv"><span class="k">Déclenché</span><span class="v">${r.when}</span></div>
        <div class="kv"><span class="k">Source</span><span class="v">Événement externe → n8n</span></div>
        <div class="kv"><span class="k">Durée</span><span class="v">${r.status === 'running' ? '—' : '1,8 s'}</span></div>
        <div class="kv"><span class="k">Résultat</span><span class="v">${r.detail}</span></div>
      </div>
      <div class="panel">
        <h2>Automatisation</h2>
        <div class="panel-sub">Réglages appliqués.</div>
        <div class="pill-row"><span class="tag">${r.name}</span><span class="tag">Événementiel</span></div>
        <a href="#/automation/${r.auto}" class="btn btn-sm" style="margin-top:16px;width:100%;justify-content:center">Ouvrir l'automatisation</a>
      </div>
    </div>`;
}

function clientSettings() {
  return `
    <div class="page-head"><h1>Paramètres</h1><p>Profil et connexion de votre espace.</p></div>
    <div class="detail-grid">
      <div class="panel">
        <h2>Profil</h2><div class="panel-sub">Informations de l'organisation.</div>
        <div class="field"><label>Nom de l'organisation</label><input value="ACME Studio"></div>
        <div class="field"><label>Email de contact</label><input value="marie@acme-studio.com"></div>
        <button class="btn btn-primary">Enregistrer</button>
      </div>
      <div class="panel">
        <h2>Connexion</h2><div class="panel-sub">Sécurité du compte.</div>
        <div class="trigger-note"><span class="ic">✉️</span><div><b>Connexion par lien magique</b><br>Pas de mot de passe : vous recevez un lien de connexion par email.</div></div>
      </div>
    </div>`;
}

// ---------------- Agency views ----------------
function agencyOverview() {
  const rows = clients.map(c => `
    <tr data-link="#/client/${c.id}">
      <td><b>${c.name}</b></td>
      <td><span class="tag">${c.plan}</span></td>
      <td>${c.active} active${c.active > 1 ? 's' : ''}</td>
      <td>${c.members} membre${c.members > 1 ? 's' : ''}</td>
      <td>${c.status === 'Actif' ? badge('success').replace('Réussi', 'Actif') : '<span class="badge queued"><span class="bd"></span>Onboarding</span>'}</td>
    </tr>`).join('');
  return `
    <div class="page-head"><h1>Vue d'ensemble</h1><p>Activité de tous vos clients et de leurs automatisations.</p></div>
    <div class="stats">
      <div class="stat"><div class="label">Clients</div><div class="num">4</div><div class="delta">+1 ce mois</div></div>
      <div class="stat"><div class="label">Automatisations actives</div><div class="num">14</div><div class="delta">tous clients</div></div>
      <div class="stat"><div class="label">Exécutions (24 h)</div><div class="num">312</div><div class="delta">+6%</div></div>
      <div class="stat"><div class="label">Erreurs (24 h)</div><div class="num">3</div><div class="delta" style="color:var(--red)">à vérifier</div></div>
    </div>
    <div class="section-title">Clients</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Client</th><th>Plan</th><th>Automatisations</th><th>Membres</th><th>Statut</th></tr></thead>
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
    <div class="page-head"><h1>${c.name}</h1><p>Plan ${c.plan} · ${c.members} membre(s). Activez et configurez les automatisations attribuées.</p></div>
    <div class="panel" style="margin-bottom:18px">
      <h2>Attribution des automatisations</h2>
      <div class="panel-sub">Choisissez ce que ce client voit dans son espace. Chaque ligne a son propre jeton d'ingestion (rattachement n8n → client).</div>
      <div class="table-wrap" style="box-shadow:none"><table>
        <thead><tr><th>Automatisation</th><th>Déclencheur</th><th>Jeton d'ingestion</th><th>Activée</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
    </div>`;
}

function agencyCatalog() {
  const rows = automations.map(a => `
    <tr data-link="#/automation/${a.slug}">
      <td><div style="display:flex;gap:10px;align-items:center"><span style="font-size:18px">${a.icon}</span><b>${a.name}</b></div></td>
      <td><span class="mono">${a.slug}</span></td>
      <td>${a.triggerLabel}</td>
      <td>${a.config.length} champ(s)</td>
      <td>${badge('success').replace('Réussi', 'Publiée')}</td>
    </tr>`).join('');
  return `
    <div class="page-head" style="display:flex;justify-content:space-between;align-items:center">
      <div><h1>Catalogue</h1><p>Les automatisations que vous pouvez attribuer à vos clients.</p></div>
      <button class="btn btn-primary">+ Nouvelle automatisation</button>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Nom</th><th>Slug</th><th>Déclencheur</th><th>Config</th><th>Statut</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

// ---------------- Login (shared) ----------------
function loginView() {
  return `
  <div class="login-wrap">
    <div class="login-card">
      <div class="logo">A</div>
      <h1>Portail Automatisations</h1>
      <p>Connectez-vous pour accéder à vos automatisations.</p>
      <div class="field"><label>Email professionnel</label><input placeholder="vous@entreprise.com" value="marie@acme-studio.com"></div>
      <button class="btn btn-primary" data-link="#/">Recevoir mon lien de connexion</button>
      <div class="magic">✉️ Connexion sans mot de passe — un lien magique vous est envoyé par email.</div>
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
