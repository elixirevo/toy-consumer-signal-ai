import { Readable } from "node:stream";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

async function readRequestBody(request) {
  const chunks = [];

  for await (const chunk of request) {
    chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
  }

  if (chunks.length === 0) {
    return undefined;
  }

  return Buffer.concat(chunks);
}

function buildUpstreamUrl(request, backendBaseUrl) {
  const incomingUrl = new URL(request.url, `https://${request.headers.host}`);
  const backendUrl = new URL(backendBaseUrl);
  const proxiedPath = incomingUrl.pathname.replace(/^\/api/, "") || "/";

  backendUrl.pathname = `${backendUrl.pathname.replace(/\/$/, "")}${proxiedPath}`;
  backendUrl.search = incomingUrl.search;
  return backendUrl;
}

function buildUpstreamHeaders(request) {
  const headers = new Headers();

  for (const [name, value] of Object.entries(request.headers)) {
    if (!value) {
      continue;
    }

    const lowerName = name.toLowerCase();
    if (lowerName === "host" || HOP_BY_HOP_HEADERS.has(lowerName)) {
      continue;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => headers.append(name, item));
      continue;
    }

    headers.set(name, value);
  }

  return headers;
}

function copyResponseHeaders(upstreamResponse, response) {
  upstreamResponse.headers.forEach((value, name) => {
    if (HOP_BY_HOP_HEADERS.has(name.toLowerCase())) {
      return;
    }
    response.setHeader(name, value);
  });
}

export default async function handler(request, response) {
  const backendBaseUrl = process.env.BACKEND_API_BASE_URL;

  if (!backendBaseUrl) {
    response.statusCode = 500;
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    response.end(
      JSON.stringify({
        error: "BACKEND_API_BASE_URL 환경변수가 설정되지 않았습니다.",
      }),
    );
    return;
  }

  try {
    const targetUrl = buildUpstreamUrl(request, backendBaseUrl);
    const upstreamResponse = await fetch(targetUrl, {
      method: request.method,
      headers: buildUpstreamHeaders(request),
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await readRequestBody(request),
    });

    response.statusCode = upstreamResponse.status;
    copyResponseHeaders(upstreamResponse, response);

    if (!upstreamResponse.body) {
      response.end();
      return;
    }

    Readable.fromWeb(upstreamResponse.body).pipe(response);
  } catch (error) {
    response.statusCode = 502;
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    response.end(
      JSON.stringify({
        error: "backend 프록시 요청에 실패했습니다.",
        message: error instanceof Error ? error.message : String(error),
      }),
    );
  }
}
