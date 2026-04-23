"""
analyzer.py - WFM strategy analysis and ranking logic
"""

import numpy as np


def build_matrix(data_dict, runs_range, oos_range):
    """Build a 2D numpy array from a dict keyed by (runs, oos_pct)."""
    matrix = np.zeros((len(runs_range), len(oos_range)))
    for i, runs in enumerate(runs_range):
        for j, oos in enumerate(oos_range):
            matrix[i, j] = data_dict.get((runs, oos), 0.0)
    return matrix


# ── Stable-zone helpers ───────────────────────────────────────────────────────

def _window_pairwise_dev(patch):
    """
    Sum of |a - b| for all 12 adjacent pairs in a 3×3 window
    (6 horizontal + 6 vertical).  Lower = flatter surface.
    """
    total = 0.0
    for i in range(3):
        for j in range(2):
            total += abs(float(patch[i, j]) - float(patch[i, j + 1]))
    for i in range(2):
        for j in range(3):
            total += abs(float(patch[i, j]) - float(patch[i + 1, j]))
    return total


def _cardinal_max_dev(matrix, ci, cj):
    """
    Max absolute deviation between the center cell and its 4 cardinal neighbors.
    Used to exclude cells sitting on a slope rather than a plateau.
    """
    center = float(matrix[ci, cj])
    n_r, n_c = matrix.shape
    devs = []
    if ci > 0:       devs.append(abs(center - float(matrix[ci - 1, cj])))
    if ci < n_r - 1: devs.append(abs(center - float(matrix[ci + 1, cj])))
    if cj > 0:       devs.append(abs(center - float(matrix[ci, cj - 1])))
    if cj < n_c - 1: devs.append(abs(center - float(matrix[ci, cj + 1])))
    return max(devs) if devs else 0.0


def find_stable_zone(matrix, runs_range, oos_range, window=3, cardinal_threshold=1.5):
    """
    Find the flattest 3×3 region on the surface.

    Algorithm:
      1. For each candidate center compute the max deviation to its 4 cardinal
         neighbors.  Centers where any neighbor deviates more than
         cardinal_threshold are on a slope, not a plateau — exclude them.
      2. Among the surviving centers, pick the one whose 3×3 window has the
         minimum total pairwise adjacency deviation (flattest patch).
      3. If every center fails step 1 (edge case), fall back to the global
         minimum pairwise deviation without the cardinal filter.

    Returns (best_run_config, window_info, zone_score).
    """
    n_runs, n_oos = matrix.shape
    candidates = []

    for i in range(n_runs - window + 1):
        for j in range(n_oos - window + 1):
            ci = i + window // 2
            cj = j + window // 2
            patch = matrix[i : i + window, j : j + window]
            pw_dev = _window_pairwise_dev(patch)
            card_dev = _cardinal_max_dev(matrix, ci, cj)
            mean_val = float(np.mean(patch))
            std_val = float(np.std(patch))
            candidates.append({
                "i_start": i,
                "i_end": i + window,
                "j_start": j,
                "j_end": j + window,
                "center_i": ci,
                "center_j": cj,
                "pw_dev": pw_dev,
                "card_dev": card_dev,
                "mean": mean_val,
                "std": std_val,
                "score": -pw_dev,  # negative so higher = better for callers
            })

    # Step 1: cardinal filter
    filtered = [c for c in candidates if c["card_dev"] < cardinal_threshold]
    pool = filtered if filtered else candidates  # graceful fallback

    # Step 2: minimum pairwise deviation = flattest plateau
    best = min(pool, key=lambda x: x["pw_dev"])

    ci, cj = best["center_i"], best["center_j"]
    best_center = (runs_range[ci], oos_range[cj])
    return best_center, best, best["score"]


# ── WFM / Param-stability checks ─────────────────────────────────────────────

def check_wfm(ps_matrix, center_i, center_j, ps_threshold=0.75, min_green=7, window=3):
    """
    Count 'green' cells (PS >= ps_threshold) in the 3×3 zone around the
    selected center.  Returns (passed, green_count, total_cells, green_pct).
    """
    n_runs, n_oos = ps_matrix.shape
    half = window // 2

    i0 = max(0, center_i - half)
    i1 = min(n_runs, center_i + half + 1)
    j0 = max(0, center_j - half)
    j1 = min(n_oos, center_j + half + 1)

    patch = ps_matrix[i0:i1, j0:j1]
    green_count = int(np.sum(patch >= ps_threshold))
    total = patch.size
    green_pct = green_count / total

    return green_count >= min_green, green_count, total, round(green_pct * 100, 1)


# ── Full analysis pipeline ────────────────────────────────────────────────────

