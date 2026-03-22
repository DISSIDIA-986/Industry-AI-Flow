import { NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000";

const PASS_HEADERS = [
  "content-type",
  "authorization",
  "x-api-key",
  "x-tenant-id",
] as const;

function buildUrl(path: string[], search: string) {
  const normalizedPath = path.join("/");
  const base = BACKEND_BASE_URL.endsWith("/")
    ? BACKEND_BASE_URL
    : `${BACKEND_BASE_URL}/`;
  const url = new URL(normalizedPath, base);
  if (search) {
    url.search = search;
  }
  return url.toString();
}

async function proxyRequest(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const target = buildUrl(path, new URL(request.url).search);
  const headers = new Headers();

  for (const header of PASS_HEADERS) {
    const value = request.headers.get(header);
    if (value) {
      headers.set(header, value);
    }
  }

  try {
    const method = request.method.toUpperCase();
    const body =
      method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

    const upstream = await fetch(target, {
      method,
      headers,
      body,
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) {
      responseHeaders.set("content-type", contentType);
    }

    // Stream SSE responses instead of buffering
    if (contentType?.includes("text/event-stream") && upstream.body) {
      responseHeaders.set("Cache-Control", "no-cache");
      responseHeaders.set("Connection", "keep-alive");
      responseHeaders.set("X-Accel-Buffering", "no");
      return new NextResponse(upstream.body, {
        status: upstream.status,
        headers: responseHeaders,
      });
    }

    return new NextResponse(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: "backend_proxy_error",
        detail: error instanceof Error ? error.message : "unknown error",
        target,
      },
      { status: 502 },
    );
  }
}

export async function GET(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxyRequest(request, context);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxyRequest(request, context);
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxyRequest(request, context);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxyRequest(request, context);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxyRequest(request, context);
}
