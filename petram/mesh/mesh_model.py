import os
import numpy as np
import mfem

PyMFEM_PATH =os.path.dirname(os.path.dirname(mfem.__file__))
PetraM_PATH =os.getenv("PetraM")
HOME = os.path.expanduser("~")

from petram.model import Model
from petram.namespace_mixin import NS_mixin
from petram.mfem_config import use_parallel

if use_parallel:
   import mfem.par as mfem
   from mpi4py import MPI
   num_proc = MPI.COMM_WORLD.size
   myid     = MPI.COMM_WORLD.rank
   from petram.helper.mpi_recipes import *   
else:
   import mfem.ser as mfem
   
import petram.debug
dprint1, dprint2, dprint3 = petram.debug.init_dprints('MeshModel')

class Mesh(Model, NS_mixin):
    isMeshGenerator = False
    isRefinement = False      
    def __init__(self, *args, **kwargs):
        super(Mesh, self).__init__(*args, **kwargs)
        NS_mixin.__init__(self, *args, **kwargs)
   
    def onItemSelChanged(self, evt):
        '''
        GUI response when model object is selected in
        the dlg_edit_model
        '''
        viewer = evt.GetEventObject().GetTopLevelParent().GetParent()
        viewer.set_view_mode('phys', self)
        
    def get_mesh_root(self):
        from petram.mfem_model import MFEM_MeshRoot
        
        p = self.parent
        while p is not None:
            if isinstance(p, MFEM_MeshRoot): return p           
            p = p.parent
            
class MFEMMesh(Model):  
    can_delete = True
    has_2nd_panel = False
    isMeshGroup = True    
    def get_possible_child(self):
        try:
           from petram.mesh.pumimesh_model import PumiMesh
           return [MeshFile, PumiMesh, Mesh1D, Mesh2D, Mesh3D, UniformRefinement, DomainRefinement]
        except:
           return [MeshFile, Mesh1D, Mesh2D, Mesh3D, UniformRefinement, DomainRefinement]

    def get_possible_child_menu(self):
        try:
           from petram.mesh.pumimesh_model import PumiMesh
           return [("", MeshFile), ("Other Meshes", Mesh1D), ("", Mesh2D), ("", Mesh3D), ("!", PumiMesh), ("Refinement...", UniformRefinement), ("!", DomainRefinement)]
        except:
           return [("", MeshFile), ("Other Meshes", Mesh1D), ("", Mesh2D), ("!", Mesh3D), ("Refinement...", UniformRefinement), ("!", DomainRefinement)]           
                
    def onItemSelChanged(self, evt):
        '''
        GUI response when model object is selected in
        the dlg_edit_model
        '''
        viewer = evt.GetEventObject().GetTopLevelParent().GetParent()
        viewer.set_view_mode('phys', self)
        
    def is_viewmode_grouphead(self):
        return True
     
    def figure_data_name(self):
        return 'mfem'

    def get_special_menu(self):
        return [["Reload Mesh", self.reload_mfem_mesh, None,],]
     
    def reload_mfem_mesh(self, evt):
        evt.GetEventObject().GetParent().onLoadMesh(evt)
        
    @property
    def sdim(self):
        if not hasattr(self, '_sdim'): self._sdim = 1
        return self._sdim
    
    @sdim.setter
    def sdim(self, value):
        self._sdim = value

        
MeshGroup = MFEMMesh

