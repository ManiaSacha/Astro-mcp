"""
Tests for fit_and_analyze_lightcurve tool.
"""

from astro_copilot.core.lightcurve import fit_and_analyze_lightcurve


def test_fit_transit_fits_table(synthetic_transit_fits):
    result = fit_and_analyze_lightcurve(
        file_path=synthetic_transit_fits,
        model_type="transit",
        period_hint=3.5,
        detrend_window_length=101,
    )
    assert result["status"] == "success"
    assert result["points_count"] == 1440
    assert result["detrended"] is True

    fit = result["fit_results"]
    assert "BoxLeastSquares" in fit["model"]
    # Check period detection within 0.05 days of 3.5
    assert abs(fit["period_days"] - 3.5) < 0.05
    # Check transit depth ~ 10,000 ppm (0.01)
    assert 7000.0 < fit["transit_depth_ppm"] < 13000.0
    assert fit["snr"] > 10.0
    assert len(result["phase_binned_curve"]) > 0


def test_fit_sinusoid_csv(synthetic_sinusoid_csv):
    result = fit_and_analyze_lightcurve(
        file_path=synthetic_sinusoid_csv,
        model_type="sinusoid",
        period_hint=1.25,
    )
    assert result["status"] == "success"
    assert result["points_count"] == 500

    fit = result["fit_results"]
    assert "LombScargle" in fit["model"]
    # Check period detection within 0.02 days of 1.25
    assert abs(fit["period_days"] - 1.25) < 0.02
    assert 0.03 < fit["amplitude"] < 0.07
    assert len(result["phase_binned_curve"]) > 0


def test_fit_polynomial(synthetic_sinusoid_csv):
    result = fit_and_analyze_lightcurve(
        file_path=synthetic_sinusoid_csv,
        model_type="polynomial",
    )
    assert result["status"] == "success"
    fit = result["fit_results"]
    assert "Polynomial" in fit["model"]
    assert len(fit["coefficients"]) == 3
    assert fit["rms_residual"] > 0.0


def test_fit_nonexistent_file():
    result = fit_and_analyze_lightcurve("/nonexistent/path/lc.fits")
    assert result["status"] == "error"
    assert result["error_type"] == "FileNotFoundError"
