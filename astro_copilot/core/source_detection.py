"""
Source detection using photutils.detection and automated PSF characterization.
"""

from typing import Any, Dict, List, Optional
import os
import math
import numpy as np
from astropy.io import fits
from astropy.stats import SigmaClip, gaussian_fwhm_to_sigma
from photutils.detection import find_peaks
from photutils.background import MeanBackground

from astro_copilot.utils.serialization import clean_for_json
from astro_copilot.core.fits_io import validate_file_path


def detect_sources(
    file_path: str,
    hdu_index: Optional[int] = None,
    threshold_sigma: float = 5.0,
    fwhm: Optional[float] = None,
    min_separation: float = 10.0,
) -> Dict[str, Any]:
    """
    Automatically detect astronomical sources in a FITS image.

    Args:
        file_path: Path to the FITS file.
        hdu_index: HDU index (if None, auto-selects first 2D image HDU).
        threshold_sigma: Detection threshold in sigma above background (default: 5.0).
        fwhm: Full-width at half-maximum of PSF in pixels (auto-estimated if None).
        min_separation: Minimum separation between detected sources in pixels (default: 10.0).
    """
    is_valid, validation_error = validate_file_path(file_path)
    if not is_valid:
        return {
            "status": "error",
            "error_type": "SecurityError",
            "message": validation_error
        }

    if not os.path.exists(file_path):
        return {
            "status": "error",
            "error_type": "FileNotFoundError",
            "message": f"FITS file not found: '{file_path}'"
        }

    try:
        with fits.open(file_path) as hdul:
            target_idx = 0
            if hdu_index is not None:
                target_idx = hdu_index
            else:
                for idx, hdu in enumerate(hdul):
                    if hdu.data is not None and len(hdu.data.shape) >= 2:
                        target_idx = idx
                        break

            target_hdu = hdul[target_idx]
            if target_hdu.data is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": f"HDU {target_idx} has no data array."
                }

            data = np.asarray(target_hdu.data, dtype=float)
            ny, nx = data.shape[-2:]

            # Estimate background
            sigma_clip = SigmaClip(sigma=3.0, maxiters=5)
            bkg_estimator = MeanBackground(sigma_clip=sigma_clip)
            try:
                background = bkg_estimator(data)
            except Exception:
                background = np.nanmedian(data)

            if np.isnan(background):
                background = 0.0

            # Estimate FWHM if not provided
            estimated_fwhm = fwhm
            if estimated_fwhm is None:
                estimated_fwhm = max(2.0, min(10.0, np.sqrt(nx * ny) / 50.0))

            # Detect sources using find_peaks
            threshold = background + threshold_sigma * np.nanstd(data)
            peaks = find_peaks(
                data,
                threshold=threshold,
                box_size=int(estimated_fwhm) + 1,
                centroid_func=None,
            )

            if len(peaks) == 0:
                return {
                    "status": "success",
                    "file_path": os.path.abspath(file_path),
                    "hdu_index": target_idx,
                    "detection_params": {
                        "threshold_sigma": threshold_sigma,
                        "fwhm_pixels": round(estimated_fwhm, 2),
                        "background_level": round(float(background), 3),
                    },
                    "sources": [],
                    "summary": {
                        "total_sources": 0,
                    }
                }

            # Filter by min_separation
            sources = []
            peaks_array = np.column_stack([peaks["x_peak"], peaks["y_peak"]])

            for i, (x, y) in enumerate(peaks_array):
                # Check distance to already-added sources
                skip = False
                for src in sources:
                    dx = src["x_px"] - x
                    dy = src["y_px"] - y
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < min_separation:
                        skip = True
                        break

                if skip:
                    continue

                # Estimate local SNR
                aperture_rad = estimated_fwhm
                y_int, x_int = int(round(y)), int(round(x))
                rad_int = int(math.ceil(aperture_rad))

                x_min = max(0, x_int - rad_int)
                x_max = min(nx, x_int + rad_int + 1)
                y_min = max(0, y_int - rad_int)
                y_max = min(ny, y_int + rad_int + 1)

                if x_max > x_min and y_max > y_min:
                    stamp = data[y_min:y_max, x_min:x_max]
                    peak_val = float(stamp[y_int - y_min, x_int - x_min]) if (y_int - y_min >= 0 and x_int - x_min >= 0) else float(peaks["peak_value"][i])
                    signal = peak_val - background
                    noise = np.nanstd(stamp)
                    snr = signal / noise if noise > 0 else 0.0
                else:
                    peak_val = float(peaks["peak_value"][i])
                    signal = peak_val - background
                    snr = 0.0

                sources.append({
                    "id": len(sources) + 1,
                    "x_px": round(x, 2),
                    "y_px": round(y, 2),
                    "peak_value": round(peak_val, 3),
                    "signal": round(signal, 3),
                    "snr": round(float(snr), 2),
                })

            return clean_for_json({
                "status": "success",
                "file_path": os.path.abspath(file_path),
                "hdu_index": target_idx,
                "detection_params": {
                    "threshold_sigma": threshold_sigma,
                    "fwhm_pixels": round(estimated_fwhm, 2),
                    "background_level": round(float(background), 3),
                    "min_separation_pixels": min_separation,
                },
                "sources": sources,
                "summary": {
                    "total_sources": len(sources),
                    "median_snr": round(float(np.median([s["snr"] for s in sources])), 2) if len(sources) > 0 else 0.0,
                }
            })

    except Exception as e:
        return clean_for_json({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        })
