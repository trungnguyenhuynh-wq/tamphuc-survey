export default {
  async fetch(request) {
    const RENDER = "https://tamphuc-survey.onrender.com";
    const url    = new URL(request.url);
    const target = RENDER + url.pathname + url.search;

    // Đọc body trước
    let body = null;
    if (request.method !== "GET" && request.method !== "HEAD") {
      body = await request.arrayBuffer();
    }

    // ✅ Tạo headers mới — KHÔNG chuyển host gốc sang Render
    const headers = new Headers();
    headers.set("Content-Type", request.headers.get("Content-Type") || "application/json");
    headers.set("Accept", request.headers.get("Accept") || "application/json");

    const response = await fetch(target, {
      method:  request.method,
      headers: headers,
      body:    body,
    });

    // Trả về response kèm CORS header
    const newHeaders = new Headers(response.headers);
    newHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(response.body, {
      status:  response.status,
      headers: newHeaders,
    });
  }
};
