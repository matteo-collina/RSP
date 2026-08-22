"""
PyTorch port of the gray-world underwater color-correction pipeline used
by Wildflow.ai (https://wildflow.ai), and compatible with it: this
implements the same method, so imagery graded here matches what that
pipeline produces. With thanks to Sergei Nozdrenkov (wildflow.ai) for the
original, published at https://gist.github.com/nozdrenkov/e3aece3dd78489fb7862ea2bbdef0e65.

"""

import threading

import cv2
import numpy as np


# Curated for underwater/GoPro reef photography rather than the gist's one
# generic example - see PLAN discussion for per-parameter reasoning.
# dehaze_omega is intentionally not user-facing (see DEFAULT_PARAMS below,
# and image_enhancement.py's PARAM_SPECS): it's an internal dark-channel-prior
# tuning constant, not something meaningfully judged by eye.
DEFAULT_PARAMS = {
    "gray_world": 1.0,
    "warmth": 0.0,
    "tint": 0.0,
    "saturation": 1.1,
    "blue_reduction": 0.3,
    "brightness": 0.0,
    "contrast": 0.10,
    "shadows": 0.10,
    "blacks": 0.05,
    "highlights": 0.10,
    "dehaze_strength": 0.15,
    "dehaze_omega": 0.9,
}

_device = None

# The enhancement phase runs its images across a ThreadPoolExecutor (see
# pipeline._apply_enhancement_multithreaded), but torch's Metal backend is
# not safe to drive from several Python threads at once: with 3 or more
# workers the whole process deadlocks permanently, reproducibly, with no
# error -- 1 or 2 workers, and the CPU backend at any worker count, are
# fine. So every tensor operation here happens under this lock. Image
# decode, JPEG encode and EXIF handling stay outside it and keep running
# in parallel, which is where a batch's wall-clock time actually goes:
# the GPU work is a fraction of a second per image.
_compute_lock = threading.Lock()


def _get_device():
    global _device
    if _device is None:
        try:
            import torch
        except OSError as e:
            # In dev mode this means PyQt6 was imported before torch (its
            # bundled stale MSVC runtime shadowed System32's) -- see
            # warmup(). In a packaged exe it means rsp.spec's runtime-DLL
            # filtering regressed.
            raise RuntimeError(
                "Failed to load torch's native libraries, most likely "
                "because a stale MSVC runtime DLL shadowed the system one "
                "(PyQt6 imported before torch?). See gray_world.warmup() "
                "for the mechanism and the required load order."
            ) from e
        _device = torch.device(
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )
    return _device


def _to_tensor(x):
    import torch
    device = _get_device()
    if isinstance(x, torch.Tensor):
        return x.to(device, dtype=torch.float32)
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def _broadcast(values):
    arr = _to_tensor(values)
    return arr[:, None, None, None]


def _mean_channels(batch):
    return batch.mean(dim=(1, 2), keepdim=True)


def _adjust_gray_world(batch, amount):
    base = _mean_channels(batch)
    scale = base.mean(dim=-1, keepdim=True) / (base + 1e-6)
    mix = amount.clamp(0.0, 1.0)[:, None, None, None]
    return (batch * (scale * mix + 1.0 - mix)).clamp(0, 255)


def _adjust_warmth(batch, warmth):
    import torch
    s = torch.tanh(warmth.clamp(-4.0, 4.0) * 0.35)
    gains = torch.stack([1.0 + s * 0.4, 1.0 - s * 0.1, 1.0 - s * 0.5], dim=1)[:, None, None, :]
    return (batch * gains).clamp(0, 255)


def _adjust_tint(batch, tint):
    import torch
    s = torch.tanh(tint.clamp(-4.0, 4.0) * 0.4)
    gains = torch.stack([1.0 - s * 0.35, 1.0 + s * 0.45, 1.0 - s * 0.35], dim=1)[:, None, None, :]
    return (batch * gains).clamp(0, 255)


def _adjust_saturation(batch, factor):
    import torch
    device = _get_device()
    factor = factor.clamp(0.0, 3.0)[:, None, None, None]
    lum = (batch * torch.tensor([0.299, 0.587, 0.114], device=device)).sum(dim=-1, keepdim=True)
    return (lum + factor * (batch - lum)).clamp(0, 255)


def _reduce_blue_cast(batch, amount):
    import torch
    amount = amount.clamp(0.0, 1.0)[:, None, None, None]
    r, g, b = batch[..., 0:1], batch[..., 1:2], batch[..., 2:3]
    dominance = ((b - torch.maximum(r, g)) / 255.0).clamp(0.0, 1.0)
    b = (b - amount * dominance * 80.0).clamp(0, 255)
    return torch.cat([r, g, b], dim=-1)


def _adjust_brightness_contrast(batch, brightness, contrast):
    b = brightness.clamp(-1.0, 1.0)[:, None, None, None] * 50.0
    c = 1.0 + contrast.clamp(-1.0, 1.0)[:, None, None, None]
    return ((batch - 127.5) * c + 127.5 + b).clamp(0, 255)


