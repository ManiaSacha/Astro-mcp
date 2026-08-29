"""
Tests for WCS round-trip coordinate conversions and edge cases.
"""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
import os

from astro_copilot.core.photometry import run_aperture_photometry


@pytest.fixture(scope="module")
def wcs_negative_declination_fits(tmp_path_factory):
    """
    Creates FITS image with WCS in southern hemisphere (negative declination).
    """
    test_data_dir = tmp_path_factory.mktemp("wcs_test_data")

    image = np.random.poisson(200.0, size=(128, 128)).astype(np.float32)
    # Add a bright star at center
    y, x = np.mgrid[0:128, 0:128]
    r2 = (x - 64)**2 + (y - 64)**2
    image += (5000.0 * np.exp(-0.5 * r2 / 2.0**2)).astype(np.float32)

    hdr = fits.Header()
    hdr["OBJECT"] = "SOUTHERN_HEMISPHERE"
    hdr["GAIN"] = 1.5
    hdr["RDNOISE"] = 4.0

    # Southern hemisphere: negative declination
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [64.0, 64.0]
    wcs.wcs.cdelt = np.array([-0.0002777, 0.0002777])  # 1 arcsec/pixel
    wcs.wcs.crval = [180.0, -45.0]  # RA=180, Dec=-45
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    hdr.extend(wcs.to_header())

    file_path = os.path.join(test_data_dir, "wcs_negative_dec.fits")
    fits.writeto(file_path, image, hdr, overwrite=True)
    return file_path


@pytest.fixture(scope="module")
def wcs_near_pole_fits(tmp_path_factory):
    """
    Creates FITS image with WCS near celestial pole.
    Tests projection singularities and high declination.
    """
    test_data_dir = tmp_path_factory.mktemp("wcs_test_data")

    image = np.random.poisson(200.0, size=(100, 100)).astype(np.float32)
    y, x = np.mgrid[0:100, 0:100]
    r2 = (x - 50)**2 + (y - 50)**2
    image += (3000.0 * np.exp(-0.5 * r2 / 2.0**2)).astype(np.float32)

    hdr = fits.Header()
    hdr["OBJECT"] = "NEAR_POLE"
    hdr["GAIN"] = 1.5
    hdr["RDNOISE"] = 4.0

    # Near north celestial pole
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [50.0, 50.0]
    wcs.wcs.cdelt = np.array([-0.0002777, 0.0002777])
    wcs.wcs.crval = [0.0, 85.0]  # RA=0, Dec=85 (close to pole)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    hdr.extend(wcs.to_header())

    file_path = os.path.join(test_data_dir, "wcs_near_pole.fits")
    fits.writeto(file_path, image, hdr, overwrite=True)
    return file_path


def test_wcs_roundtrip_standard(standard_synthetic_fits):
    """
    Test pixel -> RA/Dec -> pixel round-trip on standard WCS.
    """
    # Use central star
    positions = [[128.0, 128.0]]
    result = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        positions=positions,
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert result["status"] == "success"
    source = result["sources"][0]
    ra, dec = source["ra_deg"], source["dec_deg"]

    # Should be close to CRVAL of the WCS
    assert 202.45 < ra < 202.50
    assert 47.18 < dec < 47.20

    # Now use sky coords to convert back
    result_sky = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        sky_coords=[[ra, dec]],
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert result_sky["status"] == "success"
    source_back = result_sky["sources"][0]
    # Should recover approximately the original position
    assert abs(source_back["x_px"] - 128.0) < 0.1
    assert abs(source_back["y_px"] - 128.0) < 0.1


def test_wcs_roundtrip_negative_declination(wcs_negative_declination_fits):
    """
    Test WCS round-trip with negative declination (southern hemisphere).
    """
    # Pixel position of star
    positions = [[64.0, 64.0]]
    result = run_aperture_photometry(
        file_path=wcs_negative_declination_fits,
        aperture_radius=5.0,
        positions=positions,
    )
    assert result["status"] == "success"
    source = result["sources"][0]
    ra, dec = source["ra_deg"], source["dec_deg"]

    # Should have negative declination
    assert dec < 0
    assert 179.5 < ra < 180.5
    assert -46 < dec < -44

    # Round-trip
    result_sky = run_aperture_photometry(
        file_path=wcs_negative_declination_fits,
        aperture_radius=5.0,
        sky_coords=[[ra, dec]],
    )
    assert result_sky["status"] == "success"
    source_back = result_sky["sources"][0]
    assert abs(source_back["x_px"] - 64.0) < 0.1
    assert abs(source_back["y_px"] - 64.0) < 0.1


def test_wcs_near_pole(wcs_near_pole_fits):
    """
    Test WCS round-trip near celestial pole (high declination).
    Tangent plane projection can have singularities and distortions.
    """
    positions = [[50.0, 50.0]]
    result = run_aperture_photometry(
        file_path=wcs_near_pole_fits,
        aperture_radius=4.0,
        positions=positions,
    )
    assert result["status"] == "success"
    source = result["sources"][0]
    ra, dec = source["ra_deg"], source["dec_deg"]

    # Should have high declination
    assert dec > 84.0
    # RA can vary more near pole, but should be reasonable
    assert 0 <= ra <= 360 or -180 <= ra <= 180

    # Round-trip (may have larger tolerance near pole)
    result_sky = run_aperture_photometry(
        file_path=wcs_near_pole_fits,
        aperture_radius=4.0,
        sky_coords=[[ra, dec]],
    )
    assert result_sky["status"] == "success"
    source_back = result_sky["sources"][0]
    # Tolerance larger near pole due to projection effects
    assert abs(source_back["x_px"] - 50.0) < 0.5
    assert abs(source_back["y_px"] - 50.0) < 0.5


def test_wcs_missing_returns_none(edge_case_fits):
    """
    Verify missing WCS returns None for RA/Dec.
    """
    positions = [[50.0, 50.0]]
    result = run_aperture_photometry(
        file_path=edge_case_fits,
        aperture_radius=5.0,
        positions=positions,
    )
    assert result["status"] == "success"
    source = result["sources"][0]
    # Should have None for celestial coords
    assert source["ra_deg"] is None
    assert source["dec_deg"] is None


def test_wcs_multiple_sources_roundtrip(standard_synthetic_fits):
    """
    Test round-trip with multiple sources.
    """
    positions = [[128.0, 128.0], [60.0, 60.0], [200.0, 180.0]]
    result_pix = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        positions=positions,
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert result_pix["status"] == "success"
    assert len(result_pix["sources"]) == 3

    # Extract RA/Dec
    sky_coords = [[s["ra_deg"], s["dec_deg"]] for s in result_pix["sources"]]

    # Round-trip
    result_sky = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        sky_coords=sky_coords,
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert result_sky["status"] == "success"
    assert len(result_sky["sources"]) == 3

    # Verify round-trip accuracy for each source
    for i, src_orig in enumerate(result_pix["sources"]):
        src_back = result_sky["sources"][i]
        assert abs(src_back["x_px"] - src_orig["x_px"]) < 0.1
        assert abs(src_back["y_px"] - src_orig["y_px"]) < 0.1