def format_mesh_characteristic(mesh):
   h_min = mfem.doublep()
   h_max = mfem.doublep()
   kappa_min= mfem.doublep()
   kappa_max= mfem.doublep()
   Vh=mfem.Vector()
   Vk=mfem.Vector()
   mesh.GetCharacteristics(h_min, h_max, kappa_min, kappa_max, Vh, Vk)
   h_min=h_min.value()
   h_max=h_max.value()
   kappa_min=kappa_min.value()
   kappa_max=kappa_max.value()

   out = ["", "=== Mesh Statistics ==="]
   out.append("Dimension          : " + str(mesh.Dimension()))
   out.append("Space dimension    : " + str(mesh.SpaceDimension()))

   if mesh.Dimension() == 0:
      out.append("Number of vertices : " + str(mesh.GetNV()))
      out.append("Number of elements : " + str(mesh.GetNE()))
      out.append("Number of bdr elem : " + str(mesh.GetNBE()))
   elif mesh.Dimension() == 1:
      out.append("Number of vertices : " + str(mesh.GetNV()))
      out.append("Number of elements : " + str(mesh.GetNE()))
      out.append("Number of bdr elem : " + str(mesh.GetNBE()))
      out.append("h_min              : " + str(h_min))
      out.append("h_max              : " + str(h_max))
   elif mesh.Dimension() == 2:
      out.append("Number of vertices : " + str(mesh.GetNV()))
      out.append("Number of edges    : " + str(mesh.GetNEdges()))
      out.append("Number of elements : " + str(mesh.GetNE()))
      out.append("Number of bdr elem : " + str(mesh.GetNBE())) 
      out.append("Euler Number       : " + str(mesh.EulerNumber2D()))
      out.append("h_min              : " + str(h_min))
      out.append("h_max              : " + str(h_max))
      out.append("kappa_min              : " + str(kappa_min))
      out.append("kappa_max              : " + str(kappa_max))
   elif mesh.Dimension() == 3:
      out.append("Number of vertices : " + str(mesh.GetNV()))
      out.append("Number of edges    : " + str(mesh.GetNEdges()))
      out.append("Number of faces    : " + str(mesh.GetNFaces()))
      out.append("Number of elements : " + str(mesh.GetNE()))
      out.append("Number of bdr elem : " + str(mesh.GetNBE())) 
      out.append("Euler Number       : " + str(mesh.EulerNumber()))
      out.append("h_min              : " + str(h_min))
      out.append("h_max              : " + str(h_max))
      out.append("kappa_min              : " + str(kappa_min))
      out.append("kappa_max              : " + str(kappa_max))
   return '\n'.join(out)

