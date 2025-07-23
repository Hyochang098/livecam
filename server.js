import http from 'http';
import { WebSocketServer } from 'ws';
import { readFileSync, existsSync } from 'fs';
import { extname, join } from 'path';
import mime from 'mime';

const ROOT = join(process.cwd(), 'public');
const serveFile = (req, res) => {
  const url = req.url === '/' ? '/viewer.html' : req.url;
  const file = join(ROOT, url);
  if (existsSync(file)) {
    res.writeHead(200, { 'Content-Type': mime.getType(extname(file)) });
    res.end(readFileSync(file));
  } else { res.writeHead(404).end('not found'); }
};

const server = http.createServer(serveFile);
const wss = new WebSocketServer({ server });
const rooms = new Map();          // roomId → Set(ws)

wss.on('connection', (ws, req) => {
  const roomId = new URL(req.url, 'http://x').pathname.split('/').pop();
  if (!rooms.has(roomId)) rooms.set(roomId, new Set());
  rooms.get(roomId).add(ws);

  ws.on('message', data => {
   const text = typeof data === 'string' ? data : data.toString();
   rooms.get(roomId).forEach(peer => peer !== ws && peer.send(text));
  });

  ws.on('close', () => rooms.get(roomId).delete(ws));
});


server.listen(3000, () => console.log('http/ws :3000'));
