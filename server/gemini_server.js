/**
 * Gemini CLI HTTP Server
 *
 * Keeps Gemini CLI core loaded in memory for faster responses.
 * Communicates with Python GUI via HTTP.
 */

const http = require('http');
const path = require('path');
const { pathToFileURL } = require('url');

// Load gemini-cli-core from global npm modules
const GEMINI_CLI_PATH = path.join(
  process.env.APPDATA,
  'npm/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core'
);

let geminiCore;
let geminiClient;
let isInitialized = false;

async function initialize() {
  if (isInitialized) return;

  console.log('Loading gemini-cli-core...');
  const startTime = Date.now();

  try {
    const modulePath = pathToFileURL(path.join(GEMINI_CLI_PATH, 'dist/src/index.js')).href;
    geminiCore = await import(modulePath);
    console.log(`Loaded in ${Date.now() - startTime}ms`);
    console.log('Core module loaded successfully');
    isInitialized = true;
  } catch (err) {
    console.error('Failed to load gemini-cli-core:', err);
    throw err;
  }
}

// Parse JSON body from request
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      initialized: isInitialized
    }));
    return;
  }

  // Status endpoint
  if (req.url === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'running',
      initialized: isInitialized,
      uptime: process.uptime(),
      memory: process.memoryUsage()
    }));
    return;
  }

  // List available classes/functions
  if (req.url === '/exports') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    const exports = geminiCore ? Object.keys(geminiCore).filter(k =>
      k.includes('Gemini') || k.includes('Chat') || k.includes('Client') || k.includes('Config')
    ) : [];
    res.end(JSON.stringify({ exports }));
    return;
  }

  // Prompt endpoint - uses subprocess (fallback)
  if (req.url === '/prompt' && req.method === 'POST') {
    try {
      const body = await parseBody(req);
      const { prompt, workingDir } = body;

      if (!prompt) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'prompt is required' }));
        return;
      }

      console.log(`Received prompt: ${prompt.substring(0, 50)}...`);
      const startTime = Date.now();

      // Use subprocess for now (gemini CLI)
      const { spawn } = require('child_process');
      const geminiCmd = process.platform === 'win32' ? 'gemini.cmd' : 'gemini';

      const child = spawn(geminiCmd, ['-p', prompt, '-o', 'json'], {
        cwd: workingDir || process.cwd(),
        shell: true
      });

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', data => stdout += data);
      child.stderr.on('data', data => stderr += data);

      child.on('close', code => {
        const elapsed = Date.now() - startTime;
        console.log(`Prompt completed in ${elapsed}ms`);

        // Try to parse JSON from stdout
        let response;
        try {
          // Find JSON in output (skip any non-JSON lines)
          const jsonMatch = stdout.match(/\{[\s\S]*\}$/);
          if (jsonMatch) {
            response = JSON.parse(jsonMatch[0]);
          } else {
            response = { raw: stdout };
          }
        } catch (e) {
          response = { raw: stdout };
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: code === 0,
          response,
          elapsed,
          exitCode: code
        }));
      });

      child.on('error', err => {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      });

    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

const PORT = process.env.GEMINI_SERVER_PORT || 9876;

async function main() {
  try {
    await initialize();

    server.listen(PORT, '127.0.0.1', () => {
      console.log(`\nGemini server listening on http://127.0.0.1:${PORT}`);
      console.log('Endpoints:');
      console.log('  GET  /health  - Health check');
      console.log('  GET  /status  - Server status');
      console.log('  GET  /exports - List Gemini-related exports');
      console.log('  POST /prompt  - Send prompt (body: {prompt, workingDir?})');
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

main();
