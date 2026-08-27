print("Before import")
import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication as SMA
print("After import")

print("Checking if POINT_LOAD exists in SMA...")
try:
    pl = SMA.POINT_LOAD
    print(f"POINT_LOAD exists: {pl}")
except AttributeError as e:
    print(f"POINT_LOAD does not exist in SMA: {e}")

print("Checking for POINT_LOAD_Y...")
try:
    ply = SMA.POINT_LOAD_Y
    print(f"POINT_LOAD_Y exists: {ply}")
except AttributeError as e:
    print(f"POINT_LOAD_Y does not exist in SMA: {e}")

print("Listing available attributes...")
attrs = [a for a in dir(SMA) if 'LOAD' in a.upper()]
print(f"Attributes with 'LOAD': {attrs}")
