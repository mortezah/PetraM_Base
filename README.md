## PetraM_Base (Base Package for Petra-M)

Petra-M (Physics Equation Translator for MFEM) is a physics layer built
on the top of PyMFEM, a python wrapper for Modular FEM library
(MFEM: http://mfem.org). 

Petra-M Base includes
 - Physics modeling interface on piScope.
 - Weakform module to define PDE using MFEM integrators.
 - HypreParCSR matrix utility. 
 - NASTRAN file converter to MFEM mesh format.
 - Physics modeling interface on piScope

Petra-M consists from submodules.
   PetraM_RF : 3D frequency domain Maxwell equation
   PetraM_MUMPS : interface to MUMPS direct linear solver
   PetraM_Geom : Geometry editor module using GMSH/OpenCascade

## Publications
  S. Shiraiwa, et al. EPJ Web of Conferences 157, 03048 (2017)

### Licence
PetraM project is released under the GPL v3 license.
See files COPYRIGHT and LICENSE file for full details.

