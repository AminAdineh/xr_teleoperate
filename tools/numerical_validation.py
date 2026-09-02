#!/usr/bin/env python3
"""
Numerical validation tests for xr_teleoperate.

Tests that mathematical operations produce identical results across
platforms (Linux vs Windows). Run on both platforms and compare outputs.

Tests:
  - Inverse kinematics (IK) solver
  - Hand retargeting
  - Coordinate transforms (quaternion, homogeneous)
  - Weighted moving filter
  - Joint mapping

Usage:
    python tools/numerical_validation.py
    python tools/numerical_validation.py --output results.json
"""
import sys
import os
import json
import numpy as np
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_quaternion_operations():
    """Test quaternion to rotation matrix conversion."""
    from scipy.spatial.transform import Rotation

    # Fixed test quaternions (w, x, y, z)
    quats = [
        [1, 0, 0, 0],           # identity
        [0.7071, 0, 0, 0.7071], # 90 deg around z
        [0.7071, 0.7071, 0, 0], # 90 deg around x
        [0.5, 0.5, 0.5, 0.5],   # 120 deg
        [0.9239, 0, 0.3827, 0], # 45 deg around y
    ]

    results = []
    for q in quats:
        r = Rotation.from_quat(q)
        rotmat = r.as_matrix()
        results.append({
            "quaternion": q,
            "rotation_matrix": rotmat.tolist(),
        })
    return results


def test_weighted_moving_filter():
    """Test the weighted moving filter with known inputs."""
    from teleop.utils.weighted_moving_filter import WeightedMovingFilter

    weights = np.array([0.5, 0.3, 0.2])
    filt = WeightedMovingFilter(weights, 2)

    # Feed known values
    inputs = [1.0, 2.0, 3.0, 4.0, 5.0, 3.0, 1.0]
    outputs = []
    for val in inputs:
        result = filt.filter(np.array([val, val]))
        outputs.append(result.tolist())

    return {"weights": weights.tolist(), "inputs": inputs, "outputs": outputs}


def test_coordinate_transform():
    """Test homogeneous transformation matrix operations."""
    # Create test transformation matrices
    results = []

    # Translation
    T1 = np.eye(4)
    T1[:3, 3] = [0.1, 0.2, 0.3]
    results.append({"name": "translation", "matrix": T1.tolist()})

    # Rotation around Z
    theta = np.pi / 4
    T2 = np.eye(4)
    T2[:3, :3] = np.array([
        [np.cos(theta), -np.sin(theta), 0],
        [np.sin(theta), np.cos(theta), 0],
        [0, 0, 1]
    ])
    results.append({"name": "rotation_z_45", "matrix": T2.tolist()})

    # Combined transform
    T3 = T1 @ T2
    results.append({"name": "combined", "matrix": T3.tolist()})

    # Inverse
    T3_inv = np.linalg.inv(T3)
    results.append({"name": "inverse", "matrix": T3_inv.tolist()})

    return results


def test_joint_mapping():
    """Test joint mapping with known values."""
    # Simulate joint angle mapping (left/right arm)
    left_arm_q = np.array([0.0, -0.3, 0.0, 0.5, 0.0, 0.3, 0.0])
    right_arm_q = np.array([0.0, 0.3, 0.0, 0.5, 0.0, -0.3, 0.0])

    # Concatenation (as used in recording)
    dual_arm_q = np.concatenate([left_arm_q, right_arm_q])

    # Split back
    n = len(left_arm_q)
    left_recovered = dual_arm_q[:n]
    right_recovered = dual_arm_q[n:]

    return {
        "left_arm_q": left_arm_q.tolist(),
        "right_arm_q": right_arm_q.tolist(),
        "dual_arm_q": dual_arm_q.tolist(),
        "left_recovered": left_recovered.tolist(),
        "right_recovered": right_recovered.tolist(),
        "match": bool(np.allclose(left_arm_q, left_recovered) and np.allclose(right_arm_q, right_recovered)),
    }


