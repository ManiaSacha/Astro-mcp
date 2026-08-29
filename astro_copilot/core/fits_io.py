"""
FITS I/O, Header parsing, WCS extraction, and robust image statistics.
"""

from typing import Any, Dict, List, Optional
import os
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import mad_std
from astro_copilot.utils.serialization import clean_for_json


def inspect_fits_file(
    file_path: str,
    hdu_index: Optional[int] = None,
    header_keys: Optional[List[str]] = None,
    compute_stats: bool = True,
    saturation_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Inspects a FITS file structure, headers, WCS metadata, and data statistics.
    
    Args:
        file_path: Path to the FITS file.
        hdu_index: Optional HDU index. If None, auto-selects first HDU with 2D image data.
        header_keys: List of specific header keywords to extract. If None, returns standard astro keys.
        compute_stats: Whether to calculate numerical image statistics.
        saturation_threshold: Pixel value above which pixels are considered saturated.
    """
    if not os.path.exists(file_path):
        return {
            "status": "error",
            "error_type": "FileNotFoundError",
            "message": f"FITS file not found: '{file_path}'"
        }

    try:
        with fits.open(file_path) as hdul:
            hdu_count = len(hdul)
            hdu_summary = []
            first_image_idx = 0

            for idx, hdu in enumerate(hdul):
                shape = list(hdu.data.shape) if hdu.data is not None else None
                dtype_str = str(hdu.data.dtype) if hdu.data is not None else None
                hdu_name = hdu.name if hasattr(hdu, "name") else f"HDU_{idx}"
                hdu_summary.append({
                    "index": idx,
                    "name": hdu_name,
                    "type": type(hdu).__name__,
                    "shape": shape,
                    "dtype": dtype_str,
                })
                if shape and len(shape) >= 2 and first_image_idx == 0 and hdu.data is not None:
                    first_image_idx = idx

            # Resolve target HDU
            selected_idx = hdu_index if hdu_index is not None else first_image_idx
            if selected_idx < 0 or selected_idx >= hdu_count:
                return {
                    "status": "error",
                    "error_type": "IndexError",
                    "message": f"HDU index {selected_idx} out of range (file has {hdu_count} HDUs)."
                }

            target_hdu = hdul[selected_idx]
            header = target_hdu.header

            # Extract header keywords
            standard_keys = [
                "SIMPLE", "BITPIX", "NAXIS", "NAXIS1", "NAXIS2",
                "OBJECT", "TELESCOP", "INSTRUME", "OBSERVER",
                "DATE-OBS", "EXPTIME", "FILTER", "GAIN", "RDNOISE",
                "SATURATE", "BUNIT", "AIRMASS", "MJD-OBS",
                "EQUINOX", "RADESYS"
            ]
            keys_to_fetch = header_keys if header_keys is not None else standard_keys
            header_sample = {}
            for k in keys_to_fetch:
                k_upper = k.upper()
                if k_upper in header:
                    val = header[k_upper]
                    if isinstance(val, (int, float, str, bool)):
                        header_sample[k_upper] = val
                    else:
                        header_sample[k_upper] = str(val)

            # WCS Extraction
            wcs_info = {"has_wcs": False}
            try:
                wcs = WCS(header)
                if wcs.has_celestial:
                    wcs_info["has_wcs"] = True
                    wcs_info["ctype"] = list(wcs.wcs.ctype)
                    wcs_info["crval"] = [float(v) for v in wcs.wcs.crval]
                    wcs_info["crpix"] = [float(v) for v in wcs.wcs.crpix]
                    wcs_info["cunit"] = [str(u) for u in wcs.wcs.cunit]
                    # Compute pixel scale if possible
                    try:
                        scales = wcs.proj_plane_pixel_scales()
                        wcs_info["pixel_scale_arcsec"] = [float(s.to_value("arcsec")) for s in scales]
                    except Exception:
                        pass
            except Exception as wcs_err:
                wcs_info["wcs_warning"] = str(wcs_err)

            # Data stats
            stats_info = None
            if compute_stats and target_hdu.data is not None:
                data = np.asarray(target_hdu.data, dtype=float)
                total_pixels = int(data.size)
                nan_mask = np.isnan(data)
                inf_mask = np.isinf(data)
                nan_count = int(np.sum(nan_mask))
                inf_count = int(np.sum(inf_mask))
                valid_data = data[~nan_mask & ~inf_mask]

                sat_val = saturation_threshold
                if sat_val is None and "SATURATE" in header:
                    try:
                        sat_val = float(header["SATURATE"])
                    except Exception:
                        sat_val = None

                if len(valid_data) > 0:
                    data_min = float(np.min(valid_data))
                    data_max = float(np.max(valid_data))
                    data_mean = float(np.mean(valid_data))
                    data_median = float(np.median(valid_data))
                    data_std = float(np.std(valid_data))
                    data_mad = float(mad_std(valid_data, ignore_nan=True))
                    
                    saturated_count = 0
                    if sat_val is not None:
                        saturated_count = int(np.sum(valid_data >= sat_val))

                    stats_info = {
                        "shape": list(data.shape),
                        "total_pixels": total_pixels,
                        "valid_pixels": int(len(valid_data)),
                        "nan_count": nan_count,
                        "inf_count": inf_count,
                        "min": data_min,
                        "max": data_max,
                        "mean": data_mean,
                        "median": data_median,
                        "std": data_std,
                        "mad_std": data_mad,
                        "saturation_threshold": sat_val,
                        "saturated_pixels": saturated_count,
                    }
                else:
                    stats_info = {
                        "shape": list(data.shape),
                        "total_pixels": total_pixels,
                        "valid_pixels": 0,
                        "nan_count": nan_count,
                        "inf_count": inf_count,
                    }

            return clean_for_json({
                "status": "success",
                "file_path": os.path.abspath(file_path),
                "hdu_count": hdu_count,
                "hdus": hdu_summary,
                "selected_hdu": {
                    "index": selected_idx,
                    "name": target_hdu.name if hasattr(target_hdu, "name") else f"HDU_{selected_idx}",
                    "header_keys_count": len(header),
                    "header_sample": header_sample,
                    "wcs": wcs_info,
                    "statistics": stats_info,
                }
            })

    except Exception as e:
        return clean_for_json({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        })
