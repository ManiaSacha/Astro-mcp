"""
Error and uncertainty propagation models for astronomical reduction.
"""

from typing import Optional, Tuple
import math
import numpy as np


def compute_photometric_uncertainty(
    source_flux_adu: float,
    sky_flux_per_pixel_adu: float,
    aperture_area_pixels: float,
    gain: float = 1.0,
    read_noise_e: float = 0.0,
    n_sky_pixels: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Computes standard CCD photometric uncertainty using the CCD equation.
    
    Formula (in electrons):
      Var(S) = S*gain + A*B*gain + A * (read_noise)^2 + (A^2 / n_sky) * (B*gain + read_noise^2)
    
    Returns:
      (flux_err_adu, snr)
    """
    gain = max(float(gain), 1e-6)
    read_noise_e = max(float(read_noise_e), 0.0)
    aperture_area = max(float(aperture_area_pixels), 1e-6)
    
    # Non-negative source & sky signal in electrons
    source_signal_e = max(source_flux_adu, 0.0) * gain
    sky_signal_e = max(sky_flux_per_pixel_adu, 0.0) * gain
    
    variance_e2 = source_signal_e + (aperture_area * sky_signal_e) + (aperture_area * (read_noise_e ** 2))
    
    if n_sky_pixels and n_sky_pixels > 0:
        variance_e2 += ((aperture_area ** 2) / n_sky_pixels) * (sky_signal_e + (read_noise_e ** 2))
        
    error_e = math.sqrt(max(variance_e2, 1e-12))
    error_adu = error_e / gain
    
    snr = source_flux_adu / error_adu if error_adu > 0 else 0.0
    return float(error_adu), float(snr)


def flux_to_mag(
    flux_adu: float,
    flux_err_adu: float,
    zero_point: float = 25.0,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Converts ADU flux to instrumental or calibrated magnitude:
      m = -2.5 * log10(flux) + ZP
      sigma_m = 1.0857 * (sigma_flux / flux)
    """
    if flux_adu <= 0 or math.isnan(flux_adu):
        return None, None
    
    mag = -2.5 * math.log10(flux_adu) + zero_point
    
    if flux_err_adu is not None and flux_err_adu > 0:
        mag_err = 1.0857362 * (flux_err_adu / flux_adu)
    else:
        mag_err = None
        
    return float(mag), float(mag_err) if mag_err is not None else None
