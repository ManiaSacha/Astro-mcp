# Astro Copilot MCP Server

An open-source **Model Context Protocol (MCP)** server that acts as a local data-reduction copilot for astronomers. Instead of only querying remote online catalogs (SIMBAD, Gaia, VizieR), this MCP server enables AI assistants like Claude to work directly on a researcher's own local FITS files:

- **FITS Header & WCS Inspection**: Automatic HDU structure analysis, celestial coordinate scale resolution, and robust statistics (MAD standard deviation, NaNs, saturation).
- **Aperture Photometry**: Circular aperture photometry powered by `photutils` and `astropy`, with local sky background subtraction (annulus) and full CCD error propagation (Poisson + Read noise).
- **Light-Curve Analysis & Fitting**: Light curve detrending and flattening (Savitzky-Golay filtering) via `lightkurve`, combined with Box Least Squares (BLS) transit fitting and Lomb-Scargle periodic variable star modeling.

---

## Architecture & Subagents

This project was designed using a multi-agent workflow configured in `.claude/agents/`:
1. **`architect`** (`.claude/agents/architect.md`): Schema definitions, error propagation rules, and module design.
2. **`mcp-builder`** (`.claude/agents/mcp-builder.md`): FastMCP tool implementation and core astronomical computation.
3. **`test-writer`** (`.claude/agents/test-writer.md`): Test fixtures, edge cases (NaNs, missing WCS, saturation, multi-extension HDUs), and automated test suites.
4. **`docs-writer`** (`.claude/agents/docs-writer.md`): Tools reference and conversational astronomy prompt walkthroughs.

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- `fastmcp`, `astropy`, `photutils`, `lightkurve`, `scipy`, `pandas`

```bash
pip install -e .
```

### Running the MCP Server
```bash
python -m astro_copilot.server
```

---

## Claude Desktop Configuration

Add the following configuration to your `claude_desktop_config.json`:

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

---

## Tools Overview

| Tool Name | Key Inputs | Output Summary |
|---|---|---|
| `inspect_fits` | `file_path`, `hdu_index`, `compute_stats` | HDU listing, standard headers, WCS projection & pixel scale, min/max/median/MAD stats, NaN/saturation counts |
| `aperture_photometry` | `file_path`, `aperture_radius`, `positions` or `sky_coords`, `bkg_annulus_inner/outer` | Centroids, raw flux, local sky background/px, net flux, flux error, SNR, instrumental magnitude & error, quality flags |
| `fit_lightcurve` | `file_path`, `model_type` (`transit`/`sinusoid`), `detrend_window_length`, `period_hint` | Flattened time series, period, epoch $t_0$, depth/amplitude, duration, SNR, and phase-binned diagnostic curve |
| `generate_sample_datasets` | `output_dir` | Generates 3 synthetic datasets (`sample_image.fits`, `sample_transit.fits`, `sample_variable_star.csv`) |

---

## Out-of-the-box Sample Data

Generate reproducible synthetic datasets without needing external telescope connections:

```bash
python -c "from astro_copilot.server import generate_sample_datasets; generate_sample_datasets('sample_data')"
```

---

## Running the Test Suite

```bash
pytest -v
```
All 15 unit and integration tests validate standard data pipelines as well as astronomical edge cases.
