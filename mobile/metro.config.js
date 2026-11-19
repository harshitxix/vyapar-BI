const { getDefaultConfig } = require('expo/metro-config');
const http = require('http');

const config = getDefaultConfig(__dirname);
const originalEnhanceMiddleware = config.server.enhanceMiddleware;

config.server.enhanceMiddleware = (metroMiddleware, server) => {
  const customMiddleware = (req, res, next) => {
    const url = req.url || '';
    if (
      url.startsWith('/feed') ||
      url.startsWith('/trends') ||
      url.startsWith('/sources') ||
      url.startsWith('/ingestion') ||
      url.startsWith('/admin') ||
      url.startsWith('/users') ||
      url.startsWith('/taxonomy') ||
      url.startsWith('/entities') ||
      url.startsWith('/interactions')
    ) {
      console.log(`[Metro Proxy] ${req.method} ${url} -> 127.0.0.1:8000`);

      if (req.method === 'OPTIONS') {
        res.writeHead(200, {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
          'Access-Control-Allow-Headers': '*',
        });
        res.end();
        return;
      }

      const headers = {
        ...req.headers,
        host: '127.0.0.1:8000',
      };

      const proxyReq = http.request(
        {
          host: '127.0.0.1',
          port: 8000,
          path: url,
          method: req.method,
          headers,
        },
        (proxyRes) => {
          res.writeHead(proxyRes.statusCode, {
            ...proxyRes.headers,
            'access-control-allow-origin': '*',
          });
          proxyRes.pipe(res);
        }
      );

      proxyReq.on('error', (err) => {
        console.error(`[Metro Proxy Error] ${url}:`, err.message);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Backend proxy error', details: err.message }));
      });

      if (req.method === 'GET' || req.method === 'HEAD') {
        proxyReq.end();
      } else {
        req.pipe(proxyReq);
      }
      return;
    }
    return metroMiddleware(req, res, next);
  };

  return originalEnhanceMiddleware
    ? originalEnhanceMiddleware(customMiddleware, server)
    : customMiddleware;
};

module.exports = config;
