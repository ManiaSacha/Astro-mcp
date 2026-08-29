# Conversational Prompts for Astronomers

These example dialogues demonstrate how a researcher can work directly with an AI assistant connected to the **Astro Data-Reduction Copilot MCP**.

---

## Example 1: Inspecting a Nightly Science Image

**User:**
> "I just took a 120s exposure of M51 in V band with our 0.5m telescope. The file is saved at `data/2026-08-29/m51_v_001.fits`. Can you check the image health, exposure time, saturation level, and confirm if WCS is calibrated?"

**AI Workflow:**
1. Calls `inspect_fits(file_path="data/2026-08-29/m51_v_001.fits", compute_stats=True)`
2. Reports back:
   - **Header details**: Exposure time (120s), Filter (V), Gain ($1.5\,e^-/\text{ADU}$), Read Noise ($4.2\,e^-$).
   - **WCS Calibration**: Confirmed TAN projection centered on $\alpha = 13^{\text{h}}29^{\text{m}}52.7^{\text{s}}$, $\delta = +47^\circ 11' 43''$, pixel scale $0.72''/\text{pixel}$.
   - **Data Quality**: Median background = $312\,\text{ADU}$, robust MAD scatter = $14.8\,\text{ADU}$, 0 NaNs, 14 saturated pixels in the core nucleus.

---

## Example 2: Precision Aperture Photometry with Annulus Background

**User:**
> "In `data/2026-08-29/m51_v_001.fits`, run circular aperture photometry for our target supernova at RA 202.46957 deg, Dec 47.19525 deg. Use an aperture radius of 5.0 pixels and a sky background annulus between 8.0 and 12.0 pixels. Zero point is 25.0."

**AI Workflow:**
1. Calls `aperture_photometry`:
   ```json
   {
     "file_path": "data/2026-08-29/m51_v_001.fits",
     "sky_coords": [[202.46957, 47.19525]],
     "aperture_radius": 5.0,
     "bkg_annulus_inner": 8.0,
     "bkg_annulus_outer": 12.0,
     "zero_point": 25.0
   }
   ```
2. Summarizes the photometric reduction:
   - **Source Centroid**: $(x, y) = (512.4, 384.2)$
   - **Local Sky Background**: $15.2\,\text{ADU/pixel}$ (sigma-clipped median)
   - **Net Flux**: $11,256.4 \pm 115.8\,\text{ADU}$
   - **Signal-to-Noise Ratio (SNR)**: $97.2$
   - **Instrumental Magnitude**: $V = 14.870 \pm 0.011\,\text{mag}$
   - **Flags**: `OK` (no saturation or NaNs in aperture)

---

## Example 3: Detrending Stellar Variability & Fitting Exoplanet Transits

**User:**
> "I have a TESS Sector light curve `sample_data/sample_transit.fits`. The host star shows some low-frequency stellar rotation. Flatten the light curve with a 51-cadence Savitzky-Golay window and fit for an exoplanet transit around period = 3.5 days."

**AI Workflow:**
1. Calls `fit_lightcurve`:
   ```json
   {
     "file_path": "sample_data/sample_transit.fits",
     "model_type": "transit",
     "detrend_window_length": 51,
     "period_hint": 3.5
   }
   ```
2. Delivers scientific interpretation:
   - **Detrending**: Successfully flattened low-frequency rotational modulation.
   - **Transit Period**: $P = 3.5250\,\text{days}$
   - **Transit Epoch ($T_0$)**: $\text{BJD } 2458601.201$
   - **Transit Depth**: $12,050\,\text{ppm}$ ($1.205\%$, indicating a Jupiter-sized candidate $\sim 1.1\,R_{\text{Jup}}$ assuming a solar-type host star)
   - **Transit Duration**: $2.88\,\text{hours}$
   - **Detection Significance**: $\text{SNR} = 28.4$ with out-of-transit scatter of $720\,\text{ppm}$.
