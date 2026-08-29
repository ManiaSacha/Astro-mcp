# Astro Copilot MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A professional-grade **Model Context Protocol (MCP)** server that integrates large language models like Claude with local astronomical data analysis. Astro Copilot enables AI assistants to perform precise data reduction on FITS files, including photometry, light curve analysis, and spectroscopic inspection—without relying on remote services.

## Features

### Core Capabilities

- **FITS File Inspection**: Automated HDU structure analysis, WCS celestial coordinate extraction, and robust image statistics (median, MAD standard deviation, NaN/saturation flagging)
- **Aperture Photometry**: Circular aperture photometry with photutils, local sky background annulus subtraction, full CCD error propagation (Poisson + read noise), and quality flags
- **Light Curve Analysis**: Automatic detrending (Savitzky-Golay filtering), transit detection (Box Least Squares), and periodic variable detection (Lomb-Scargle periodogram)
- **Synthetic Data Generation**: Built-in sample datasets for testing and demonstration without external dependencies

### Quality & Reliability

- Comprehensive error handling with informative error messages
- Input parameter validation to prevent silent failures
- Edge case handling (NaNs, missing WCS, saturated pixels, multi-extension HDUs)
- 15+ unit and integration tests covering nominal and pathological cases

## Requirements

- Python 3.10 or later
- Core dependencies: `fastmcp`, `astropy>=5.3`, `photutils>=1.8`, `lightkurve>=2.4`, `scipy`, `numpy`

## Installation

### From PyPI (Recommended)

```bash
pip install astro-copilot
```

### From Source

```bash
git clone https://github.com/ManiaSacha/Astro-mcp.git
cd Astro-mcp
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Start the MCP Server

```bash
python -m astro_copilot.server
```

### 2. Configure Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "astro-copilot": {
      "command": "python",
      "args": ["-m", "astro_copilot.server"]
    }
  }
}
```

### 3. Generate Sample Data

```bash
python -c "from astro_copilot.server import generate_sample_datasets; \
           generate_sample_datasets('sample_data')"
```

## API Reference

### `inspect_fits`

Inspect FITS file structure, headers, and image statistics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | str | Yes | Path to FITS file |
| `hdu_index` | int | No | HDU index to inspect (auto-detects first 2D image if omitted) |
| `compute_stats` | bool | No | Calculate image statistics (default: True) |
| `header_keys` | list[str] | No | Specific header keywords to extract |
| `saturation_threshold` | float | No | Pixel value threshold for saturation flagging |

**Returns:** Dictionary containing HDU summary, header samples, WCS metadata, and image statistics.

---

### `aperture_photometry`

Perform circular aperture photometry with background subtraction and error propagation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | str | Yes | Path to FITS image |
| `aperture_radius` | float | Yes | Aperture radius in pixels (must be > 0) |
| `positions` | list[[x, y]] | No* | Pixel coordinates (0-indexed by default) |
| `sky_coords` | list[[ra, dec]] | No* | Celestial coordinates in degrees |
| `one_indexed` | bool | No | If True, input coordinates are 1-indexed (DS9/IRAF style) |
| `bkg_annulus_inner` | float | No | Inner radius for background annulus in pixels |
| `bkg_annulus_outer` | float | No | Outer radius for background annulus in pixels |
| `gain` | float | No | Detector gain in e⁻/ADU (read from header if omitted) |
| `read_noise` | float | No | Detector read noise in e⁻ (read from header if omitted) |
| `zero_point` | float | No | Magnitude zero point (default: 25.0) |
| `saturation_threshold` | float | No | Saturation threshold for flagging |

*Either `positions` or `sky_coords` must be provided.

**Returns:** Dictionary with per-source results including flux, magnitude, SNR, and quality flags.

---

### `fit_lightcurve`

Analyze and fit periodic or transit signals in light curves.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | str | Yes | Path to FITS table or CSV light curve |
| `model_type` | str | No | Model: `transit`, `sinusoid`, or `polynomial` (default: `transit`) |
| `time_col` | str | No | Time column name (auto-detected if omitted) |
| `flux_col` | str | No | Flux column name (auto-detected if omitted) |
| `flux_err_col` | str | No | Flux error column name |
| `detrend_window_length` | int | No | Savitzky-Golay filter window length for detrending |
| `period_hint` | float | No | Estimated period in days to narrow search space |
| `min_period` | float | No | Minimum search period in days (default: 0.5) |
| `max_period` | float | No | Maximum search period in days (default: 30.0) |
| `n_phase_bins` | int | No | Number of bins in phase-folded light curve (default: 50) |

**Returns:** Dictionary with model parameters, fitted period, phase-binned light curve, and diagnostics.

---

### `generate_sample_datasets`

Generate synthetic astronomical datasets for testing and demonstration.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `output_dir` | str | No | Output directory (default: `sample_data`) |

