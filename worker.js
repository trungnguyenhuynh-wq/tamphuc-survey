export default {
  async fetch(request) {
    const RENDER = "https://tamphuc-survey.onrender.com";

    // ✅ Xử lý CORS preflight – bắt buộc phải có
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin":  "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Accept",
        }
      });
    }

    const url    = new URL(request.url);
    const target = RENDER + url.pathname + url.search;

    try {
      // ✅ Đọc body dạng text – ổn định hơn arrayBuffer
      let body        = undefined;
      let contentType = "application/json";

      if (request.method !== "GET" && request.method !== "HEAD") {
        body        = await request.text();
        contentType = request.headers.get("Content-Type") || "application/json";
      }

      // ✅ Chỉ gửi headers cần thiết – không gửi host gốc
      const res = await fetch(target, {
        method:  request.method,
        headers: {
          "Content-Type": contentType,
          "Accept":       "application/json",
        },
        body: body,
      });

      const text = await res.text();

      return new Response(text, {
        status:  res.status,
        headers: {
          "Content-Type":                res.headers.get("Content-Type") || "application/json",
          "Access-Control-Allow-Origin": "*",
        }
      });

    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: {
          "Content-Type":                "application/json",
          "Access-Control-Allow-Origin": "*",
        }
      });
    }
  }
};