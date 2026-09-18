/**
 * 后端契约镜像（services/api/app/schemas/api.py）。
 * 升级接口时两处同步改；后续可改由 /api/v1/openapi.json 自动生成。
 */
export type PopulationKey = "healthy" | "sensitive" | "pregnant" | "rhinitis" | "anosmic";
export type RiskLevel = "green" | "yellow" | "red";
export type EvidenceLevel = "documented" | "indicative" | "insufficient";
export type RecognitionChannel = "barcode" | "image" | "text" | "manual";
export type VisionMode = "anosmic" | "normal" | "sensitive";

export interface ProductRef {
  product_id?: string | null;
  barcode?: string | null;
  query?: string | null;
  manual_ingredients?: Record<string, number> | null;
}

export interface OxidationInput {
  opened_days: number;
  temp_c: number;
  light: number;
}

export interface AnalyzeRequest {
  product: ProductRef;
  profile: PopulationKey;
  oxidation?: OxidationInput;
  co_use?: Record<string, number>;
}

export interface IngredientFinding {
  inci: string;
  name_zh: string;
  cas?: string | null;
  concentration_pct?: number | null;
  tier?: string | null;
  high_frequency: boolean;
  banned_eu: boolean;
  oxidation_prone: boolean;
  note?: string | null;
  nesil?: number | null;
  saf?: number | null;
  ael?: number | null;
  cel_p50?: number | null;
  cel_p90?: number | null;
  cel_p99?: number | null;
  margin_p50?: number | null;
  margin_p90?: number | null;
  margin_p99?: number | null;
  decision_percentile?: string | null;
  level?: RiskLevel | null;
  gate?: string | null;
  evidence_level?: EvidenceLevel | null;
  data_note?: string | null;
}

export interface OxidationFinding {
  applicable: boolean;
  substances: string[];
  d_value?: number | null;
  level: RiskLevel;
  advice?: string | null;
  model_note: string;
}

export interface PopulationFinding {
  population: PopulationKey;
  threshold_multiplier: number;
  percentile_policy: string;
  special_flags: string[];
}

export interface RiskReport {
  overall_level: RiskLevel;
  ingredients: IngredientFinding[];
  data_insufficient: string[];
  oxidation: OxidationFinding;
  population: PopulationFinding;
  summary: string;
}

export interface PyramidNote {
  name: string;
  weight: number;
  family?: string | null;
}

export interface VisionReport {
  mode: VisionMode;
  families: { key: string; name_zh: string; weight: number }[];
  palette: string[];
  gradient_direction: number;
  motion: { type?: string; particle_count?: number; speed?: number; shape?: string; label?: string };
  mood_label: string;
  radar: Record<string, number>;
  pyramid: Record<string, PyramidNote[]>;
  synesthesia_text: string;
  text_source: "qwen" | "template";
  /** 降级标记：可视化构建失败或数据不足时为 true（不静默交付空壳）。 */
  degraded: boolean;
  /** 降级原因，用于在界面上如实说明，而不是显示一个空壳。 */
  degrade_reason?: string | null;
}

export interface ProductInfo {
  product_id: string;
  brand: string;
  name: string;
  concentration_type?: string | null;
  barcode?: string | null;
  is_golden: boolean;
}

export interface AnalyzeData {
  product?: ProductInfo | null;
  recognition_channel: RecognitionChannel;
  recognition_confidence?: number | null;
  risk: RiskReport;
  vision: VisionReport;
}

export interface Meta {
  request_id?: string | null;
  engine: string;
  models: Record<string, string>;
  mock_mode: boolean;
  generated_at: string;
}

export interface Envelope<T> {
  data: T;
  meta: Meta;
}

export interface ErrorEnvelope {
  error: { code: string; message: string; details?: Record<string, unknown> };
  meta: Meta;
}

export interface ProductSummary {
  product_id: string;
  brand: string;
  name: string;
  concentration_type?: string | null;
  families: string[];
  is_golden: boolean;
}

export interface RecognitionCandidate {
  product_id: string;
  brand: string;
  name: string;
  confidence: number;
  source: RecognitionChannel;
}

export interface RecognitionData {
  candidates: RecognitionCandidate[];
  best?: RecognitionCandidate | null;
  needs_manual: boolean;
  message: string;
}