**Generates:**
- `sample_image.fits`: 256×256 synthetic image with stars, background, and WCS
- `sample_transit.fits`: Simulated exoplanet transit light curve (TESS format)
- `sample_variable_star.csv`: Sinusoidal variable star time series

## Examples

### Inspect a FITS File

```python
from astro_copilot.core.fits_io import inspect_fits_file

result = inspect_fits_file(
    file_path="observation.fits",
    compute_stats=True,
    saturation_threshold=50000
)
print(result["selected_hdu"]["statistics"])
```

### Perform Aperture Photometry

```python
from astro_copilot.core.photometry import run_aperture_photometry

result = run_aperture_photometry(
    file_path="image.fits",
    aperture_radius=6.0,
    positions=[[128.5, 128.5], [200.0, 180.0]],
    bkg_annulus_inner=9.0,
    bkg_annulus_outer=14.0
)

for source in result["sources"]:
    print(f"Source {source['id']}: {source['mag']:.3f} ± {source['mag_err']:.3f}")
```

### Fit a Light Curve

```python
from astro_copilot.core.lightcurve import fit_and_analyze_lightcurve

result = fit_and_analyze_lightcurve(
    file_path="lightcurve.fits",
    model_type="transit",
    detrend_window_length=51
)

print(f"Period: {result['fit_results']['period_days']:.6f} days")
print(f"Transit depth: {result['fit_results']['transit_depth_ppm']:.1f} ppm")
```

## Testing

Run the full test suite:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_aperture_photometry.py -v
```

Tests cover:
- Standard photometric pipelines
- Astronomical edge cases (NaNs, missing WCS, saturation)
- Error handling and validation
- Sample data generation

## Architecture

### Module Organization

```
astro_copilot/
├── server.py              # FastMCP server entrypoint
├── core/
│   ├── fits_io.py        # FITS file I/O and WCS handling
│   ├── photometry.py     # Aperture photometry implementation
│   └── lightcurve.py     # Light curve fitting and analysis
└── utils/
    ├── error_models.py   # CCD error propagation
    └── serialization.py  # JSON serialization helpers
```

### Error Handling

All tools return structured error dictionaries on failure:

```python
{
    "status": "error",
    "error_type": "ValueError|FileNotFoundError|SecurityError|...",
    "message": "Human-readable error description"
}
```

## Security

- **Path Traversal Prevention**: All file paths are validated to prevent directory traversal attacks
- **Command Injection Prevention**: Process execution uses `spawn()` instead of shell string interpolation
- **Input Validation**: All numeric parameters are validated for reasonable ranges
- **No Remote Code Execution**: Local-only operation; no external service calls

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork and Branch**: Create a feature branch from `main`
2. **Code Style**: Follow PEP 8; use `black` for formatting
3. **Tests**: Add tests for all new features; ensure existing tests pass
4. **Documentation**: Update docstrings and README as needed
5. **Commit Messages**: Use clear, descriptive messages

### Development Workflow

```bash
# Clone and setup
git clone https://github.com/ManiaSacha/Astro-mcp.git
cd Astro-mcp
pip install -e ".[dev]"

# Make changes
git checkout -b feature/my-feature
# ... implement feature ...

# Test
pytest -v

# Commit and push
git push origin feature/my-feature
```

Submit a pull request with a clear description of changes.

## Troubleshooting

### ImportError: No module named 'photutils'

Ensure all dependencies are installed:
```bash
pip install -e .
```

### FITS file not found error

Verify the file path is absolute or relative to the current working directory:
```python
import os
print(os.path.abspath("my_file.fits"))
```

### WCS not found error when using sky_coords

Verify the FITS header contains valid WCS keywords (CTYPE1, CRPIX1, CRVAL1, etc.).

### Transit detection returns no signal

Try:
- Adjusting `min_period` and `max_period` to match expected transit duration
- Enabling detrending with `detrend_window_length=51`
- Checking SNR of individual sources with `inspect_fits` first

## Citation

If you use Astro Copilot in research, please cite:

```bibtex
@software{astro_copilot_2026,
  author = {Sacha, Mania},
  title = {Astro Copilot: Local Astronomical Data Reduction for AI Assistants},
  year = {2026},
  url = {https://github.com/ManiaSacha/Astro-mcp}
}
```

## License

This project is licensed under the MIT License—see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: See inline docstrings in module files
- **Issues**: Report bugs at [GitHub Issues](https://github.com/ManiaSacha/Astro-mcp/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/ManiaSacha/Astro-mcp/discussions)

## Acknowledgments

Built with:
- [Astropy](https://www.astropy.org/) — Core astronomical Python library
- [Photutils](https://photutils.readthedocs.io/) — Photometry and source detection
- [Lightkurve](https://lightkurve.readthedocs.io/) — Time series analysis for Kepler/TESS
- [FastMCP](https://github.com/jlowin/fastmcp) — Model Context Protocol implementation

---

**Last Updated:** August 2026  
**Status:** Active Development
