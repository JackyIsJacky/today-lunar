import os

import numpy as np

CUDA_AVAILABLE = False
DEVICE = "cpu"

try:
    import cupy as cp
    CUDA_AVAILABLE = True
except ImportError:
    pass

if not CUDA_AVAILABLE:
    try:
        import torch
        if torch.cuda.is_available():
            CUDA_AVAILABLE = True
    except ImportError:
        pass


def detect_device():
    global DEVICE
    from config import Config

    forced = Config.DEVICE
    if forced == "cuda" and CUDA_AVAILABLE:
        DEVICE = "cuda"
    elif forced == "cpu":
        DEVICE = "cpu"
    elif CUDA_AVAILABLE:
        DEVICE = "cuda"
    else:
        DEVICE = "cpu"

    if DEVICE == "cuda":
        try:
            import cupy as cp
            _ = cp.array([1.0])
        except Exception:
            DEVICE = "cpu"

    print(f"[DEVICE] Using: {DEVICE}")
    return DEVICE


def get_array_module():
    if DEVICE == "cuda":
        import cupy
        return cupy
    return np


def to_device(arr):
    xp = get_array_module()
    if isinstance(arr, xp.ndarray):
        return arr
    return xp.asarray(arr)


def to_cpu(arr):
    if hasattr(arr, "get"):
        return arr.get()
    if hasattr(arr, "cpu"):
        return arr.cpu().numpy()
    return np.asarray(arr)


def compute_sma(data, period):
    xp = get_array_module()
    arr = xp.asarray(data, dtype=xp.float64)
    result = xp.zeros(len(arr), dtype=xp.float64)
    result[:] = xp.nan
    if len(arr) >= period:
        cumsum = xp.cumsum(arr, dtype=xp.float64)
        result[period - 1:] = (cumsum[period - 1:] - xp.pad(cumsum[:-period], (period, 0), constant_values=0)[period - 1:]) / period
    return to_cpu(result)
