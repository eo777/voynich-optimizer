"""Original rule-guided seeds and continuing family KL preference.

Only existing named routes are favored. This module does not infer rules or
meanings; 50%/95% templates and the initial-class lock are stated assumptions.
"""
import re
import numpy as np
from scipy import sparse

def initial_class(word):
    return word[:2] if word.startswith(('ch','sh')) else 'other'


def import_kernels(c,record):
    result=[]
    for exported,(a,b,ptr) in zip(record['kernels'],c.edges):
        lookup={(x,y):p for x,y,p in exported}
        p=np.array([lookup.get((int(c.ids[x]),int(c.ids[y])),0.) for x,y in zip(a,b)])
        total=np.bincount(a,weights=p,minlength=c.n)
        p[(total[a]==0)&(a==b)]=1
        total=np.bincount(a,weights=p,minlength=c.n)
        p/=total[a]
        result.append(sparse.csr_matrix((p,b,ptr),shape=(c.n,c.n)))
    return result

def guided_seed(c,reference,changed_share):
    """Prefer S1 early, B1/C1 later, and retention of their e-dy results.

    Only existing, forward, observed-destination edges qualify. Plain ch/sh
    terminal-liquid families with any unchanged prefix are included. 95/50%
    are starting guesses, not estimated historical application frequencies.
    """
    kernels=import_kernels(c,reference);rows=[]
    for t,(k,(aa,bb,ptr)) in enumerate(zip(kernels,c.edges)):
        key=c.stages[t]['key']+'>'+c.stages[t+1]['key']
        edge_labels={}
        for a,b,degree,labels,direction in c.data['menus']['scheduled_v22']['step_edges'][key]:
            if direction>0:
                edge_labels.setdefault((a,b),set()).update(c.data['labels'][i] for i in labels)
        early=t<2
        for a in range(c.n):
            word=c.words[c.ids[a]]
            liquid=re.fullmatch(r'(.*(?:ch|sh))(e*)o([lr])',word)
            outcome=re.fullmatch(r'.*(?:ch|sh)e+dy',word)
            if not liquid and not outcome:continue
            sl=slice(ptr[a],ptr[a+1]);dest=bb[sl];preferred=[]
            if liquid:
                prefix,es,lr=liquid.groups()
                desired=(prefix+'eo'+lr) if early and not es else (prefix+(es or 'e')+'dy' if not early else None)
                for pos,b in enumerate(dest):
                    if c.words[c.ids[b]]!=desired:continue
                    tags=edge_labels.get((int(c.ids[a]),int(c.ids[b])),set())
                    valid=bool(tags&{'S1','C1.1'}) if early else bool(tags&{'B1','C1.2'} or any(x.startswith('C1 (via ') for x in tags))
                    if valid:preferred.append(pos)
            p=np.full(len(dest),1e-6)
            identity=np.flatnonzero(dest==a)[0]
            if preferred:
                p[identity]+=1-changed_share
                p[preferred]+=changed_share/len(preferred)
            else:p[identity]+=1
            p/=p.sum();k.data[sl]=p
            rows.append({'step':key,'word':word,'preferred':[c.words[c.ids[dest[i]]] for i in preferred] or [word]})
    return kernels,rows

def actual_objective(c,k,weight):
    m=c.metrics(k)
    return m['mean_frequency_mismatch']+weight*(1-m['stages'][-1]['information_retained'])


def focus(c,ks):
    joints=c.forward(ks);out={}
    for word in ['chol','chor','shol','shor','cheol','sheol']:
        gi=c.words.index(word);local=c.local.get(gi)
        if local not in c.source_ids:continue
        a=int(np.flatnonzero(c.source_ids==local)[0]);prior=c.prior[a]
        rows=[]
        for t,j in enumerate(joints):
            v=j[a]/prior
            rows.append({'stage':c.stages[t]['key'],
                         'destinations':[{'word':c.words[c.ids[b]],'fraction':float(v[b]),
                                          'projected_per_10000':float(j[:,b].sum()*10000),
                                          'observed_count':c.stages[t]['counts'].get(c.words[c.ids[b]],0),
                                          'observed_per_10000':float(c.q[t,b]*10000)}
                                         for b in np.argsort(-v) if v[b]>1e-7],
                         'to_chedy':float(v[c.local[c.words.index('chedy')]]),
                         'to_shedy':float(v[c.local[c.words.index('shedy')]]),
                         'opposite_initial_share':float(sum(v[b] for b in range(c.n) if initial_class(c.words[c.ids[b]]) in ('ch','sh') and initial_class(c.words[c.ids[b]])!=initial_class(word)))})
        out[word]=rows
    return out

class BiasedObjective:
    def __init__(self,c,reference,eta):
        self.c=c;self.eta=eta
        early,rows=guided_seed(c,reference,.5)
        later,_=guided_seed(c,reference,.95)
        self.template=[k.copy() for k in early[:2]+later[2:]]
        by_step={}
        for row in rows:by_step.setdefault(row['step'],set()).add(row['word'])
        self.mask=[]
        for t in range(c.T):
            key=c.stages[t]['key']+'>'+c.stages[t+1]['key']
            self.mask.append(np.array([c.words[g] in by_step.get(key,set()) for g in c.ids]))
        self.starting_family_mass=float(c.q[0,self.mask[0]].sum())
        self.scale=1/(c.T*self.starting_family_mass)

    def penalty(self,ks,gradient=False):
        c=self.c;mass=[c.q[0].copy()]
        for k in ks:mass.append(np.asarray(k.T@mass[-1]).ravel())
        row_costs=[];edge_logs=[];value=0.
        for t,(k,r,(a,b,ptr)) in enumerate(zip(ks,self.template,c.edges)):
            log=np.log(np.maximum(k.data,1e-300)/r.data)*self.mask[t][a]
            row=np.bincount(a,weights=k.data*log,minlength=c.n)
            value+=float(mass[t]@row)*self.scale
            row_costs.append(row);edge_logs.append(log)
        if not gradient:return value
        adj=np.zeros(c.n);grad=np.empty(c.size)
        for t in range(c.T-1,-1,-1):
            a,b,ptr=c.edges[t];k=ks[t]
            edge=mass[t][a]*(adj[b]+self.scale*(edge_logs[t]+self.mask[t][a]))
            center=np.bincount(a,weights=k.data*edge,minlength=c.n)
            grad[c.slices[t]]=k.data*(edge-center[a])
            adj=np.asarray(k@adj).ravel()+self.scale*row_costs[t]
        return value,grad

    def value_grad(self,theta,weight):
        f,g=self.c.value_grad(theta,weight)
        p,pg=self.penalty(self.c.kernels(theta),True)
        return f+self.eta*p,g+self.eta*pg

    def actual(self,ks,weight):
        return actual_objective(self.c,ks,weight)+self.eta*self.penalty(ks)
