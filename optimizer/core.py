"""Portable form of the Echo7 fixed-prior whole-chain optimizer.

Adapted from joint_optimization.py and the chunked gradient in
joint_generic_optimization.py. See provenance.json for source hashes.
No repo imports, file reads, or mutable global dataset at import time.
"""
from __future__ import annotations
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from scipy.special import xlogy

LN2 = np.log(2.)


def entropy(p):
    return float(-xlogy(p, p).sum()/LN2)


class Chain:
    def __init__(self, data, start):
        self.data = data
        self.words = data["words"]
        if not 0 <= start < len(data["stages"]) - 1:
            raise ValueError("start must precede at least one later section")
        self.start = start
        self.stages = self.data['stages'][start:]
        self.T = len(self.stages)-1
        raw = []
        active = set()
        for t in range(start, len(self.data['stages'])-1):
            key = self.data['chain'][t]+'>'+self.data['chain'][t+1]
            edges = {(a,b) for a,b,*_ in self.data['menus']['scheduled_v22']['step_edges'][key]
                     if a != b and self.data['stages'][t+1]['counts'].get(self.words[b],0)}
            raw.append(edges)
            for a,b in edges:
                active.update((a,b))
        self.ids = np.array(sorted(active))
        self.n = len(self.ids)
        self.local = {int(g):i for i,g in enumerate(self.ids)}
        self.q_full = np.array([[s['counts'].get(w,0)/s['N'] for w in self.words] for s in self.stages])
        self.q = self.q_full[:,self.ids]
        inactive = np.ones(len(self.words),dtype=bool); inactive[self.ids] = False
        self.inactive = inactive
        self.fixed_tv = .5*np.abs(self.q_full[1:,inactive]-self.q_full[0,inactive]).sum(1)
        self.source_ids = np.flatnonzero(self.q[0]>0)
        self.prior = self.q[0,self.source_ids]
        self.all_prior = self.q_full[0,self.q_full[0]>0]
        self.h = entropy(self.all_prior)
        self.j0 = np.zeros((len(self.source_ids),self.n))
        self.j0[np.arange(len(self.source_ids)),self.source_ids] = self.prior
        self.edges=[]; self.slices=[]; offset=0
        for edges in raw:
            pairs={(self.local[a],self.local[b]) for a,b in edges}
            pairs.update((a,a) for a in range(self.n))
            a,b=np.array(sorted(pairs),dtype=np.int32).T
            indptr=np.r_[0,np.cumsum(np.bincount(a,minlength=self.n))]
            self.edges.append((a,b,indptr))
            self.slices.append(slice(offset,offset+len(a)));offset+=len(a)
        self.size=offset

    def kernels(self, theta):
        out=[]
        for sl,(a,b,indptr) in zip(self.slices,self.edges):
            z=theta[sl]
            top=np.maximum.reduceat(z,indptr[:-1])
            e=np.exp(z-top[a]); probability=e/np.bincount(a,weights=e,minlength=self.n)[a]
            out.append(sparse.csr_matrix((probability,b,indptr),shape=(self.n,self.n)))
        return out

    def theta(self, kernels):
        return np.concatenate([np.log(np.maximum(k.data,1e-8)) for k in kernels])

    def identity_theta(self, seed=0):
        rng=np.random.default_rng(seed)
        return np.concatenate([np.where(a==b,5.,-3.)+rng.normal(0,.2,len(a))
                               for a,b,_ in self.edges])

    def forward(self, kernels):
        joints=[self.j0]
        for k in kernels:
            joints.append(np.asarray(k.T @ joints[-1].T).T)
        return joints

    def value_grad(self, theta, weight, smooth=1e-7):
        ks=self.kernels(theta); joints=self.forward(ks)
        tv=[]; local=[]
        for t,j in enumerate(joints[1:]):
            delta=j.sum(0)-self.q[t+1]
            root=np.sqrt(delta*delta+smooth*smooth)
            tv.append(.5*(root-smooth).sum()+self.fixed_tv[t])
            local.append(.5/self.T*delta/root)
        last=joints[-1]; mass=last.sum(0)
        conditional=float((xlogy(mass,mass).sum()-xlogy(last,last).sum())/LN2)
        objective=float(np.mean(tv)+weight*conditional/self.h)
        g=weight/self.h/LN2*np.log(np.maximum(mass[None,:],1e-300)/np.maximum(last,1e-300))
        # Structural zeros cannot gain mass under any supported kernel sequence.
        g[last==0]=0
        grad=np.empty_like(theta)
        for t in range(self.T-1,-1,-1):
            g+=local[t][None,:]
            a,b,indptr=self.edges[t]; k=ks[t]
            edge_grad=np.empty(len(a))
            # Same gradient as the study; chunk columns for ED3 memory use.
            for lo in range(0,len(a),1024):
                block=slice(lo,lo+1024)
                edge_grad[block]=np.einsum('ij,ij->j',joints[t][:,a[block]],g[:,b[block]],optimize=False)
            center=np.bincount(a,weights=k.data*edge_grad,minlength=self.n)
            grad[self.slices[t]]=k.data*(edge_grad-center[a])
            if t:
                g=np.asarray(k @ g.T).T
        return objective,grad

    def frequency_optimum(self):
        """LP on full-chain flows gives a global mean-TV minimum on this support."""
        E=self.size; aux=self.T*self.n
        obj=np.r_[np.zeros(E),np.full(2*aux,.5/self.T)]
        rr=[];cc=[];vv=[];rhs=[]; row=0
        for t,(a,b,_) in enumerate(self.edges):
            sl=self.slices[t]; cols=np.arange(sl.start,sl.stop)
            rr.extend(row+a);cc.extend(cols);vv.extend(np.ones(len(a)))
            if t:
                pa,pb,_=self.edges[t-1]; psl=self.slices[t-1]
                rr.extend(row+pb);cc.extend(np.arange(psl.start,psl.stop));vv.extend(-np.ones(len(pb)))
                rhs.extend(np.zeros(self.n))
            else:
                rhs.extend(self.q[0])
            row+=self.n
            rr.extend(row+b);cc.extend(cols);vv.extend(np.ones(len(b)))
            idx=np.arange(self.n)
            rr.extend(row+idx);cc.extend(E+t*self.n+idx);vv.extend(-np.ones(self.n))
            rr.extend(row+idx);cc.extend(E+aux+t*self.n+idx);vv.extend(np.ones(self.n))
            rhs.extend(self.q[t+1]);row+=self.n
        A=sparse.coo_matrix((vv,(rr,cc)),shape=(row,len(obj))).tocsr()
        fit=linprog(obj,A_eq=A,b_eq=rhs,bounds=(0,None),method='highs',
                    options={'dual_feasibility_tolerance':1e-8,'primal_feasibility_tolerance':1e-8})
        if not fit.success:
            raise RuntimeError(fit.message)
        ks=[]
        for sl,(a,b,indptr) in zip(self.slices,self.edges):
            flow=fit.x[sl]; supply=np.bincount(a,weights=flow,minlength=self.n)
            p=np.divide(flow,supply[a],out=np.zeros_like(flow),where=supply[a]>0)
            p[(supply[a]==0)&(a==b)]=1
            ks.append(sparse.csr_matrix((p,b,indptr),shape=(self.n,self.n)))
        return ks,{'success':True,'mean_tv_lower_bound':float(fit.fun+self.fixed_tv.mean()),
                   'max_equality_error':float(np.max(abs(A@fit.x-rhs))),
                   'solver':fit.message,'iterations':int(fit.nit)}

    def metrics(self, ks, detailed=False):
        joints=self.forward(ks); rows=[]
        common=np.array([self.stages[0]['counts'][self.words[self.ids[a]]] >=10 for a in self.source_ids])
        common_full=np.array([self.stages[0]['counts'][w]>=10 if w in self.stages[0]['counts'] else False for w in self.words])
        common_mass=float(self.q_full[0,common_full].sum())
        common_h=entropy(self.q_full[0,common_full]/common_mass)
        common_fixed=float(self.q_full[0,self.inactive&common_full].sum())
        hapax=np.array([self.stages[0]['counts'][self.words[self.ids[a]]] ==1 for a in self.source_ids])
        hapax_full=np.array([self.stages[0]['counts'].get(w,0)==1 for w in self.words])
        hapax_mass=float(self.q_full[0,hapax_full].sum())
        hapax_h=entropy(self.q_full[0,hapax_full]/hapax_mass)
        endpoints=[]
        for t,j in enumerate(joints):
            mass=j.sum(0)
            conditional=float((xlogy(mass,mass).sum()-xlogy(j,j).sum())/LN2)
            full=self.q_full[0].copy();full[self.ids]=mass
            actual=self.q_full[t]
            tv=float(.5*np.abs(full-actual).sum())
            jc=j[common]; pc=jc.sum(0)
            c_cond=float((xlogy(pc,pc).sum()-xlogy(jc,jc).sum())/LN2/common_mass)
            jh=j[hapax]; ph=jh.sum(0)
            h_cond=float((xlogy(ph,ph).sum()-xlogy(jh,jh).sum())/LN2/hapax_mass)
            all_decoder=float(j.max(0).sum()+self.q_full[0,self.inactive].sum())
            # Ambiguity between selected labels and other values is also exposed.
            c_unknown=-sum(float(np.sum(v[v>0]*np.log2(v[v>0]/mass[v>0]))) for v in jc)/common_mass
            row={'stage':self.stages[t]['key'],'tokens':self.stages[t]['N'],
                 'frequency_mismatch':tv,'information_bits':self.h-conditional,
                 'information_retained':1-conditional/self.h,'source_entropy_bits':self.h,
                 'common_information_retained':1-c_cond/common_h,
                 'common_source_entropy_bits':common_h,
                 'common_uncertainty_with_other_values_bits':c_unknown,
                 'hapax_information_retained':1-h_cond/hapax_h,
                 'attested_mass':float(full[actual>0].sum()),'exact_id_decoding':all_decoder}
            if detailed:
                row['words']=[{'word':self.words[g],'projected_per_10000':float(10000*full[g]),
                               'observed_count':self.stages[t]['counts'].get(self.words[g],0),
                               'observed_per_10000':float(10000*actual[g])}
                              for g in np.flatnonzero((full>0)|(actual>0))]
            rows.append(row)
        if detailed:
            last=joints[-1]; mass=last.sum(0)
            for b in np.argsort(-mass):
                if mass[b]<=1e-10:continue
                source_rows=[{'word':self.words[self.ids[self.source_ids[a]]],
                              'source_count':self.stages[0]['counts'][self.words[self.ids[self.source_ids[a]]]],
                              'per_10000':float(last[a,b]*10000),
                              'fraction_of_source':float(last[a,b]/self.prior[a])}
                             for a in np.flatnonzero(last[:,b]>1e-10)]
                source_rows.sort(key=lambda x:-x['per_10000'])
                endpoints.append({'word':self.words[self.ids[b]],'projected_per_10000':float(10000*mass[b]),
                                  'observed_count':self.stages[-1]['counts'].get(self.words[self.ids[b]],0),
                                  'observed_per_10000':float(10000*self.q[-1,b]),'sources':source_rows})
            # Reduced-out identity-only labels still belong in the endpoint list.
            for b in np.flatnonzero(self.inactive & (self.q_full[0]>1e-10)):
                rate=float(10000*self.q_full[0,b]);word=self.words[b]
                endpoints.append({'word':word,'projected_per_10000':rate,
                                  'observed_count':self.stages[-1]['counts'].get(word,0),
                                  'observed_per_10000':float(10000*self.q_full[-1,b]),
                                  'sources':[{'word':word,'source_count':self.stages[0]['counts'][word],
                                              'per_10000':rate,'fraction_of_source':1.}]})
            endpoints.sort(key=lambda e:-e['projected_per_10000'])
        return {'stages':rows,'mean_frequency_mismatch':float(np.mean([r['frequency_mismatch'] for r in rows[1:]])),
                'common_start_share':common_mass,'endpoints':endpoints}

    def export_kernels(self, ks):
        return [[[int(self.ids[a]),int(self.ids[b]),float(p)] for a,b,p in zip(aa,bb,k.data) if p>0]
                for (aa,bb,_),k in zip(self.edges,ks)]
