const elList=document.getElementById('list');const elQ=document.getElementById('q');const elCount=document.getElementById('count');
async function load(){try{const r=await fetch('data/projects.json',{cache:'no-store'});const items=await r.json();items.sort((a,b)=>{const dateA=new Date(a.datetime||a.published||0);const dateB=new Date(b.datetime||b.published||0);return dateB-dateA});render(items)}catch{elList.innerHTML=`<p style="color:#9a9a9a">No data yet. The scheduler will populate <code>docs/data/projects.json</code>.</p>`}}
function card(item){const el=document.createElement('article');el.className='card '+getShadeClass(item.source);el.innerHTML=`
<h2 class="title">${escapeHTML(item.title)}</h2>
<div class="meta"><span>${new Date(item.datetime||item.published||Date.now()).toLocaleString()}</span><span>${(item.hash||'').slice(0,8)}</span><a class="source" href="${escapeAttr(item.source||'#')}" target="_blank" rel="noopener">source</a></div>
<p class="desc">${escapeHTML(item.description||'')}</p>
`;el.addEventListener('pointermove',e=>{el.style.setProperty('--mx',`${e.offsetX}px`);el.style.setProperty('--my',`${e.offsetY}px`)});return el}
function render(items){window.__items=items;applyFilter()}
function applyFilter(){const q=(elQ.value||'').toLowerCase();const items=(window.__items||[]).filter(it=>{const blob=`${it.title} ${it.description}`.toLowerCase();return !q||blob.includes(q)});elList.innerHTML='';items.forEach(it=>elList.appendChild(card(it)));elCount.textContent=`${items.length} micro actions`;elList.setAttribute('aria-busy','false')}
function escapeHTML(s){return (s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function escapeAttr(s){return String(s||'').replace(/"/g,'%22')}
function getShadeClass(url){if(!url)return'shade-3';try{const domain=new URL(url).hostname.toLowerCase();if(domain.includes('bip.lesnica.pl'))return'shade-1';if(domain==='lesnica.pl')return'shade-2';if(domain.includes('strzelce360'))return'shade-3';if(domain.includes('workers.dev'))return'shade-4';if(domain.includes('nto.pl'))return'shade-5';return'shade-3'}catch{return'shade-3'}}
elQ.addEventListener('input',applyFilter);load();
