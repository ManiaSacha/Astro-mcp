"""
Light curve analysis, detrending, and transit/periodic fitting using Lightkurve and Astropy.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import os
import math
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.timeseries import LombScargle, BoxLeastSquares
import lightkurve as lk

from astro_copilot.utils.serialization import clean_for_json


def load_lightcurve_data(
    file_path: str,
    time_col: Optional[str] = None,
    flux_col: Optional[str] = None,
    flux_err_col: Optional[str] = None,
    hdu_index: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Loads time, flux, and flux_err from a FITS binary table or CSV file.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    time_arr = None
    flux_arr = None
    err_arr = None
    meta = {}

    if ext in [".fits", ".fit", ".fts"]:
        with fits.open(file_path) as hdul:
            target_idx = 1
            if hdu_index is not None:
                target_idx = hdu_index
            else:
                for idx, hdu in enumerate(hdul):
                    if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                        target_idx = idx
                        break

            table_hdu = hdul[target_idx]
            cols = [c.name.upper() for c in table_hdu.columns]
            meta["columns"] = cols
            meta["header"] = {
                k: table_hdu.header[k]
                for k in ["OBJECT", "TELESCOP", "INSTRUME", "KEPLERID", "TICID", "SECTOR"]
                if k in table_hdu.header
            }

            # Find time column
            time_name = time_col.upper() if time_col else None
            if not time_name:
                for candidate in ["TIME", "BJD", "HJD", "MJD", "JD", "DATE"]:
                    if candidate in cols:
                        time_name = candidate
                        break
            if not time_name:
                raise ValueError(f"Could not automatically identify time column. Found columns: {cols}")

            # Find flux column
            flux_name = flux_col.upper() if flux_col else None
            if not flux_name:
                for candidate in ["PDCSAP_FLUX", "SAP_FLUX", "FLUX", "DETRENDED_FLUX", "CORRECTED_FLUX", "COUNTS"]:
                    if candidate in cols:
                        flux_name = candidate
                        break
            if not flux_name:
                raise ValueError(f"Could not automatically identify flux column. Found columns: {cols}")

            # Find err column
            err_name = flux_err_col.upper() if flux_err_col else None
            if not err_name:
                for candidate in [f"{flux_name}_ERR", f"{flux_name}_ERROR", "FLUX_ERR", "FLUX_ERROR", "ERROR", "UNCERTAINTY"]:
                    if candidate in cols:
                        err_name = candidate
                        break

            time_arr = np.asarray(table_hdu.data[time_name], dtype=float)
            flux_arr = np.asarray(table_hdu.data[flux_name], dtype=float)
            if err_name and err_name in cols:
                err_arr = np.asarray(table_hdu.data[err_name], dtype=float)
            else:
                err_arr = np.zeros_like(flux_arr)

    elif ext in [".csv", ".txt", ".dat"]:
        df = pd.read_csv(file_path, comment="#")
        cols = [c.strip().upper() for c in df.columns]
        df.columns = cols
        meta["columns"] = cols

        # Find time
        time_name = time_col.upper() if time_col else None
        if not time_name:
            for candidate in ["TIME", "BJD", "HJD", "MJD", "JD", "T"]:
                if candidate in cols:
                    time_name = candidate
                    break
        if not time_name and len(cols) >= 1:
            time_name = cols[0]

        # Find flux
        flux_name = flux_col.upper() if flux_col else None
        if not flux_name:
            for candidate in ["FLUX", "PDCSAP_FLUX", "SAP_FLUX", "MAG", "MAGNITUDE", "COUNTS", "Y"]:
                if candidate in cols:
                    flux_name = candidate
                    break
        if not flux_name and len(cols) >= 2:
            flux_name = cols[1]

        # Find err
        err_name = flux_err_col.upper() if flux_err_col else None
        if not err_name:
            for candidate in [f"{flux_name}_ERR", "FLUX_ERR", "MAG_ERR", "ERR", "UNCERTAINTY", "SIGMA"]:
                if candidate in cols:
                    err_name = candidate
                    break
        if not err_name and len(cols) >= 3:
            err_name = cols[2]

        time_arr = np.asarray(df[time_name], dtype=float)
        flux_arr = np.asarray(df[flux_name], dtype=float)
        if err_name and err_name in df.columns:
            err_arr = np.asarray(df[err_name], dtype=float)
        else:
            err_arr = np.zeros_like(flux_arr)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Expected FITS or CSV.")

    return time_arr, flux_arr, err_arr, meta


def fit_and_analyze_lightcurve(
    file_path: str,
    model_type: str = "transit",
    time_col: Optional[str] = None,
    flux_col: Optional[str] = None,
    flux_err_col: Optional[str] = None,
    detrend_window_length: Optional[int] = None,
    period_hint: Optional[float] = None,
    min_period: float = 0.5,
    max_period: float = 30.0,
    n_phase_bins: int = 50,
) -> Dict[str, Any]:
    """
    Detrends and fits periodic or transit signals in a light curve.
    
    Args:
        file_path: Path to the FITS table or CSV light curve.
        model_type: "transit" (exoplanet transit fit), "sinusoid" (Lomb-Scargle periodic fit), or "polynomial".
        time_col: Column name for time.
        flux_col: Column name for flux.
        flux_err_col: Column name for flux uncertainties.
        detrend_window_length: Window length (odd integer) for Savitzky-Golay detrending filter.
        period_hint: Period in days (optional hint for period search).
        min_period: Minimum period in days for search grid.
        max_period: Maximum period in days for search grid.
        n_phase_bins: Number of points in phase-binned diagnostic curve.
    """
    if not os.path.exists(file_path):
        return {
            "status": "error",
            "error_type": "FileNotFoundError",
            "message": f"Light curve file not found: '{file_path}'"
        }

    try:
        t_raw, f_raw, e_raw, meta = load_lightcurve_data(
            file_path, time_col=time_col, flux_col=flux_col, flux_err_col=flux_err_col
        )

        # Filter NaNs and Infs
        valid = (
            ~np.isnan(t_raw)
            & ~np.isnan(f_raw)
            & ~np.isinf(t_raw)
            & ~np.isinf(f_raw)
        )
        if e_raw is not None:
            valid &= ~np.isnan(e_raw) & ~np.isinf(e_raw)

        t = t_raw[valid]
        f = f_raw[valid]
        e = e_raw[valid] if e_raw is not None else np.zeros_like(f)

        if len(t) < 10:
            return {
                "status": "error",
                "error_type": "DataError",
                "message": f"Insufficient valid data points ({len(t)}) for light curve analysis."
            }

        # Normalize flux if unnormalized (median flux > 10)
        median_flux = float(np.nanmedian(f))
        normalized = False
        if abs(median_flux) > 5.0:
            f = f / median_flux
            if np.any(e > 0):
                e = e / median_flux
            normalized = True

        # Construct Lightkurve LightCurve
        lk_kwargs = {"time": t, "flux": f}
        if np.any(e > 0):
            lk_kwargs["flux_err"] = e
        lc = lk.LightCurve(**lk_kwargs)

        detrended = False
        if detrend_window_length is not None and detrend_window_length > 3:
            # Ensure odd integer
            win_len = int(detrend_window_length)
            if win_len % 2 == 0:
                win_len += 1
            if win_len < len(lc):
                lc = lc.flatten(window_length=win_len)
                detrended = True

        t_clean = lc.time.value
        f_clean = lc.flux.value
        e_clean = lc.flux_err.value if lc.flux_err is not None else np.full_like(f_clean, np.std(f_clean))

        total_points = len(t_clean)
        time_span_days = float(np.max(t_clean) - np.min(t_clean))

        fit_results = {}
        phase_binned = []

        if model_type.lower() == "transit":
            # Use Box Least Squares (BLS)
            durations = np.linspace(0.05, 0.3, 10) # 1.2 to 7.2 hours
            if period_hint is not None:
                p_min = max(0.1, period_hint * 0.9)
                p_max = period_hint * 1.1
            else:
                p_min = max(0.2, min_period)
                p_max = min(time_span_days / 1.5, max_period)

            bls = BoxLeastSquares(t_clean, f_clean, dy=e_clean if np.any(e_clean > 0) else None)
            periods = np.linspace(p_min, p_max, 5000)
            periodogram = bls.power(periods, durations)

            best_idx = np.argmax(periodogram.power)
            best_period = float(periodogram.period[best_idx])
            best_t0 = float(periodogram.transit_time[best_idx])
            best_duration = float(periodogram.duration[best_idx])
            best_depth = float(periodogram.depth[best_idx])

            # Fold light curve
            phase = ((t_clean - best_t0 + 0.5 * best_period) % best_period) / best_period - 0.5
            sort_idx = np.argsort(phase)
            phase_sorted = phase[sort_idx]
            flux_sorted = f_clean[sort_idx]

            # Compute phase bins
            bin_edges = np.linspace(-0.5, 0.5, n_phase_bins + 1)
            for b in range(n_phase_bins):
                in_bin = (phase_sorted >= bin_edges[b]) & (phase_sorted < bin_edges[b + 1])
                if np.any(in_bin):
                    b_phase = float(0.5 * (bin_edges[b] + bin_edges[b + 1]))
                    b_flux = float(np.median(flux_sorted[in_bin]))
                    b_err = float(np.std(flux_sorted[in_bin]) / math.sqrt(np.sum(in_bin)))
                    phase_binned.append({
                        "phase": round(b_phase, 4),
                        "binned_flux": round(b_flux, 6),
                        "err": round(b_err, 6),
                    })

            # Calculate SNR and statistics
            in_transit = np.abs(phase_sorted) < (best_duration / (2.0 * best_period))
            out_of_transit = ~in_transit
            noise_est = float(np.std(flux_sorted[out_of_transit])) if np.any(out_of_transit) else 0.01
            snr = (best_depth / noise_est) * math.sqrt(max(np.sum(in_transit), 1)) if noise_est > 0 else 0.0

            fit_results = {
                "model": "BoxLeastSquares Transit",
                "period_days": round(best_period, 6),
                "t0_epoch": round(best_t0, 5),
                "duration_hours": round(best_duration * 24.0, 3),
                "transit_depth_ppm": round(best_depth * 1e6, 2),
                "transit_depth_fraction": round(best_depth, 6),
                "snr": round(float(snr), 2),
                "out_of_transit_scatter": round(noise_est, 6),
            }

        elif model_type.lower() == "sinusoid":
            # Lomb-Scargle Periodogram
            ls = LombScargle(t_clean, f_clean, dy=e_clean if np.any(e_clean > 0) else None)
            if period_hint is not None:
                freq_min = 1.0 / (period_hint * 1.5)
                freq_max = 1.0 / (period_hint * 0.5)
            else:
                freq_min = 1.0 / max_period
                freq_max = 1.0 / min_period

            frequency, power = ls.autopower(minimum_frequency=freq_min, maximum_frequency=freq_max)
            best_freq = float(frequency[np.argmax(power)])
            best_period = 1.0 / best_freq
            peak_power = float(np.max(power))

            # Amplitude and offset
            theta = ls.model_parameters(best_freq)
            # Offset + A*sin(2pi*f*t) + B*cos(2pi*f*t)
            offset = float(theta[0])
            amp = math.sqrt(theta[1]**2 + theta[2]**2)

            # Fold light curve
            phase = (t_clean * best_freq) % 1.0
            sort_idx = np.argsort(phase)
            phase_sorted = phase[sort_idx]
            flux_sorted = f_clean[sort_idx]

            bin_edges = np.linspace(0.0, 1.0, n_phase_bins + 1)
            for b in range(n_phase_bins):
                in_bin = (phase_sorted >= bin_edges[b]) & (phase_sorted < bin_edges[b + 1])
                if np.any(in_bin):
                    b_phase = float(0.5 * (bin_edges[b] + bin_edges[b + 1]))
                    b_flux = float(np.median(flux_sorted[in_bin]))
                    b_err = float(np.std(flux_sorted[in_bin]) / math.sqrt(np.sum(in_bin)))
                    phase_binned.append({
                        "phase": round(b_phase, 4),
                        "binned_flux": round(b_flux, 6),
                        "err": round(b_err, 6),
                    })

            fit_results = {
                "model": "LombScargle Sinusoid",
                "period_days": round(best_period, 6),
                "frequency_per_day": round(best_freq, 6),
                "power": round(peak_power, 4),
                "amplitude": round(amp, 6),
                "offset": round(offset, 6),
            }

        elif model_type.lower() == "polynomial":
            # Polynomial baseline fit
            deg = 2
            poly_coeffs = np.polyfit(t_clean - np.min(t_clean), f_clean, deg=deg)
            poly_eval = np.polyval(poly_coeffs, t_clean - np.min(t_clean))
            residuals = f_clean - poly_eval
            rms = float(np.std(residuals))

            fit_results = {
                "model": "Polynomial Degree 2",
                "coefficients": [round(float(c), 6) for c in poly_coeffs],
                "rms_residual": round(rms, 6),
            }

        return clean_for_json({
            "status": "success",
            "file_path": os.path.abspath(file_path),
            "points_count": total_points,
            "time_range": [round(float(np.min(t_clean)), 4), round(float(np.max(t_clean)), 4)],
            "time_span_days": round(time_span_days, 3),
            "normalized_flux": normalized,
            "detrended": detrended,
            "model_type": model_type,
            "fit_results": fit_results,
            "phase_binned_curve": phase_binned,
        })

    except Exception as e:
        return clean_for_json({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        })
