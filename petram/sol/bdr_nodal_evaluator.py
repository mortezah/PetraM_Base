'''
   BdrNodalEvaluator:
      a thing to evaluate solution on a boundary
'''
import numpy as np
import parser
import weakref
import six

from weakref import WeakKeyDictionary as WKD
from weakref import WeakValueDictionary as WVD


from petram.mfem_config import use_parallel
if use_parallel:
    import mfem.par as mfem
else:
    import mfem.ser as mfem

from petram.sol.evaluator_agent import EvaluatorAgent


def process_iverts2nodals(mesh, iverts):
    ''' 
    collect data to evalutate nodal values of mesh
    at iverts
    '''
    # we dont want to process the same vert many times.
        # so first we take a unique set...
    iverts_f, iverts_inv = np.unique(iverts.flatten(),
                                        return_inverse = True)
    iverts_inv = iverts_inv.reshape(iverts.shape)

    # then get unique set of elements relating to the verts.
    vert2el = mesh.GetVertexToElementTable()

    ieles = np.hstack([vert2el.GetRowList(i) for i in iverts_f])
    ieles = np.unique(ieles)

    # map from element -> (element's vert index, ivert_f index)
    elvert2facevert = [None]*len(ieles)
    elvertloc = [None]*len(ieles)
    elattr = [None]*len(ieles)

    wverts = np.zeros(len(iverts_f))
    for kk, iel in enumerate(ieles):
        elvert2facevert[kk] = []
        elvertloc[kk] = []
        elattr[kk] = mesh.GetAttribute(iel)
        elverts = mesh.GetElement(iel).GetVerticesArray()
        for k, elvert in enumerate(elverts):
            idx = np.searchsorted(iverts_f, elvert)
            if idx == len(iverts_f): continue ## not found   
            if iverts_f[idx] != elvert: continue ## not found
            elvert2facevert[kk].append((k, idx))
            elvertloc[kk].append(mesh.GetVertexArray(elvert))
            wverts[idx] = wverts[idx]+1

    # idx of element needs to be evaluated
    
    return {'ieles': np.array(ieles),
            'elvert2facevert': elvert2facevert,
            'locs': np.stack([mesh.GetVertexArray(k) for k in iverts_f]),
            'elvertloc': elvertloc,
            'elattr': np.array(elattr),
            'iverts_inv': iverts_inv,
            'iverts_f' : iverts_f,
            'wverts' : wverts}

def edge_detect(index):
    print("edge_detect", index.shape)
    store = []
    def check_pair(store, a, b):
        a1 = min(a,b)
        b1 = max(a,b)
        p = (a1, b1)
        if p in store: store.remove(p)
        else: store.append(p)
        return store
        
    for iv in index:
        store = check_pair(store, iv[0], iv[1])
        store = check_pair(store, iv[0], iv[2])
        store = check_pair(store, iv[1], iv[2])        
    ret = np.vstack(store)
    return  ret 

def eval_at_nodals(obj, expr, solvars, phys):
    '''
    evaluate nodal valus based on preproceessed 
    geometry data

    to be done : obj should be replaced by a dictionary
    '''

    from petram.helper.variables import Variable, var_g
    
    if len(obj.iverts) == 0: return None
    variables = []
    st = parser.expr(expr)
    code= st.compile('<string>')
    names = code.co_names

    g = {}
    #print solvars.keys()
    #print phys._global_ns.keys()
    for key in phys._global_ns.keys():
       g[key] = phys._global_ns[key]
    for key in solvars.keys():
       g[key] = solvars[key]

    ll_name = []
    ll_value = []
    var_g2 = var_g.copy()

    for n in names:
       if (n in g and isinstance(g[n], Variable)):
           if not g[n] in obj.knowns:
              obj.knowns[g[n]] = (
                  g[n].nodal_values(iele = obj.ieles,
                                    ibele = obj.ibeles,
                                    elattr = obj.elattr, 
                                    el2v = obj.elvert2facevert,
                                    locs  = obj.locs,
                                    elvertloc = obj.elvertloc,
                                    wverts = obj.wverts,
                                    mesh = obj.mesh(),
                                    iverts_f = obj.iverts_f,
                                    g  = g))
           #ll[n] = self.knowns[g[n]]
           ll_name.append(n)
           ll_value.append(obj.knowns[g[n]])
       elif (n in g):
           var_g2[n] = g[n]

    val = np.array([eval(code, var_g2, dict(zip(ll_name, v)))
                    for v in zip(*ll_value)])
    return val

class BdrNodalEvaluator(EvaluatorAgent):
    def __init__(self, battrs):
        super(BdrNodalEvaluator, self).__init__()
        self.battrs = battrs
        
    def preprocess_geometry(self, battrs):
        mesh = self.mesh()
        #print 'preprocess_geom',  mesh, battrs
        self.battrs = battrs        
        self.knowns = WKD()
        self.iverts = []
        
        x = [mesh.GetBdrArray(battr) for battr in battrs]
        if np.sum([len(xx) for xx in x]) == 0: return
        
        ibdrs = np.hstack(x).astype(int).flatten()
        self.ibeles = np.array(ibdrs)
        
        iverts = np.stack([mesh.GetBdrElement(i).GetVerticesArray()
                           for i in ibdrs])
        self.iverts = iverts
        if len(self.iverts) == 0: return

        data = process_iverts2nodals(mesh, iverts)
        for k in six.iterkeys(data):
            setattr(self, k, data[k])
        
        
    def eval(self, expr, solvars, phys, **kwargs):
        val = eval_at_nodals(self, expr, solvars, phys)
        if val is None: return None, None

        edge_only = kwargs.pop('edge_only', False)
        if not edge_only:
            return self.locs[self.iverts_inv], val[self.iverts_inv, ...]
        else:
            idx = edge_detect(self.iverts_inv)
            return self.locs[idx], val[idx, ...]            
    
