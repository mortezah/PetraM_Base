'''

   Variables

  
    This modules interface string exression to MFEM

    for example, when a user write

       epsiolnr = 'x + 0.5y'

     and if epsilonr is one of Variable object, it will become 

        call of epsilon(x,y,z) at integration points (matrix assembly)

        or 

        many such calles for all nodal points (plot) 

    about variable decorator: 
       this class instance is used to convered a user written function
       to a Vriable object.
    
    from petram.helper.variables import variable
    @variable.float
    def test(x, y, z):
       return 1-0.1j
    @variable.complex
    def ctest(x, y, z):
       return 1-0.1j
    @variable.array(complex=True,shape=(2,))
    def atest(x, y, z):
       return np.array([1-0.1j,1-0.1j])
     
'''
import numpy as np
import parser
import weakref
import traceback
from weakref import WeakKeyDictionary as WKD
from weakref import WeakValueDictionary as WVD

from petram.mfem_config import use_parallel
if use_parallel:
    import mfem.par as mfem
else:
    import mfem.ser as mfem

class _decorator(object):
    def float(self, func):
        obj = PyFunctionVariable(func, complex = False)
        return obj
    def complex(self, func):
        obj = PyFunctionVariable(func, complex = True)
        return obj
    def array(self, complex=False, shape = (1,)):
        def dec(func):
            #print "inside dec", complex, shape
            obj = PyFunctionVariable(func, complex = complex, shape = shape)
            return obj
        return dec
        
variable = _decorator()        

def eval_code(co, g, l):
    a = eval(co, g, l)
    if callable(a): return a()
    return a

var_g = {'sin':  np.sin,
         'cos':  np.cos,
         'tan':  np.tan,
         'arctan':  np.arctan,                                      
         'arctan2':  np.arctan2,
         'log10':  np.log10,
         'log':  np.log,
         'log2':  np.log2,
         'abs':  np.abs,                   
         'conj': np.conj,
         'real': np.real,
         'imag': np.imag,
         'dot': np.dot,
         'vdot': np.vdot,
         'array': np.array,
         'cross': np.cross, 
         'pi': np.pi,}

class Variables(dict):
    def __repr__(self):
        txt = []
        for k in self.keys():
            txt.append(k + ':' + str(self[k]))
        return "\n".join(txt)

class Variable(object):
    '''
    define everything which we define algebra
    '''
    def __init__(self, complex=False):
        self.complex = complex

    def __add__(self, other):
        if isinstance(other, Variable):
            return self() + other()
        else:
            return self() + other
        
    def __sub__(self, other):
        if isinstance(other, Variable):
            return self() - other()
        else:
            return self() - other
    def __mul__(self, other):
        if isinstance(other, Variable):
            return self() * other()
        else:
            return self() * other
    def __div__(self, other):
        if isinstance(other, Variable):
            return self() / other()
        else:
            return self() / other

    def __radd__(self, other):
        if isinstance(other, Variable):
            return self() + other()
        else:
            return self() + other

    def __rsub__(self, other):
        if isinstance(other, Variable):
            return other() - self()
        else:
            return other - self()
        
    def __rmul__(self, other):
        if isinstance(other, Variable):
            return self() * other()
        else:
            return self() * other
        
    def __rdiv__(self, other):
        if isinstance(other, Variable):
            return other()/self()
        else:
            return other/self()

    def __divmod__(self, other):
        if isinstance(other, Variable):
            return self().__divmod__(other())
        else:
            return self().__divmod__(other)

    def __floordiv__(self, other):
        if isinstance(other, Variable):
            return self().__floordiv__(other())
        else:
            return self().__floordiv__(other)
        
    def __mod__(self, other):
        if isinstance(other, Variable):
            return self().__mod__(other())
        else:
            return self().__mod__(other)
        
    def __pow__(self, other):
        if isinstance(other, Variable):
            return self().__pow__(other())
        else:
            return self().__pow__(other)
        
    def __neg__(self):
        return self().__neg__()
        
    def __pos__(self):
        return self().__pos__()
    
    def __abs__(self):
        return self().__abs__()

    def __getitem__(self, idx):
        print idx
        print self().shape
        return self()[idx]

    def make_callable(self):
        raise NotImplementedError("Subclass need to implement")
    
    def make_nodal(self):
        raise NotImplementedError("Subclass need to implement")
    
