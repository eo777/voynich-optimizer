/* Exact replay of saved source-blind kernels. No fit or route selection here. */
export function compileModel(data){
 const n=data.prior.length;
 const kernels=data.kernels.map(edges=>{
  const a=new Uint32Array(edges.length),b=new Uint32Array(edges.length),p=new Float64Array(edges.length),used=new Uint8Array(n);
  edges.forEach((e,i)=>{a[i]=e[0];b[i]=e[1];p[i]=e[2];used[e[0]]=1});
  const identity=[];for(let i=0;i<n;i++)if(!used[i])identity.push(i);
  return {a,b,p,identity};
 });
 return {...data,kernels,n};
}
export function forward(v,k){
 const out=new Float64Array(v.length);
 for(let e=0;e<k.p.length;e++)out[k.b[e]]+=v[k.a[e]]*k.p[e];
 for(const i of k.identity)out[i]=v[i];
 return out;
}
export function backward(v,k){
 const out=new Float64Array(v.length);
 for(let e=0;e<k.p.length;e++)out[k.a[e]]+=v[k.b[e]]*k.p[e];
 for(const i of k.identity)out[i]=v[i];
 return out;
}
export function traceValue(model,index){
 if(!model.prior[index])return null;
 const first=new Float64Array(model.n);first[index]=1;
 const out=[first];for(const k of model.kernels)out.push(forward(out.at(-1),k));return out;
}
export function origins(model,stage,index){
 let v=new Float64Array(model.n);v[index]=1;
 for(let t=stage-1;t>=0;t--)v=backward(v,model.kernels[t]);
 let total=0;for(let a=0;a<v.length;a++){v[a]*=model.prior[a];total+=v[a]}
 if(total)for(let a=0;a<v.length;a++)v[a]/=total;
 return v;
}
export function ranked(v,limit=6){
 return Array.from(v,(value,index)=>({value,index})).filter(x=>x.value>1e-12).sort((a,b)=>b.value-a.value).slice(0,limit);
}

