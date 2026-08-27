import sys
print("Python version:", sys.version, file=sys.stderr)
print("START", file=sys.stderr)

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication as SMA

print("IMPORTS DONE", file=sys.stderr)

model = Kratos.Model()
mp = model.CreateModelPart("Main")
mp.ProcessInfo[Kratos.DOMAIN_SIZE] = 3

print("MODEL CREATED", file=sys.stderr)

mp.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
mp.AddNodalSolutionStepVariable(Kratos.REACTION)
mp.AddNodalSolutionStepVariable(SMA.POINT_LOAD)

print("VARIABLES ADDED", file=sys.stderr)

n1 = mp.CreateNewNode(1, 0.0, 0.0, 0.0)
n2 = mp.CreateNewNode(2, 1.0, 0.0, 0.0)
n3 = mp.CreateNewNode(3, 0.0, 1.0, 0.0)
n4 = mp.CreateNewNode(4, 0.0, 0.0, 1.0)

print("NODES CREATED", file=sys.stderr)

for n in mp.Nodes:
    n.AddDof(Kratos.DISPLACEMENT_X, Kratos.REACTION_X)
    n.AddDof(Kratos.DISPLACEMENT_Y, Kratos.REACTION_Y)
    n.AddDof(Kratos.DISPLACEMENT_Z, Kratos.REACTION_Z)

print("DOFS SET", file=sys.stderr)

props = mp.GetProperties()[1]
props[Kratos.YOUNG_MODULUS] = 210e9
props[Kratos.POISSON_RATIO] = 0.3
props[Kratos.DENSITY] = 7850.0
props.SetValue(Kratos.CONSTITUTIVE_LAW, SMA.LinearElastic3DLaw())

print("PROPERTIES SET", file=sys.stderr)

elem = mp.CreateNewElement("SmallDisplacementElement3D4N", 1, [1,2,3,4], props)

print("ELEMENT CREATED", file=sys.stderr)

for n in [n1, n3, n4]:
    n.Fix(Kratos.DISPLACEMENT_X)
    n.Fix(Kratos.DISPLACEMENT_Y)
    n.Fix(Kratos.DISPLACEMENT_Z)

print("NODES FIXED", file=sys.stderr)

cond = mp.CreateNewCondition("PointLoadCondition3D1N", 1, [2], props)
n2.SetSolutionStepValue(SMA.POINT_LOAD, [0.0, -1000.0, 0.0])

print("CONDITION CREATED", file=sys.stderr)

# Inicializar ProcessInfo
mp.ProcessInfo[Kratos.TIME] = 0.0
mp.ProcessInfo[Kratos.DELTA_TIME] = 1.0
mp.ProcessInfo[Kratos.STEP] = 1
print("PROCESS INFO INITIALIZED", file=sys.stderr)

# Inicializar elementos y condiciones
for elem in mp.Elements:
    elem.Initialize(mp.ProcessInfo)

for cond in mp.Conditions:
    cond.Initialize(mp.ProcessInfo)

print("ELEMENTOS Y CONDICIONES INICIALIZADOS", file=sys.stderr)

try:
    scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
    print("SCHEME CREATED", file=sys.stderr)
    
    scheme.Initialize(mp)
    print("SCHEME INITIALIZED", file=sys.stderr)
    
    builder_and_solver = Kratos.ResidualBasedBlockBuilderAndSolver(Kratos.SkylineLUFactorizationSolver())
    print("BUILDER CREATED", file=sys.stderr)
    
    builder_and_solver.SetUpDofSet(scheme, mp)
    print("DOF SET UP", file=sys.stderr)
    
    builder_and_solver.SetUpSystem(mp)
    print("SYSTEM SET UP", file=sys.stderr)
    
    A = Kratos.CompressedMatrix(); b = Kratos.Vector(); x = Kratos.Vector()
    print("VECTORS CREATED", file=sys.stderr)
    
    builder_and_solver.ResizeAndInitializeVectors(scheme, A, x, b, mp)
    print("VECTORS INITIALIZED", file=sys.stderr)
    
    print("ABOUT TO BUILD", file=sys.stderr)
    builder_and_solver.Build(scheme, mp, A, b)
    print("RHS BUILT", file=sys.stderr)

    print("Norma del RHS ensamblado:", max(abs(v) for v in b))
    print("RHS completo:", list(b))
except Exception as e:
    print(f"ERROR IN SOLVER SETUP: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