class TestVariable(Variable):
    def __init__(self, comp = -1, complex=False):
        super(TestVariable, self).__init__(complex = complex)
        
    def set_point(self,T, ip, g, l, t = None):
        self.x = T.Transform(ip)        
               
    def __call__(self):
        return 2.
    
    def nodal_values(self, locs = None,  **kwargs):
                    # iele = None, elattr = None, el2v = None,
                    #  wverts = None, locs = None, g = None
        return locs[:, 0]*0 + 2.0
    
class Constant(Variable):
    def __init__(self, value, comp = -1):
        super(Constant, self).__init__(complex = np.iscomplexobj(value))
        self.value = value
        
    def __repr__(self):
        return "Constant("+str(self.value)+")"
        
    def set_point(self,T, ip, g, l, t = None):
        self.x = T.Transform(ip)        
               
    def __call__(self):
        return self.value
    
    def nodal_values(self, iele = None, el2v = None, locs = None,
                     wverts = None, elvertloc = None, **kwargs):

        size = len(wverts)        
        shape = [size] + list(np.array(self.value).shape)

        dtype = np.complex if self.complex else np.float
        ret = np.zeros(shape, dtype = dtype)
        wverts = np.zeros(size)
        
        for kk, m, loc in zip(iele, el2v, elvertloc):
            if kk < 0: continue
            for pair, xyz in zip(m, loc):
                idx = pair[1]
                ret[idx] = self.value

        return ret
        
class CoordVariable(Variable):
    def __init__(self, comp = -1, complex=False):
        super(CoordVariable, self).__init__(complex = complex)
        self.comp = comp
        
    def __repr__(self):
        return "Coordinates"
        
    def set_point(self,T, ip, g, l, t = None):
        self.x = T.Transform(ip)        
               
    def __call__(self):
        if self.comp == -1:
            return self.x
        else:
            return self.x[self.comp-1]
    
    def nodal_values(self, locs = None,  **kwargs):
                    # iele = None, elattr = None, el2v = None,
                    #  wverts = None, locs = None, g = None
        if self.comp == -1:
            return locs
        else:
            return locs[:, self.comp-1]
    
class ExpressionVariable(Variable):
    def __init__(self, expr, ind_vars, complex=False):
        super(ExpressionVariable, self).__init__(complex = complex)


        variables = []
        st = parser.expr(expr)
        code= st.compile('<string>')
        names = code.co_names
        self.co = code
        self.names = names
        self.expr = expr
        self.ind_vars = ind_vars
        self.variables = WVD()
        #print 'Check Expression', expr.__repr__(), names
    def __repr__(self):
        return "Expression("+self.expr + ")"
    
    def set_point(self,T, ip, g, l, t = None):
        self.x = T.Transform(ip)        
        for n in self.names:
            if (n in g and isinstance(g[n], Variable)):
               g[n].set_point(T, ip, g, l, t=t)
               self.variables[n] = g[n]
               
    def __call__(self):
        l = {}
        for k, name in enumerate(self.ind_vars):
           l[name] = self.x[k]
        keys = self.variables.keys()
        for k in keys:
           l[k] = self.variables[k]()
        return (eval_code(self.co, var_g, l))
    
    def nodal_values(self, iele = None, el2v = None, locs = None,
                     wverts = None, elvertloc = None, g = None,
                     **kwargs):

        size = len(wverts)        
        dtype = np.complex if self.complex else np.float
        ret = np.zeros(size, dtype = dtype)
        for kk, m, loc in zip(iele, el2v, elvertloc):
            if kk < 0: continue
            for pair, xyz in zip(m, loc):
                idx = pair[1]
                ret[idx] = 1

        l = {}
        ll_name = []
        ll_value = []
        var_g2 = var_g.copy()
        for n in self.names:
            if (n in g and isinstance(g[n], Variable)):
                l[n] = g[n].nodal_values(iele = iele, el2v = el2v, locs = locs,
                                         wverts = wverts, elvertloc = elvertloc,
                                         g = g, **kwargs)
                ll_name.append(n)
                ll_value.append(l[n])
            elif (n in g):
                var_g2[n] = g[n]
        if len(ll_name) > 0:
            value = np.array([eval(self.co, var_g2, dict(zip(ll_name, v)))
                        for v in zip(*ll_value)])
        else:
            for k, name in enumerate(self.ind_vars):
                l[name] = locs[...,k]
            value = np.array(eval_code(self.co, var_g2, l), copy=False)
            if value.ndim > 1:
                value = np.stack([value]*size)
        #value = np.array(eval_code(self.co, var_g, l), copy=False)

        from petram.helper.right_broadcast import multi

        #print 'value!!!', ret.shape, value.shape
        ret = multi(ret, value)
        return ret
    
