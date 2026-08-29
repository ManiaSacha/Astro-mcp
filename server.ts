import express from "express";
import path from "path";
import { exec, spawn } from "child_process";
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

    const toolMap: { [key: string]: string } = {
      "inspect_fits": "astro_copilot.core.fits_io",
      "aperture_photometry": "astro_copilot.core.photometry",
      "fit_lightcurve": "astro_copilot.core.lightcurve",
      "generate_sample_datasets": "astro_copilot.server",
    };

    const functionMap: { [key: string]: string } = {
      "inspect_fits": "inspect_fits_file",
      "aperture_photometry": "run_aperture_photometry",
      "fit_lightcurve": "fit_and_analyze_lightcurve",
      "generate_sample_datasets": "generate_sample_datasets",
    };

    if (!toolMap[tool]) {
      return res.status(400).json({ error: "Unknown tool" });
    }

    const pyCode = `import json, sys; from ${toolMap[tool]} import ${functionMap[tool]}; params = json.loads(sys.stdin.read()); result = ${functionMap[tool]}(**params); print(json.dumps(result))`;
    const paramsJson = JSON.stringify(params || {});

    const proc = spawn("python3", ["-c", pyCode], { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return res.status(500).json({ error: "Python execution failed", stderr });
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

    proc.stdin.write(paramsJson);
    proc.stdin.end();
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
    const args = createNew ? ["checkout", "-b", branchName] : ["checkout", branchName];
    const proc = spawn("git", args);
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return res.status(500).json({ status: "error", error: `git command failed`, stderr });
      }
      res.json({ status: "success", output: stdout || stderr });
    });
  });

  app.post("/api/git/commit", (req, res) => {
    const { message } = req.body;
    const commitMsg = message || "Auto-commit by Git Agent";

    const proc = spawn("git", ["commit", "-m", commitMsg]);
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return res.status(500).json({ status: "error", error: `git commit failed`, stderr });
      }
      res.json({ status: "success", output: stdout || stderr });
    });
  });

  app.post("/api/git/push", (req, res) => {
    const { branch } = req.body;
    const branchName = branch || "main";

    const proc = spawn("git", ["push", "-u", "origin", branchName]);
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return res.status(500).json({ status: "error", error: `git push failed`, stderr, hint: "Please configure git remote origin first." });
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
