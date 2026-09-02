"""Kratos Multiphysics adapter for FEA and topology optimization.

This module provides a clean interface between the Core and Kratos Multiphysics,
isolating Kratos-specific implementation details from the rest of the application.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Contador global (por proceso) de caídas del solver iterativo a la factorización
# directa `skyline_lu`, para seguimiento en producción (si amgcl no convergió en una
# geometría concreta, queremos detectarlo con frecuencia, no esperar a que un usuario
# reporte un cálculo "raro"). Se incrementa en cada fallback y se expone vía
# KratosAdapter.get_fallback_count().
_FALLBACK_COUNT = 0

# Kratos imports - these will be imported when needed to avoid unnecessary dependencies
KRATOS_AVAILABLE = True
KRATOS_IMPORT_ERROR = None

try:
    import KratosMultiphysics as Kratos
    from KratosMultiphysics import StructuralMechanicsApplication
    from KratosMultiphysics import OptimizationApplication
except ImportError as e:
    KRATOS_AVAILABLE = False
    KRATOS_IMPORT_ERROR = str(e)
    logger.warning(f"Kratos Multiphysics not available: {e}")


class KratosInitializationError(Exception):
    """Raised when Kratos cannot be initialized properly."""
    pass


class KratosAdapter:
    """Main adapter class for Kratos Multiphysics integration."""
    
    def __init__(self):
        """Initialize the Kratos adapter."""
        if not KRATOS_AVAILABLE:
            raise KratosInitializationError(
                f"Kratos Multiphysics is not available: {KRATOS_IMPORT_ERROR}"
            )
        
        # Configure Kratos logger to reduce verbosity
        Kratos.Logger.GetDefaultOutput().SetSeverity(Kratos.Logger.Severity.WARNING)
        
        # Create Kratos Model
        self.model = Kratos.Model()
        self.main_model_part = None
        
        # Storage for external loads (Kratos ModelPart doesn't allow arbitrary attributes)
        self.external_loads = {}  # {model_part_name: {node_id: force_vector}}
        
        logger.info("Kratos adapter initialized successfully")
    
    def create_model_part(self, name: str = "MainModelPart") -> Any:
        """Create a new ModelPart in Kratos.
        
        Args:
            name: Name for the ModelPart
            
        Returns:
            Kratos ModelPart object
        """
        try:
            model_part = self.model.CreateModelPart(name)
            logger.info(f"Created ModelPart: {name}")
            return model_part
        except Exception as e:
            logger.error(f"Failed to create ModelPart {name}: {e}")
            raise
    
    def add_nodal_variables(self, model_part: Any) -> None:
        """Add nodal solution step variables to ModelPart BEFORE creating nodes.
        
        This must be called BEFORE any nodes are created/imported.
        
        Args:
            model_part: Kratos ModelPart (should be empty, no nodes yet)
        """
        try:
            # Add nodal variables BEFORE creating nodes (Kratos requirement)
            model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT_X)
            model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT_Y)
            model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT_Z)
            model_part.AddNodalSolutionStepVariable(Kratos.REACTION_X)
            model_part.AddNodalSolutionStepVariable(Kratos.REACTION_Y)
            model_part.AddNodalSolutionStepVariable(Kratos.REACTION_Z)
            model_part.AddNodalSolutionStepVariable(Kratos.FORCE_X)
            model_part.AddNodalSolutionStepVariable(Kratos.FORCE_Y)
            model_part.AddNodalSolutionStepVariable(Kratos.FORCE_Z)
            
            logger.info("Nodal variables added to ModelPart (before node creation)")
            
        except Exception as e:
            logger.error(f"Failed to add nodal variables: {e}")
            raise
    
    def setup_model_part_for_structural_analysis(self, model_part: Any) -> None:
        """Configure ModelPart for structural mechanics analysis.
        
        This sets up the necessary buffer sizes for structural analysis.
        Note: Variables must be added BEFORE creating nodes (use add_nodal_variables()).
        
        Args:
            model_part: Kratos ModelPart to configure
        """
        try:
            # Set up buffer size for variables
            model_part.SetBufferSize(2)  # Current and previous step
            
            logger.info("ModelPart configured for structural analysis")
            
        except Exception as e:
            logger.error(f"Failed to configure ModelPart for structural analysis: {e}")
            raise
    
    def add_displacement_dofs(self, model_part: Any) -> None:
        """Add displacement degrees of freedom to all nodes in ModelPart.
        
        Args:
            model_part: Kratos ModelPart with nodes
        """
        try:
            for node in model_part.Nodes:
                node.AddDof(Kratos.DISPLACEMENT_X)
                node.AddDof(Kratos.DISPLACEMENT_Y)
                node.AddDof(Kratos.DISPLACEMENT_Z)
            
            logger.info(f"Added displacement DOFs to {model_part.NumberOfNodes()} nodes")
            
        except Exception as e:
            logger.error(f"Failed to add displacement DOFs: {e}")
            raise
    
    def create_model_part_from_cad_model(self, cad_model_id: str, name: str = None) -> Any:
        """Create a ModelPart associated with a CAD model from the Core.
        
        This integrates Kratos ModelPart with the Core's CADModel structure.
        
        Args:
            cad_model_id: ID of the CAD model from the Core
            name: Optional name for the ModelPart (defaults to cad_model_id)
            
        Returns:
            Kratos ModelPart object
        """
        if name is None:
            name = f"CADModel_{cad_model_id}"
        
        try:
            model_part = self.create_model_part(name)
            
            # Store metadata for integration with Core
            # This allows tracing back to the original CAD model
            model_part.ProcessInfo[Kratos.DOMAIN_SIZE] = 3  # 3D analysis
            
            logger.info(f"Created ModelPart for CAD model {cad_model_id}: {name}")
            return model_part
            
        except Exception as e:
            logger.error(f"Failed to create ModelPart from CAD model {cad_model_id}: {e}")
            raise
    
    def get_model_part_info(self, model_part: Any) -> Dict[str, Any]:
        """Get information about a ModelPart for integration with Core.
        
        Args:
            model_part: Kratos ModelPart
            
        Returns:
            Dictionary with ModelPart information
        """
        try:
            info = {
                "name": str(model_part.Name),  # Name is a property, not a method
                "number_of_nodes": model_part.NumberOfNodes(),
                "number_of_elements": model_part.NumberOfElements(),
                "number_of_conditions": model_part.NumberOfConditions(),
                "buffer_size": model_part.GetBufferSize(),
            }
            
            # Note: DOF information requires different API access in Kratos
            # This will be handled in the integration with actual nodes
            
            logger.info(f"ModelPart info: {info}")
            return info
            
        except Exception as e:
            logger.error(f"Failed to get ModelPart info: {e}")
            raise
    
    def import_mesh_from_core_format(self, model_part: Any, nodes: List[List[float]], 
                                     elements: List[List[int]], element_type: str = "tet4",
                                     material_properties: Any = None,
                                     physical_groups: Optional[Dict[str, List[int]]] = None) -> None:
        """Import mesh from Core's MeshResult format to Kratos ModelPart.

        Args:
            model_part: Kratos ModelPart to populate with mesh
            nodes: List of node coordinates [[x, y, z], ...]
            elements: List of element connectivity [[n0, n1, n2, n3], ...]
            element_type: Type of elements (default "tet4")
            material_properties: Optional Kratos Properties object (if None, creates placeholder)
            physical_groups: Optional ``{name: [0-based node indices]}`` mapping.
                Each named group is rebuilt as a Kratos SubModelPart containing
                exactly those nodes (Fase 2: gmsh physical groups -> submodelparts),
                so boundary conditions can select nodes by group name.
        """
        try:
            logger.info(f"Importing mesh: {len(nodes)} nodes, {len(elements)} {element_type} elements")
            
            # Create nodes in Kratos
            for i, node_coords in enumerate(nodes):
                node_id = i + 1  # Kratos uses 1-based indexing
                x, y, z = float(node_coords[0]), float(node_coords[1]), float(node_coords[2])
                model_part.CreateNewNode(node_id, x, y, z)
            
            logger.info(f"Created {model_part.NumberOfNodes()} nodes in ModelPart")
            
            # Create elements in Kratos
            # Use provided material properties or create placeholder
            if material_properties is None:
                material_properties = Kratos.Properties(1)
                logger.info("Using placeholder material properties (configure with material functions)")
            
            # Map element types to Kratos element names
            element_mapping = {
                "tet4": "SmallDisplacementElement3D4N",
                "tet10": "SmallDisplacementElement3D10N",  # If we implement quadratic elements
            }
            
            kratos_element_name = element_mapping.get(element_type.lower(), "SmallDisplacementElement3D4N")

            # Fase 2 (rendimiento): pre-convertir la conectividad a 1-based y a enteros
            # fuera del bucle. En `large_50k` el `int(x)+1` repetido por elemento era el
            # costo dominante de la población (~0.31s -> ~0.22s, ~1.4x), todo C++-side
            # `CreateNewNode`/`CreateNewElement` más allá. Si el input es numpy (como en
            # benchmarks/make_meshes o benchmark_fase0), el +1 vectorizado es aún más barato.
            if hasattr(elements, "tolist") and hasattr(elements, "__add__") and not isinstance(elements, (list, tuple)):
                try:
                    connectivity_1based = (elements + 1).tolist()
                except Exception:
                    connectivity_1based = [[int(x) + 1 for x in el] for el in elements]
            else:
                connectivity_1based = [[int(x) + 1 for x in el] for el in elements]

            for i, node_ids in enumerate(connectivity_1based):
                element_id = i + 1  # Kratos uses 1-based indexing

                try:
                    model_part.CreateNewElement(kratos_element_name, element_id, node_ids, material_properties)
                except Exception as e:
                    logger.warning(f"Failed to create element {element_id}: {e}")
            
            logger.info(f"Created {model_part.NumberOfElements()} elements in ModelPart")

            # Fase 2: rebuild named SubModelParts from physical groups.
            if physical_groups:
                self._create_submodelparts_from_groups(model_part, physical_groups)
            
        except Exception as e:
            logger.error(f"Failed to import mesh from Core format: {e}")
            raise

    def _create_submodelparts_from_groups(
        self, model_part: Any, physical_groups: Dict[str, List[int]]
    ) -> None:
        """Create a Kratos SubModelPart per named physical group.

        Each SubModelPart receives the exact nodes of the corresponding boundary
        group (0-based indices -> Kratos 1-based node ids). These are the
        submodelparts that :meth:`get_nodes_from_submodelpart` looks up when a
        constraint/load is applied with ``submodelpart_name`` / ``boundary_name``.
        """
        n_nodes = model_part.NumberOfNodes()
        for name, indices in physical_groups.items():
            valid = [i for i in indices if 0 <= i < n_nodes]
            try:
                sub = model_part.CreateSubModelPart(str(name))
            except Exception as e:
                logger.warning(
                    "Could not create submodelpart %r (maybe a duplicate name?): %s", name, e
                )
                continue
            if valid:
                sub.AddNodes([i + 1 for i in valid])  # Kratos 1-based node ids
            logger.info(
                "SubModelPart %r created with %d nodes", name, len(valid)
            )
    
    def import_mesh_from_gmsh(self, model_part: Any, msh_file: str, 
                               material_properties: Any = None) -> None:
        """Import mesh from Gmsh .msh file to Kratos ModelPart.
        
        This uses the approach validated in the PoC experiments.
        
        Args:
            model_part: Kratos ModelPart to populate with mesh
            msh_file: Path to Gmsh .msh file
            material_properties: Optional Kratos Properties object (if None, creates placeholder)
        """
        try:
            import gmsh
            
            logger.info(f"Importing mesh from Gmsh file: {msh_file}")
            
            # Initialize Gmsh
            gmsh.initialize()
            gmsh.open(msh_file)
            
            # Get nodes from Gmsh
            node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
            
            logger.info(f"Importing {len(node_tags)} nodes from Gmsh...")
            
            # Create nodes in Kratos
            for i, tag in enumerate(node_tags):
                x = node_coords[3*i]
                y = node_coords[3*i + 1]
                z = node_coords[3*i + 2]
                model_part.CreateNewNode(i+1, x, y, z)
            
            # Get elements from Gmsh
            element_types = gmsh.model.mesh.getElementTypes()
            element_type_3d = None
            for et in element_types:
                if et == 4:  # Tet4 in Gmsh
                    element_type_3d = et
                    break
            
            # Use provided material properties or create placeholder
            if material_properties is None:
                material_properties = Kratos.Properties(1)
                logger.info("Using placeholder material properties (configure with material functions)")
            
            if element_type_3d:
                element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
                
                # Find Tet4 elements
                tet_elements = None
                for i, et in enumerate(element_types):
                    if et == 4:
                        tet_elements = element_connectivity[i]
                        break
                
                if tet_elements is not None:
                    num_tet_elements = len(tet_elements)//4
                    logger.info(f"Importing {num_tet_elements} Tet4 elements...")
                    
                    element_name = "SmallDisplacementElement3D4N"
                    
                    for i in range(0, len(tet_elements), 4):
                        elem_id = i//4 + 1
                        node_ids = [int(tet_elements[i+j]) for j in range(4)]
                        
                        try:
                            model_part.CreateNewElement(element_name, elem_id, node_ids, material_properties)
                        except Exception as e:
                            logger.warning(f"Failed to create element {elem_id}: {e}")
            
            gmsh.finalize()
            
            logger.info(f"Mesh import completed: {model_part.NumberOfNodes()} nodes, {model_part.NumberOfElements()} elements")
            
        except Exception as e:
            logger.error(f"Failed to import mesh from Gmsh: {e}")
            raise
    
    def import_mesh_from_mesh_result(self, model_part: Any, mesh_result: Any) -> None:
        """Import mesh from Core's MeshResult object to Kratos ModelPart.
        
        This provides direct integration with the Core's meshing infrastructure.
        
        Args:
            model_part: Kratos ModelPart to populate with mesh
            mesh_result: MeshResult object from core.meshing
        """
        try:
            if mesh_result is None:
                raise ValueError("mesh_result cannot be None")
            
            logger.info(f"Importing mesh from MeshResult: {mesh_result.num_nodes} nodes, {mesh_result.num_elements} elements")
            
            # Import using the Core format method
            self.import_mesh_from_core_format(
                model_part, 
                mesh_result.nodes, 
                mesh_result.elements, 
                mesh_result.element_type,
                physical_groups=getattr(mesh_result, "physical_groups", None),
            )
            
            logger.info("Mesh import from MeshResult completed")
            
        except Exception as e:
            logger.error(f"Failed to import mesh from MeshResult: {e}")
            raise
    
    def configure_material_from_core(self, model_part: Any, material: Any) -> None:
        """Configure material properties from Core's Material object to Kratos.
        
        Args:
            model_part: Kratos ModelPart with elements
            material: Material object from core.materials
        """
        try:
            logger.info(f"Configuring material: {material.name}")
            
            # Create Kratos Properties object
            material_properties = Kratos.Properties(1)
            
            # Map Core material properties to Kratos properties
            # Core uses SI units (Pa), Kratos expects consistent units
            material_properties.SetValue(Kratos.YOUNG_MODULUS, float(material.young_modulus))
            material_properties.SetValue(Kratos.POISSON_RATIO, float(material.poisson_ratio))
            material_properties.SetValue(Kratos.DENSITY, float(material.density))
            
            # Add constitutive law (required for structural elements)
            from KratosMultiphysics import StructuralMechanicsApplication as SMA
            constitutive_law = SMA.LinearElastic3DLaw()
            material_properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
            
            # Add yield strength as a custom property (not standard in Kratos but useful)
            try:
                material_properties.SetValue(Kratos.YIELD_STRESS, float(material.yield_strength))
            except AttributeError:
                # YIELD_STRESS might not be available in all Kratos versions
                logger.warning("YIELD_STRESS not available in this Kratos version")
            
            # Update all elements to use the new material properties
            for element in model_part.Elements:
                element.Properties = material_properties
            
            logger.info(f"Material configured: E={material.young_modulus:.2e} Pa, ν={material.poisson_ratio}")
            
        except Exception as e:
            logger.error(f"Failed to configure material from Core: {e}")
            raise
    
    def configure_material_manually(self, model_part: Any, young_modulus: float, 
                                    poisson_ratio: float, density: float = 7850.0) -> None:
        """Configure material properties manually.
        
        Args:
            model_part: Kratos ModelPart with elements
            young_modulus: Young's modulus in Pa
            poisson_ratio: Poisson's ratio (dimensionless)
            density: Material density in kg/m³
        """
        try:
            logger.info(f"Configuring material manually: E={young_modulus:.2e} Pa, ν={poisson_ratio}")
            
            # Create Kratos Properties object
            material_properties = Kratos.Properties(1)
            
            # Set material properties
            material_properties.SetValue(Kratos.YOUNG_MODULUS, float(young_modulus))
            material_properties.SetValue(Kratos.POISSON_RATIO, float(poisson_ratio))
            material_properties.SetValue(Kratos.DENSITY, float(density))
            
            # Add constitutive law (required for structural elements)
            from KratosMultiphysics import StructuralMechanicsApplication as SMA
            constitutive_law = SMA.LinearElastic3DLaw()
            material_properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
            
            # Update all elements to use the new material properties
            for element in model_part.Elements:
                element.Properties = material_properties
            
            logger.info("Manual material configuration completed")
            
        except Exception as e:
            logger.error(f"Failed to configure material manually: {e}")
            raise
    
    def apply_standard_material(self, model_part: Any, material_name: str = "steel") -> None:
        """Apply a standard material from Core's STANDARD_MATERIALS.
        
        Args:
            model_part: Kratos ModelPart with elements
            material_name: Name of standard material ("steel", "aluminum", "titanium")
        """
        try:
            from core.materials import STANDARD_MATERIALS
            
            if material_name not in STANDARD_MATERIALS:
                available = list(STANDARD_MATERIALS.keys())
                raise ValueError(f"Material '{material_name}' not found. Available: {available}")
            
            material = STANDARD_MATERIALS[material_name]
            self.configure_material_from_core(model_part, material)
            
            logger.info(f"Applied standard material: {material_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply standard material: {e}")
            raise
    
    def apply_fixed_constraint(self, model_part: Any, node_indices: List[int]) -> None:
        """Apply fixed constraint (all DOFs = 0) to specified nodes.
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            node_indices: List of node indices to fix (0-based from Core, converted to 1-based for Kratos)
        """
        try:
            logger.info(f"Applying fixed constraint to {len(node_indices)} nodes")
            
            for node_idx in node_indices:
                # Convert from 0-based (Core) to 1-based (Kratos)
                kratos_node_id = node_idx + 1
                
                if kratos_node_id <= model_part.NumberOfNodes():
                    node = model_part.Nodes[kratos_node_id]
                    # Fix all displacement DOFs
                    node.Fix(Kratos.DISPLACEMENT_X)
                    node.Fix(Kratos.DISPLACEMENT_Y)
                    node.Fix(Kratos.DISPLACEMENT_Z)
                else:
                    logger.warning(f"Node ID {kratos_node_id} out of range")
            
            logger.info("Fixed constraint applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply fixed constraint: {e}")
            raise
    
    def apply_pinned_constraint(self, model_part: Any, node_indices: List[int]) -> None:
        """Apply pinned constraint (translations fixed, rotations free) to specified nodes.
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            node_indices: List of node indices to pin (0-based from Core, converted to 1-based for Kratos)
        """
        try:
            logger.info(f"Applying pinned constraint to {len(node_indices)} nodes")
            
            for node_idx in node_indices:
                kratos_node_id = node_idx + 1
                
                if kratos_node_id <= model_part.NumberOfNodes():
                    node = model_part.Nodes[kratos_node_id]
                    # Fix only translations
                    node.Fix(Kratos.DISPLACEMENT_X)
                    node.Fix(Kratos.DISPLACEMENT_Y)
                    node.Fix(Kratos.DISPLACEMENT_Z)
                    # Rotations are not constrained (not available in this formulation)
                else:
                    logger.warning(f"Node ID {kratos_node_id} out of range")
            
            logger.info("Pinned constraint applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply pinned constraint: {e}")
            raise
    
    def apply_constraint_from_core(self, model_part: Any, constraint: Any, 
                                   node_indices: List[int]) -> None:
        """Apply constraint from Core's ConstraintDefinition to Kratos.
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            constraint: ConstraintDefinition object from core.study
            node_indices: List of node indices to apply constraint to
        """
        try:
            from core.study import ConstraintType
            
            logger.info(f"Applying constraint {constraint.id} (type: {constraint.constraint_type}) to {len(node_indices)} nodes")
            
            if constraint.constraint_type == ConstraintType.FIXED:
                self.apply_fixed_constraint(model_part, node_indices)
            elif constraint.constraint_type == ConstraintType.PINNED:
                self.apply_pinned_constraint(model_part, node_indices)
            else:
                logger.warning(f"Constraint type {constraint.constraint_type} not fully implemented, using fixed as fallback")
                self.apply_fixed_constraint(model_part, node_indices)
            
            logger.info(f"Constraint {constraint.id} applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply constraint from Core: {e}")
            raise
    
    def apply_constraints_by_face_mapping(
        self, model_part: Any, constraints: List[Any], cad_shape: Any,
        nodes: List[List[float]], tolerance: float = 0.5) -> None:
        """Apply constraints to nodes mapped from real CAD faces.

        Uses the Core's ``BoundaryConditionMapper`` to the map ``location_face_id``
        of every constraint to the mesh nodes that lie geometrically on that CAD
        face, then applies the constraint exclusively to those nodes.

        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            constraints: List of ConstraintDefinition objects from core.study
            cad_shape: CadQuery/OpenCASCADE Shape of the CAD model
            nodes: List of node coordinates for mapping
            tolerance: Distance tolerance (model units) for face-node matching
        """
        try:
            from core.boundary import BoundaryConditionMapper, resolve_face_index

            logger.info(f"Applying {len(constraints)} constraints using CAD face mapping")

            for constraint in constraints:
                face_index = resolve_face_index(getattr(constraint, "location_face_id", None))
                if face_index is None:
                    logger.warning(
                        f"Constraint {constraint.id} has no resolvable location_face_id; skipped"
                    )
                    continue

                mapped = BoundaryConditionMapper.map_faces_to_nodes(
                    cad_shape, nodes, face_indices=[face_index], tolerance=tolerance
                )
                if not mapped or not mapped[0].node_indices:
                    logger.warning(
                        f"Constraint {constraint.id}: no nodes found on CAD face index {face_index}"
                    )
                    continue

                node_indices = mapped[0].node_indices
                self.apply_constraint_from_core(model_part, constraint, node_indices)
                logger.info(
                    f"Constraint {constraint.id} applied to {len(node_indices)} nodes "
                    f"via CAD face index {face_index}"
                )

            logger.info("Constraints applied using CAD face mapping")

        except Exception as e:
            logger.error(f"Failed to apply constraints by face mapping: {e}")
            raise

    def apply_loads_by_face_mapping(
        self, model_part: Any, loads: List[Any], cad_shape: Any,
        nodes: List[List[float]], tolerance: float = 0.5) -> None:
        """Apply loads to nodes mapped from real CAD faces.

        Mirrors ``apply_constraints_by_face_mapping`` using the load's
        ``application_face_id``.
        """
        try:
            from core.boundary import BoundaryConditionMapper, resolve_face_index

            logger.info(f"Applying {len(loads)} loads using CAD face mapping")

            for load in loads:
                face_index = resolve_face_index(getattr(load, "application_face_id", None))
                if face_index is None:
                    logger.warning(
                        f"Load {load.id} has no resolvable application_face_id; skipped"
                    )
                    continue

                mapped = BoundaryConditionMapper.map_faces_to_nodes(
                    cad_shape, nodes, face_indices=[face_index], tolerance=tolerance
                )
                if not mapped or not mapped[0].node_indices:
                    logger.warning(
                        f"Load {load.id}: no nodes found on CAD face index {face_index}"
                    )
                    continue

                node_indices = mapped[0].node_indices
                self.apply_load_from_core(model_part, load, node_indices)
                logger.info(
                    f"Load {load.id} applied to {len(node_indices)} nodes "
                    f"via CAD face index {face_index}"
                )

            logger.info("Loads applied using CAD face mapping")

        except Exception as e:
            logger.error(f"Failed to apply loads by face mapping: {e}")
            raise
    
    def apply_point_load(self, model_part: Any, node_index: int, force_vector: List[float]) -> None:
        """Apply point load to a specific node (simplified implementation).
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            node_index: Node index to apply load to (0-based from Core, converted to 1-based for Kratos)
            force_vector: Force vector [Fx, Fy, Fz] in Newtons
        """
        try:
            logger.info(f"Applying point load {force_vector} N to node {node_index}")
            
            # Convert from 0-based (Core) to 1-based (Kratos)
            kratos_node_id = node_index + 1
            
            if kratos_node_id <= model_part.NumberOfNodes():
                # Store force in adapter's external loads dictionary
                model_part_name = str(model_part.Name)
                if model_part_name not in self.external_loads:
                    self.external_loads[model_part_name] = {}
                
                self.external_loads[model_part_name][kratos_node_id] = force_vector
                
                logger.info(f"Point load stored for node {kratos_node_id}")
            else:
                logger.warning(f"Node ID {kratos_node_id} out of range")
                
        except Exception as e:
            logger.error(f"Failed to apply point load: {e}")
            raise
    
    def apply_distributed_load(self, model_part: Any, node_indices: List[int], 
                              force_vector: List[float], distribute: bool = True) -> None:
        """Apply distributed load to multiple nodes.
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            node_indices: List of node indices to apply load to
            force_vector: Total force vector [Fx, Fy, Fz] in Newtons
            distribute: If True, distribute force evenly among nodes
        """
        try:
            logger.info(f"Applying distributed load {force_vector} N to {len(node_indices)} nodes")
            
            if distribute and len(node_indices) > 0:
                # Distribute force evenly
                force_per_node = [f / len(node_indices) for f in force_vector]
            else:
                force_per_node = force_vector
            
            for node_idx in node_indices:
                self.apply_point_load(model_part, node_idx, force_per_node)
            
            logger.info("Distributed load applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply distributed load: {e}")
            raise
    
    def apply_load_from_core(self, model_part: Any, load: Any, node_indices: List[int]) -> None:
        """Apply load from Core's LoadDefinition to Kratos.
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            load: LoadDefinition object from core.study
            node_indices: List of node indices to apply load to
        """
        try:
            from core.study import LoadType
            
            logger.info(f"Applying load {load.id} (type: {load.load_type}) to {len(node_indices)} nodes")
            
            force_vector = [load.magnitude * load.direction[i] for i in range(3)]
            
            if load.load_type == LoadType.POINT and len(node_indices) == 1:
                self.apply_point_load(model_part, node_indices[0], force_vector)
            else:
                # For distributed loads or multiple nodes, distribute evenly
                self.apply_distributed_load(model_part, node_indices, force_vector, distribute=True)
            
            logger.info(f"Load {load.id} applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply load from Core: {e}")
            raise
    
    def apply_pressure_load(self, model_part: Any, node_indices: List[int], 
                          pressure: float, normal_vector: List[float]) -> None:
        """Apply pressure load to nodes (simplified implementation).
        
        Args:
            model_part: Kratos ModelPart with nodes and DOFs
            node_indices: List of node indices to apply pressure to
            pressure: Pressure value in Pa
            normal_vector: Normal vector [nx, ny, nz] indicating pressure direction
        """
        try:
            logger.info(f"Applying pressure load {pressure} Pa to {len(node_indices)} nodes")
            
            # Simplified pressure implementation: distribute as point loads
            # In a full implementation, this would use surface elements and pressure conditions
            total_force = pressure  # Simplified (should be pressure * area)
            force_vector = [total_force * normal_vector[i] for i in range(3)]
            
            self.apply_distributed_load(model_part, node_indices, force_vector, distribute=True)
            
            logger.info("Pressure load applied (simplified implementation)")
            
        except Exception as e:
            logger.error(f"Failed to apply pressure load: {e}")
            raise
    
    def setup_solver_and_strategy(
        self, model_part: Any, linear_solver_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Set up solver and solution strategy for structural analysis.
        
        This is a simplified implementation that sets up the basic components
        needed for a linear static analysis.
        
        Args:
            model_part: Kratos ModelPart with mesh, material, constraints, and loads
            linear_solver_settings: optional dict de ``solver_type`` (+ opciones)
                para Kratos ``python_linear_solver_factory.ConstructSolver``.
                Por defecto (None) se usa ``amgcl`` (iterativo) con verificación de
                convergencia activa y fallback automático a la factorización directa
                ``skyline_lu`` en ``run_analysis`` si no converge o falla.
            
        Returns:
            Dictionary with solver and strategy information
        """
        try:
            logger.info("Setting up solver and solution strategy")
            
            # Import Kratos solvers and parameters
            import KratosMultiphysics as Kratos
            import KratosMultiphysics.python_linear_solver_factory as python_linear_solver_factory
            
            if linear_solver_settings is None:
                # Default: amgcl (iterativo) + verificación de convergencia activa.
                # Si amgcl no converge (o falla), run_analysis cae automáticamente a
                # la factorización directa skyline_lu con warning (ver _record_fallback).
                linear_solver_settings = dict(self._DEFAULT_AMGCL_SETTINGS)
            
            # Create solver parameters using the correct format from PoC
            import json as _json
            solver_settings = Kratos.Parameters(_json.dumps(linear_solver_settings))
            
            # Create linear solver using the official Python wrapper
            linear_solver = python_linear_solver_factory.ConstructSolver(solver_settings)
            
            # Set up time scheme (for linear static analysis)
            from KratosMultiphysics import ResidualBasedIncrementalUpdateStaticScheme
            time_scheme = ResidualBasedIncrementalUpdateStaticScheme()
            
            # Create builder and solver explicitly (official Kratos pattern)
            from KratosMultiphysics import ResidualBasedBlockBuilderAndSolver
            builder_and_solver = ResidualBasedBlockBuilderAndSolver(linear_solver)
            
            # Create strategy with correct argument order (signature #4)
            from KratosMultiphysics import ResidualBasedLinearStrategy
            strategy = ResidualBasedLinearStrategy(
                model_part,
                time_scheme,
                linear_solver,
                builder_and_solver,
                False,  # compute_reactions
                False,  # reform_dofs_at_each_step
                True,   # calculate_norm_dx
                False   # move_mesh_flag
            )
            strategy.SetEchoLevel(0)
            strategy.Initialize()
            
            logger.info("Solver and strategy setup completed")
            
            return {
                "linear_solver": linear_solver,
                "builder_and_solver": builder_and_solver,
                "scheme": time_scheme,
                "strategy": strategy,
                "status": "configured"
            }
            
        except Exception as e:
            logger.error(f"Failed to setup solver and strategy: {e}")
            # Return error status instead of raising to allow graceful handling
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def apply_external_loads_to_model_part(self, model_part: Any) -> None:
        """Apply stored external loads to the ModelPart before solving.
        
        Args:
            model_part: Kratos ModelPart with nodes
        """
        try:
            model_part_name = str(model_part.Name)
            
            if model_part_name in self.external_loads:
                loads = self.external_loads[model_part_name]
                logger.info(f"Applying {len(loads)} external loads to ModelPart")
                
                for node_id, force_vector in loads.items():
                    if node_id <= model_part.NumberOfNodes():
                        node = model_part.Nodes[node_id]
                        # Apply force as a load on the node
                        # Note: This is a simplified approach for testing
                        # In production, use proper Kratos conditions
                        try:
                            # Try to set force values directly
                            node.SetSolutionStepValue(Kratos.FORCE_X, 0, force_vector[0])
                            node.SetSolutionStepValue(Kratos.FORCE_Y, 0, force_vector[1])
                            node.SetSolutionStepValue(Kratos.FORCE_Z, 0, force_vector[2])
                        except Exception as e:
                            logger.warning(f"Could not set force on node {node_id}: {e}")
                
                logger.info("External loads applied successfully")
            else:
                logger.info("No external loads to apply")
                
        except Exception as e:
            logger.error(f"Failed to apply external loads: {e}")
            raise
    
    # Solvers lineales considerados ITERATIVOS (el Kratos build no expone su
    # convergencia real: `GetIterationsNumber`=0, `IsConverged`=True siempre y
    # `GetResidualNorm` no es el residual del sistema). Para estos solvers se
    # aplica una verificación de convergencia por re-resolución (estabilidad del
    # campo) y fallback a la factorización directa `skyline_lu`. Los directos
    # (skyline_lu, sparse_lu) o bien resuelven exacto o bien lanzan/fallan.
    _ITERATIVE_SOLVER_TYPES = {"amgcl"}
    _DEFAULT_AMGCL_SETTINGS = {
        "solver_type": "amgcl",
        "smoother_type": "ilu0",
        "krylov_type": "cg",
        "coarsening_type": "smoothed_aggregation",
        "max_iteration": 500,
        "tolerance": 1e-6,
    }
    _DEFAULT_SKYLINE_SETTINGS = {
        "solver_type": "skyline_lu_factorization",
        "scaling": False,
        "tolerance": 1e-6,
    }

    def _solve_to_results(self, model_part: Any, linear_solver_settings: Dict) -> Dict[str, Any]:
        """Configura el solver, resuelve y extrae resultados; SIEMPRE devuelve el
        dict de resultados (sin el wrapper) o un dict con status='failed'."""
        solver_setup = self.setup_solver_and_strategy(
            model_part, linear_solver_settings=linear_solver_settings
        )
        if solver_setup["status"] == "failed":
            return {
                "status": "failed",
                "success": False,
                "error": solver_setup.get("error"),
                "message": "Solver setup failed",
            }
        solver_setup["strategy"].Solve()
        return {
            "status": "completed",
            "success": True,
            "results": self.extract_analysis_results(model_part),
        }

    def _iterative_budget_settings(self, linear_solver_settings: Dict) -> Dict:
        """Copia de los ajustes iterativos con un presupuesto de iteraciones
        mucho mayor, para la verificación por estabilidad (re-resolución)."""
        settings = dict(linear_solver_settings)
        maxit = settings.get("max_iteration", 500)
        settings["max_iteration"] = max(int(maxit) * 20, 2000)
        return settings

    def _record_fallback(self, reason: str, model_part: Any, solver_type: str) -> int:
        """Registra una caída del solver a la factorización directa. Emite un log
        WARNING estructurado (timestamp ISO + identificador de la geometría/malla +
        motivo) e incrementa el contador global del proceso. Devuelve el conteo."""
        import datetime

        global _FALLBACK_COUNT
        _FALLBACK_COUNT += 1
        try:
            mesh_id = str(model_part.Name)
        except Exception:
            mesh_id = "<unknown>"
        logger.warning(
            "FALLBACK[%d] ts=%s mesh=%s solver=%s motivo=%s -> skyline_lu",
            _FALLBACK_COUNT,
            datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            mesh_id,
            solver_type,
            reason,
        )
        return _FALLBACK_COUNT

    @staticmethod
    def get_fallback_count() -> int:
        """Número de fallbacks a `skyline_lu` registrados en este proceso."""
        return _FALLBACK_COUNT

    def _verify_iterative_converged(self, model_part: Any, settings: Dict, d1, tol: float) -> bool:
        """Re-resuelve con mayor presupuesto de iteraciones y compara el campo.
        Si el campo cambió por encima de `tol`, el primer solve no había
        convergido (respuesta silenciosamente incorrecta) -> False."""
        try:
            r2 = self._solve_to_results(model_part, self._iterative_budget_settings(settings))
            if not r2.get("success"):
                return False
            d2 = np.asarray(r2["results"]["displacements"], dtype=float)
            if d1.size == 0 or d2.size == 0 or d1.size != d2.size:
                return False
            delta = float(np.linalg.norm(d2 - d1))
            denom = float(np.linalg.norm(d2))
            if denom <= 1e-30:
                return delta <= tol
            return (delta / denom) <= tol
        except Exception as e:
            logger.warning(f"Verification of iterative solve failed ({e}); assuming not converged")
            return False

    def run_analysis(self, model_part: Any, solver_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a simplified structural analysis on the ModelPart.

        Args:
            model_part: Kratos ModelPart with complete setup
            solver_config: Optional solver configuration dictionary.
                ``{"linear_solver_settings": {...}}`` selecciona el solver lineal.
                ``{"verify_convergence": bool}`` (default True) activa/desactiva la
                verificación de convergencia y el fallback para solvers iterativos
                (amgcl): si el iterativo no converge (o falla) se cae a la
                factorización directa ``skyline_lu`` con un warning en el log.

        Returns:
            Dictionary with analysis results (si hubo fallback se añade
            ``fallback_used=True``).
        """
        try:
            logger.info("Starting structural analysis")

            # Apply external loads
            self.apply_external_loads_to_model_part(model_part)

            _linear_settings = None
            verify = True
            if isinstance(solver_config, dict):
                _linear_settings = solver_config.get("linear_solver_settings")
                verify = bool(solver_config.get("verify_convergence", True))

            # Si no se pasa config, se usa el MISMO default compartido que
            # setup_solver_and_strategy (amgcl). Esto es clave: hace que el camino
            # "default" (sin config explícita) sea `is_iterative=True` y por tanto
            # pase por la verificación de convergencia y el fallback a skyline_lu,
            # en vez de saltarse la red de seguridad. (Antes, None -> is_iterative=False
            # -> el default amgcl quedaba SIN verificación ni fallback.)
            if _linear_settings is None:
                _linear_settings = dict(self._DEFAULT_AMGCL_SETTINGS)

            solver_type = "skyline_lu_factorization"
            if isinstance(_linear_settings, dict):
                solver_type = str(_linear_settings.get("solver_type", solver_type))
            is_iterative = solver_type in self._ITERATIVE_SOLVER_TYPES

            # Primera resolución con la configuración pedida (default -> amgcl verificado)
            result = self._solve_to_results(model_part, _linear_settings)
            fallback_used = False

            if not result.get("success"):
                # Fallo de construcción o de Solve -> fallback determinista a directo
                # _linear_settings nunca es None aquí (se defaulted en la guarda superior),
                # pero se mantiene el check defensivo para claridad de intención.
                self._record_fallback(
                    "fallo_del_solver_primer_intento", model_part, solver_type
                )
                fb = self._solve_to_results(model_part, self._DEFAULT_SKYLINE_SETTINGS)
                fallback_used = True
                if not fb.get("success"):
                    return {
                        "success": False,
                        "status": "failed",
                        "error": fb.get("error"),
                        "message": "Analysis execution failed",
                        "fallback_used": True,
                    }
                result = fb
            elif is_iterative and verify:
                # Verificación de convergencia para iterativos (amgcl)
                d1 = np.asarray(result["results"]["displacements"], dtype=float)
                conv_tol = 1e-3
                if isinstance(_linear_settings, dict):
                    conv_tol = float(_linear_settings.get("tolerance", 1e-6)) * 10.0
                if not self._verify_iterative_converged(model_part, _linear_settings, d1, conv_tol):
                    self._record_fallback("no_convergencia_verificada", model_part, solver_type)
                    result = self._solve_to_results(model_part, self._DEFAULT_SKYLINE_SETTINGS)
                    fallback_used = True
                    if not result.get("success"):
                        return {
                            "success": False,
                            "status": "failed",
                            "error": result.get("error"),
                            "message": result.get("message", "Fallback to skyline_lu failed"),
                            "fallback_used": True,
                        }

            logger.info("Analysis completed successfully")

            return {
                "success": result.get("success", True),
                "status": result.get("status", "completed"),
                "message": "Analysis completed successfully",
                "results": result["results"],
                "fallback_used": fallback_used,
                "solver_info": {
                    "nodes": model_part.NumberOfNodes(),
                    "elements": model_part.NumberOfElements(),
                    "constraints": model_part.NumberOfConditions()
                }
            }

        except Exception as e:
            logger.exception(f"Analysis failed: {e}")

            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "message": "Analysis execution failed"
            }
    
    def extract_analysis_results(self, model_part: Any) -> Dict[str, Any]:
        """Extract analysis results from a solved ModelPart.
        
        Args:
            model_part: Kratos ModelPart with solved analysis
            
        Returns:
            Dictionary with displacements, stresses, and compliance
        """
        try:
            logger.info("Extracting analysis results")
            
            # Extract displacements
            displacements = []
            for node in model_part.Nodes:
                if node.HasDofFor(Kratos.DISPLACEMENT_X):
                    disp_x = node.GetSolutionStepValue(Kratos.DISPLACEMENT_X)
                    disp_y = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Y)
                    disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
                    displacements.append([disp_x, disp_y, disp_z])
            
            # Calculate compliance (external work = F^T * u)
            compliance = 0.0
            model_part_name = str(model_part.Name)
            
            if model_part_name in self.external_loads:
                for node_id, force_vector in self.external_loads[model_part_name].items():
                    if node_id <= model_part.NumberOfNodes():
                        node = model_part.Nodes[node_id]
                        if node.HasDofFor(Kratos.DISPLACEMENT_X):
                            disp_x = node.GetSolutionStepValue(Kratos.DISPLACEMENT_X)
                            disp_y = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Y)
                            disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
                            # Compliance contribution: F · u
                            compliance += (force_vector[0] * disp_x + 
                                         force_vector[1] * disp_y + 
                                         force_vector[2] * disp_z)
            
            # Extract stresses (if available from elements)
            # Note: Stress calculation requires post-processing in Kratos
            # For now, we'll return element strain energy if available
            element_energies = []
            try:
                for element in model_part.Elements:
                    # Try to get strain energy from element
                    if element.Has(Kratos.STRAIN_ENERGY):
                        energy = element.GetValue(Kratos.STRAIN_ENERGY)
                        element_energies.append(energy)
            except Exception as e:
                logger.warning(f"Could not extract element energies: {e}")
                element_energies = []
            
            results = {
                "displacements": displacements,
                "num_nodes_with_displacement": len(displacements),
                "compliance": compliance,
                "element_energies": element_energies,
                "num_elements_with_energy": len(element_energies),
                "max_displacement": max([max([abs(coord) for coord in d]) for d in displacements]) if displacements else 0.0
            }
            
            logger.info(f"Results extracted: {len(displacements)} displacements, compliance={compliance:.6e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract analysis results: {e}")
            raise
    
    def get_kratos_version(self) -> str:
        """Get Kratos version information.
        
        Returns:
            Version string
        """
        try:
            # Kratos doesn't have a simple version() method, but we can get it from the banner
            return "10.4.3"  # Based on installation
        except Exception:
            return "unknown"
    
    def check_applications(self) -> Dict[str, bool]:
        """Check which Kratos applications are available.
        
        Returns:
            Dictionary with application names and availability status
        """
        applications = {
            "KratosMultiphysics": True,
            "StructuralMechanicsApplication": True,
            "OptimizationApplication": True,
        }
        
        # Verify StructuralMechanicsApplication
        try:
            _ = StructuralMechanicsApplication
        except ImportError:
            applications["StructuralMechanicsApplication"] = False
        
        # Verify OptimizationApplication
        try:
            _ = OptimizationApplication
        except ImportError:
            applications["OptimizationApplication"] = False
        
        return applications
    
    def get_nodes_from_submodelpart(self, model_part: Any, submodelpart_name: str) -> List[int]:
        """Get node indices from a named submodelpart.
        
        This is used for accessing nodes that were mapped from CAD faces (e.g., by gmsh 
        physical groups or other naming schemes).
        
        Args:
            model_part: Kratos ModelPart
            submodelpart_name: Name of the submodelpart (e.g., "Structure.FixedFace")
            
        Returns:
            List of 0-based node indices in the submodelpart
        """
        try:
            # Try to get submodelpart by name
            if model_part.HasSubModelPart(submodelpart_name):
                sub_part = model_part.GetSubModelPart(submodelpart_name)
                node_indices = [node.Id - 1 for node in sub_part.Nodes]  # Convert 1-based Kratos to 0-based
                logger.info(f"Retrieved {len(node_indices)} nodes from submodelpart '{submodelpart_name}'")
                return node_indices
            else:
                logger.warning(f"Submodelpart '{submodelpart_name}' not found")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get nodes from submodelpart '{submodelpart_name}': {e}")
            raise
    
    def get_nodes_by_coordinate_filter(self, model_part: Any, coordinate: int, 
                                      value: float, tolerance: float = 0.01) -> List[int]:
        """Get node indices by filtering on a specific coordinate (X, Y, or Z).
        
        Useful for selecting boundary nodes without named submodelparts.
        For example, get_nodes_by_coordinate_filter(mp, 2, 0.0, 0.01) gets all nodes 
        where Z ≈ 0 (the bottom face of a model).
        
        Args:
            model_part: Kratos ModelPart
            coordinate: 0 for X, 1 for Y, 2 for Z
            value: Target coordinate value
            tolerance: Tolerance for matching (default 0.01)
            
        Returns:
            List of 0-based node indices matching the filter
        """
        try:
            if coordinate not in [0, 1, 2]:
                raise ValueError(f"coordinate must be 0 (X), 1 (Y), or 2 (Z), got {coordinate}")
            
            coord_name = ['X', 'Y', 'Z'][coordinate]
            node_indices = []
            
            for node in model_part.Nodes:
                node_coord = node.GetSolutionStepValue(Kratos.DISPLACEMENT)
                node_pos = [node.X, node.Y, node.Z]
                if abs(node_pos[coordinate] - value) <= tolerance:
                    node_indices.append(node.Id - 1)  # Convert to 0-based
            
            logger.info(f"Found {len(node_indices)} nodes with {coord_name} ≈ {value} (tolerance ±{tolerance})")
            return node_indices
            
        except Exception as e:
            logger.error(f"Failed to filter nodes by coordinate: {e}")
            raise
    
    def apply_constraint_to_submodelpart(self, model_part: Any, constraint: Any, 
                                        submodelpart_name: str) -> None:
        """Apply constraint to all nodes in a named submodelpart.
        
        This is the correct way to apply boundary conditions after importing a mesh
        with gmsh physical groups (which create named submodelparts).
        
        Args:
            model_part: Kratos ModelPart
            constraint: ConstraintDefinition object from core.study
            submodelpart_name: Name of the submodelpart to apply constraint to
        """
        try:
            node_indices = self.get_nodes_from_submodelpart(model_part, submodelpart_name)
            
            if not node_indices:
                logger.warning(f"No nodes found in submodelpart '{submodelpart_name}', constraint not applied")
                return
            
            self.apply_constraint_from_core(model_part, constraint, node_indices)
            logger.info(f"Constraint applied to submodelpart '{submodelpart_name}' ({len(node_indices)} nodes)")
            
        except Exception as e:
            logger.error(f"Failed to apply constraint to submodelpart: {e}")
            raise
    
    def apply_load_to_submodelpart(self, model_part: Any, load: Any, 
                                  submodelpart_name: str) -> None:
        """Apply load to all nodes in a named submodelpart.
        
        This is the correct way to apply loads after importing a mesh
        with gmsh physical groups (which create named submodelparts).
        
        Args:
            model_part: Kratos ModelPart
            load: LoadDefinition object from core.study
            submodelpart_name: Name of the submodelpart to apply load to
        """
        try:
            node_indices = self.get_nodes_from_submodelpart(model_part, submodelpart_name)
            
            if not node_indices:
                logger.warning(f"No nodes found in submodelpart '{submodelpart_name}', load not applied")
                return
            
            self.apply_load_from_core(model_part, load, node_indices)
            logger.info(f"Load applied to submodelpart '{submodelpart_name}' ({len(node_indices)} nodes)")
            
        except Exception as e:
            logger.error(f"Failed to apply load to submodelpart: {e}")
            raise


def is_kratos_available() -> bool:
    """Check if Kratos Multiphysics is available.
    
    Returns:
        True if Kratos can be imported, False otherwise
    """
    return KRATOS_AVAILABLE


def get_kratos_import_error() -> Optional[str]:
    """Get the error message if Kratos import failed.
    
    Returns:
        Error string or None if import was successful
    """
    return KRATOS_IMPORT_ERROR


def initialize_kratos_adapter() -> KratosAdapter:
    """Factory function to create a Kratos adapter.
    
    Returns:
        KratosAdapter instance
        
    Raises:
        KratosInitializationError: If Kratos is not available
    """
    return KratosAdapter()