class DomainVariable(Variable):
    def __init__(self, expr = '', ind_vars = None, domains = None,
                 complex = False):
        super(DomainVariable, self).__init__(complex = complex)
        self.domains = {}
        if expr == '': return
        domains = sorted(domains)
        self.domains[tuple(domains)] = ExpressionVariable(expr, ind_vars,
                                                  complex = complex)
    def __repr__(self):
        return "DomainVariable"
        
    def add_expression(self, expr, ind_vars, domains, complex = False):
        domains = sorted(domains)
        #print 'adding expression expr',expr, domains
        self.domains[tuple(domains)] = ExpressionVariable(expr, ind_vars,
                                                  complex = complex)
        if complex: self.complex = True

    def add_const(self, value, domains):
        domains = sorted(domains)        
        self.domains[tuple(domains)] = Constant(value)
        if np.iscomplexobj(value):self.complex = True
        
    def set_point(self,T, ip, g, l, t = None):
        attr = T.Attribute
        self.domain_target = None
        for domains in self.domains.keys():
           if attr in domains:
               self.domains[domains].set_point(T, ip, g, l, t=t)
           self.domain_target = domains
               
    def __call__(self):
        if self.domain_target is None: return 0.0
        return self.domains[self.domain_target]()

    def nodal_values(self, iele = None, elattr = None, g = None,
                     **kwargs):
                     #iele = None, elattr = None, el2v = None,
                     #wverts = None, locs = None, g = None):

        from petram.helper.right_broadcast import add
        
        ret = None
        w = None
        for domains in self.domains.keys():
            iele0 = np.zeros(iele.shape)-1
            for domain in domains:
                idx = np.where(np.array(elattr) == domain)[0]
                iele0[idx] = iele[idx]

            expr = self.domains[domains]
            v = expr.nodal_values(iele = iele0, elattr = elattr,
                                  g = g, **kwargs)
                                  #iele = iele, elattr = elattr,
                                  #el2v = el2v, wvert = wvert,
                                  #locs = locs, g = g
            if w is None:
                a  = np.sum(np.abs(v.reshape(len(v), -1)), -1)
                w = (a != 0).astype(float)
            else:
                a  = np.sum(np.abs(v.reshape(len(v), -1)), -1)                
                w = w + (a != 0).astype(float)                
            ret = v if ret is None else add(ret, v)

        idx = np.where(w != 0)[0]
        #ret2 = ret.copy()
        from petram.helper.right_broadcast import div                
        ret[idx, ...] = div(ret[idx, ...], w[idx])
        return ret
        
        