def _lift_shadows(batch, amount):
    amount = amount.clamp(0.0, 1.0)[:, None, None, None]
    mask = (1.0 - _mean_channels(batch) / 255.0).pow(2.0)
    return (batch + amount * mask * 80.0).clamp(0, 255)


def _lift_blacks(batch, amount):
    amount = amount.clamp(0.0, 1.0)[:, None, None, None]
    mask = (1.0 - _mean_channels(batch) / 255.0).pow(4.0)
    return (batch + amount * mask * 60.0).clamp(0, 255)


def _tame_highlights(batch, amount):
    amount = amount.clamp(0.0, 1.0)[:, None, None, None]
    mask = (_mean_channels(batch) / 255.0).pow(2.0)
    return (batch - amount * mask * 120.0).clamp(0, 255)


def _dehaze(batch, strength, omega):
    import torch
    norm = batch / 255.0
    dark = norm.min(dim=-1, keepdim=True).values
    flat = dark.reshape(dark.shape[0], -1)
    if flat.shape[1] > 1_000_000:
        idx = torch.randperm(flat.shape[1], device=flat.device)[:1_000_000]
        flat = flat[:, idx]
    atm = torch.quantile(flat, 0.99, dim=1)[:, None, None, None]
    omega_b = _broadcast(omega.clamp(0.1, 1.0))
    trans = (1.0 - omega_b * (dark / (atm + 1e-6))).clamp(0.1, 1.0)
    dehazed = (((norm - atm) / (trans + 1e-6)) + atm).clamp(0.0, 1.0) * 255.0
    strength_b = _broadcast(strength.clamp(0.0, 1.0))
    return batch + (dehazed - batch) * strength_b


def _process_batch(batch, params):
    """batch: float32 tensor, shape (N, H, W, 3), RGB, 0-255."""
    import torch
    with torch.inference_mode():
        p = {k: _to_tensor([v]) for k, v in params.items()}
        batch = _adjust_gray_world(batch, p["gray_world"].clamp(0.0, 1.0))
        batch = _adjust_warmth(batch, p["warmth"])
        batch = _adjust_tint(batch, p["tint"])
        batch = _adjust_saturation(batch, p["saturation"])
        batch = _reduce_blue_cast(batch, p["blue_reduction"])
        batch = _adjust_brightness_contrast(batch, p["brightness"], p["contrast"])
        batch = _lift_shadows(batch, p["shadows"])
        batch = _lift_blacks(batch, p["blacks"])
        batch = _tame_highlights(batch, p["highlights"])
        batch = _dehaze(batch, p["dehaze_strength"], p["dehaze_omega"])
        return batch.cpu().numpy()


def apply_gray_world_enhancement(image, **params):
    """Apply the gray-world/dehaze pipeline to one image.

    Args:
        image (numpy.ndarray): Input image, BGR uint8 (OpenCV convention,
            matching apply_clahe_enhancement's contract).
        **params: any of DEFAULT_PARAMS' keys; missing ones use their default.

    Returns:
        numpy.ndarray: Enhanced image, BGR uint8.
    """
    if image is None:
        raise ValueError("Input image cannot be None")
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a 3-channel BGR image")

    resolved = dict(DEFAULT_PARAMS)
    resolved.update(params)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
    with _compute_lock:  # torch's MPS backend deadlocks under concurrency
        batch_in = _to_tensor(rgb[None, ...])
        result = _process_batch(batch_in, resolved)[0]
    result = np.clip(result, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)


_DEVICE_DISPLAY_NAMES = {
    "cuda": "NVIDIA GPU (CUDA)",
    "mps": "Apple Silicon (Metal)",
    "cpu": "CPU",
}


def get_device_name():
    """Human-readable device the pipeline will run on (for status/reporting)."""
    return _get_device().type


def get_device_display_name():
    """User-facing label for the detected device, e.g. for a status bar."""
    return _DEVICE_DISPLAY_NAMES.get(get_device_name(), get_device_name())


def warmup():
    """Force torch's lazy import + native DLL init to happen now.

    Must run before PyQt6 is imported anywhere in this process: PyQt6
    ships stale MSVC runtime copies (msvcp140/vcruntime140) in its
    Qt6/bin directory and puts that directory on the DLL search path at
    import, and torch's c10.dll needs a newer runtime than those -- so
    importing torch afterward fails with "WinError 1114: DLL
    initialization routine failed". Loading torch first resolves its
    runtime deps from System32's current redistributable, and they stay
    loaded for the whole process.

    torch is imported lazily (inside functions, not at module load) so
    CLAHE-only or no-enhancement runs never pay PyTorch's import cost --
    which is what makes this ordering something callers have to manage.
    rsp.py's run_gui() calls this before importing PyQt6 (it can't know
    in advance whether the user will pick this method); CLI mode never
    touches PyQt6 and only warms up when this method is requested.

    The packaged onefile .exe has its own variant of the same bug --
    stale runtime copies harvested off the build machine's PATH get
    bundled at the extraction root -- fixed at the build level in
    rsp.spec, not here (runtime PATH manipulation is provably
    ineffective: torch loads its DLLs with search flags that don't
    consult PATH at all).
    """
    _get_device()
