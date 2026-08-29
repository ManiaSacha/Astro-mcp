"""
Tests for aperture_photometry tool.
"""

from astro_copilot.core.photometry import run_aperture_photometry


def test_aperture_photometry_pixel_coords(standard_synthetic_fits):
    # Star 1 is at (128, 128) with amplitude 15000 and Gaussian sigma 2.5
    # Star 2 is at (60, 60)
    positions = [[128.0, 128.0], [60.0, 60.0]]
    result = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=6.0,
        positions=positions,
        bkg_annulus_inner=9.0,
        bkg_annulus_outer=14.0,
        zero_point=25.0,
    )
    assert result["status"] == "success"
    assert len(result["sources"]) == 2

    s1 = result["sources"][0]
    assert s1["id"] == 1
    assert s1["flags"] == ["OK"]
    assert s1["bkg_subtracted_flux"] > 50000.0  # Total integrated flux of Gaussian
    assert s1["snr"] > 50.0
    assert s1["mag"] is not None
    assert s1["mag_err"] is not None
    assert s1["local_bkg_per_px"] is not None
    # Background should be around 300 ADU
    assert 280.0 < s1["local_bkg_per_px"] < 320.0

    s2 = result["sources"][1]
    assert s2["id"] == 2
    assert s2["flags"] == ["OK"]
    assert s2["bkg_subtracted_flux"] < s1["bkg_subtracted_flux"]
    assert s2["mag"] > s1["mag"]  # Fainter star has larger magnitude


def test_aperture_photometry_sky_coords_wcs(standard_synthetic_fits):
    # CRVAL [202.46957, 47.19525] corresponds to 1-based CRPIX [128.0, 128.0],
    # which is 0-based pixel (127.0, 127.0) in Python
    sky_coords = [[202.46957, 47.19525]]
    result = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        sky_coords=sky_coords,
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert result["status"] == "success"
    assert len(result["sources"]) == 1
    s = result["sources"][0]
    # Check pixel position reconstructed from WCS in 0-based Python indexing
    assert abs(s["x_px"] - 127.0) < 0.1
    assert abs(s["y_px"] - 127.0) < 0.1
    assert s["flags"] == ["OK"]


def test_aperture_photometry_edge_case_flags(edge_case_fits):
    # (12, 12) is inside NaN block
    # (82, 82) is inside saturated block
    positions = [[12.0, 12.0], [82.0, 82.0], [500.0, 500.0]]
    result = run_aperture_photometry(
        file_path=edge_case_fits,
        aperture_radius=4.0,
        positions=positions,
    )
    assert result["status"] == "success"
    assert len(result["sources"]) == 3

    # Source in NaNs
    assert "NAN_IN_APERTURE" in result["sources"][0]["flags"]
    # Source in Saturation
    assert "SATURATED" in result["sources"][1]["flags"]
    # Source off image
    assert "OFF_IMAGE" in result["sources"][2]["flags"]


def test_aperture_photometry_missing_wcs_error(edge_case_fits):
    # edge_case_fits has no WCS, passing sky_coords should return informative error
    result = run_aperture_photometry(
        file_path=edge_case_fits,
        aperture_radius=5.0,
        sky_coords=[[150.0, 20.0]],
    )
    assert result["status"] == "error"
    assert result["error_type"] == "WCSNotFoundError"


def test_aperture_photometry_one_indexed(standard_synthetic_fits):
    # Testing 1-indexed conversion (DS9 style)
    # (129.0, 129.0) in 1-based is (128.0, 128.0) in 0-based
    result = run_aperture_photometry(
        file_path=standard_synthetic_fits,
        aperture_radius=5.0,
        positions=[[129.0, 129.0]],
        one_indexed=True,
    )
    assert result["status"] == "success"
    assert abs(result["sources"][0]["x_px"] - 128.0) < 1e-3
    assert abs(result["sources"][0]["y_px"] - 128.0) < 1e-3