class PyFunctionVariable(Variable):
    def __init__(self, func, complex=False, shape = tuple()):
        super(PyFunctionVariable, self).__init__(complex = complex)
        self.func = func
        self.t = None
        self.x = (0,0,0)
        self.shape = shape
        
    def __repr__(self):
        return "PyFunction"
        
    def set_point(self,T, ip, g, l, t = None):
        self.x = T.Transform(ip)
        self.t = t
        
    def __call__(self):
        if self.t is not None:
           args = tuple(np.hstack((self.x, t)))
        else:
           args = tuple(self.x)
        return np.array(self.func(*args), copy=False)
       
    def nodal_values(self, iele = None, el2v = None, locs = None,
                     wverts = None, elvertloc = None, **kwargs):
                     # elattr = None, el2v = None,
                     # wverts = None, locs = None, g = None
        if locs is None: return

        size = len(wverts)        
        shape = [size] + list(self.shape)

        dtype = np.complex if self.complex else np.float
        ret = np.zeros(shape, dtype = dtype)
        wverts = np.zeros(size)
        for kk, m, loc in zip(iele, el2v, elvertloc):
            if kk < 0: continue
            for pair, xyz in zip(m, loc):
                idx = pair[1]
                ret[idx] = ret[idx] + self.func(*xyz)
                wverts[idx] = wverts[idx] + 1
        ret = np.stack([x for x in ret if x is not None])


        idx = np.where(wverts == 0)[0]        
        wverts[idx] = 1.0
        
        from petram.helper.right_broadcast import div        
        ret = div(ret, wverts)

        return ret


class GridFunctionVariable(Variable):
    def __init__(self, gf_real, gf_imag = None, comp = 1,
                 deriv = None, complex = False):
        
        super(GridFunctionVariable, self).__init__(complex = complex)
        self.dim = gf_real.VectorDim()
        self.comp = comp
        self.isDerived = False
        self.deriv = deriv if deriv is not None else self._def_deriv
        self.deriv_args = (gf_real, gf_imag)
        
    def _def_deriv(self, *args):
        return args[0], args[1], None
    
    def set_point(self,T, ip, g, l, t = None):
        self.T = T
        self.ip = ip
        self.t = t
    
class GFScalarVariable(GridFunctionVariable):
    def __repr__(self):
        return "GridFunctionVariable (Scalar)"

    def set_funcs(self):
        # I should come back here to check if this works
        # with vector gf and/or boundary element. probably not...
        gf_real, gf_imag, extra = self.deriv(*self.deriv_args)
        self.gfr = gf_real
        self.gfi = gf_imag
        self.func_r = mfem.GridFunctionCoefficient(gf_real,
                                                   comp = self.comp)
        if gf_imag is not None:
            self.func_i = mfem.GridFunctionCoefficient(gf_imag,
                                                       comp = self.comp)
        else:
            self.func_i = None
        self.isDerived = True
        self.extra = extra            
    def __call__(self):
        if not self.isDerived: self.set_funcs()
        if self.func_i is None:
            return self.func_r.Eval(self.T, self.ip)
        else:
            return (self.func_r.Eval(self.T, self.ip) +
                    1j*self.func_i.Eval(self.T, self.ip))

    def nodal_values(self, iele = None, el2v = None, wverts = None,
                     **kwargs):
                    # iele = None, elattr = None, el2v = None,
                    # wverts = None, locs = None, g = None
        if iele is None: return        
        if not self.isDerived: self.set_funcs()
        
        size = len(wverts)
        if self.gfi is None:
            ret = np.zeros(size, dtype = np.float)
        else:
            ret = np.zeros(size, dtype = np.complex)
        for kk, m in zip(iele, el2v):
            if kk < 0: continue            
            values = mfem.doubleArray()
            self.gfr.GetNodalValues(kk, values, self.comp)
            for k, idx in m:
                ret[idx] = ret[idx] + values[k]
            if self.gfi is not None:
                arr = mfem.doubleArray()                
                self.gfi.GetNodalValues(kk, arr, self.comp)
                for k, idx in m:
                    ret[idx] = ret[idx] + arr[k]*1j
        ret = ret / wverts
        return ret
            