def analyze_strategy(sqx_data, fitness_threshold=0.70, ps_threshold=0.75, min_green=7):
    """
    Full analysis pipeline for a single strategy.

    Steps:
      1. Build Ret/DD, Fitness OOS, and ParametersStability matrices.
      2. Find the most stable zone using the Ret/DD surface
         (cardinal filter + minimum pairwise window deviation).
         Falls back to ParametersStability if Ret/DD is unavailable.
      3. WFM check: count PS >= ps_threshold cells in the 3×3 zone.
      4. Param stability check: PS[center] >= ps_threshold.
      5. Compute composite score and APPROVED / DISCARDED status.
    """
    if sqx_data.get("error"):
        return {
            "strategy_name": sqx_data.get("strategy_name", "Unknown"),
            "file_path": sqx_data.get("file_path", ""),
            "status": "ERROR",
            "error": sqx_data["error"],
        }

    runs_range = sqx_data["runs_range"]
    oos_range = sqx_data["oos_range"]

    if not runs_range or not oos_range:
        return {
            "strategy_name": sqx_data["strategy_name"],
            "file_path": sqx_data.get("file_path", ""),
            "status": "ERROR",
            "error": "Matrix axes not found",
        }

    fitness_matrix = build_matrix(sqx_data["fitness_matrix"], runs_range, oos_range)
    ps_matrix = build_matrix(sqx_data["param_stability"], runs_range, oos_range)
    retdd_matrix = build_matrix(sqx_data.get("retdd_matrix", {}), runs_range, oos_range)

    # Step 1: Stable-zone detection.
    # Prefer the IS Ret/DD surface (directly decoded from binary SQStats index 25)
    # because it is the actual metric shown on the SQX 3D surface.
    # Fall back to ParametersStability when Ret/DD is unavailable.
    if np.any(retdd_matrix > 0):
        zone_matrix = retdd_matrix
        zone_matrix_name = "retdd"
    else:
        zone_matrix = ps_matrix
        zone_matrix_name = "ps"

    best_run, zone_info, zone_score = find_stable_zone(zone_matrix, runs_range, oos_range)

    if best_run is None:
        return {
            "strategy_name": sqx_data["strategy_name"],
            "file_path": sqx_data.get("file_path", ""),
            "status": "ERROR",
            "error": "Could not determine stable zone",
        }

    best_runs, best_oos = best_run
    ci = zone_info["center_i"]
    cj = zone_info["center_j"]

    # Step 2: WFM check using ParametersStability
    # PS >= ps_threshold is the proxy for a "green" cell.
    wfm_pass, green_count, total_cells, green_pct = check_wfm(
        ps_matrix, ci, cj, ps_threshold, min_green
    )

    # Step 3: Param stability check at the selected center
    ps_value = float(ps_matrix[ci, cj])
    ps_pass = ps_value >= ps_threshold

    # Fitness OOS at the selected center
    fitness_at_best = float(fitness_matrix[ci, cj])

    # Composite score (0-1)
    score = (
        0.40 * fitness_at_best
        + 0.40 * ps_value
        + 0.20 * (green_count / total_cells)
    )

    status = "APPROVED" if (wfm_pass and ps_pass) else "DISCARDED"

    return {
        "strategy_name": sqx_data["strategy_name"],
        "file_path": sqx_data.get("file_path", ""),
        "status": status,
        "best_runs": best_runs,
        "best_oos_pct": best_oos,
        "score": round(score, 4),
        "fitness_score": round(fitness_at_best, 4),
        "ps_value": round(ps_value, 4),
        "ps_pass": ps_pass,
        "wfm_pass": wfm_pass,
        "green_count": green_count,
        "total_cells": total_cells,
        "green_pct": green_pct,
        "zone_mean": round(zone_info["mean"], 4),
        "zone_std": round(zone_info["std"], 4),
        "zone_score": round(zone_score, 4),
        "zone_matrix_name": zone_matrix_name,
        # Raw matrices for visualization
        "fitness_matrix": fitness_matrix,
        "ps_matrix": ps_matrix,
        "retdd_matrix": retdd_matrix,
        "runs_range": runs_range,
        "oos_range": oos_range,
        "zone_info": zone_info,
    }


def rank_strategies(results):
    """Sort: APPROVED first (by score desc), then DISCARDED (by score desc), then errors."""
    approved = sorted(
        [r for r in results if r.get("status") == "APPROVED"],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
    discarded = sorted(
        [r for r in results if r.get("status") == "DISCARDED"],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
    errors = [r for r in results if r.get("status") == "ERROR"]
    return approved + discarded + errors
