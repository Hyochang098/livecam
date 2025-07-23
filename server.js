
/**
 * 실시간 라이브캠 스트리밍 서버
 * Room 기반 통신: 같은 roomId로 접속한 클라이언트들끼리 데이터 공유
 */
import http from 'http';
import { WebSocketServer } from 'ws';
import { readFileSync, existsSync } from 'fs';
import { extname, join } from 'path';
import mime from 'mime';

// 정적 파일들이 위치한 루트 디렉토리 경로
const ROOT = join(process.cwd(), 'public');

// HTTP 요청을 처리하여 정적 파일을 제공하는 함수
const serveFile = (req, res) => {
  const url = req.url === '/' ? '/viewer.html' : req.url;
  const file = join(ROOT, url);
  
  if (existsSync(file)) {
    // 파일이 존재하면 MIME 타입을 설정하고 파일 내용을 응답으로 전송
    res.writeHead(200, { 'Content-Type': mime.getType(extname(file)) });
    res.end(readFileSync(file));
  } else { res.writeHead(404).end('not found'); }
};

// HTTP 서버 생성 (정적 파일 서빙용)
const server = http.createServer(serveFile);
const wss = new WebSocketServer({ server });
const rooms = new Map();          // roomId → Set(ws)

// 새로운 WebSocket 연결이 생성될 때 실행되는 이벤트 핸들러
wss.on('connection', (ws, req) => {
  const roomId = new URL(req.url, 'http://x').pathname.split('/').pop();
  if (!rooms.has(roomId)) rooms.set(roomId, new Set());
  rooms.get(roomId).add(ws);

  // 클라이언트로부터 메시지를 받았을 때 실행되는 이벤트 핸들러
  ws.on('message', data => {
   const text = typeof data === 'string' ? data : data.toString();
   

   rooms.get(roomId).forEach(peer => peer !== ws && peer.send(text));
   
   /**
    * 1:1 통화
    * 
    * const room = rooms.get(roomId);
    * if (room.size <= 2) {
    *   room.forEach(peer => peer !== ws && peer.send(text));
    * } else {
    *   ws.send(JSON.stringify({ error: 'Room full' }));
    * }
    */ 
  });

  ws.on('close', () => rooms.get(roomId).delete(ws));
});


server.listen(3000, () => console.log('http/ws :3000'));