class GFVectorVariable(GridFunctionVariable):
    def __repr__(self):
        return "GridFunctionVariable (Vector)"
    
    def set_funcs(self):
        gf_real, gf_imag, extra = self.deriv(*self.deriv_args)
        self.gfr = gf_real
        self.gfi = gf_imag
        self.dim = gf_real.VectorDim()        
        self.func_r = [mfem.GridFunctionCoefficient(gf_real, comp = k+1)
                          for k in range(self.dim)]
           
        if gf_imag is not None:
            self.func_i = [mfem.GridFunctionCoefficient(gf_imag, comp = k+1)
                           for k in range(self.dim)]

        self.isDerived = True
        self.extra = extra                    
    def __call__(self):
        if self.func_i is None:
            return np.array([func_r.Eval(self.T, self.ip) for
                                 func_r in self.func_r])
        else:
            return np.array([(func_r.Eval(self.T, self.ip) +
                                  1j*func_i.Eval(self.T, self.ip))
                                 for func_r, func_i
                                 in zip(self.func_r, self.func_i)])
            
    def nodal_values(self, iele = None, el2v = None, wverts = None,
                     **kwargs):
                    # iele = None, elattr = None, el2v = None,
                    # wverts = None, locs = None, g = None
       
        if iele is None: return        
        if not self.isDerived: self.set_funcs()

        size = len(wverts)

        ans = []
        for comp in range(self.dim):
            if self.gfi is None:
                ret = np.zeros(size, dtype = np.float)
            else:
                ret = np.zeros(size, dtype = np.complex)
            for kk, m in zip(iele, el2v):
                if kk < 0: continue  
                values = mfem.doubleArray()
                self.gfr.GetNodalValues(kk, values, comp+1)
                for k, idx in m:
                    ret[idx] = ret[idx] + values[k]
                if self.gfi is not None:
                    arr = mfem.doubleArray()                
                    self.gfi.GetNodalValues(kk, arr, comp+1)
                    for k, idx in m:
                        ret[idx] = ret[idx] + arr[k]*1j
            ans.append(ret / wverts)
        ret =np.transpose(np.vstack(ans))
        return ret
'''

Surf Variable:
 Regular Variable + Surface Geometry (n, nx, ny, nz)

'''    
class SurfVariable(Variable):
    def __init__(self, sdim, complex = False):
        self.sdim = sdim
        super(SurfVariable, self).__init__(complex = complex)
        
class SurfNormal(SurfVariable):
    def __init__(self, sdim, comp = -1, complex = False):
        self.comp = comp
        SurfVariable.__init__(self, sdim, complex = complex)
        
    def __repr__(self):
        return "SurfaceNormal (nx, ny, nz)"
        
    def set_point(self, T, ip, g, l, t = None):
        nor = mfem.Vector(self.sdim)
        mfem.CalcOrtho(T.Jacobian(), nor)
        self.nor =nor.GetDataArray().copy()
        
    def __call__(self):
        if self.comp == -1:
            return self.nor
        else:
            return self.nor[self.comp-1]
        
    def nodal_values(self, ibele = None, mesh = None, iverts_f = None,
                     **kwargs):
                    # iele = None, elattr = None, el2v = None,
                    # wverts = None, locs = None, g = None
      
        g = mfem.Geometry()
        size = len(iverts_f)
        #wverts = np.zeros(size)
        ret = np.zeros((size, self.sdim))
        if ibele is None: return               
                       
        ibe  = ibele[0]
        el = mesh.GetBdrElement(ibe)
        rule = g.GetVertices(el.GetGeometryType())
        nv = rule.GetNPoints()
        

        for ibe in ibele:
           T = mesh.GetBdrElementTransformation(ibe)
           bverts = mesh.GetBdrElement(ibe).GetVerticesArray()

           for i in range(nv):
               nor = mfem.Vector(self.sdim)                       
               T.SetIntPoint(rule.IntPoint(i))
               mfem.CalcOrtho(T.Jacobian(), nor)
               idx = np.searchsorted(iverts_f, bverts[i])
                             
               ret[idx, :] += nor.GetDataArray().copy()
               #wverts[idx] = wverts[idx] + 1
                             
        #for i in range(self.sdim): ret[:,i] /= wvert
        # normalize to length one. 
        ret = ret / np.sqrt(np.sum(ret**2, 1)).reshape(-1,1)
        
        if self.comp == -1: return ret
        return ret[:, self.comp-1]
        
