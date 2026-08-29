import express from "express";
import path from "path";
import { exec } from "child_process";
import { createServer as createViteServer } from "vite";

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API Routes
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", server: "astro-copilot-mcp" });
  });

  app.get("/api/subagents", (req, res) => {
    res.json({
      subagents: [
        {
          name: "architect",
          description: "Designs MCP server schemas, tool interfaces, error models, and pipeline composition (read-only mode).",
          file: ".claude/agents/architect.md",
          status: "active"
        },
        {
          name: "mcp-builder",
          description: "Implements FastMCP tools and astro reduction modules (Astropy, Photutils, Lightkurve).",
          file: ".claude/agents/mcp-builder.md",
          status: "active"
        },
        {
          name: "test-writer",
          description: "Generates synthetic datasets & tests astro edge cases (missing WCS, NaNs, saturation).",
          file: ".claude/agents/test-writer.md",
          status: "active"
        },
        {
          name: "docs-writer",
          description: "Writes user-facing docs, tool references, and conversational astronomy prompt workflows.",
          file: ".claude/agents/docs-writer.md",
          status: "active"
        }
      ]
    });
  });

  app.post("/api/mcp/execute", (req, res) => {
    const { tool, params } = req.body;
    const jsonStr = JSON.stringify(params || {}).replace(/"/g, '\\"');
    
    let pyCode = "";
    if (tool === "inspect_fits") {
      pyCode = `import json; from astro_copilot.core.fits_io import inspect_fits_file; print(json.dumps(inspect_fits_file(**json.loads('${jsonStr}'))))`;
    } else if (tool === "aperture_photometry") {
      pyCode = `import json; from astro_copilot.core.photometry import run_aperture_photometry; print(json.dumps(run_aperture_photometry(**json.loads('${jsonStr}'))))`;
    } else if (tool === "fit_lightcurve") {
      pyCode = `import json; from astro_copilot.core.lightcurve import fit_and_analyze_lightcurve; print(json.dumps(fit_and_analyze_lightcurve(**json.loads('${jsonStr}'))))`;
    } else if (tool === "generate_sample_datasets") {
      pyCode = `import json; from astro_copilot.server import generate_sample_datasets; print(json.dumps(generate_sample_datasets(**json.loads('${jsonStr}'))))`;
    } else {
      return res.status(400).json({ error: "Unknown tool" });
    }

    exec(`python3 -c "${pyCode}"`, (error, stdout, stderr) => {
      if (error) {
        return res.status(500).json({ error: error.message, stderr });
      }
      try {
        const lines = stdout.trim().split("\n");
        const lastLine = lines[lines.length - 1];
        const parsed = JSON.parse(lastLine);
        res.json(parsed);
      } catch (e) {
        res.status(500).json({ error: "Failed to parse Python output", raw: stdout, stderr });
      }
    });
  });

  app.get("/api/run-tests", (req, res) => {
    exec("python3 -m pytest --json-report --json-report-file=/tmp/pytest_report.json || python3 -m pytest", (err, stdout, stderr) => {
      res.json({
        output: stdout,
        error: err ? err.message : null,
      });
    });
  });

  // Git Agent API Endpoints
  app.get("/api/git/status", (req, res) => {
    exec("git status --porcelain && git branch --show-current && git remote -v", (err, stdout, stderr) => {
      if (err) {
        // Initialize git repo if not already initialized
        exec("git init && git branch -M main", (initErr) => {
          if (initErr) {
            return res.json({ status: "error", message: initErr.message });
          }
          return res.json({
            status: "success",
            branch: "main",
            changes: [],
            remotes: [],
            initialized: true
          });
        });
        return;
      }
      const lines = stdout.trim().split("\n");
      const branch = lines.find(l => !l.includes(" ") && l !== "" && !l.includes("\t")) || "main";
      res.json({
        status: "success",
        raw: stdout,
        branch: branch.trim(),
        stderr
      });
    });
  });

  app.get("/api/git/log", (req, res) => {
    exec("git log -n 15 --oneline", (err, stdout) => {
      if (err) {
        return res.json({ status: "success", logs: [] });
      }
      const commits = stdout.trim().split("\n").filter(Boolean).map(line => {
        const parts = line.split(" ");
        return { hash: parts[0], message: parts.slice(1).join(" ") };
      });
      res.json({ status: "success", commits });
    });
  });

  app.post("/api/git/branch", (req, res) => {
    const { branchName, createNew } = req.body;
    if (!branchName) {
      return res.status(400).json({ error: "Branch name is required" });
    }
    const cmd = createNew ? `git checkout -b ${branchName}` : `git checkout ${branchName}`;
    exec(cmd, (err, stdout, stderr) => {
      if (err) {
        return res.status(500).json({ status: "error", error: err.message, stderr });
      }
      res.json({ status: "success", output: stdout || stderr });
    });
  });

  app.post("/api/git/commit", (req, res) => {
    const { message } = req.body;
    const commitMsg = message || "Auto-commit by Git Agent";
    exec(`git add . && git commit -m "${commitMsg.replace(/"/g, '\\"')}"`, (err, stdout, stderr) => {
      if (err) {
        return res.status(500).json({ status: "error", error: err.message, stderr });
      }
      res.json({ status: "success", output: stdout || stderr });
    });
  });

  app.post("/api/git/push", (req, res) => {
    const { branch } = req.body;
    const branchName = branch || "main";
    exec(`git push -u origin ${branchName}`, (err, stdout, stderr) => {
      if (err) {
        // If remote origin is not set, report gracefully
        return res.status(500).json({ status: "error", error: err.message, stderr, hint: "Please configure git remote origin first." });
      }
      res.json({ status: "success", output: stdout || stderr });
    });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
