import { useRef, useState } from "react";
import { api, ApiError } from "../shared/api";
import type { ProductSummary, ProductRef, RecognitionData } from "../shared/api-types";
import { Card, ErrorBanner, Tag } from "../shared/components";

type Tab = "search" | "photo" | "barcode" | "manual";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "search", label: "搜索", icon: "🔍" },
  { key: "photo", label: "拍照", icon: "📸" },
  { key: "barcode", label: "条码", icon: "🏷️" },
  { key: "manual", label: "手动", icon: "✏️" },
];

export default function CapturePanel({ selected, selectedLabel, onSelect }: {
  selected: ProductRef | null;
  selectedLabel?: string;
  onSelect: (ref: ProductRef | null, label?: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recogMsg, setRecogMsg] = useState("");
  const [barcode, setBarcode] = useState("");
  const [manualText, setManualText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const label = (p: ProductSummary) => `${p.brand} · ${p.name}${p.is_golden ? "（黄金算例）" : ""}`;

  async function runSearch(q: string) {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.products(q);
      setProducts(data.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "搜索失败");
    } finally {
      setBusy(false);
    }
  }

  async function runPhoto(file: File) {
    setBusy(true);
    setError("");
    setRecogMsg("");
    try {
      const { data } = await api.recognitionImage(file);
      handleRecognition(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "识别失败");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function runBarcode() {
    if (!barcode.trim()) return;
    setBusy(true);
    setError("");
    setRecogMsg("");
    try {
      const { data } = await api.recognitionBarcode(barcode.trim());
      handleRecognition(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "条码查询失败");
    } finally {
      setBusy(false);
    }
  }

  function handleRecognition(data: RecognitionData) {
    setRecogMsg(data.message);
    if (data.best) {
      onSelect({ product_id: data.best.product_id }, `${data.best.brand} · ${data.best.name}`);
    } else {
      onSelect(null);
    }
  }

  function applyManual() {
    // 解析 "INCI名: 浓度%" 每行一条
    const map: Record<string, number> = {};
    for (const line of manualText.split("\n")) {
      const m = line.match(/^\s*([^:：]+)[：:]\s*([\d.]+)\s*%?\s*$/);
      if (m) map[m[1].trim()] = parseFloat(m[2]);
    }
    if (Object.keys(map).length) {
      onSelect({ manual_ingredients: map }, `手动成分表（${Object.keys(map).length} 项）`);
    }
  }

  const inputCls =
    "flex-1 rounded-xl bg-panel-2 px-3 py-2.5 text-sm text-ink ring-1 ring-white/15 placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-grad-b";

  return (
    <Card title="② 识别香水（拍照 / 条码 / 搜索 / 手动）">
      <div className="mb-3 flex gap-1 rounded-xl bg-white/5 p-1" role="tablist" aria-label="识别通道">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-lg px-2 py-2 text-sm font-medium transition-colors ${
              tab === t.key ? "grad-bg text-white" : "text-ink-2 hover:text-ink"
            }`}
          >
            <span aria-hidden className="mr-1">{t.icon}</span>{t.label}
          </button>
        ))}
      </div>

      {error && <div className="mb-3"><ErrorBanner message={error} onRetry={() => setError("")} /></div>}
      {recogMsg && (
        <p className="mb-3 rounded-lg bg-sky-400/10 px-3 py-2 text-xs text-sky-300 ring-1 ring-sky-400/25">{recogMsg}</p>
      )}
      {selected && (
        <p className="grad-ring mb-3 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink">
          <span aria-hidden className="grad-bg inline-block h-2 w-2 rounded-full" />
          <span className="flex-1 truncate font-medium">{selectedLabel ?? "已选择"}</span>
          <button className="text-xs text-ink-2 underline underline-offset-2" onClick={() => onSelect(null, "")}>
            清除
          </button>
        </p>
      )}

      {tab === "search" && (
        <div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              runSearch(query);
            }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="品牌 / 品名，如「Libre」「Angel」"
              className={inputCls}
            />
            <button
              disabled={busy}
              className="grad-bg rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? "搜索中…" : "搜索"}
            </button>
          </form>
          {products.length === 0 && !busy && (
            <button className="mt-3 text-xs text-gold underline underline-offset-2" onClick={() => runSearch("")}>
              展示全部演示香水库 →
            </button>
          )}
          <ul className="mt-3 space-y-2" aria-label="候选产品">
            {products.map((p) => (
              <li key={p.product_id}>
                <button
                  onClick={() => onSelect({ product_id: p.product_id }, label(p))}
                  className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                    selected?.product_id === p.product_id
                      ? "grad-ring"
                      : "bg-panel-2 ring-1 ring-white/10 hover:ring-white/25"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-ink">{p.name}</span>
                      <span className="block text-xs text-ink-3">{p.brand}</span>
                    </span>
                    <span className="flex flex-none gap-1">
                      {p.is_golden && (
                        <span className="grad-ring-gold rounded px-1.5 py-0.5 text-xs text-gold">黄金算例</span>
                      )}
                      <Tag>{p.concentration_type}</Tag>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "photo" && (
        <div className="space-y-3">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => e.target.files?.[0] && runPhoto(e.target.files[0])}
            className="block w-full text-sm text-ink-2 file:mr-3 file:rounded-xl file:border-0 file:bg-grad-b file:px-4 file:py-2.5 file:font-semibold file:text-white hover:file:opacity-90"
          />
          <p className="text-xs text-ink-3">
            阿里云百炼 qwen-vl-max 瓶身识别。未配置 API Key 时自动降级 mock（演示不中断），
            置信度低于 0.7 将提示手动确认。
          </p>
        </div>
      )}

      {tab === "barcode" && (
        <div className="flex gap-2">
          <input
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            placeholder="输入/扫描 EAN 条码（演示库：0000000000001）"
            inputMode="numeric"
            className={inputCls}
          />
          <button
            onClick={runBarcode}
            disabled={busy}
            className="grad-bg rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            查询
          </button>
        </div>
      )}

      {tab === "manual" && (
        <div className="space-y-3">
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            rows={5}
            placeholder={"每行一条：INCI名: 浓度%\n如：\nd-Limonene: 5.0\nLinalool: 1.5"}
            className="w-full rounded-xl bg-panel-2 px-3 py-2.5 font-mono text-sm text-ink ring-1 ring-white/15 placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-grad-b"
          />
          <button
            onClick={applyManual}
            className="grad-bg rounded-xl px-4 py-2.5 text-sm font-semibold text-white"
          >
            应用成分表
          </button>
          <p className="text-xs text-ink-3">未收录成分会显式标注「数据不足」，不会静默降级。</p>
        </div>
      )}
    </Card>
  );
}