class MeshFile(Mesh):
    isMeshGenerator = True   
    isRefinement = False   
    has_2nd_panel = False        
    def __init__(self, parent = None, **kwargs):
        self.path = kwargs.pop("path", "")
        self.generate_edges = kwargs.pop("generate_edges", 1)
        self.refine = kwargs.pop("refien", 1)
        self.fix_orientation = kwargs.pop("fix_orientation", True)        
        super(MeshFile, self).__init__(parent = parent, **kwargs)

    def __repr__(self):
        try:
           return 'MeshFile('+self.path+')'
        except:
           return 'MeshFile(!!!Error!!!)'
        
    def attribute_set(self, v):
        v = super(MeshFile, self).attribute_set(v)
        v['path'] = ''
        v['generate_edges'] = 1
        v['refine'] = True
        v['fix_orientation'] = True

        return v
        
    def panel1_param(self):
        if not hasattr(self, "_mesh_char"):
           self._mesh_char = ''
        wc = "ANY|*|MFEM|*.mesh|GMSH|*.gmsh"       
        ret =  [["Path",   self.path,  45, {'wildcard':wc}],
                ["", "rule: {petram}=$PetraM, {mfem}=PyMFEM, \n     {home}=~ ,{model}=project file dir."  ,2, None],
                [None,  self.generate_edges == 1,  3, {"text":"Generate edges"}],
                [None,   self.refine==1 ,  3, {"text":"Refine"}],
                [None,   self.fix_orientation ,  3, {"text":"FixOrientation"}],
                [None, self._mesh_char ,2, None],]
        return ret
     
    def get_panel1_value(self):
        return (self.path, None, self.generate_edges, self.refine, self.fix_orientation, None)
    
    def import_panel1_value(self, v):
        self.path = str(v[0])
        self.generate_edges = 1 if v[2] else 0
        self.refine = 1 if v[3] else 0
        self.fix_orientation = v[4]
        
    def use_relative_path(self):
        self._path_bk  = self.path
        self.path = os.path.basename(self.get_real_path())

        
    def restore_fullpath(self):       
        self.path = self._path_bk
        self._path_bk = ''


    def get_real_path(self):
        path = str(self.path)
        if path == '':
           # if path is empty, file is given by internal mesh generator.
           parent = self.get_mesh_root()
           for key in parent.keys():
              if not parent[key].is_enabled(): continue
              if hasattr(parent[key], 'get_meshfile_path'):
                 return parent[key].get_meshfile_path()
        if path.find('{mfem}') != -1:
            path = path.replace('{mfem}', PyMFEM_PATH)
        if path.find('{petram}') != -1:
            path = path.replace('{petram}', PetraM_PATH)
        if path.find('{home}') != -1:
            path = path.replace('{home}', HOME)
        if path.find('{model}') != -1:
            path = path.replace('{model}', str(self.root().model_path))

        if not os.path.isabs(path):
            dprint2("meshfile relative path mode")
            path1 = os.path.join(os.getcwd(), path)
            dprint2("trying :", path1)
            if not os.path.exists(path1):
                path1 = os.path.join(os.path.dirname(os.getcwd()), path)
                dprint2("trying :", path1)
                if (not os.path.exists(path1) and "__main__" in globals() and hasattr(__main__, '__file__')):
                    from __main__ import __file__ as mainfile        
                    path1 = os.path.join(os.path.dirname(os.path.realpath(mainfile)), path)   
                    dprint1("trying :", path1)
                if not os.path.exists(path1) and os.getenv('PetraM_MeshDir') is not None:
                    path1 = os.path.join(os.getenv('PetraM_MeshDir'), path)
                    dprint1("trying :", path1)                    
            if os.path.exists(path1):
                path = path1
            else:
                assert False, "can not find mesh file from relative path: "+path
        return path

    def run(self, mesh = None):
        path = self.get_real_path()
        if not os.path.exists(path):
            print("mesh file does not exists : " + path + " in " + os.getcwd())
            return None
        args = (path,  self.generate_edges, self.refine, self.fix_orientation)
        mesh =  mfem.Mesh(*args)
        self.parent.sdim = mesh.SpaceDimension()
        self._mesh_char = format_mesh_characteristic(mesh)
        try:
           mesh.GetNBE()
           return mesh
        except:
           return None
        
