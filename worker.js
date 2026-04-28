export default {
  async fetch(request) {
    const RENDER = "https://tamphuc-survey.onrender.com";
    const url    = new URL(request.url);
    const target = RENDER + url.pathname + url.search;

    const body = (request.method === "GET" || request.method === "HEAD")
      ? null
      : await request.arrayBuffer();

    return fetch(target, {
      method:  request.method,
      headers: request.headers,
      body:    body,
    });
  }
};
