"""
Aperture Photometry module using Photutils and Astropy.
Performs circular aperture photometry with local background annulus estimation and CCD error propagation.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import os
import math
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import SigmaClip
from photutils.aperture import (
    CircularAperture,
    CircularAnnulus,
    aperture_photometry,
    ApertureStats,
)

from astro_copilot.utils.serialization import clean_for_json
from astro_copilot.utils.error_models import compute_photometric_uncertainty, flux_to_mag
from astro_copilot.core.fits_io import validate_file_path


def run_aperture_photometry(
    file_path: str,
    aperture_radius: float,
    hdu_index: Optional[int] = None,
    positions: Optional[List[List[float]]] = None,
    sky_coords: Optional[List[List[float]]] = None,
    one_indexed: bool = False,
    bkg_annulus_inner: Optional[float] = None,
    bkg_annulus_outer: Optional[float] = None,
    gain: Optional[float] = None,
    read_noise: Optional[float] = None,
    zero_point: float = 25.0,
    saturation_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Performs circular aperture photometry on target positions or sky coordinates.

    Args:
        file_path: Path to the FITS file.
        aperture_radius: Radius of circular aperture in pixels.
        hdu_index: HDU index (if None, auto-selects first 2D image HDU).
        positions: List of [x, y] coordinates in pixels.
        sky_coords: List of [ra_deg, dec_deg] coordinates.
        one_indexed: If True, input pixel coordinates are 1-indexed (DS9/IRAF style).
        bkg_annulus_inner: Inner radius for local sky background annulus.
        bkg_annulus_outer: Outer radius for local sky background annulus.
        gain: Detector gain in e-/ADU (if None, read from header).
        read_noise: Detector read noise in e- (if None, read from header).
        zero_point: Magnitude zero point (default 25.0).
        saturation_threshold: Saturated pixel threshold.
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

    if positions is None and sky_coords is None:
        return {
            "status": "error",
            "error_type": "ValueError",
            "message": "Either 'positions' (pixel coords) or 'sky_coords' (RA/Dec) must be provided."
        }

    if aperture_radius <= 0:
        return {
            "status": "error",
            "error_type": "ValueError",
            "message": f"aperture_radius must be positive (got {aperture_radius})."
        }

    if bkg_annulus_inner is not None or bkg_annulus_outer is not None:
        if bkg_annulus_inner is None or bkg_annulus_outer is None:
            return {
                "status": "error",
                "error_type": "ValueError",
                "message": "Both bkg_annulus_inner and bkg_annulus_outer must be provided together."
            }
        if bkg_annulus_inner <= 0 or bkg_annulus_outer <= 0:
            return {
                "status": "error",
                "error_type": "ValueError",
                "message": f"Annulus radii must be positive (inner={bkg_annulus_inner}, outer={bkg_annulus_outer})."
            }
        if bkg_annulus_outer <= bkg_annulus_inner:
            return {
                "status": "error",
                "error_type": "ValueError",
                "message": f"bkg_annulus_outer ({bkg_annulus_outer}) must be greater than bkg_annulus_inner ({bkg_annulus_inner})."
            }

    try:
        with fits.open(file_path) as hdul:
            # Auto-detect image HDU if not provided
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
            header = target_hdu.header
            ny, nx = data.shape[-2:]

            # Resolve detector parameters from header if not provided
            detector_gain = gain
            if detector_gain is None:
                for k in ["GAIN", "EGAIN", "GAINVAL"]:
                    if k in header:
                        try:
                            detector_gain = float(header[k])
                            break
                        except Exception:
                            pass
            if detector_gain is None or detector_gain <= 0:
                detector_gain = 1.0

            detector_rdnoise = read_noise
            if detector_rdnoise is None:
                for k in ["RDNOISE", "RON", "READNOIS"]:
                    if k in header:
                        try:
                            detector_rdnoise = float(header[k])
                            break
                        except Exception:
                            pass
            if detector_rdnoise is None or detector_rdnoise < 0:
                detector_rdnoise = 0.0

            sat_threshold = saturation_threshold
            if sat_threshold is None and "SATURATE" in header:
                try:
                    sat_threshold = float(header["SATURATE"])
                except Exception:
                    sat_threshold = None

            # Parse WCS
            wcs_obj = None
            try:
                wcs_obj = WCS(header)
                if not wcs_obj.has_celestial:
                    wcs_obj = None
            except Exception:
                wcs_obj = None

            # Resolve coordinates to 0-indexed pixel positions
            pixel_positions: List[Tuple[float, float]] = []
            celestial_positions: List[Optional[Tuple[float, float]]] = []

            if sky_coords is not None:
                if wcs_obj is None:
                    return {
                        "status": "error",
                        "error_type": "WCSNotFoundError",
                        "message": "FITS header lacks valid celestial WCS required to convert 'sky_coords' to pixel positions."
                    }
                for pair in sky_coords:
                    ra, dec = float(pair[0]), float(pair[1])
                    px, py = wcs_obj.all_world2pix(ra, dec, 0)
                    pixel_positions.append((float(px), float(py)))
                    celestial_positions.append((ra, dec))
            elif positions is not None:
                for pair in positions:
                    x, y = float(pair[0]), float(pair[1])
                    if one_indexed:
                        x -= 1.0
                        y -= 1.0
                    pixel_positions.append((x, y))
                    if wcs_obj is not None:
                        try:
                            ra, dec = wcs_obj.all_pix2world(x, y, 0)
                            celestial_positions.append((float(ra), float(dec)))
                        except Exception:
                            celestial_positions.append(None)
                    else:
                        celestial_positions.append(None)

            if len(pixel_positions) == 0:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": "No valid coordinate pairs provided."
                }

            # Setup apertures
            apertures = CircularAperture(pixel_positions, r=aperture_radius)
            phot_table = aperture_photometry(data, apertures)
            raw_fluxes = phot_table["aperture_sum"]

            # Background subtraction setup
            use_annulus = (
                bkg_annulus_inner is not None
                and bkg_annulus_outer is not None
                and bkg_annulus_outer > bkg_annulus_inner
            )

            bkg_per_px_list = []
            n_bkg_pixels_list = []

            if use_annulus:
                annulus_apertures = CircularAnnulus(
                    pixel_positions,
                    r_in=bkg_annulus_inner,
                    r_out=bkg_annulus_outer,
                )
                sigclip = SigmaClip(sigma=3.0, maxiters=5)
                annulus_stats = ApertureStats(data, annulus_apertures, sigma_clip=sigclip)
                med_vals = np.asarray(annulus_stats.median)
                area_vals = np.asarray(annulus_stats.sum_aper_area)
                bkg_per_px_list = [
                    float(m) if not np.isnan(m) else 0.0 for m in med_vals
                ]
                n_bkg_pixels_list = [
                    float(c) if not np.isnan(c) else 0.0 for c in area_vals
                ]
            else:
                bkg_per_px_list = [0.0] * len(pixel_positions)
                n_bkg_pixels_list = [0.0] * len(pixel_positions)

            # Build results per source
            aper_area_val = getattr(apertures.area, "value", apertures.area)
            aperture_area = float(aper_area_val)
            sources_result = []

            for i, (px, py) in enumerate(pixel_positions):
                flags = []
                # Check bounds
                if px < 0 or px >= nx or py < 0 or py >= ny:
                    flags.append("OFF_IMAGE")

                raw_flux = float(raw_fluxes[i])
                if np.isnan(raw_flux) or np.isinf(raw_flux):
                    flags.append("NAN_IN_APERTURE")
                    raw_flux = 0.0

                bkg_val = bkg_per_px_list[i]
                bkg_total = bkg_val * aperture_area
                net_flux = raw_flux - bkg_total

                # Compute photometric error and SNR
                flux_err, snr = compute_photometric_uncertainty(
                    source_flux_adu=max(net_flux, 0.0),
                    sky_flux_per_pixel_adu=max(bkg_val, 0.0),
                    aperture_area_pixels=aperture_area,
                    gain=detector_gain,
                    read_noise_e=detector_rdnoise,
                    n_sky_pixels=n_bkg_pixels_list[i] if use_annulus else None,
                )

                # Check saturation in local bounding box
                ix, iy = int(round(px)), int(round(py))
                rad_int = int(math.ceil(aperture_radius))
                x_min, x_max = max(0, ix - rad_int), min(nx, ix + rad_int + 1)
                y_min, y_max = max(0, iy - rad_int), min(ny, iy + rad_int + 1)
                if sat_threshold is not None and x_max > x_min and y_max > y_min:
                    sub_stamp = data[y_min:y_max, x_min:x_max]
                    if np.any(sub_stamp >= sat_threshold):
                        flags.append("SATURATED")

                if len(flags) == 0:
                    flags.append("OK")

                mag, mag_err = flux_to_mag(net_flux, flux_err, zero_point=zero_point)

                ra_val, dec_val = None, None
                if celestial_positions[i] is not None:
                    ra_val, dec_val = celestial_positions[i]

                sources_result.append({
                    "id": i + 1,
                    "x_px": round(px, 3),
                    "y_px": round(py, 3),
                    "ra_deg": round(ra_val, 6) if ra_val is not None else None,
                    "dec_deg": round(dec_val, 6) if dec_val is not None else None,
                    "raw_flux": round(raw_flux, 3),
                    "local_bkg_per_px": round(bkg_val, 4) if use_annulus else None,
                    "bkg_subtracted_flux": round(net_flux, 3),
                    "flux_err": round(flux_err, 3),
                    "snr": round(snr, 2),
                    "mag": round(mag, 4) if mag is not None else None,
                    "mag_err": round(mag_err, 4) if mag_err is not None else None,
                    "flags": flags,
                })

            valid_snrs = [s["snr"] for s in sources_result if "OK" in s["flags"] and s["snr"] > 0]
            summary = {
                "total_sources": len(sources_result),
                "median_snr": round(float(np.median(valid_snrs)), 2) if len(valid_snrs) > 0 else 0.0,
                "gain_used": detector_gain,
                "read_noise_used": detector_rdnoise,
            }

            return clean_for_json({
                "status": "success",
                "file_path": os.path.abspath(file_path),
                "hdu_index": target_idx,
                "aperture_radius_px": aperture_radius,
                "annulus": {
                    "inner_radius_px": bkg_annulus_inner,
                    "outer_radius_px": bkg_annulus_outer,
                } if use_annulus else None,
                "zero_point": zero_point,
                "sources": sources_result,
                "summary": summary,
            })

    except Exception as e:
        return clean_for_json({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        })