class SurfExpressionVariable(ExpressionVariable, SurfVariable):
    def __init__(self, expr, ind_vars, sdim, complex=False):
        ExpressionVariable.__init__(self, expr, ind_vars, complex=complex)
        SurfVariable.__init__(self, sdim, complex = complex)
        
    def __repr__(self):
        return "SurfaceExpression("+self.expr+")"
        
    def set_point(self, T, ip, g, l, t = None):
        self.x = T.Transform(ip)
        self.t = t
        T.SetIntPoint(ip)
        nor = mfem.Vector(self.sdim)
        mfem.CalcOrtho(T.Jacobian(), nor)
        self.nor =nor.GetDataArray().copy()
        
    def __call__(self):
        l = {}
        for k, name in enumerate(self.ind_vars):
           l[name] = self.x[k]
        l['n'] = self.nor
        for k, name in enumerate(self.ind_vars):
           l['n'+name] = self.nor[k]
        keys = self.variables.keys()
        for k in keys:
           l[k] = self.variables[k]()
        return (eval_code(self.co, var_g, l))
    
    def nodal_values(self, **kwargs):
        l = {}        
        for n in self.names:
            if (n in g and isinstance(g[n], Variable)):
                l[n] = g[n].nodal_values(**kwargs)
        for k, name in enumerate(self.ind_vars):
           l[name] = locs[...,k]
        for k, name in enumerate(self.ind_vars):
           l['n'+name] = nor[...,k]
        return (eval_code(self.co, var_g, l))

'''
 Bdr Variable = Surface Variable defined on particular boundary
'''    
class BdrVariable(ExpressionVariable, SurfVariable):
    pass

def append_suffix_to_expression(expr, vars, suffix):
    for v in vars:
        expr = expr.replace(v, v+suffix)
    return expr

def add_scalar(solvar, name, suffix, ind_vars, solr, soli=None, deriv = None):
    solvar[name + suffix] = GFScalarVariable(solr, soli, comp=1,
                                                deriv = deriv)

def add_components(solvar, name, suffix, ind_vars, solr,
                   soli=None, deriv = None):
    solvar[name + suffix] = GFVectorVariable(solr, soli, deriv = deriv)
    for k, p in enumerate(ind_vars):
       solvar[name + suffix + p] = GFScalarVariable(solr, soli, comp=k+1,
                                                    deriv = deriv)

def add_expression(solvar, name, suffix, ind_vars, expr, vars,
                   domains = None, bdrs = None, complex = None):
    expr = append_suffix_to_expression(expr, vars, suffix)
    if domains is not None:
        if (name + suffix) in solvar:
            solvar[name + suffix].add_expression(expr, ind_vars, domains,
                                                 complex = complex)
        else:
            solvar[name + suffix] = DomainVariable(expr, ind_vars,
                                               domains = domains,
                                               complex = complex)
    elif bdrs is not None:
        pass
    else:
        solvar[name + suffix] = ExpressionVariable(expr, ind_vars,
                                                   complex = complex)
        
def add_constant(solvar, name, suffix, value, domains = None, bdrs = None):
    if domains is not None:
        if (name + suffix) in solvar:
            solvar[name + suffix].add_const(value, domains)
        else:
            solvar[name + suffix] = DomainVariable('')
            solvar[name + suffix].add_const(value, domains)
    elif bdrs is not None:
        pass
    else:
        solvar[name + suffix] = Constant(value)
        

def add_surf_normals(solvar, ind_vars):
    sdim = len(ind_vars)                         
    solvar['n'] = SurfNormal(sdim, comp = -1)
    for k, p in enumerate(ind_vars):
       solvar['n'+p] = SurfNormal(sdim, comp = k+1)

def add_coordinates(solvar, ind_vars):
    for k, p in enumerate(ind_vars):    
       solvar[p] = CoordVariable(comp = k+1)

       


       
  

    


            
   