import {compileModel,traceValue,origins,ranked} from './joint_word_math.mjs';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>v>0&&v<.0005?'&lt;0.1%':(100*v).toFixed(1)+'%',rate=v=>v>0&&v<.000005?'&lt;0.1':(10000*v).toFixed(1);
const displayRank=(v,limit=6)=>{const all=ranked(v,limit),visible=all.filter(x=>x.value>=.0005);return visible.length?visible:all.slice(0,1)};

export async function mountWordExplorer(host){
 const response=await fetch('joint_word_explorer_manifest.json');if(!response.ok)throw Error('Word-view data could not be loaded.');
 const manifest=await response.json(),words=manifest.words,index=new Map(words.map((w,i)=>[w,i]));
 const params=new URLSearchParams(location.search),initialWord=params.get('word')||'chol';
 const initialModel=manifest.models.some(m=>m.id===params.get('condition'))?params.get('condition'):manifest.default;
 host.innerHTML='<h3>Inspect a specific word</h3><p>Choose a spelling and a fitted model. All sections appear together below. The first table inspects that spelling; the second follows its original assigned value through spelling changes.</p>'+
  '<div class="controls"><div><label for="joint-word">Voynich word</label><input id="joint-word" list="joint-word-list" value="'+esc(initialWord)+'" autocomplete="off" spellcheck="false"><datalist id="joint-word-list">'+words.map(w=>'<option value="'+esc(w)+'">').join('')+'</datalist></div>'+
  '<div style="flex:2"><label for="joint-condition">Fitted model</label><select id="joint-condition">'+manifest.models.map(m=>'<option value="'+esc(m.id)+'"'+(m.id===initialModel?' selected':'')+'>'+esc(m.label)+'</option>').join('')+'</select></div></div>'+
  '<p class="quiet">Examples: '+['chol','chor','cheol','chedy','ol','daiin'].map(w=>'<button type="button" class="destination-button" data-word="'+w+'">'+w+'</button>').join(' · ')+'</p>'+
  '<p id="joint-word-status" class="quiet" role="status" aria-live="polite"></p><div id="joint-word-output"></div>';
 const input=host.querySelector('#joint-word'),select=host.querySelector('#joint-condition'),status=host.querySelector('#joint-word-status'),output=host.querySelector('#joint-word-output');
 let cached=null,pending=null,ticket=0,timer;
 async function modelFor(id){
  if(cached?.id===id)return cached;
  if(pending?.id===id)return pending.promise;
  const meta=manifest.models.find(m=>m.id===id);
  const promise=fetch(meta.file).then(r=>{if(!r.ok)throw Error('This model could not be loaded.');return r.json()}).then(data=>compileModel(data));
  pending={id,promise};const model=await promise;cached=model;return model;
 }
 async function render(){
  const request=++ticket,word=input.value.trim(),a=index.get(word),id=select.value;
  if(a===undefined){status.textContent='Enter an exact spelling or choose a suggestion.';output.innerHTML='';output.removeAttribute('aria-busy');return}
  status.textContent='Loading the saved model and tracing '+word+'…';output.setAttribute('aria-busy','true');
  try{
   const m=await modelFor(id);if(request!==ticket)return;
   const trace=traceValue(m,a),originCache=new Map();
   const originAt=(t,b)=>{const key=t+':'+b;if(!originCache.has(key))originCache.set(key,origins(m,t,b));return originCache.get(key)};
   const originText=(t,b)=>{
    if(m.stages[t].projected[b]>0&&m.stages[t].projected[b]<.000005)return 'Negligible projected usage (below 0.1 per 10,000)';
    const top=displayRank(originAt(t,b),4),shown=top.reduce((s,x)=>s+x.value,0);
    return top.length?top.map(x=>'<span class="word-small">'+esc(words[x.index])+'</span> '+pct(x.value)).join(', ')+(shown<1-1e-7?' · '+pct(1-shown)+' other values':''):'No projected arrivals';
   };
   const start=m.stages[0],last=m.stages.at(-1),count=start.counts[a];
   let html='<div class="rule"><strong>'+esc(word)+'</strong> occurs '+count+' time'+(count===1?'':'s')+' in starting section '+start.key+' ('+start.tokens.toLocaleString()+' tokens). '+
    (count?'It carries '+pct(m.prior[a])+' of the fixed starting weight.':'It has no separately assigned starting value in this model; its spelling can still receive other values later.')+
    '<br><span class="quiet">Selected model: '+esc(m.label)+'. Whole-model average frequency mismatch '+pct(m.mean_frequency_mismatch)+'; final information retained '+pct(m.information_retained)+'. These are model-wide scores, not scores for this word.</span></div>';
   html+='<h4>Usage and origins at the spelling <span class="word-small">'+esc(word)+'</span></h4><p class="quiet">Observed counts come from the manuscript. Projected usage adds every starting value arriving at this spelling. Origin percentages describe that projected mixture.</p>'+
    '<div class="tablewrap"><table aria-label="Selected spelling usage and origins"><thead><tr><th>Section</th><th class="num">Observed count<br>/ section total</th><th class="num">Observed<br>per 10,000</th><th class="num">Projected<br>per 10,000</th><th>Original values at this spelling</th></tr></thead><tbody>'+
    m.stages.map((s,t)=>'<tr><td>'+s.key+'</td><td class="num">'+s.counts[a]+' / '+s.tokens.toLocaleString()+'</td><td class="num">'+rate(s.counts[a]/s.tokens)+'</td><td class="num">'+rate(s.projected[a])+'</td><td>'+originText(t,a)+'</td></tr>').join('')+'</tbody></table></div>';
   if(trace){
    html+='<h4>Where the original <span class="word-small">'+esc(word)+'</span> value travels</h4><p class="quiet">A destination’s share is the fraction of this original value arriving there. Its projected usage includes all sources, so it can be checked against the observed rate. Up to six largest branches are shown per section; tiny branches are combined in the stated remainder.</p>'+
     '<div class="tablewrap"><table aria-label="Selected original value through every section"><thead><tr><th>Section</th><th>Destination</th><th class="num">Share of<br>'+esc(word)+' value</th><th class="num">Projected<br>per 10,000</th><th class="num">Observed rate<br>(count)</th><th>Original values sharing this output</th></tr></thead><tbody>';
    m.stages.forEach((s,t)=>{
     const top=displayRank(trace[t]),shown=top.reduce((sum,x)=>sum+x.value,0);
     html+=top.map((x,i)=>'<tr><td>'+(i?'':s.key)+'</td><td class="word-small">'+esc(words[x.index])+'</td><td class="num">'+pct(x.value)+'</td><td class="num">'+rate(s.projected[x.index])+'</td><td class="num">'+rate(s.counts[x.index]/s.tokens)+' ('+s.counts[x.index]+')</td><td>'+originText(t,x.index)+'</td></tr>').join('');
     if(shown<1-1e-7)html+='<tr><td></td><td colspan="5" class="quiet">'+pct(1-shown)+' of this value is on smaller branches.</td></tr>';
    });
    html+='</tbody></table></div>';
   }
   html+='<p class="quiet">The saved fitted probabilities are replayed exactly; choosing a word does not refit the model. Origin mixtures use all starting values, including hapaxes. These paths are candidate transformations, not identified historical meanings.</p>';
   output.innerHTML=html;output.removeAttribute('aria-busy');status.textContent='Showing '+word+' across '+m.stages.length+' sections.';
   const url=new URL(location.href);url.searchParams.set('word',word);url.searchParams.set('condition',id);history.replaceState(null,'',url);
   if(location.hash==='#word-explorer'&&!host.dataset.positioned){host.scrollIntoView({block:'start'});host.dataset.positioned='1'}
  }catch(e){if(request===ticket){status.textContent=e.message;output.innerHTML='';output.removeAttribute('aria-busy')}}
 }
 input.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(render,180)});
 input.addEventListener('change',()=>{clearTimeout(timer);render()});
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){clearTimeout(timer);render()}});
 select.addEventListener('change',render);
 host.querySelectorAll('[data-word]').forEach(button=>button.addEventListener('click',()=>{input.value=button.dataset.word;render()}));
 await render();
}

