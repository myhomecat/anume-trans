import { NextRequest } from 'next/server';

// 분석기(맥 MPS backend) 주소 — 서버 전용 env. 브라우저에 노출되지 않음(NEXT_PUBLIC_ 아님).
const ANALYZER_URL = process.env.ANALYZER_URL || 'http://127.0.0.1:8000';

// hop-by-hop / 호스트 의존 헤더는 제외하고 그대로 전달 (multipart boundary 보존)
function forwardHeaders(req: NextRequest): Headers {
  const h = new Headers(req.headers);
  ['host', 'connection', 'content-length', 'expect'].forEach((k) => h.delete(k));
  return h;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${ANALYZER_URL}/api/${path.join('/')}${req.nextUrl.search}`;
  const method = req.method;
  // 요청 body는 버퍼링해 전달 (스트리밍 duplex는 undici에서 큰 업로드 시 UND_ERR_NOT_SUPPORTED).
  // content-type(멀티파트 boundary 포함)을 그대로 넘기면 raw 바이트로 멀티파트가 재구성됨.
  const body =
    method === 'GET' || method === 'HEAD' ? undefined : await req.arrayBuffer();
  const res = await fetch(target, { method, headers: forwardHeaders(req), body });
  return new Response(res.body, { status: res.status, headers: res.headers });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
