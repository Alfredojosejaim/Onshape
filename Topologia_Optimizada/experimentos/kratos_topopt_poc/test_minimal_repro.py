print("START")
import sys
print("Python:", sys.version)

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication as SMA

print("AFTER IMPORTS")
model = Kratos.Model()
mp = model.CreateModelPart("Main")
mp.ProcessInfo[Kratos.DOMAIN_SIZE] = 3
print("AFTER MODEL CREATE")

try:
    mp.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
    print("AFTER DISPLACEMENT")
    mp.AddNodalSolutionStepVariable(Kratos.REACTION)
    print("AFTER REACTION")
    mp.AddNodalSolutionStepVariable(SMA.POINT_LOAD)
    print("AFTER POINT_LOAD")
except Exception as e:
    print(f"ERROR ADDING VARIABLES: {e}")
    import traceback
    traceback.print_exc()

mp.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
mp.AddNodalSolutionStepVariable(Kratos.REACTION)
mp.AddNodalSolutionStepVariable(SMA.POINT_LOAD)

n1 = mp.CreateNewNode(1, 0.0, 0.0, 0.0)
n2 = mp.CreateNewNode(2, 1.0, 0.0, 0.0)
n3 = mp.CreateNewNode(3, 0.0, 1.0, 0.0)
n4 = mp.CreateNewNode(4, 0.0, 0.0, 1.0)

for n in mp.Nodes:
    n.AddDof(Kratos.DISPLACEMENT_X, Kratos.REACTION_X)
    n.AddDof(Kratos.DISPLACEMENT_Y, Kratos.REACTION_Y)
    n.AddDof(Kratos.DISPLACEMENT_Z, Kratos.REACTION_Z)

props = mp.GetProperties()[1]
props[Kratos.YOUNG_MODULUS] = 210e9
props[Kratos.POISSON_RATIO] = 0.3
props[Kratos.DENSITY] = 7850.0
props.SetValue(Kratos.CONSTITUTIVE_LAW, SMA.LinearElastic3DLaw())

elem = mp.CreateNewElement("SmallDisplacementElement3D4N", 1, [1,2,3,4], props)

for n in [n1, n3, n4]:
    n.Fix(Kratos.DISPLACEMENT_X)
    n.Fix(Kratos.DISPLACEMENT_Y)
    n.Fix(Kratos.DISPLACEMENT_Z)

cond = mp.CreateNewCondition("PointLoadCondition3D1N", 1, [2], props)
n2.SetSolutionStepValue(SMA.POINT_LOAD, [0.0, -1000.0, 0.0])

scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
builder_and_solver = Kratos.ResidualBasedBlockBuilderAndSolver(Kratos.SkylineLUFactorizationSolver())
builder_and_solver.SetUpDofSet(scheme, mp)
builder_and_solver.SetUpSystem(mp)
A = Kratos.CompressedMatrix(); b = Kratos.Vector(); x = Kratos.Vector()
builder_and_solver.ResizeAndInitializeVectors(scheme, A, x, b, mp)
builder_and_solver.Build(scheme, mp, A, b)

print("Norma del RHS ensamblado:", max(abs(v) for v in b))
print("RHS completo:", list(b))
