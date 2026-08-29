"""
Pytest configuration and synthetic FITS dataset generators.
Provides realistic astronomical fixtures without external network calls or telescope archives.
"""

import os
import pytest
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Temporary directory for test FITS files."""
    data_dir = tmp_path_factory.mktemp("astro_data")
    return str(data_dir)


@pytest.fixture(scope="session")
def standard_synthetic_fits(test_data_dir):
    """
    Creates a standard single-extension 256x256 image FITS file with:
    - 2D Gaussian stellar sources
    - Poisson sky background
    - Proper celestial WCS
    - Standard astronomical header keywords (OBJECT, EXPTIME, GAIN, RDNOISE, SATURATE)
    """
    np.random.seed(42)
    ny, nx = 256, 256
    y, x = np.mgrid[0:ny, 0:nx]

    # Background of 300 ADU + Poisson noise
    bkg_level = 300.0
    image = np.random.poisson(bkg_level, size=(ny, nx)).astype(np.float32)

    # Add 3 Gaussian stars:
    # Star 1: center at (128, 128), amplitude 15000 (bright)
    # Star 2: center at (60, 60), amplitude 4000 (medium)
    # Star 3: center at (200, 180), amplitude 800 (faint)
    stars = [
        {"x0": 128.0, "y0": 128.0, "amp": 15000.0, "sigma": 2.5},
        {"x0": 60.0, "y0": 60.0, "amp": 4000.0, "sigma": 2.2},
        {"x0": 200.0, "y0": 180.0, "amp": 800.0, "sigma": 2.0},
    ]
    for s in stars:
        r2 = (x - s["x0"]) ** 2 + (y - s["y0"]) ** 2
        star_profile = s["amp"] * np.exp(-0.5 * r2 / (s["sigma"] ** 2))
        image += star_profile.astype(np.float32)

    # Build Header
    hdr = fits.Header()
    hdr["OBJECT"] = "NGC_TEST"
    hdr["TELESCOP"] = "Copilot-0.5m"
    hdr["INSTRUME"] = "CCD_Cam"
    hdr["EXPTIME"] = 60.0
    hdr["FILTER"] = "V"
    hdr["GAIN"] = 1.5
    hdr["RDNOISE"] = 4.0
    hdr["SATURATE"] = 50000.0
    hdr["DATE-OBS"] = "2026-08-29T12:00:00"

    # WCS (RA ~ 202.47 deg, Dec ~ 47.19 deg)
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [128.0, 128.0]
    wcs.wcs.cdelt = np.array([-0.0002777, 0.0002777])  # 1 arcsec/pixel
    wcs.wcs.crval = [202.46957, 47.19525]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs_hdr = wcs.to_header()
    hdr.extend(wcs_hdr)

    file_path = os.path.join(test_data_dir, "synthetic_standard.fits")
    fits.writeto(file_path, image, hdr, overwrite=True)
    return file_path


@pytest.fixture(scope="session")
def edge_case_fits(test_data_dir):
    """
    Creates an image with NaNs, Infs, saturated pixels, and missing WCS.
    """
    np.random.seed(99)
    image = np.ones((100, 100), dtype=np.float32) * 200.0
    # Inject NaNs
    image[10:15, 10:15] = np.nan
    # Inject Inf
    image[50, 50] = np.inf
    # Inject saturated pixels
    image[80:85, 80:85] = 65535.0

    hdr = fits.Header()
    hdr["OBJECT"] = "EDGE_CASE"
    hdr["SATURATE"] = 60000.0
    # No WCS keys

    file_path = os.path.join(test_data_dir, "synthetic_edge_case.fits")
    fits.writeto(file_path, image, hdr, overwrite=True)
    return file_path


@pytest.fixture(scope="session")
def multi_extension_fits(test_data_dir):
    """
    Creates MEF with:
    HDU 0: PrimaryHDU (header only, no data)
    HDU 1: ImageHDU 'SCI' (2D image)
    HDU 2: ImageHDU 'ERR' (Uncertainty map)
    """
    prim_hdr = fits.Header()
    prim_hdr["TELESCOP"] = "SpaceObs"
    prim_hdr["INSTRUME"] = "WFC"
    prim_hdu = fits.PrimaryHDU(header=prim_hdr)

    sci_data = np.full((128, 128), 150.0, dtype=np.float32)
    sci_hdr = fits.Header()
    sci_hdr["EXTNAME"] = "SCI"
    sci_hdr["GAIN"] = 2.0
    sci_hdu = fits.ImageHDU(data=sci_data, header=sci_hdr, name="SCI")

    err_data = np.full((128, 128), 5.0, dtype=np.float32)
    err_hdr = fits.Header()
    err_hdr["EXTNAME"] = "ERR"
    err_hdu = fits.ImageHDU(data=err_data, header=err_hdr, name="ERR")

    hdul = fits.HDUList([prim_hdu, sci_hdu, err_hdu])
    file_path = os.path.join(test_data_dir, "synthetic_mef.fits")
    hdul.writeto(file_path, overwrite=True)
    return file_path


@pytest.fixture(scope="session")
def synthetic_transit_fits(test_data_dir):
    """
    Creates a synthetic Kepler/TESS-style FITS binary table light curve with:
    - Time baseline: 30 days, 30-min cadences (1440 cadences)
    - Planet transit: Period = 3.5 days, Epoch t0 = 1.0, Depth = 0.01 (10,000 ppm), Duration = 0.15 days (3.6 hours)
    - Low-frequency stellar variability + Gaussian photometric noise
    """
    np.random.seed(123)
    t = np.linspace(0.0, 30.0, 1440)
    period = 3.5
    t0 = 1.0
    depth = 0.010
    duration = 0.15

    # Stellar trend + noise
    trend = 1.0 + 0.005 * np.sin(2 * np.pi * t / 15.0)
    noise = np.random.normal(0.0, 0.0008, size=len(t))
    flux = trend + noise

    # Inject box transits
    phase = ((t - t0 + 0.5 * period) % period) - 0.5 * period
    in_transit = np.abs(phase) < (0.5 * duration)
    flux[in_transit] -= depth

    flux_err = np.full_like(flux, 0.0008)

    # Make FITS table HDU
    cols = [
        fits.Column(name="TIME", format="D", unit="BJD", array=t),
        fits.Column(name="PDCSAP_FLUX", format="E", unit="e-/s", array=flux * 10000.0),
        fits.Column(name="PDCSAP_FLUX_ERR", format="E", unit="e-/s", array=flux_err * 10000.0),
    ]
    prim_hdu = fits.PrimaryHDU()
    table_hdu = fits.BinTableHDU.from_columns(cols, name="LIGHTCURVE")
    table_hdu.header["OBJECT"] = "SYNTH_EXOPLANET"
    table_hdu.header["TELESCOP"] = "TESS"

    hdul = fits.HDUList([prim_hdu, table_hdu])
    file_path = os.path.join(test_data_dir, "synthetic_transit.fits")
    hdul.writeto(file_path, overwrite=True)
    return file_path


@pytest.fixture(scope="session")
def synthetic_sinusoid_csv(test_data_dir):
    """
    Creates a CSV light curve of a periodic variable star (e.g. RR Lyrae/pulsating star).
    Period = 1.25 days, Amplitude = 0.05 mag/fraction.
    """
    import pandas as pd
    np.random.seed(456)
    t = np.linspace(0.0, 20.0, 500)
    period = 1.25
    amplitude = 0.05
    flux = 1.0 + amplitude * np.sin(2 * np.pi * t / period) + np.random.normal(0, 0.005, size=len(t))
    flux_err = np.full_like(flux, 0.005)

    df = pd.DataFrame({
        "TIME": t,
        "FLUX": flux,
        "FLUX_ERR": flux_err
    })
    file_path = os.path.join(test_data_dir, "synthetic_pulsator.csv")
    df.to_csv(file_path, index=False)
    return file_path

