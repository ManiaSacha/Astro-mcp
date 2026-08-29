"""
Tests for inspect_fits tool and FITS I/O handling.
"""

from astro_copilot.core.fits_io import inspect_fits_file


def test_inspect_standard_fits(standard_synthetic_fits):
    result = inspect_fits_file(standard_synthetic_fits)
    assert result["status"] == "success"
    assert result["hdu_count"] == 1
    assert len(result["hdus"]) == 1
    
    selected = result["selected_hdu"]
    assert selected["index"] == 0
    assert selected["header_sample"]["OBJECT"] == "NGC_TEST"
    assert selected["header_sample"]["EXPTIME"] == 60.0
    assert selected["header_sample"]["GAIN"] == 1.5
    
    # WCS
    wcs = selected["wcs"]
    assert wcs["has_wcs"] is True
    assert "RA---TAN" in wcs["ctype"][0]
    assert len(wcs["crval"]) == 2
    
    # Statistics
    stats = selected["statistics"]
    assert stats["shape"] == [256, 256]
    assert stats["nan_count"] == 0
    assert stats["inf_count"] == 0
    assert stats["mean"] > 250.0  # Background was ~300
    assert stats["max"] > 10000.0  # Bright star has high peak


def test_inspect_edge_case_nans_and_saturation(edge_case_fits):
    result = inspect_fits_file(edge_case_fits)
    assert result["status"] == "success"
    
    selected = result["selected_hdu"]
    assert selected["wcs"]["has_wcs"] is False
    
    stats = selected["statistics"]
    assert stats["nan_count"] == 25  # 5x5 block of NaNs
    assert stats["inf_count"] == 1   # 1 Inf
    assert stats["saturated_pixels"] == 25  # 5x5 block above 60000
    assert stats["min"] == 200.0


def test_inspect_multi_extension_fits_autodetect(multi_extension_fits):
    # Auto-detects HDU 1 (SCI) because HDU 0 has no 2D image data
    result = inspect_fits_file(multi_extension_fits)
    assert result["status"] == "success"
    assert result["hdu_count"] == 3
    assert result["selected_hdu"]["index"] == 1
    assert result["selected_hdu"]["name"] == "SCI"
    assert result["selected_hdu"]["statistics"]["shape"] == [128, 128]


def test_inspect_explicit_hdu_index(multi_extension_fits):
    result = inspect_fits_file(multi_extension_fits, hdu_index=2)
    assert result["status"] == "success"
    assert result["selected_hdu"]["index"] == 2
    assert result["selected_hdu"]["name"] == "ERR"


def test_inspect_nonexistent_file():
    result = inspect_fits_file("/nonexistent/astro/file.fits")
    assert result["status"] == "error"
    assert result["error_type"] == "FileNotFoundError"
