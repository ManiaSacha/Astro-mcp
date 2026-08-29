import React, { useState, useEffect } from "react";
import {
  Telescope,
  Search,
  Sparkles,
  Play,
  Terminal,
  FileCode2,
  CheckCircle2,
  AlertCircle,
  Activity,
  Layers,
  HelpCircle,
  Bot,
  Copy,
  Check,
  ChevronRight,
  Database,
  Crosshair,
  Sliders,
  Menu,
  X,
  GitBranch,
  GitCommit,
  Upload,
  RefreshCw
} from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState<"copilot" | "tools" | "docs" | "tests" | "git-agent">("copilot");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<"inspect_fits" | "aperture_photometry" | "fit_lightcurve">("inspect_fits");
  
  // Tool Parameters State
  const [inspectPath, setInspectPath] = useState("sample_data/sample_image.fits");
  const [inspectStats, setInspectStats] = useState(true);

  const [photPath, setPhotPath] = useState("sample_data/sample_image.fits");
  const [photRadius, setPhotRadius] = useState(5.0);
  const [photPositions, setPhotPositions] = useState("[[128.0, 128.0], [60.0, 60.0]]");
  const [photAnnulusIn, setPhotAnnulusIn] = useState(8.0);
  const [photAnnulusOut, setPhotAnnulusOut] = useState(12.0);

  const [lcPath, setLcPath] = useState("sample_data/sample_transit.fits");
  const [lcModel, setLcModel] = useState<"transit" | "sinusoid" | "polynomial">("transit");
  const [lcPeriodHint, setLcPeriodHint] = useState(3.525);
  const [lcDetrendWin, setLcDetrendWin] = useState(51);

  // Execution & Output State
  const [isRunning, setIsRunning] = useState(false);
  const [toolOutput, setToolOutput] = useState<any>(null);
  const [testOutput, setTestOutput] = useState<string>("");
  const [isTesting, setIsTesting] = useState(false);
  const [copiedConfig, setCopiedConfig] = useState(false);



  const handleRunTool = async () => {
    setIsRunning(true);
    setToolOutput(null);
    let params: any = {};

    if (selectedTool === "inspect_fits") {
      params = {
        file_path: inspectPath,
        compute_stats: inspectStats,
      };
    } else if (selectedTool === "aperture_photometry") {
      try {
        const parsedPositions = JSON.parse(photPositions);
        params = {
          file_path: photPath,
          aperture_radius: Number(photRadius),
          positions: parsedPositions,
          bkg_annulus_inner: Number(photAnnulusIn),
          bkg_annulus_outer: Number(photAnnulusOut),
          zero_point: 25.0,
        };
      } catch (err) {
        setToolOutput({ status: "error", message: "Invalid JSON for pixel positions." });
        setIsRunning(false);
        return;
      }
    } else if (selectedTool === "fit_lightcurve") {
      params = {
        file_path: lcPath,
        model_type: lcModel,
        period_hint: lcPeriodHint ? Number(lcPeriodHint) : undefined,
        detrend_window_length: lcDetrendWin ? Number(lcDetrendWin) : undefined,
      };
    }

    try {
      const res = await fetch("/api/mcp/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: selectedTool, params }),
      });
      const data = await res.json();
      setToolOutput(data);
    } catch (err: any) {
      setToolOutput({ status: "error", message: err.message });
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunTests = async () => {
    setIsTesting(true);
    setTestOutput("Running pytest suite across all astronomical tools and fixtures...");
    try {
      const res = await fetch("/api/run-tests");
      const data = await res.json();
      setTestOutput(data.output || data.error || "Tests executed.");
    } catch (err: any) {
      setTestOutput("Failed to run tests: " + err.message);
    } finally {
      setIsTesting(false);
    }
  };

  const copyClaudeConfig = () => {
    const config = JSON.stringify(
      {
        mcpServers: {
          "astro-copilot": {
            command: "python",
            args: ["-m", "astro_copilot.server"],
          },
        },
      },
      null,
      2
    );
    navigator.clipboard.writeText(config);
    setCopiedConfig(true);
    setTimeout(() => setCopiedConfig(false), 2000);
  };

  const navItems = [
    { id: "copilot", label: "Overview & Sandbox" },
    { id: "tools", label: "MCP Tool Schemas" },
    { id: "docs", label: "Prompts & Guide" },
    { id: "tests", label: "Pytest Suite" },
  ] as const;

  return (
    <div id="app-root" className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Header */}
      <header id="main-header" className="border-b border-slate-800 bg-slate-900/90 backdrop-blur px-4 sm:px-6 py-3.5 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 shrink-0 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Telescope className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2 flex-wrap">
                <h1 className="text-sm sm:text-base font-bold tracking-tight text-white truncate">
                  Astro Copilot MCP
                </h1>
                <span className="text-[10px] sm:text-xs bg-indigo-500/20 text-indigo-300 font-mono px-2 py-0.5 rounded-full border border-indigo-500/30 whitespace-nowrap">
                  MCP v0.1.0
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400 truncate hidden sm:block">
                Local astronomical FITS inspection, photometry & light-curve reduction
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav id="desktop-nav" className="hidden lg:flex items-center space-x-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700">
            {navItems.map((item) => (
              <button
                key={item.id}
                id={`desktop-tab-${item.id}`}
                onClick={() => setActiveTab(item.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition whitespace-nowrap ${
                  activeTab === item.id ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* Mobile/Tablet Hamburger Button */}
          <div className="flex items-center lg:hidden">
            <button
              id="mobile-menu-toggle-btn"
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileMenuOpen}
              className={`p-2.5 rounded-lg border text-slate-200 transition focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                mobileMenuOpen
                  ? "bg-slate-800 border-indigo-500 text-white"
                  : "bg-slate-800/80 border-slate-700 hover:bg-slate-700"
              }`}
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-indigo-400" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div id="mobile-nav-dropdown" className="lg:hidden mt-3 pt-3 border-t border-slate-800 space-y-1.5">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  id={`mobile-tab-${item.id}`}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-xs font-medium transition min-h-[44px] ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-md font-semibold"
                      : "bg-slate-950/60 text-slate-300 hover:bg-slate-800 hover:text-white border border-slate-800/80"
                  }`}
                >
                  <span>{item.label}</span>
                  {isActive && <Check className="w-4 h-4 text-white shrink-0 ml-2" />}
                </button>
              );
            })}
          </div>
        )}
      </header>

      {/* Main Container */}
      <main id="main-content" className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        {activeTab === "copilot" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6">
            {/* Left Column: Tool Controls */}
            <div className="lg:col-span-5 space-y-5">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-indigo-400" />
                    Local Tool Invoker
                  </h2>
                  <span className="text-[11px] sm:text-xs text-slate-400">FastMCP Interface</span>
                </div>

                {/* Tool Selector */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
                  <button
                    id="btn-select-inspect"
                    onClick={() => setSelectedTool("inspect_fits")}
                    className={`py-2.5 sm:py-2 px-2 text-xs rounded-lg font-medium border text-center transition min-h-[44px] sm:min-h-[38px] flex items-center justify-center ${
                      selectedTool === "inspect_fits"
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
                    }`}
                  >
                    inspect_fits
                  </button>
                  <button
                    id="btn-select-phot"
                    onClick={() => setSelectedTool("aperture_photometry")}
                    className={`py-2.5 sm:py-2 px-2 text-xs rounded-lg font-medium border text-center transition min-h-[44px] sm:min-h-[38px] flex items-center justify-center ${
                      selectedTool === "aperture_photometry"
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
                    }`}
                  >
                    aperture_photometry
                  </button>
                  <button
                    id="btn-select-lc"
                    onClick={() => setSelectedTool("fit_lightcurve")}
                    className={`py-2.5 sm:py-2 px-2 text-xs rounded-lg font-medium border text-center transition min-h-[44px] sm:min-h-[38px] flex items-center justify-center ${
                      selectedTool === "fit_lightcurve"
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
                    }`}
                  >
                    fit_lightcurve
                  </button>
                </div>

                {/* Parameters Form */}
                <div className="space-y-3">
                  {selectedTool === "inspect_fits" && (
                    <>
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Local FITS File Path</label>
                        <input
                          type="text"
                          value={inspectPath}
                          onChange={(e) => setInspectPath(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                        />
                      </div>
                      <div className="flex items-center space-x-2 pt-1">
                        <input
                          type="checkbox"
                          id="stats-check"
                          checked={inspectStats}
                          onChange={(e) => setInspectStats(e.target.checked)}
                          className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0 cursor-pointer"
                        />
                        <label htmlFor="stats-check" className="text-xs text-slate-300 cursor-pointer select-none">
                          Compute robust statistics (median, MAD-std, NaNs, saturation)
                        </label>
                      </div>
                    </>
                  )}

                  {selectedTool === "aperture_photometry" && (
                    <>
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">FITS Image Path</label>
                        <input
                          type="text"
                          value={photPath}
                          onChange={(e) => setPhotPath(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Radius (px)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={photRadius}
                            onChange={(e) => setPhotRadius(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Annulus In (px)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={photAnnulusIn}
                            onChange={(e) => setPhotAnnulusIn(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Annulus Out (px)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={photAnnulusOut}
                            onChange={(e) => setPhotAnnulusOut(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Source Pixel Positions [[x, y], ...]</label>
                        <input
                          type="text"
                          value={photPositions}
                          onChange={(e) => setPhotPositions(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                        />
                      </div>
                    </>
                  )}

                  {selectedTool === "fit_lightcurve" && (
                    <>
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Light Curve File (FITS table or CSV)</label>
                        <input
                          type="text"
                          value={lcPath}
                          onChange={(e) => setLcPath(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Model Type</label>
                          <select
                            value={lcModel}
                            onChange={(e: any) => setLcModel(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          >
                            <option value="transit">Transit (BLS)</option>
                            <option value="sinusoid">Sinusoid (LS)</option>
                            <option value="polynomial">Polynomial</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Period Hint (d)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={lcPeriodHint}
                            onChange={(e) => setLcPeriodHint(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Detrend Win</label>
                          <input
                            type="number"
                            step="2"
                            value={lcDetrendWin}
                            onChange={(e) => setLcDetrendWin(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none min-h-[40px]"
                          />
                        </div>
                      </div>
                    </>
                  )}

                  <button
                    onClick={handleRunTool}
                    disabled={isRunning}
                    className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-3 sm:py-2.5 rounded-lg text-xs flex items-center justify-center gap-2 shadow-md transition min-h-[44px]"
                  >
                    {isRunning ? (
                      <>
                        <Activity className="w-4 h-4 animate-spin" />
                        Running Python Reducer...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-current" />
                        Execute Tool on Local Dataset
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Sample Files Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
                  Preloaded Sample Datasets
                </h3>
                <div className="space-y-2">
                  <div
                    onClick={() => {
                      setSelectedTool("inspect_fits");
                      setInspectPath("sample_data/sample_image.fits");
                    }}
                    className="p-3 bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg cursor-pointer transition flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-200 truncate">sample_data/sample_image.fits</div>
                      <div className="text-[11px] text-slate-400 truncate">256x256 image with synthetic stars, WCS & noise</div>
                    </div>
                    <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700 shrink-0">
                      Image
                    </span>
                  </div>

                  <div
                    onClick={() => {
                      setSelectedTool("fit_lightcurve");
                      setLcPath("sample_data/sample_transit.fits");
                      setLcModel("transit");
                      setLcPeriodHint(3.525);
                    }}
                    className="p-3 bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg cursor-pointer transition flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-200 truncate">sample_data/sample_transit.fits</div>
                      <div className="text-[11px] text-slate-400 truncate">TESS-style 28-day light curve with exoplanet transit</div>
                    </div>
                    <span className="text-[10px] bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-800 shrink-0">
                      Transit
                    </span>
                  </div>

                  <div
                    onClick={() => {
                      setSelectedTool("fit_lightcurve");
                      setLcPath("sample_data/sample_variable_star.csv");
                      setLcModel("sinusoid");
                      setLcPeriodHint(1.45);
                    }}
                    className="p-3 bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg cursor-pointer transition flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-200 truncate">sample_data/sample_variable_star.csv</div>
                      <div className="text-[11px] text-slate-400 truncate">Pulsating variable star time-series (P=1.45d)</div>
                    </div>
                    <span className="text-[10px] bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded border border-cyan-800 shrink-0">
                      CSV
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Structured JSON & Visualizer */}
            <div className="lg:col-span-7 space-y-5">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 h-full flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3 flex-wrap gap-2">
                  <div className="flex items-center space-x-2">
                    <Terminal className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-white">LLM-Readable Output</h3>
                  </div>
                  {toolOutput && (
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded font-mono ${
                        toolOutput.status === "success"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-red-950 text-red-400 border border-red-800"
                      }`}
                    >
                      status: {toolOutput.status}
                    </span>
                  )}
                </div>

                {toolOutput ? (
                  <div className="space-y-4 flex-1">
                    {/* Visual cards if photometry */}
                    {selectedTool === "aperture_photometry" && toolOutput.sources && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">Total Sources Measured</span>
                          <div className="text-xl font-bold text-white mt-0.5">{toolOutput.sources.length}</div>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">Median SNR</span>
                          <div className="text-xl font-bold text-emerald-400 mt-0.5">
                            {toolOutput.summary?.median_snr || "N/A"}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Visual cards if lightcurve */}
                    {selectedTool === "fit_lightcurve" && toolOutput.fit_results && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">Detected Period</span>
                          <div className="text-lg font-bold text-cyan-400 mt-0.5">
                            {toolOutput.fit_results.period_days} days
                          </div>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">
                            {toolOutput.fit_results.transit_depth_ppm ? "Transit Depth" : "Amplitude"}
                          </span>
                          <div className="text-lg font-bold text-indigo-400 mt-0.5">
                            {toolOutput.fit_results.transit_depth_ppm
                              ? `${toolOutput.fit_results.transit_depth_ppm} ppm`
                              : toolOutput.fit_results.amplitude}
                          </div>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                          <span className="text-[11px] text-slate-400">Fit Metric</span>
                          <div className="text-lg font-bold text-emerald-400 mt-0.5">
                            {toolOutput.fit_results.snr ? `SNR ${toolOutput.fit_results.snr}` : `Power ${toolOutput.fit_results.power}`}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* JSON Code Viewer */}
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 sm:p-4 font-mono text-[11px] sm:text-xs text-slate-300 overflow-x-auto max-h-[380px] sm:max-h-[420px] overflow-y-auto leading-relaxed">
                      <pre>{JSON.stringify(toolOutput, null, 2)}</pre>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-8 text-slate-500 min-h-[200px]">
                    <Crosshair className="w-10 h-10 mb-2 opacity-40 text-slate-400" />
                    <p className="text-xs text-slate-400">Select a tool and click "Execute Tool" to view structured output.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}



        {/* Tab 3: MCP Tool Schemas */}
        {activeTab === "tools" && (
          <div className="space-y-5 sm:space-y-6">
            <div>
              <h2 className="text-base font-bold text-white">FastMCP Tool Schemas</h2>
              <p className="text-xs text-slate-400">
                Every tool is typed and strictly returns 100% JSON-serializable structured dictionaries.
              </p>
            </div>

            <div className="space-y-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
                <div className="flex items-start sm:items-center justify-between mb-2 flex-col sm:flex-row gap-1">
                  <h3 className="font-mono text-xs sm:text-sm font-semibold text-indigo-300 break-all">
                    inspect_fits(file_path, hdu_index, header_keys, compute_stats)
                  </h3>
                  <span className="text-[11px] sm:text-xs text-slate-400 shrink-0">Astropy Header & WCS Parser</span>
                </div>
                <p className="text-xs text-slate-300 mb-3">
                  Inspects header structure, multi-extension HDUs, celestial WCS matrix, pixel scale, and robust image statistics with NaN/saturation masks.
                </p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto">
                  Returns: {"{ status, file_path, hdu_count, hdus, selected_hdu: { wcs, header_sample, statistics } }"}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
                <div className="flex items-start sm:items-center justify-between mb-2 flex-col sm:flex-row gap-1">
                  <h3 className="font-mono text-xs sm:text-sm font-semibold text-emerald-300 break-all">
                    aperture_photometry(file_path, aperture_radius, positions, sky_coords, bkg_annulus_inner, bkg_annulus_outer)
                  </h3>
                  <span className="text-[11px] sm:text-xs text-slate-400 shrink-0">Photutils Aperture Reducer</span>
                </div>
                <p className="text-xs text-slate-300 mb-3">
                  Performs circular aperture photometry with background annulus subtraction and CCD equation error propagation (Poisson + Read noise).
                </p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto">
                  Returns: {"{ status, aperture_radius_px, sources: [{ id, x_px, y_px, net_flux, flux_err, snr, mag, flags }], summary }"}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
                <div className="flex items-start sm:items-center justify-between mb-2 flex-col sm:flex-row gap-1">
                  <h3 className="font-mono text-xs sm:text-sm font-semibold text-cyan-300 break-all">
                    fit_lightcurve(file_path, model_type, detrend_window_length, period_hint)
                  </h3>
                  <span className="text-[11px] sm:text-xs text-slate-400 shrink-0">Lightkurve Detrend & Fit</span>
                </div>
                <p className="text-xs text-slate-300 mb-3">
                  Detrends stellar variability via Savitzky-Golay filtering and executes Box Least Squares (transit) or Lomb-Scargle (periodic) fits.
                </p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto">
                  Returns: {"{ status, points_count, time_span_days, fit_results: { period_days, depth_ppm, snr }, phase_binned_curve }"}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Docs & Prompts */}
        {activeTab === "docs" && (
          <div className="space-y-5 sm:space-y-6">
            {/* Claude Desktop Config */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  Claude Desktop MCP Configuration
                </h3>
                <button
                  onClick={copyClaudeConfig}
                  className="px-3 py-1.5 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 rounded-md text-xs text-indigo-300 flex items-center gap-1.5 transition min-h-[36px]"
                >
                  {copiedConfig ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedConfig ? "Copied" : "Copy Config"}
                </button>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
                <pre>{JSON.stringify(
                  {
                    mcpServers: {
                      "astro-copilot": {
                        command: "python",
                        args: ["-m", "astro_copilot.server"],
                      },
                    },
                  },
                  null,
                  2
                )}</pre>
              </div>
            </div>

            {/* Conversational Prompts */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-white">Conversational Prompt Examples</h3>
              
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="text-xs font-semibold text-indigo-300">Astronomer:</div>
                <div className="text-xs text-slate-200 bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed">
                  "Inspect <code>sample_data/sample_image.fits</code>. Check the exposure time, filter, and calculate the background median and scatter."
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="text-xs font-semibold text-emerald-300">Astronomer:</div>
                <div className="text-xs text-slate-200 bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed">
                  "Run circular aperture photometry on the star at (128, 128) in <code>sample_data/sample_image.fits</code> with an aperture radius of 5.0 pixels and background annulus [8.0, 12.0]. Report the net flux and SNR."
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="text-xs font-semibold text-cyan-300">Astronomer:</div>
                <div className="text-xs text-slate-200 bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed">
                  "Flatten the TESS light curve <code>sample_data/sample_transit.fits</code> with a 51-cadence window and fit an exoplanet transit around period = 3.5 days."
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Tests */}
        {activeTab === "tests" && (
          <div className="space-y-4">
            <div className="flex items-start sm:items-center justify-between gap-3 flex-col sm:flex-row">
              <div>
                <h2 className="text-base font-bold text-white">Pytest Suite & Astro Edge-Case Verification</h2>
                <p className="text-xs text-slate-400">15 automated tests verifying NaNs, missing WCS, saturation, and MEF HDUs.</p>
              </div>
              <button
                onClick={handleRunTests}
                disabled={isTesting}
                className="w-full sm:w-auto px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition shadow min-h-[44px]"
              >
                {isTesting ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                Run Pytest Suite
              </button>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 sm:p-4 font-mono text-[11px] sm:text-xs text-slate-300 overflow-x-auto min-h-[300px]">
              {testOutput ? (
                <pre className="whitespace-pre-wrap">{testOutput}</pre>
              ) : (
                <div className="text-slate-500 text-center py-12">
                  Click "Run Pytest Suite" to execute all tests on synthetic FITS and CSV datasets.
                </div>
              )}
            </div>
          </div>
        )}


      </main>
    </div>
  );
}