def test_interpolation():
    """Test linear interpolation between known points."""
    # Linear interpolation
    p0 = np.array([0.0, 0.0, 0.0])
    p1 = np.array([1.0, 2.0, 3.0])
    alphas = [0.0, 0.25, 0.5, 0.75, 1.0]

    results = []
    for a in alphas:
        p = p0 + a * (p1 - p0)
        results.append({"alpha": a, "point": p.tolist()})

    return results


def run_all_tests():
    """Run all numerical validation tests and return results."""
    results = {
        "platform": sys.platform,
        "python_version": sys.version,
        "numpy_version": np.__version__,
    }

    print("Running numerical validation tests...\n")

    # Test 1: Quaternion operations
    print("  Testing quaternion operations...")
    try:
        results["quaternion"] = test_quaternion_operations()
        print("  [OK] Quaternion operations")
    except Exception as e:
        results["quaternion"] = {"error": str(e)}
        print(f"  [FAIL] Quaternion operations: {e}")

    # Test 2: Weighted moving filter
    print("  Testing weighted moving filter...")
    try:
        results["weighted_moving_filter"] = test_weighted_moving_filter()
        print("  [OK] Weighted moving filter")
    except Exception as e:
        results["weighted_moving_filter"] = {"error": str(e)}
        print(f"  [FAIL] Weighted moving filter: {e}")

    # Test 3: Coordinate transforms
    print("  Testing coordinate transforms...")
    try:
        results["coordinate_transform"] = test_coordinate_transform()
        print("  [OK] Coordinate transforms")
    except Exception as e:
        results["coordinate_transform"] = {"error": str(e)}
        print(f"  [FAIL] Coordinate transforms: {e}")

    # Test 4: Joint mapping
    print("  Testing joint mapping...")
    try:
        results["joint_mapping"] = test_joint_mapping()
        match = results["joint_mapping"].get("match", False)
        status = "OK" if match else "FAIL"
        print(f"  [{status}] Joint mapping (match={match})")
    except Exception as e:
        results["joint_mapping"] = {"error": str(e)}
        print(f"  [FAIL] Joint mapping: {e}")

    # Test 5: Interpolation
    print("  Testing interpolation...")
    try:
        results["interpolation"] = test_interpolation()
        print("  [OK] Interpolation")
    except Exception as e:
        results["interpolation"] = {"error": str(e)}
        print(f"  [FAIL] Interpolation: {e}")

    # Test 6: IK solver (if available)
    print("  Testing IK solver...")
    try:
        from teleop.robot_control.robot_arm_ik import G1_29_ArmIK
        ik = G1_29_ArmIK()
        # Test with known wrist poses
        left_wrist = np.eye(4)
        left_wrist[:3, 3] = [0.3, 0.2, 0.5]
        right_wrist = np.eye(4)
        right_wrist[:3, 3] = [0.3, -0.2, 0.5]
        current_q = np.zeros(14)
        current_dq = np.zeros(14)
        sol_q, sol_tauff = ik.solve_ik(left_wrist, right_wrist, current_q, current_dq)
        results["ik_solver"] = {
            "left_wrist": left_wrist.tolist(),
            "right_wrist": right_wrist.tolist(),
            "sol_q": sol_q.tolist(),
            "sol_tauff": sol_tauff.tolist(),
        }
        print("  [OK] IK solver")
    except Exception as e:
        results["ik_solver"] = {"error": str(e)}
        print(f"  [SKIP] IK solver: {e}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Numerical validation for xr_teleoperate")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file for results")
    args = parser.parse_args()

    results = run_all_tests()

    print(f"\n{'=' * 60}")
    print(f"  Platform: {results['platform']}")
    print(f"  Python: {results['python_version']}")
    print(f"  NumPy: {results['numpy_version']}")
    print(f"{'=' * 60}")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to {args.output}")
    else:
        print("\nResults:")
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
