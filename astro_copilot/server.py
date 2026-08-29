"""
FastMCP Server for Astro Data-Reduction Copilot.
Exposes local astronomical reduction tools (FITS inspection, aperture photometry, light curve fitting).
"""

from typing import Any, Dict, List, Optional
import os
import sys
from fastmcp import FastMCP

from astro_copilot.core.fits_io import inspect_fits_file
from astro_copilot.core.photometry import run_aperture_photometry
from astro_copilot.core.lightcurve import fit_and_analyze_lightcurve

# Initialize FastMCP Server
mcp = FastMCP(
    name="astro-copilot",
)


@mcp.tool()
def inspect_fits(
    file_path: str,
    hdu_index: Optional[int] = None,
    header_keys: Optional[List[str]] = None,
    compute_stats: bool = True,
    saturation_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Inspects headers, HDU structure, celestial WCS, and robust image statistics of a local FITS file.
    
    Args:
        file_path: Absolute or relative path to the FITS file.
        hdu_index: Specific HDU index to inspect. If None, auto-selects the first HDU containing 2D image data.
        header_keys: List of specific FITS header keywords to extract (e.g. ['TELESCOP', 'EXPTIME', 'GAIN', 'FILTER']).
        compute_stats: Whether to calculate robust min/max/mean/median/MAD-std/NaN counts.
        saturation_threshold: Optional pixel count threshold above which pixels are flagged as saturated.
    """
    return inspect_fits_file(
        file_path=file_path,
        hdu_index=hdu_index,
        header_keys=header_keys,
        compute_stats=compute_stats,
        saturation_threshold=saturation_threshold,
    )


@mcp.tool()
def aperture_photometry(
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
    Performs circular aperture photometry on local FITS images with background subtraction and CCD error propagation.
    
    Args:
        file_path: Path to the local FITS image file.
        aperture_radius: Radius of the circular aperture in pixels.
        hdu_index: Target HDU index containing image data.
        positions: List of [x, y] pixel coordinates (e.g. [[128.5, 128.5]]).
        sky_coords: List of celestial [ra_deg, dec_deg] coordinates (requires valid WCS in header).
        one_indexed: Set to True if input pixel coordinates are 1-based (DS9/IRAF style).
        bkg_annulus_inner: Inner radius in pixels for local background subtraction annulus.
        bkg_annulus_outer: Outer radius in pixels for local background subtraction annulus.
        gain: Detector gain in e-/ADU (if omitted, extracted from FITS header or defaults to 1.0).
        read_noise: Detector read noise in e- (if omitted, extracted from FITS header or defaults to 0.0).
        zero_point: Photometric magnitude zero point (default 25.0).
        saturation_threshold: Saturated pixel count threshold to flag saturated apertures.
    """
    return run_aperture_photometry(
        file_path=file_path,
        aperture_radius=aperture_radius,
        hdu_index=hdu_index,
        positions=positions,
        sky_coords=sky_coords,
        one_indexed=one_indexed,
        bkg_annulus_inner=bkg_annulus_inner,
        bkg_annulus_outer=bkg_annulus_outer,
        gain=gain,
        read_noise=read_noise,
        zero_point=zero_point,
        saturation_threshold=saturation_threshold,
    )


@mcp.tool()
def fit_lightcurve(
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
    Loads, detrends, and fits periodic / transit signals in a local light curve (FITS binary table or CSV).
    
    Args:
        file_path: Path to the FITS table (e.g. Kepler/TESS SPOC format) or CSV light curve.
        model_type: Model to fit: 'transit' (Box Least Squares exoplanet fit), 'sinusoid' (Lomb-Scargle variable star fit), or 'polynomial'.
        time_col: Column name for time (auto-detected if omitted: TIME, BJD, HJD, etc.).
        flux_col: Column name for flux (auto-detected: PDCSAP_FLUX, SAP_FLUX, FLUX, etc.).
        flux_err_col: Column name for flux uncertainties.
        detrend_window_length: Window length (odd integer) for Savitzky-Golay flattening filter before fitting.
        period_hint: Optional estimated period in days to narrow the period search grid.
        min_period: Minimum period in days for the search grid.
        max_period: Maximum period in days for the search grid.
        n_phase_bins: Number of points in the phase-binned diagnostic light curve for LLM interpretation.
    """
    return fit_and_analyze_lightcurve(
        file_path=file_path,
        model_type=model_type,
        time_col=time_col,
        flux_col=flux_col,
        flux_err_col=flux_err_col,
        detrend_window_length=detrend_window_length,
        period_hint=period_hint,
        min_period=min_period,
        max_period=max_period,
        n_phase_bins=n_phase_bins,
    )


@mcp.tool()
def generate_sample_datasets(output_dir: str = "sample_data") -> Dict[str, Any]:
    """
    Generates out-of-the-box synthetic astronomical sample datasets for testing:
    1. 'sample_image.fits': 256x256 image with synthetic stars, background noise, and WCS.
    2. 'sample_transit.fits': TESS-style light curve table with an exoplanet transit signal.
    3. 'sample_variable_star.csv': Time series of a pulsating sinusoidal variable star.
    
    Args:
        output_dir: Directory where sample FITS and CSV files will be written.
    """
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS
    import pandas as pd

    os.makedirs(output_dir, exist_ok=True)
    generated = []

    # 1. Sample Image FITS
    ny, nx = 256, 256
    y, x = np.mgrid[0:ny, 0:nx]
    np.random.seed(42)
    bkg = np.random.poisson(300.0, size=(ny, nx)).astype(np.float32)
    stars = [
        {"x0": 128.0, "y0": 128.0, "amp": 15000.0, "sigma": 2.5},
        {"x0": 60.0, "y0": 60.0, "amp": 4000.0, "sigma": 2.2},
        {"x0": 200.0, "y0": 180.0, "amp": 1200.0, "sigma": 2.0},
    ]
    img = bkg.copy()
    for s in stars:
        r2 = (x - s["x0"]) ** 2 + (y - s["y0"]) ** 2
        img += (s["amp"] * np.exp(-0.5 * r2 / (s["sigma"] ** 2))).astype(np.float32)

    hdr = fits.Header()
    hdr["OBJECT"] = "SAMPLE_FIELD"
    hdr["TELESCOP"] = "Copilot-0.5m"
    hdr["EXPTIME"] = 60.0
    hdr["GAIN"] = 1.5
    hdr["RDNOISE"] = 4.0
    hdr["SATURATE"] = 50000.0

    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [128.0, 128.0]
    wcs.wcs.cdelt = np.array([-0.0002777, 0.0002777])
    wcs.wcs.crval = [202.46957, 47.19525]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    hdr.extend(wcs.to_header())

    img_path = os.path.join(output_dir, "sample_image.fits")
    fits.writeto(img_path, img, hdr, overwrite=True)
    generated.append(os.path.abspath(img_path))

    # 2. Sample Transit FITS Table
    t = np.linspace(0.0, 28.0, 1344)
    period = 3.525
    t0 = 1.2
    depth = 0.012
    duration = 0.12
    trend = 1.0 + 0.004 * np.sin(2 * np.pi * t / 14.0)
    noise = np.random.normal(0.0, 0.0007, size=len(t))
    flux = trend + noise
    phase = ((t - t0 + 0.5 * period) % period) - 0.5 * period
    flux[np.abs(phase) < (0.5 * duration)] -= depth
    flux_err = np.full_like(flux, 0.0007)

    cols = [
        fits.Column(name="TIME", format="D", unit="BJD", array=t),
        fits.Column(name="PDCSAP_FLUX", format="E", unit="e-/s", array=flux * 10000.0),
        fits.Column(name="PDCSAP_FLUX_ERR", format="E", unit="e-/s", array=flux_err * 10000.0),
    ]
    thdu = fits.BinTableHDU.from_columns(cols, name="LIGHTCURVE")
    thdu.header["OBJECT"] = "SAMPLE_EXOPLANET"
    thdu.header["TELESCOP"] = "TESS"
    lc_path = os.path.join(output_dir, "sample_transit.fits")
    fits.HDUList([fits.PrimaryHDU(), thdu]).writeto(lc_path, overwrite=True)
    generated.append(os.path.abspath(lc_path))

    # 3. Sample Variable Star CSV
    t_var = np.linspace(0.0, 15.0, 400)
    f_var = 1.0 + 0.06 * np.sin(2 * np.pi * t_var / 1.45) + np.random.normal(0, 0.006, size=len(t_var))
    csv_path = os.path.join(output_dir, "sample_variable_star.csv")
    pd.DataFrame({"TIME": t_var, "FLUX": f_var, "FLUX_ERR": np.full_like(f_var, 0.006)}).to_csv(csv_path, index=False)
    generated.append(os.path.abspath(csv_path))

    return {
        "status": "success",
        "message": f"Generated 3 sample astronomical datasets in '{output_dir}'",
        "files": generated,
    }


def main():
    """CLI entrypoint for running the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
