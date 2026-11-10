import { createApi } from "./api.js";

const port = Number(process.env.PORT ?? 3001);
createApi(process.env.SERVICE_URL ?? "http://127.0.0.1:8000").listen(port, () => {
  console.log(`API on http://127.0.0.1:${port}`);
});
