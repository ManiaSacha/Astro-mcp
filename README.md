# Astro Copilot

**Give your AI assistant real astronomical data-reduction tools — FITS inspection, photometry, light curves, and spectra, running locally, no external service required.**

[![PyPI version](https://img.shields.io/pypi/v/astro-copilot.svg)](https://pypi.org/project/astro-copilot/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Publish](https://github.com/ManiaSacha/Astro-mcp/actions/workflows/publish.yml/badge.svg)](https://github.com/ManiaSacha/Astro-mcp/actions/workflows/publish.yml)

## Why this exists

Doing real astronomical data reduction — aperture photometry, transit fitting, WCS-aware source lookups — normally means writing throwaway Astropy/Photutils/Lightkurve scripts by hand, every time. Astro Copilot exposes that workflow as a set of [Model Context Protocol](https://modelcontextprotocol.io/) tools, so an LLM like Claude can inspect your FITS files, run photometry, detect sources, extract spectra, and fit light curves directly — with proper error propagation, WCS handling, and quality flags — entirely on your machine. No data leaves your computer, and no astronomy API keys required.

## Features

- **FITS inspection** — HDU structure, header keywords, WCS metadata, and robust image statistics (median, MAD-std, NaN/saturation flags)
- **Aperture photometry** — circular apertures with local sky-background annulus subtraction, full CCD error propagation (Poisson + read noise), per-source `quality_tier` (good/marginal/bad), and out-of-bounds pre-validation
- **Automatic source detection** — peak-finding with auto-estimated background and FWHM, minimum-separation filtering, and per-source SNR
- **Light curve analysis** — Savitzky-Golay detrending, transit detection via Box Least Squares, periodic-signal detection via Lomb-Scargle, phase-folded diagnostics
- **1D spectrum extraction** — sum/median/center-row extraction from 2D spectroscopic FITS, header-based wavelength calibration, spectral feature (line) detection
- **Synthetic sample data generator** — creates a test FITS image, transit light curve, and variable-star CSV with one call, no external downloads needed
- **Security-conscious by design** — path traversal validation on every file input, coordinate bounds checking before expensive operations

## Install

```bash
pip install astro-copilot
```

### Quick Start

```python
from astro_copilot.core.fits_io import inspect_fits_file
from astro_copilot.core.photometry import run_aperture_photometry

# Inspect a FITS file's structure, WCS, and image statistics
info = inspect_fits_file("sample_data/sample_image.fits")
print(info["selected_hdu"]["statistics"]["median"])

# Run aperture photometry on a known pixel position
result = run_aperture_photometry(
    file_path="sample_data/sample_image.fits",
    aperture_radius=6.0,
    positions=[[128.0, 128.0]],
    bkg_annulus_inner=9.0,
    bkg_annulus_outer=14.0,
)
print(result["sources"][0]["mag"], result["sources"][0]["quality_tier"])
```

Don't have a FITS file handy? Generate one:

```python
from astro_copilot.server import generate_sample_datasets
generate_sample_datasets("sample_data")
```

## Connect to Claude Desktop

Add this to your `claude_desktop_config.json`:

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

Restart Claude Desktop, and the following tools become available in chat: `inspect_fits`, `aperture_photometry`, `detect_sources_auto`, `extract_spectrum`, `fit_lightcurve`, and `generate_sample_datasets`.

## Example

Once connected, you can ask Claude directly:

> "Run aperture photometry on `sample_image.fits` at pixel (128, 128) with a 6-pixel aperture and a 9–14 pixel background annulus."

Claude calls `aperture_photometry` and gets back structured JSON like:

```json
{
  "status": "success",
  "sources": [
    {
      "id": 1,
      "x_px": 128.0,
      "y_px": 128.0,
      "bkg_subtracted_flux": 94210.5,
      "snr": 187.3,
      "mag": 15.318,
      "mag_err": 0.006,
      "quality_tier": "good",
      "flags": ["OK"]
    }
  ]
}
```

More worked examples — including transit detection and WCS-based sky coordinate lookups — are in [`docs/example_prompts.md`](docs/example_prompts.md). Full tool parameter reference: [`docs/tools_reference.md`](docs/tools_reference.md).

## Roadmap

- PSF-fitting photometry for crowded fields
- Multi-band/multi-epoch batch processing
- Image alignment and stacking helpers

Have a feature request? Open an issue.

## Contributing

Contributions are welcome:

1. Fork the repo and create a feature branch from `main`
2. Make your change, add or update tests under `tests/`, and run `pytest -v`
3. Open a pull request describing what changed and why

## License

MIT — see [LICENSE](LICENSE).
