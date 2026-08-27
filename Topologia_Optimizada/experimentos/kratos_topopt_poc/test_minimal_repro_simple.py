import sys
print("Python version:", sys.version)

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication as SMA

try:
    print("1. Creando modelo...")
    model = Kratos.Model()
    mp = model.CreateModelPart("Main")
    mp.ProcessInfo[Kratos.DOMAIN_SIZE] = 3

    print("2. Agregando variables...")
    mp.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
    mp.AddNodalSolutionStepVariable(Kratos.FORCE)
    mp.AddNodalSolutionStepVariable(Kratos.REACTION)
    mp.AddNodalSolutionStepVariable(Kratos.VELOCITY)
    mp.AddNodalSolutionStepVariable(Kratos.ACCELERATION)

    print("3. Creando nodos...")
    n1 = mp.CreateNewNode(1, 0.0, 0.0, 0.0)
    n2 = mp.CreateNewNode(2, 1.0, 0.0, 0.0)
    n3 = mp.CreateNewNode(3, 0.0, 1.0, 0.0)
    n4 = mp.CreateNewNode(4, 0.0, 0.0, 1.0)

    print("4. Configurando DOFs...")
    Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_X, Kratos.REACTION_X, mp)
    Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Y, Kratos.REACTION_Y, mp)
    Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Z, Kratos.REACTION_Z, mp)

    print("5. Configurando propiedades...")
    props = mp.GetProperties()[1]
    props[Kratos.YOUNG_MODULUS] = 210e9
    props[Kratos.POISSON_RATIO] = 0.3
    props[Kratos.DENSITY] = 7850.0
    cl = SMA.LinearElastic3DLaw()
    props.SetValue(Kratos.CONSTITUTIVE_LAW, cl)

    print("6. Creando elemento...")
    elem = mp.CreateNewElement("SmallDisplacementElement3D4N", 1, [1,2,3,4], props)

    print("7. Fijando nodos...")
    for n in [n1, n3, n4]:
        n.Fix(Kratos.DISPLACEMENT_X)
        n.Fix(Kratos.DISPLACEMENT_Y)
        n.Fix(Kratos.DISPLACEMENT_Z)

    print("8. Aplicando fuerza...")
    n2.SetValue(Kratos.FORCE, Kratos.Array3([0.0, -1000.0, 0.0]))

    print("9. Configurando solver...")
    scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
    builder_and_solver = Kratos.ResidualBasedBlockBuilderAndSolver(
        Kratos.SkylineLUFactorizationSolver())

    print("10. Inicializando sistema...")
    builder_and_solver.SetUpDofSet(scheme, mp)
    builder_and_solver.SetUpSystem(mp)

    print("11. Creando vectores...")
    A = Kratos.CompressedMatrix()
    b = Kratos.Vector()
    x = Kratos.Vector()
    builder_and_solver.ResizeAndInitializeVectors(scheme, A, x, b, mp)

    print("12. Construyendo sistema...")
    builder_and_solver.Build(scheme, mp, A, b)

    print("Norma del RHS ensamblado:", max(abs(v) for v in b))
    print("RHS completo:", list(b))
    
except Exception as e:
    print(f"ERROR en paso: {e}")
    import traceback
    traceback.print_exc()
