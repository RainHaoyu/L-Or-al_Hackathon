import type {
  AnalyzeData,
  AnalyzeRequest,
  Envelope,
  ErrorEnvelope,
  Meta,
  ProductSummary,
  RecognitionData,
} from "./api-types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; meta: Meta }> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, {
      headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError("NETWORK", "网络不可达：请检查后端服务（演示模式可用预置案例）");
  }
  const body = await resp.json().catch(() => null);
  if (!resp.ok) {
    const err = (body as ErrorEnvelope | null)?.error;
    throw new ApiError(err?.code ?? `HTTP_${resp.status}`, err?.message ?? `请求失败(${resp.status})`);
  }
  return body as Envelope<T>;
}

export const api = {
  health: () => request<{ status: string; engine: string; mock_mode: boolean }>("/health"),
  products: (q: string) => request<{ items: ProductSummary[] }>(`/products?q=${encodeURIComponent(q)}`),
  analyze: (req: AnalyzeRequest) =>
    request<AnalyzeData>("/analyze", { method: "POST", body: JSON.stringify(req) }),
  recognitionImage: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<RecognitionData>("/recognition/image", { method: "POST", body: fd });
  },
  recognitionBarcode: (barcode: string) =>
    request<RecognitionData>("/recognition/barcode", {
      method: "POST",
      body: JSON.stringify({ barcode }),
    }),
};
