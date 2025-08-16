const elList=document.getElementById('list');const elQ=document.getElementById('q');const elCount=document.getElementById('count');
async function load(){try{const r=await fetch('data/projects.json',{cache:'no-store'});const items=await r.json();items.sort((a,b)=>{const dateA=new Date(a.datetime||a.published||0);const dateB=new Date(b.datetime||b.published||0);return dateB-dateA});render(items)}catch{elList.innerHTML=`<p style="color:#9a9a9a">No data yet. The scheduler will populate <code>docs/data/projects.json</code>.</p>`}}
function card(item){const el=document.createElement('article');el.className='card';el.innerHTML=`
<div class="row">
  <h2 class="title">${escapeHTML(item.title)}</h2>
  <a class="source" href="${escapeAttr(item.source||'#')}" target="_blank" rel="noopener">source</a>
</div>
<div class="meta"><span>${new Date(item.datetime||item.published||Date.now()).toLocaleString()}</span><span>${(item.hash||'').slice(0,8)}</span></div>
<p class="desc">${escapeHTML(item.description||'')}</p>
<div class="btn" aria-label="toggle more">expand</div>
`;el.addEventListener('pointermove',e=>{el.style.setProperty('--mx',`${e.offsetX}px`);el.style.setProperty('--my',`${e.offsetY}px`)});el.querySelector('.btn').addEventListener('click',()=>el.classList.toggle('expanded'));return el}
function render(items){window.__items=items;applyFilter()}
function applyFilter(){const q=(elQ.value||'').toLowerCase();const items=(window.__items||[]).filter(it=>{const blob=`${it.title} ${it.description}`.toLowerCase();return !q||blob.includes(q)});elList.innerHTML='';items.forEach(it=>elList.appendChild(card(it)));elCount.textContent=`${items.length} micro actions`;elList.setAttribute('aria-busy','false')}
function escapeHTML(s){return (s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function escapeAttr(s){return String(s||'').replace(/"/g,'%22')}
elQ.addEventListener('input',applyFilter);load();
