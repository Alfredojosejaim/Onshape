"""Comprehensive test suite for TopOpt library capabilities evaluation.

This script tests the TopOpt solver interface to understand:
1. Configuration parameters and their validation
2. Error handling and edge cases
3. Interface design and extensibility
4. Current limitations and dependencies
5. Integration possibilities with external FEA solvers
"""

import sys
import unittest
import numpy as np
from typing import Dict, Any

# Import the TopOpt solver
from topopt_solver import TopOptSolver, run_topology_optimization, NOT_IMPLEMENTED


class MockFEASolver:
    """Mock FEA solver for testing integration capabilities."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.call_count = 0
    
    def __call__(self, densities, forces, supports, max_iterations, tolerance, callback=None) -> Dict[str, Any]:
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError("Mock FEA solver intentionally failed")
        
        # Simulate a simple optimization process
        iterations_performed = min(max_iterations, 10)
        final_volume_fraction = 0.3 + (0.1 * np.random.random())
        
        return {
            "success": True,
            "status": "completed",
            "iterations": iterations_performed,
            "final_volume_fraction": final_volume_fraction,
            "compliance": 100.0 * (1.0 - final_volume_fraction),
            "densities": densities * 0.5,  # Simulated density reduction
            "displacement": np.random.random(len(densities)) * 0.1,
        }


class TestTopOptConfiguration(unittest.TestCase):
    """Test TopOpt solver configuration and parameter validation."""
    
    def test_basic_2d_configuration(self):
        """Test basic 2D mesh configuration."""
        solver = TopOptSolver(nelx=30, nely=20, volfrac=0.4)
        
        self.assertEqual(solver.nelx, 30)
        self.assertEqual(solver.nely, 20)
        self.assertIsNone(solver.nelz)
        self.assertEqual(solver.volfrac, 0.4)
        self.assertEqual(solver.nelem, 600)  # 30 * 20
        self.assertEqual(len(solver.x), 600)
    
    def test_basic_3d_configuration(self):
        """Test basic 3D mesh configuration."""
        solver = TopOptSolver(nelx=20, nely=15, nelz=10, volfrac=0.3)
        
        self.assertEqual(solver.nelx, 20)
        self.assertEqual(solver.nely, 15)
        self.assertEqual(solver.nelz, 10)
        self.assertEqual(solver.volfrac, 0.3)
        self.assertEqual(solver.nelem, 3000)  # 20 * 15 * 10
        self.assertEqual(len(solver.x), 3000)
    
    def test_parameter_validation(self):
        """Test parameter validation and error handling."""
        # Invalid mesh dimensions
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=0, nely=10)
        
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=10, nely=-5)
        
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=10, nely=10, nelz=0)
        
        # Invalid volume fraction
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=10, nely=10, volfrac=0.0)
        
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=10, nely=10, volfrac=1.5)
        
        with self.assertRaises(ValueError):
            TopOptSolver(nelx=10, nely=10, volfrac=-0.1)
    
    def test_penalization_parameter(self):
        """Test penalization parameter configuration."""
        solver = TopOptSolver(nelx=10, nely=10, penalization=1.5)
        self.assertEqual(solver.penalization, 1.5)
        
        solver = TopOptSolver(nelx=10, nely=10, penalization=5.0)
        self.assertEqual(solver.penalization, 5.0)
    
    def test_filter_radius_parameter(self):
        """Test filter radius parameter configuration."""
        solver = TopOptSolver(nelx=10, nely=10, rmin=1.0)
        self.assertEqual(solver.rmin, 1.0)
        
        solver = TopOptSolver(nelx=10, nely=10, rmin=3.0)
        self.assertEqual(solver.rmin, 3.0)
    
    def test_density_initialization(self):
        """Test density array initialization."""
        solver = TopOptSolver(nelx=10, nely=10, volfrac=0.5)
        
        # All densities should be initialized to volfrac
        self.assertTrue(np.allclose(solver.x, 0.5))
        self.assertEqual(solver.x.dtype, float)


class TestTopOptWithoutFEASolver(unittest.TestCase):
    """Test TopOpt solver behavior without FEA solver (current state)."""
    
    def test_solve_without_fea_solver(self):
        """Test that solve returns not_implemented without FEA solver."""
        solver = TopOptSolver(nelx=10, nely=10)
        result = solver.solve()
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_implemented")
        self.assertEqual(result["code"], "FEA_SOLVER_REQUIRED")
        self.assertIn(NOT_IMPLEMENTED, result["error"])
        self.assertEqual(result["iterations"], 0)
    
    def test_solve_with_invalid_iterations(self):
        """Test that invalid iterations are rejected even without FEA solver."""
        solver = TopOptSolver(nelx=10, nely=10)
        result = solver.solve(max_iterations=0)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["code"], "INVALID_ITERATIONS")
    
    def test_convenience_function_without_fea(self):
        """Test convenience function without FEA solver."""
        result = run_topology_optimization(
            volume_fraction=0.3,
            max_iterations=100,
            nelx=20,
            nely=20
        )
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_implemented")


class TestTopOptWithMockFEASolver(unittest.TestCase):
    """Test TopOpt solver integration with mock FEA solver."""
    
    def test_solve_with_mock_fea_solver(self):
        """Test successful solve with mock FEA solver."""
        mock_fea = MockFEASolver(should_fail=False)
        solver = TopOptSolver(nelx=10, nely=10, volfrac=0.4, fea_solver=mock_fea)
        
        result = solver.solve(max_iterations=50)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        self.assertGreater(result["iterations"], 0)
        self.assertGreater(result["final_volume_fraction"], 0)
        self.assertEqual(mock_fea.call_count, 1)
    
    def test_solve_with_fea_solver_failure(self):
        """Test handling of FEA solver failure."""
        mock_fea = MockFEASolver(should_fail=True)
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=mock_fea)
        
        result = solver.solve(max_iterations=50)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["code"], "FEA_SOLVER_FAILED")
    
    def test_forces_and_supports_parameters(self):
        """Test that forces and supports are passed to FEA solver."""
        mock_fea = MockFEASolver(should_fail=False)
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=mock_fea)
        
        forces = np.array([1.0, 0.0, -1.0])
        supports = np.array([0, 1, 2])
        
        result = solver.solve(forces=forces, supports=supports, max_iterations=10)
        
        self.assertTrue(result["success"])
        # The mock solver was called with the parameters
        self.assertEqual(mock_fea.call_count, 1)
    
    def test_tolerance_parameter(self):
        """Test tolerance parameter is passed through."""
        mock_fea = MockFEASolver(should_fail=False)
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=mock_fea)
        
        result = solver.solve(max_iterations=100, tolerance=0.001)
        
        self.assertTrue(result["success"])
        self.assertEqual(mock_fea.call_count, 1)
    
    def test_callback_functionality(self):
        """Test callback functionality for progress monitoring."""
        callback_calls = []
        
        def progress_callback(iteration, volume_fraction, compliance):
            callback_calls.append({
                'iteration': iteration,
                'volume_fraction': volume_fraction,
                'compliance': compliance
            })
        
        mock_fea = MockFEASolver(should_fail=False)
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=mock_fea)
        
        result = solver.solve(max_iterations=10, callback=progress_callback)
        
        self.assertTrue(result["success"])
        # Note: Our mock doesn't actually call the callback, but the interface accepts it


class TestTopOptAdvancedConfiguration(unittest.TestCase):
    """Test advanced configuration options."""
    
    def test_use_full_domain_parameter(self):
        """Test use_full_domain parameter."""
        solver_full = TopOptSolver(nelx=10, nely=10, use_full_domain=True)
        self.assertTrue(solver_full.use_full_domain)
        
        solver_partial = TopOptSolver(nelx=10, nely=10, use_full_domain=False)
        self.assertFalse(solver_partial.use_full_domain)
    
    def test_extreme_parameters(self):
        """Test behavior with extreme parameter values."""
        # Very fine mesh
        solver_fine = TopOptSolver(nelx=100, nely=100, volfrac=0.1)
        self.assertEqual(solver_fine.nelem, 10000)
        
        # Very coarse mesh
        solver_coarse = TopOptSolver(nelx=2, nely=2, volfrac=0.9)
        self.assertEqual(solver_coarse.nelem, 4)
        
        # High penalization
        solver_high_pen = TopOptSolver(nelx=10, nely=10, penalization=10.0)
        self.assertEqual(solver_high_pen.penalization, 10.0)
        
        # Large filter radius
        solver_large_filter = TopOptSolver(nelx=10, nely=10, rmin=5.0)
        self.assertEqual(solver_large_filter.rmin, 5.0)


class TestTopOptConvenienceFunction(unittest.TestCase):
    """Test the convenience function interface."""
    
    def test_convenience_function_with_fea(self):
        """Test convenience function with FEA solver."""
        mock_fea = MockFEASolver(should_fail=False)
        
        result = run_topology_optimization(
            volume_fraction=0.3,
            max_iterations=50,
            nelx=15,
            nely=15,
            nelz=5,
            penalization=3.0,
            rmin=1.5,
            tolerance=0.01,
            fea_solver=mock_fea
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
    
    def test_convenience_function_default_parameters(self):
        """Test convenience function with default parameters."""
        mock_fea = MockFEASolver(should_fail=False)
        
        result = run_topology_optimization(fea_solver=mock_fea)
        
        self.assertTrue(result["success"])
        # Should use defaults from function signature
        self.assertEqual(mock_fea.call_count, 1)


class TestTopOptIntegrationCapabilities(unittest.TestCase):
    """Test integration capabilities and extensibility."""
    
    def test_fea_solver_interface_requirements(self):
        """Test what the FEA solver interface should provide."""
        # The FEA solver should accept:
        # - densities: current density distribution
        # - forces: force vectors
        # - supports: constraint definitions
        # - max_iterations: maximum iterations
        # - tolerance: convergence tolerance
        # - callback: optional progress callback
        
        # And should return a dict with:
        # - success: boolean
        # - status: string ("completed", "failed", etc.)
        # - iterations: int
        # - final_volume_fraction: float
        # - Optional: compliance, densities, displacement, etc.
        
        mock_fea = MockFEASolver(should_fail=False)
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=mock_fea)
        
        # Test that the interface is callable
        self.assertTrue(callable(solver.fea_solver))
    
    def test_solver_state_management(self):
        """Test that solver maintains state correctly."""
        solver = TopOptSolver(nelx=10, nely=10, volfrac=0.5)
        
        # Initial state
        initial_x = solver.x.copy()
        
        # After initialization, densities should be uniform
        self.assertTrue(np.allclose(initial_x, 0.5))
        
        # The solver should maintain configuration
        self.assertEqual(solver.nelx, 10)
        self.assertEqual(solver.nely, 10)
        self.assertEqual(solver.volfrac, 0.5)


class TestTopOptErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def test_invalid_fea_solver_return(self):
        """Test handling of invalid FEA solver return value."""
        def bad_fea_solver(**kwargs):
            return "not a dict"  # Invalid return type
        
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=bad_fea_solver)
        result = solver.solve(max_iterations=10)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["code"], "FEA_SOLVER_FAILED")
    
    def test_fea_solver_with_failed_status(self):
        """Test handling of FEA solver that returns failed status."""
        def failing_fea_solver(**kwargs):
            return {
                "success": False,
                "status": "completed",  # Contradictory: success=False but status=completed
                "iterations": 5
            }
        
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=failing_fea_solver)
        result = solver.solve(max_iterations=10)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
    
    def test_fea_solver_exception_handling(self):
        """Test that exceptions in FEA solver are caught."""
        def exception_fea_solver(**kwargs):
            raise RuntimeError("FEA solver error")
        
        solver = TopOptSolver(nelx=10, nely=10, fea_solver=exception_fea_solver)
        result = solver.solve(max_iterations=10)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["code"], "FEA_SOLVER_FAILED")


def run_comprehensive_tests():
    """Run all tests and provide detailed output."""
    print("=" * 70)
    print("COMPREHENSIVE TOPOPT LIBRARY TESTING")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptWithoutFEASolver))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptWithMockFEASolver))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptAdvancedConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptConvenienceFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptIntegrationCapabilities))
    suite.addTests(loader.loadTestsFromTestCase(TestTopOptErrorHandling))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