class Mesh1D(Mesh):
    isMeshGenerator = True      
    isRefinement = False   
    has_2nd_panel = False
    unique_child = True    

    def attribute_set(self, v):
        v = super(Mesh1D, self).attribute_set(v)
        v['length'] = [1,]
        v['nsegs'] = [100,]
        v['length_txt'] = "1"
        v['nsegs_txt'] = "100"
        v['refine'] = 1
        v['fix_orientation'] = True
        v['mesh_x0_txt'] = "0.0"
        v['mesh_x0'] = 0.0
        return v
        
    def panel1_param(self):
        if not hasattr(self, "_mesh_char"):
           self._mesh_char = ''
       
        def check_int_array(txt, param, w):
            try:
               val  = [int(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float_array(txt, param, w):
            try:
               val  = [float(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float(txt, param, w):
            try:
               val  = float(txt)
               return True
            except:
               return False
            
        return [["Length",   self.length_txt,  0, {"validator":check_float_array}],
                ["N segments",   self.nsegs_txt,  0, {"validator":check_int_array}],
                ["x0",   self.mesh_x0_txt,  0, {"validator":check_float}],
                [None, "Note: use comma separated float/integer for a multisegments mesh",   2, {}],
                [None, self._mesh_char ,2, None],]     

    def get_panel1_value(self):
        return (self.length_txt, self.nsegs_txt, self.mesh_x0_txt, None, None)
    
    def import_panel1_value(self, v):
        self.length_txt = str(v[0])
        self.nsegs_txt = str(v[1])
        self.mesh_x0_txt = str(v[2])        

        success = self.eval_strings()

    def eval_strings(self):
        g = self._global_ns.copy()
        l = {}
       
        try:
            self.length = [float(eval(x, g, l)) for x in self.length_txt.split(',')]
            self.nsegs= [int(eval(x, g, l)) for x in self.nsegs_txt.split(',')]
            self.mesh_x0 = float(eval(self.mesh_x0_txt, g, l))
            return True
        except:
            import traceback
            traceback.print_exc()
            
        return False
     
    def run(self, mesh = None):

        from petram.mesh.make_simplemesh import straight_line_mesh

        success = self.eval_strings()
        assert success, "Conversion error of input parameter"
        
        mesh = straight_line_mesh(self.length, self.nsegs,
                               filename='',
                               refine = self.refine == 1,
                               fix_orientation = self.fix_orientation,
                               sdim = 1, x0=self.mesh_x0)
        self.parent.sdim = mesh.SpaceDimension()
        self._mesh_char = format_mesh_characteristic(mesh)        
        try:
           mesh.GetNBE()
           return mesh
        except:
           return None
        
class Mesh2D(Mesh):
    isMeshGenerator = True      
    isRefinement = False   
    has_2nd_panel = False
    unique_child = True    

    def attribute_set(self, v):
        v = super(Mesh2D, self).attribute_set(v)
        v['length'] = [1,]
        v['nsegs'] = [100,]
        v['xlength_txt'] = "1"
        v['ylength_txt'] = "1"
        v['xnsegs_txt'] = "30"
        v['ynsegs_txt'] = "20"
        v['refine'] = 1
        v['fix_orientation'] = True
        v['mesh_x0_txt'] = "0.0, 0.0"
        v['mesh_x0'] = (0.0, 0.0, )
        return v
        
    def panel1_param(self):
        if not hasattr(self, "_mesh_char"):
           self._mesh_char = ''
       
        def check_int_array(txt, param, w):
            try:
               val  = [int(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float_array(txt, param, w):
            try:
               val  = [float(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float(txt, param, w):
            try:
               val  = float(txt)
               return True
            except:
               return False
            
        return [["Length(x)",   self.xlength_txt,  0, {"validator":check_float_array}],
                ["N segments(x)",   self.xnsegs_txt,  0, {"validator":check_int_array}],                
                ["Length(y)",   self.ylength_txt,  0, {"validator":check_float_array}],
                ["N segments(y)",   self.ynsegs_txt,  0, {"validator":check_int_array}],                
                ["x0",   self.mesh_x0_txt,  0, {"validator":check_float_array}],
                [None, "Note: use comma separated float/integer for a multisegments mesh",   2, {}],
                [None, self._mesh_char ,2, None],]          

    def get_panel1_value(self):
        return (self.xlength_txt, self.xnsegs_txt, self.ylength_txt, self.ynsegs_txt,
                self.mesh_x0_txt, None, None)
    
    def import_panel1_value(self, v):
        self.xlength_txt = str(v[0])
        self.xnsegs_txt = str(v[1])
        self.ylength_txt = str(v[2])
        self.ynsegs_txt = str(v[3])
        self.mesh_x0_txt = str(v[4])        

        success = self.eval_strings()

    def eval_strings(self):
        g = self._global_ns.copy()
        l = {}
       
        try:
            self.xlength = [float(eval(x, g, l)) for x in self.xlength_txt.split(',')]
            self.xnsegs= [int(eval(x, g, l)) for x in self.xnsegs_txt.split(',')]
            self.ylength = [float(eval(x, g, l)) for x in self.ylength_txt.split(',')]
            self.ynsegs= [int(eval(x, g, l)) for x in self.ynsegs_txt.split(',')]
            self.mesh_x0 = [float(eval(x, g, l)) for x in self.mesh_x0_txt.split(',')]
            return True
        except:
            import traceback
            traceback.print_exc()
            
        return False
       
    def run(self, mesh = None):

        from petram.mesh.make_simplemesh import quad_rectangle_mesh

        success = self.eval_strings()
        assert success, "Conversion error of input parameter"
        
        mesh = quad_rectangle_mesh(self.xlength, self.xnsegs, self.ylength, self.ynsegs,
                               filename='', refine = self.refine == 1,
                               fix_orientation = self.fix_orientation,
                               sdim=2, x0=self.mesh_x0)
        
        self.parent.sdim = mesh.SpaceDimension()
        self._mesh_char = format_mesh_characteristic(mesh)
        
        try:
           mesh.GetNBE()
           return mesh
        except:
           return None

class Mesh3D(Mesh):
    isMeshGenerator = True      
    isRefinement = False   
    has_2nd_panel = False        
    unique_child = True
    
    def attribute_set(self, v):
        v = super(Mesh3D, self).attribute_set(v)
        v['length'] = [1,]
        v['nsegs'] = [100,]
        v['xlength_txt'] = "1"
        v['ylength_txt'] = "1"
        v['zlength_txt'] = "1"                
        v['xnsegs_txt'] = "10"
        v['ynsegs_txt'] = "10"
        v['znsegs_txt'] = "10"        
        v['refine'] = 1
        v['fix_orientation'] = True
        v['mesh_x0_txt'] = "0.0, 0.0, 0.0"
        v['mesh_x0'] = (0.0, 0.0, 0.0)
        return v
        
    def panel1_param(self):
        if not hasattr(self, "_mesh_char"):
           self._mesh_char = ''
       
        def check_int_array(txt, param, w):
            try:
               val  = [int(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float_array(txt, param, w):
            try:
               val  = [float(x) for x in txt.split(',')]
               return True
            except:
               return False
            
        def check_float(txt, param, w):
            try:
               val  = float(txt)
               return True
            except:
               return False
            
        return [["Length(x)",   self.xlength_txt,  0, {"validator":check_float_array}],
                ["N segments(x)",   self.xnsegs_txt,  0, {"validator":check_int_array}],                
                ["Length(y)",   self.ylength_txt,  0, {"validator":check_float_array}],
                ["N segments(y)",   self.ynsegs_txt,  0, {"validator":check_int_array}],                
                ["Length(z)",   self.zlength_txt,  0, {"validator":check_float_array}],                
                ["N segments(z)",   self.znsegs_txt,  0, {"validator":check_int_array}],                
                ["x0",   self.mesh_x0_txt,  0, {"validator":check_float_array}],
                [None, "Note: use comma separated float/integer for a multisegments mesh",   2, {}],
                [None, self._mesh_char ,2, None],]
     
    def get_panel1_value(self):
        return (self.xlength_txt, self.xnsegs_txt, self.ylength_txt, self.ynsegs_txt,
                self.zlength_txt, self.znsegs_txt, self.mesh_x0_txt, None, None)
    
    def import_panel1_value(self, v):
        self.xlength_txt = str(v[0])
        self.xnsegs_txt = str(v[1])
        self.ylength_txt = str(v[2])
        self.ynsegs_txt = str(v[3])
        self.zlength_txt = str(v[4])
        self.znsegs_txt = str(v[5])
        self.mesh_x0_txt = str(v[6])        

        success = self.eval_strings()

    def eval_strings(self):
        g = self._global_ns.copy()
        l = {}
       
        try:
            self.xlength = [float(eval(x, g, l)) for x in self.xlength_txt.split(',')]
            self.xnsegs= [int(eval(x, g, l)) for x in self.xnsegs_txt.split(',')]
            self.ylength = [float(eval(x, g, l)) for x in self.ylength_txt.split(',')]
            self.ynsegs= [int(eval(x, g, l)) for x in self.ynsegs_txt.split(',')]
            self.zlength = [float(eval(x, g, l)) for x in self.zlength_txt.split(',')]
            self.znsegs= [int(eval(x, g, l)) for x in self.znsegs_txt.split(',')]
            self.mesh_x0 = [float(eval(x, g, l)) for x in self.mesh_x0_txt.split(',')]
            return True
        except:
            import traceback
            traceback.print_exc()
            
        return False
       
    def run(self, mesh = None):
        from petram.mesh.make_simplemesh import hex_box_mesh

        success = self.eval_strings()
        assert success, "Conversion error of input parameter"
        
        mesh = hex_box_mesh(self.xlength, self.xnsegs,self.ylength, self.ynsegs, self.zlength, self.znsegs,
                            filename='', refine = self.refine == 1, fix_orientation=self.fix_orientation,
                            sdim=3, x0=self.mesh_x0)
        self.parent.sdim = mesh.SpaceDimension()
        self._mesh_char = format_mesh_characteristic(mesh)        
        
        try:
           mesh.GetNBE()
           return mesh
        except:
           return None
        
        
class UniformRefinement(Mesh):
    isRefinement = True
    has_2nd_panel = False           
    def __init__(self, parent = None, **kwargs):
        self.num_refine = kwargs.pop("num_refine", "0")
        super(UniformRefinement, self).__init__(parent = parent, **kwargs)        
    def __repr__(self):
        try:
           return 'MeshUniformRefinement('+self.num_refine+')'
        except:
           return 'MeshUniformRefinement(!!!Error!!!)'
        
    def attribute_set(self, v):
        v = super(UniformRefinement, self).attribute_set(v)       
        v['num_refine'] = '0'
        return v
        
    def panel1_param(self):
        return [["Number",   str(self.num_refine),  0, {}],]
     
    def import_panel1_value(self, v):
        self.num_refine = str(v[0])
        
    def get_panel1_value(self):
        return (str(self.num_refine),)
     
    def run(self, mesh):
        gtype = np.unique([mesh.GetElementBaseGeometry(i) for i in range(mesh.GetNE())])
        if use_parallel:
            from mpi4py import MPI
            gtype = gtype.astype(np.int32)
            gtype = np.unique(allgather_vector(gtype, MPI.INT))

        if len(gtype) > 1:
           dprint1("(Warning) Element Geometry Type is mixed. Cannot perform UniformRefinement")
           return mesh
        for i in range(int(self.num_refine)):           
            mesh.UniformRefinement() # this is parallel refinement
        return mesh
     
class DomainRefinement(Mesh):
    isRefinement = True
    has_2nd_panel = False 
    def __init__(self, parent = None, **kwargs):
        self.num_refine = kwargs.pop("num_refine", "0")
        self.domain_txt = kwargs.pop("domain_txt", "")
        super(DomainRefinement, self).__init__(parent = parent, **kwargs)        
    def __repr__(self):
        try:
           return 'MeshUniformRefinement('+self.num_refine+')'
        except:
           return 'MeshUniformRefinement(!!!Error!!!)'
        
    def attribute_set(self, v):
        v = super(DomainRefinement, self).attribute_set(v)       
        v['num_refine'] = '0'
        v['domain_txt'] = ''
        return v
        
    def panel1_param(self):
        return [["Number",    str(self.num_refine),  0, {}],
                ["Domains",   self.domain_txt,  0, {}],]
     
    def import_panel1_value(self, v):
        self.num_refine = str(v[0])
        self.domain_txt = str(v[1])
        
    def get_panel1_value(self):
        return (str(self.num_refine), str(self.domain_txt))
     
    def run(self, mesh):
        gtype = np.unique([mesh.GetElementBaseGeometry(i) for i in range(mesh.GetNE())])
        if use_parallel:
            from mpi4py import MPI
            gtype = gtype.astype(np.int32)
            gtype = np.unique(allgather_vector(gtype, MPI.INT))

        if len(gtype) > 1:
           dprint1("(Warning) Element Geometry Type is mixed. Cannot perform UniformRefinement")
           return mesh
        domains = [int(x) for x in self.domain_txt.split(',')]
        if len(domains) == 0: return mesh


        for i in range(int(self.num_refine)):
            attr = mesh.GetAttributeArray()
            idx = mfem.intArray(list(np.where(np.in1d(attr, domains))[0]))
            mesh.GeneralRefinement(idx) # this is parallel refinement
        return mesh

   

