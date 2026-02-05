/**
 * Gemini CLI HTTP Server
 *
 * Keeps Gemini CLI core loaded in memory for faster responses.
 * Communicates with Python GUI via HTTP.
 */

const http = require('http');
const path = require('path');
const { pathToFileURL } = require('url');
const fs = require('fs');
const { randomUUID } = require('crypto');

let geminiCore;
let geminiClient;
let isInitialized = false;
let coreAvailable = false;
const inFlight = new Map();
const completed = new Map();

function resolveWorkingDir(requestedDir) {
  const resolved = path.resolve(requestedDir || process.cwd());

  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    return null;
  }

  return resolved;
}

function resolveCoreEntry() {
  const candidates = [];
  if (process.env.GEMINI_CLI_CORE_PATH) {
    candidates.push(process.env.GEMINI_CLI_CORE_PATH);
  }

  if (process.env.APPDATA) {
    candidates.push(path.join(
      process.env.APPDATA,
      'npm/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core'
    ));
  }

  candidates.push(path.join(
    process.cwd(),
    'node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core'
  ));

  for (const base of candidates) {
    const entry = path.join(base, 'dist/src/index.js');
    if (fs.existsSync(entry)) {
      return entry;
    }
  }

  return null;
}

async function initialize() {
  if (isInitialized) return;

  const entry = resolveCoreEntry();
  if (!entry) {
    console.warn('gemini-cli-core not found. Starting in subprocess-only mode.');
    coreAvailable = false;
    isInitialized = true;
    return;
  }

  console.log('Loading gemini-cli-core...');
  const startTime = Date.now();

  try {
    const modulePath = pathToFileURL(entry).href;
    geminiCore = await import(modulePath);
    coreAvailable = true;
    console.log(`Loaded in ${Date.now() - startTime}ms`);
    console.log('Core module loaded successfully');
    isInitialized = true;
  } catch (err) {
    console.error('Failed to load gemini-cli-core. Falling back to subprocess:', err);
    coreAvailable = false;
    isInitialized = true;
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
      initialized: isInitialized,
      coreAvailable
    }));
    return;
  }

  // Status endpoint
  if (req.url === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'running',
      initialized: isInitialized,
      coreAvailable,
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
    res.end(JSON.stringify({ exports, coreAvailable }));
    return;
  }

  function startPrompt(body, res, { respondImmediately }) {
    const { prompt, workingDir, timeoutMs } = body;

    if (!prompt) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'prompt is required' }));
      return;
    }

    console.log(`Received prompt: ${String(prompt).substring(0, 50)}...`);
    const startTime = Date.now();

    const { spawn } = require('child_process');
    const geminiCmd = process.platform === 'win32' ? 'gemini.cmd' : 'gemini';

    const cwd = resolveWorkingDir(workingDir);
    if (!cwd) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid workingDir' }));
      return;
    }

    const isWin = process.platform === 'win32';
    const promptArg = isWin ? `"${String(prompt).replace(/"/g, '\\"')}"` : prompt;

    const child = spawn(geminiCmd, ['-p', promptArg, '-o', 'json', '-y'], {
      cwd,
      shell: true
    });

    const requestId = randomUUID();
    let timedOut = false;
    const killTimeoutMs = Number.isFinite(timeoutMs) ? Math.max(1000, timeoutMs) : 120000;
    const killTimer = setTimeout(() => {
      timedOut = true;
      try {
        child.kill('SIGKILL');
      } catch { }
    }, killTimeoutMs);

    const entry = {
      child,
      startedAt: Date.now(),
      killTimer,
      stdout: '',
      stderr: '',
      done: false,
      result: null
    };
    inFlight.set(requestId, entry);

    req.on('close', () => {
      if (!child.killed) {
        try {
          child.kill('SIGKILL');
        } catch { }
      }
    });

    child.stdout.on('data', data => { entry.stdout += data; });
    child.stderr.on('data', data => { entry.stderr += data; });

    child.on('close', code => {
      clearTimeout(killTimer);
      inFlight.delete(requestId);
      const elapsed = Date.now() - startTime;
      console.log(`Prompt completed in ${elapsed}ms`);

      let response;
      try {
        const jsonMatch = entry.stdout.match(/\{[\s\S]*\}$/);
        if (jsonMatch) {
          response = JSON.parse(jsonMatch[0]);
        } else {
          response = { raw: entry.stdout };
        }
      } catch (e) {
        response = { raw: entry.stdout };
      }

      const payload = {
        requestId,
        timedOut,
        success: code === 0,
        response,
        stderr: entry.stderr ? entry.stderr.trim() : '',
        elapsed,
        exitCode: code
      };

      entry.done = true;
      entry.result = payload;
      completed.set(requestId, payload);
      setTimeout(() => completed.delete(requestId), 5 * 60 * 1000);

      if (!respondImmediately) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(payload));
      }
    });

    child.on('error', err => {
      clearTimeout(killTimer);
      inFlight.delete(requestId);
      const payload = { requestId, timedOut, success: false, error: err.message };
      completed.set(requestId, payload);
      setTimeout(() => completed.delete(requestId), 5 * 60 * 1000);
      if (!respondImmediately) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });

    if (respondImmediately) {
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ requestId }));
    }
  }

  // Prompt endpoint - uses subprocess (fallback)
  if (req.url === '/prompt' && req.method === 'POST') {
    try {
      const body = await parseBody(req);
      startPrompt(body, res, { respondImmediately: false });

    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // Prompt start endpoint (async)
  if (req.url === '/prompt/start' && req.method === 'POST') {
    try {
      const body = await parseBody(req);
      startPrompt(body, res, { respondImmediately: true });
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // Prompt result endpoint
  if (req.url.startsWith('/prompt/result') && req.method === 'GET') {
    const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
    const requestId = url.searchParams.get('requestId');
    if (!requestId) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'requestId is required' }));
      return;
    }
    if (completed.has(requestId)) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(completed.get(requestId)));
      return;
    }
    if (inFlight.has(requestId)) {
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'running' }));
      return;
    }
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'requestId not found' }));
    return;
  }

  // Cancel endpoint
  if (req.url === '/cancel' && req.method === 'POST') {
    try {
      const body = await parseBody(req);
      const { requestId } = body;
      if (!requestId || !inFlight.has(requestId)) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'requestId not found' }));
        return;
      }
      const entry = inFlight.get(requestId);
      clearTimeout(entry.killTimer);
      try {
        entry.child.kill('SIGKILL');
      } catch { }
      const payload = {
        requestId,
        cancelled: true,
        success: false
      };
      completed.set(requestId, payload);
      setTimeout(() => completed.delete(requestId), 5 * 60 * 1000);
      inFlight.delete(requestId);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ cancelled: true }));
      return;
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
      return;
    }
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
      console.log('  POST /prompt/start - Start prompt async (body: {prompt, workingDir?, timeoutMs?})');
      console.log('  GET  /prompt/result?requestId=... - Fetch prompt result');
      console.log('  POST /cancel - Cancel prompt (body: {requestId})');
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

main();
