"""
parser.py - SQX file parser for WFM Analyzer
Extracts fitness matrix, parameter stability, RetDD matrix and run configs from .sqx files.
"""

import base64
import struct
import zipfile
import re
from pathlib import Path


def _decode_retdd_blob(b64_data):
    """
    Extract the Ret/DD Ratio (stat index 25) from a base64-encoded SQStats binary blob.
    Binary format: repeating 0x03 <index_byte> <4-byte big-endian float>.
    Returns the last occurrence of index 25, or None if not found.
    """
    try:
        raw = base64.b64decode(b64_data + "==")
    except Exception:
        return None
    val = None
    i = 0
    while i < len(raw) - 5:
        if raw[i] == 0x03 and raw[i + 1] == 25:
            val = struct.unpack(">f", raw[i + 2 : i + 6])[0]
        i += 1
    return val


def parse_sqx(file_path):
    """
    Parse a StrategyQuant .sqx file and extract key WFM metrics.

    Returns a dict with:
      strategy_name, fitness_matrix, param_stability, retdd_matrix,
      runs_range, oos_range, conditions, error
    """
    result = {
        "strategy_name": "",
        "file_path": str(file_path),
        "fitness_matrix": {},   # (runs, oos_pct) -> float  (OOS Fitness 0-1)
        "param_stability": {},  # (runs, oos_pct) -> float  (ParametersStability)
        "retdd_matrix": {},     # (runs, oos_pct) -> float  (IS Ret/DD Ratio, index 25)
        "runs_range": [],
        "oos_range": [],
        "conditions": {
            "threshold_pct": 80,
            "rows": 3,
            "cols": 3,
            "min_comb": 7,
        },
        "error": None,
    }

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            if "settings.xml" not in z.namelist():
                result["error"] = "settings.xml not found inside .sqx"
                return result
            with z.open("settings.xml") as xml_file:
                content = xml_file.read().decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        result["error"] = "File is not a valid .sqx (not a ZIP archive)"
        return result
    except Exception as e:
        result["error"] = f"Could not open file: {e}"
        return result

    # --- Strategy name ---
    name_match = re.search(r'<ResultsGroup ResultName="([^"]+)"', content)
    result["strategy_name"] = (
        name_match.group(1) if name_match else Path(file_path).stem
    )

    # --- Matrix axes (OOS% range and Runs range) ---
    mr_match = re.search(
        r'<MatrixResult start1="(\d+)" stop1="(\d+)" increment1="(\d+)" '
        r'start2="(\d+)" stop2="(\d+)" increment2="(\d+)"',
        content,
    )
    if mr_match:
        oos_start = int(mr_match.group(1))
        oos_stop = int(mr_match.group(2))
        oos_inc = int(mr_match.group(3))
        runs_start = int(mr_match.group(4))
        runs_stop = int(mr_match.group(5))
        runs_inc = int(mr_match.group(6))
        result["oos_range"] = list(range(oos_start, oos_stop + 1, oos_inc))
        result["runs_range"] = list(range(runs_start, runs_stop + 1, runs_inc))
    else:
        result["error"] = "WFM MatrixResult not found — file may not contain WF data"
        return result

    # --- Per-run-config data (Fitness OOS + IS Ret/DD binary) ---
    for m in re.finditer(
        r'<Result resultKey="WF: (\d+) runs : (\d+) % OOS".*?</Result>',
        content,
        re.DOTALL,
    ):
        runs = int(m.group(1))
        oos = int(m.group(2))
        block = m.group(0)
        key = (runs, oos)

        # OOS Fitness (0-1 normalized)
        fit_m = re.search(r'<Fitnesses[^/]*\bOOS="([^"]+)"', block)
        if fit_m:
            result["fitness_matrix"][key] = float(fit_m.group(1))

        # IS Ret/DD Ratio from binary SQStats blob.
        # The blob tagged with direction_DD_1 (long) + sample_DD_127 (all-sample aggregate)
        # contains the combined IS performance metrics at stat index 25.
        blob_m = re.search(
            r'stats_[^<]*direction_DD_1[^<]*sample_DD_127[^<]*'
            r'type="com\.strategyquant\.tradinglib\.SQStats">'
            r'<SQStats[^>]+e="b64">([^<]+)<',
            block,
        )
        if blob_m:
            val = _decode_retdd_blob(blob_m.group(1))
            if val is not None and val > 0:
                result["retdd_matrix"][key] = val

    # --- ParametersStability per run configuration ---
    for m in re.finditer(
        r'<ParametersStability_WF_(\d+)_runs_(\d+)_OOS[^>]* type="Double">([\d.]+)<',
        content,
    ):
        runs, oos, val = int(m.group(1)), int(m.group(2)), float(m.group(3))
        result["param_stability"][(runs, oos)] = val

    # --- WalkForward conditions thresholds ---
    cond_match = re.search(
        r'<Conditions thresholdPct="(\d+)" robCombRows="(\d+)" '
        r'robCombCols="(\d+)" robMinComb="(\d+)"',
        content,
    )
    if cond_match:
        result["conditions"] = {
            "threshold_pct": int(cond_match.group(1)),
            "rows": int(cond_match.group(2)),
            "cols": int(cond_match.group(3)),
            "min_comb": int(cond_match.group(4)),
        }

    # Validate we got data
    if not result["fitness_matrix"]:
        result["error"] = "No fitness data found — check if WF Matrix was computed"

    return result
