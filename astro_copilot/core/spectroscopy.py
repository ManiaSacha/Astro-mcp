"""
1D Spectrum extraction and wavelength calibration for spectroscopic FITS data.
"""

from typing import Any, Dict, List, Optional
import os
import numpy as np
from astropy.io import fits
from scipy.signal import find_peaks

from astro_copilot.utils.serialization import clean_for_json
from astro_copilot.core.fits_io import validate_file_path


def extract_1d_spectrum(
    file_path: str,
    hdu_index: Optional[int] = None,
    extraction_method: str = "sum",
    row_range: Optional[List[int]] = None,
    wavelength_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extracts a 1D spectrum from 2D spectroscopic data.

    Args:
        file_path: Path to the FITS spectroscopic data (2D image).
        hdu_index: HDU index to extract (auto-selects first 2D image if None).
        extraction_method: "sum" (sum all rows), "median" (median), or "center" (central row only).
        row_range: [row_min, row_max] to extract (if None, uses full spatial dimension).
        wavelength_key: Header keyword for wavelength calibration (e.g., 'CRVAL1' for RA-based guess).

    Returns:
        Dictionary with extracted spectrum, wavelengths, and diagnostics.
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
            if len(data.shape) != 2:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": f"Expected 2D spectroscopic data; got shape {data.shape}"
                }

            ny, nx = data.shape
            header = target_hdu.header

            # Determine spatial extraction range
            row_min, row_max = 0, ny
            if row_range is not None:
                row_min = max(0, row_range[0])
                row_max = min(ny, row_range[1])

            if row_max <= row_min:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": f"Invalid row_range: {row_range}"
                }

            # Extract 1D spectrum
            if extraction_method.lower() == "sum":
                spectrum_1d = np.sum(data[row_min:row_max, :], axis=0)
            elif extraction_method.lower() == "median":
                spectrum_1d = np.median(data[row_min:row_max, :], axis=0)
            elif extraction_method.lower() == "center":
                center_row = (row_min + row_max) // 2
                spectrum_1d = data[center_row, :]
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": f"Unknown extraction method: {extraction_method}"
                }

            # Generate wavelength array
            wavelength = None
            wavelength_info = {"type": "pixel", "start": 0, "delta": 1.0}

            # Try to read FITS wavelength calibration
            if "CRVAL1" in header and "CDELT1" in header:
                try:
                    crval = float(header["CRVAL1"])
                    cdelt = float(header["CDELT1"])
                    crpix = float(header.get("CRPIX1", 1.0))
                    wavelength = crval + (np.arange(nx) - (crpix - 1)) * cdelt
                    wavelength_info = {
                        "type": "wavelength",
                        "unit": header.get("CUNIT1", "Angstrom"),
                        "start": round(float(wavelength[0]), 2),
                        "delta": round(cdelt, 4),
                    }
                except Exception:
                    wavelength = np.arange(nx)
            else:
                wavelength = np.arange(nx)

            # Find spectral features (peaks above background)
            background = np.nanmedian(spectrum_1d)
            noise = np.nanstd(spectrum_1d)
            threshold = background + 3.0 * noise

            peaks, properties = find_peaks(
                spectrum_1d,
                height=threshold,
                distance=5,
                prominence=noise
            )

            features = []
            if len(peaks) > 0:
                peak_heights = properties.get("peak_heights", np.zeros(len(peaks)))
                for i, peak_idx in enumerate(peaks):
                    w_val = wavelength[peak_idx] if wavelength is not None else peak_idx
                    features.append({
                        "pixel": int(peak_idx),
                        "wavelength": round(float(w_val), 2) if isinstance(w_val, (int, float, np.number)) else None,
                        "intensity": round(float(spectrum_1d[peak_idx]), 3),
                        "height_above_background": round(float(peak_heights[i]) if i < len(peak_heights) else 0.0, 3),
                    })

            # Downsample spectrum for JSON output
            downsample_factor = max(1, nx // 500)
            spec_downsampled = spectrum_1d[::downsample_factor]
            wav_downsampled = wavelength[::downsample_factor] if wavelength is not None else np.arange(len(spec_downsampled))

            spectrum_points = [
                {
                    "wavelength": round(float(wav_downsampled[i]), 2) if isinstance(wav_downsampled[i], (int, float, np.number)) else i,
                    "intensity": round(float(spec_downsampled[i]), 3),
                }
                for i in range(len(spec_downsampled))
            ]

            return clean_for_json({
                "status": "success",
                "file_path": os.path.abspath(file_path),
                "hdu_index": target_idx,
                "data_shape": list(data.shape),
                "extraction_params": {
                    "method": extraction_method.lower(),
                    "row_range": [row_min, row_max],
                    "rows_summed": row_max - row_min,
                },
                "wavelength": wavelength_info,
                "spectrum": {
                    "raw_pixels": int(nx),
                    "points": spectrum_points,
                    "background_level": round(float(background), 3),
                    "noise_estimate": round(float(noise), 3),
                    "min_intensity": round(float(np.nanmin(spectrum_1d)), 3),
                    "max_intensity": round(float(np.nanmax(spectrum_1d)), 3),
                },
                "features": {
                    "count": len(features),
                    "detections": features,
                }
            })

    except Exception as e:
        return clean_for_json({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        })
