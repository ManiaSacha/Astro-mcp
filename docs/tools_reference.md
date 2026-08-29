# Astro Copilot MCP — Tools Reference (v1)

This document provides the parameter and return schemas for all tools provided by the **Astro Copilot MCP Server**.

---

## 1. `inspect_fits`

Inspects headers, HDU hierarchy, celestial WCS (World Coordinate System), and calculates robust image statistics for any local FITS file.

### Input Parameters
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_path` | `str` | Yes | — | Local path to the FITS file. |
| `hdu_index` | `int` | No | `None` | HDU index (auto-detects first 2D image HDU if omitted). |
| `header_keys` | `list[str]` | No | `None` | Custom header keywords to extract. If omitted, extracts standard astro headers (`EXPTIME`, `GAIN`, `OBJECT`, `FILTER`, `RDNOISE`, etc.). |
| `compute_stats` | `bool` | No | `true` | Whether to calculate robust stats (min, max, mean, median, MAD-std, NaN count, saturation count). |
| `saturation_threshold` | `float` | No | `None` | Custom threshold in ADU to count saturated pixels (defaults to `SATURATE` header if present). |

### Output Format
```json
{
  "status": "success",
  "file_path": "/path/to/image.fits",
  "hdu_count": 1,
  "hdus": [
    {"index": 0, "name": "PRIMARY", "type": "PrimaryHDU", "shape": [256, 256], "dtype": "float32"}
  ],
  "selected_hdu": {
    "index": 0,
    "name": "PRIMARY",
    "header_sample": {
      "OBJECT": "SAMPLE_FIELD",
      "EXPTIME": 60.0,
      "FILTER": "V",
      "GAIN": 1.5,
      "RDNOISE": 4.0
    },
    "wcs": {
      "has_wcs": true,
      "crval": [202.46957, 47.19525],
      "crpix": [128.0, 128.0],
      "ctype": ["RA---TAN", "DEC--TAN"],
      "pixel_scale_arcsec": [1.0, 1.0]
    },
    "statistics": {
      "shape": [256, 256],
      "min": 150.0,
      "max": 50000.0,
      "mean": 305.2,
      "median": 300.0,
      "std": 85.4,
      "mad_std": 17.2,
      "nan_count": 0,
      "inf_count": 0,
      "saturated_pixels": 0
    }
  }
}
```

---

## 2. `aperture_photometry`

Performs circular aperture photometry with optional annular local sky background subtraction and CCD error propagation (Poisson + Read Noise).

### Input Parameters
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_path` | `str` | Yes | — | Local path to the FITS image file. |
| `aperture_radius` | `float` | Yes | — | Circular aperture radius in pixels. |
| `hdu_index` | `int` | No | `None` | Target HDU index containing image data. |
| `positions` | `list[[x, y]]` | Optional* | `None` | List of pixel coordinate pairs. |
| `sky_coords` | `list[[ra, dec]]`| Optional* | `None` | List of celestial coordinates in degrees (converted via WCS). |
| `one_indexed` | `bool` | No | `false` | Set to `true` if input pixel coordinates are 1-based (DS9/IRAF style). |
| `bkg_annulus_inner` | `float` | No | `None` | Inner radius of local sky background annulus (pixels). |
| `bkg_annulus_outer` | `float` | No | `None` | Outer radius of local sky background annulus (pixels). |
| `gain` | `float` | No | Header / `1.0` | Detector gain in $e^-/\text{ADU}$. |
| `read_noise` | `float` | No | Header / `0.0` | Detector read noise in $e^-$. |
| `zero_point` | `float` | No | `25.0` | Magnitude zero point ($m = -2.5 \log_{10}(F) + ZP$). |
| `saturation_threshold` | `float` | No | `None` | Threshold to flag saturated apertures. |

*\* Either `positions` or `sky_coords` must be provided.*

### Output Format
```json
{
  "status": "success",
  "file_path": "/path/to/image.fits",
  "hdu_index": 0,
  "aperture_radius_px": 5.0,
  "annulus": {"inner_radius_px": 8.0, "outer_radius_px": 12.0},
  "zero_point": 25.0,
  "sources": [
    {
      "id": 1,
      "x_px": 128.0,
      "y_px": 128.0,
      "ra_deg": 202.46957,
      "dec_deg": 47.19525,
      "raw_flux": 117850.2,
      "local_bkg_per_px": 300.1,
      "bkg_subtracted_flux": 94290.5,
      "flux_err": 308.2,
      "snr": 305.9,
      "mag": 12.562,
      "mag_err": 0.0035,
      "flags": ["OK"]
    }
  ],
  "summary": {
    "total_sources": 1,
    "median_snr": 305.9,
    "gain_used": 1.5,
    "read_noise_used": 4.0
  }
}
```

---

## 3. `fit_lightcurve`

Detrends stellar / systematic variability with Savitzky-Golay filtering and fits transit (Box Least Squares) or periodic (Lomb-Scargle) models.

### Input Parameters
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_path` | `str` | Yes | — | Local path to FITS table (Kepler/TESS format) or CSV. |
| `model_type` | `str` | No | `"transit"` | Model type: `"transit"`, `"sinusoid"`, or `"polynomial"`. |
| `time_col` | `str` | No | Auto | Column name for time (e.g. `TIME`, `BJD`). |
| `flux_col` | `str` | No | Auto | Column name for flux (e.g. `PDCSAP_FLUX`, `FLUX`). |
| `flux_err_col` | `str` | No | Auto | Column name for flux uncertainties. |
| `detrend_window_length` | `int` | No | `None` | Odd integer window length for Savitzky-Golay flattening filter. |
| `period_hint` | `float` | No | `None` | Approximate period in days to focus the search grid. |
| `min_period` | `float` | No | `0.5` | Minimum period in days. |
| `max_period` | `float` | No | `30.0` | Maximum period in days. |
| `n_phase_bins` | `int` | No | `50` | Number of bins in the phase-folded summary curve. |

### Output Format
```json
{
  "status": "success",
  "file_path": "/path/to/lightcurve.fits",
  "points_count": 1344,
  "time_range": [0.0, 28.0],
  "time_span_days": 28.0,
  "detrended": true,
  "model_type": "transit",
  "fit_results": {
    "model": "BoxLeastSquares Transit",
    "period_days": 3.525,
    "t0_epoch": 1.201,
    "duration_hours": 2.88,
    "transit_depth_ppm": 12050.0,
    "snr": 28.4,
    "out_of_transit_scatter": 0.00072
  },
  "phase_binned_curve": [
    {"phase": -0.05, "binned_flux": 1.0001, "err": 0.00015},
    {"phase": 0.00, "binned_flux": 0.9880, "err": 0.00014},
    {"phase": 0.05, "binned_flux": 1.0002, "err": 0.00015}
  ]
}
```
