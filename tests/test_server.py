"""
Integration tests for FastMCP server tools and sample data generator.
"""

import os
from astro_copilot.server import (
    inspect_fits,
    aperture_photometry,
    fit_lightcurve,
    generate_sample_datasets,
)


def test_generate_sample_datasets_and_run_pipeline(tmp_path):
    out_dir = str(tmp_path / "sample_out")
    gen_res = generate_sample_datasets(output_dir=out_dir)
    assert gen_res["status"] == "success"
    assert len(gen_res["files"]) == 3

    img_file = str(tmp_path / "sample_out" / "sample_image.fits")
    transit_file = str(tmp_path / "sample_out" / "sample_transit.fits")
    var_file = str(tmp_path / "sample_out" / "sample_variable_star.csv")

    assert os.path.exists(img_file)
    assert os.path.exists(transit_file)
    assert os.path.exists(var_file)

    # 1. Test inspect_fits MCP tool
    insp_res = inspect_fits(file_path=img_file)
    assert insp_res["status"] == "success"
    assert insp_res["selected_hdu"]["header_sample"]["OBJECT"] == "SAMPLE_FIELD"
    assert insp_res["selected_hdu"]["wcs"]["has_wcs"] is True

    # 2. Test aperture_photometry MCP tool
    phot_res = aperture_photometry(
        file_path=img_file,
        aperture_radius=5.0,
        positions=[[128.0, 128.0]],
        bkg_annulus_inner=8.0,
        bkg_annulus_outer=12.0,
    )
    assert phot_res["status"] == "success"
    assert phot_res["sources"][0]["flags"] == ["OK"]
    assert phot_res["sources"][0]["snr"] > 50.0

    # 3. Test fit_lightcurve MCP tool on transit
    lc_res = fit_lightcurve(
        file_path=transit_file,
        model_type="transit",
        period_hint=3.5,
        detrend_window_length=51,
    )
    assert lc_res["status"] == "success"
    assert abs(lc_res["fit_results"]["period_days"] - 3.525) < 0.1
    assert lc_res["fit_results"]["transit_depth_ppm"] > 8000.0

    # 4. Test fit_lightcurve MCP tool on variable star CSV
    var_res = fit_lightcurve(
        file_path=var_file,
        model_type="sinusoid",
        period_hint=1.45,
    )
    assert var_res["status"] == "success"
    assert abs(var_res["fit_results"]["period_days"] - 1.45) < 0.05
