import { getAccessToken } from '@auth0/nextjs-auth0';
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL;
export const dynamic = 'force-dynamic';
export const revalidate = 0;

function backendUrl(pathSegments: string[], search: string): string {
  const trimmedBase = (BACKEND_URL || '').replace(/\/$/, '');
  return `${trimmedBase}/api/${pathSegments.join('/')}${search}`;
}

async function proxy(request: NextRequest, pathSegments: string[]) {
  if (!BACKEND_URL) {
    return NextResponse.json({ detail: 'BACKEND_API_URL is not configured' }, { status: 500 });
  }

  const method = request.method;
  const isPublicBooksRead = (method === 'GET' || method === 'HEAD') && pathSegments[0] === 'books';

  let accessToken: string | undefined;
  try {
    const tokenResponse = await getAccessToken();
    accessToken = tokenResponse.accessToken;
  } catch {
    if (!isPublicBooksRead) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }
  }

  const contentType = request.headers.get('content-type');
  const outgoingHeaders: Record<string, string> = {};
  if (accessToken) {
    outgoingHeaders.Authorization = `Bearer ${accessToken}`;
  }

  if (contentType) {
    outgoingHeaders['Content-Type'] = contentType;
  }

  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.text();

  const upstream = await fetch(backendUrl(pathSegments, request.nextUrl.search), {
    method,
    headers: outgoingHeaders,
    body,
    cache: 'no-store'
  });

  const headers = new Headers();
  const upstreamType = upstream.headers.get('content-type');
  if (upstreamType) {
    headers.set('Content-Type', upstreamType);
  }
  headers.set('Cache-Control', 'no-store, max-age=0');

  // Response status codes that must not include a body.
  if (upstream.status === 204 || upstream.status === 205 || upstream.status === 304 || method === 'HEAD') {
    return new NextResponse(null, {
      status: upstream.status,
      headers
    });
  }

  const text = await upstream.text();
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return new NextResponse(text, {
    status: upstream.status,
    headers
  });
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params.path);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params.path);
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params.path);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params.path);
}
