export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface JwtLoginResponse {
  access_token: string;
  token_type: "bearer";
}

export interface ApiErrorBody {
  detail: string | Array<{ msg: string; loc: unknown }>;
}

export interface PositionOut {
  id: string;
  name: string;
  assetType: string;
  effectiveClass: string | null;
  amount: number;
  currentPrice: number | null;
  currentValueBrl: number;
  priceUpdatedAt: string | null;
  categoryId: string | null;
  strength: number;
  diagramResponses: string[] | null;
  tradable: boolean;
  source: string;
}

export interface TargetOut {
  id: string;
  assetType: string;
  targetPercentage: number;
}

export interface AporteAllocationOut {
  id: string;
  positionId: string | null;
  positionNameSnapshot: string;
  assetTypeSnapshot: string;
  priceAtAporteBrl: number | null;
  suggestedValueBrl: number;
  suggestedQuantity: number;
  applied: boolean;
  appliedAt: string | null;
  appliedValueBrl: number | null;
  appliedQuantity: number | null;
}

export interface AporteEventOut {
  id: string;
  aporteValueBrl: number;
  createdAt: string;
  allocations: AporteAllocationOut[];
}

export interface PositionCreate {
  name: string;
  assetType: string;
  effectiveClass?: string | null;
  categoryId?: string | null;
  amount: number;
  currentPrice?: number | null;
  strength: number;
  diagramResponses?: string[] | null;
  tradable?: boolean;
}

export interface PositionUpdate {
  amount?: number;
  currentPrice?: number | null;
  strength?: number;
  diagramResponses?: string[] | null;
  effectiveClass?: string | null;
  categoryId?: string | null;
  tradable?: boolean;
}

export interface DiagramQuestionOut {
  id: string;
  diagramType: string;
  criterias: string;
  questionText: string;
  displayOrder: number;
  externalId: string | null;
}

export interface DiagramQuestionCreate {
  diagramType: string;
  criterias?: string;
  questionText: string;
  displayOrder?: number | null;
}

export interface DiagramQuestionUpdate {
  criterias?: string;
  questionText?: string;
  displayOrder?: number;
}

export interface PriceFailureOut {
  name: string;
  reason: string;
}

export interface RefreshSummaryOut {
  refreshed: number;
  skippedManual: number;
  failed: PriceFailureOut[];
}

export interface CandidateOut {
  name: string;
  label: string | null;
  currentPriceBrl: number | null;
}

export interface TargetUpdateIn {
  assetType: string;
  targetPercentage: number;
}

export interface TargetsUpdateBody {
  targets: TargetUpdateIn[];
}

export interface PresetOut {
  id: string;
  name: string;
  values: Record<string, number>;
  createdAt: string;
}

export interface PresetIn {
  name: string;
  values: Record<string, number>;
}

export interface PortfolioOut {
  id: string;
  name: string;
  isDefault: boolean;
  createdAt: string;
}

export interface PortfolioCreate {
  name: string;
}

export interface PortfolioRename {
  name: string;
}

export interface Subcategory {
  id: string;
  name: string;
  weightPct: number;
}

export interface CategoryGroup {
  id: string;
  name: string;
  weightPct: number;
  children: Subcategory[];
}

export interface CategoryTree {
  groups: CategoryGroup[];
}

export interface SubcategoryIn {
  id?: string | null;
  name: string;
  weightPct: number;
}

export interface CategoryGroupIn {
  id?: string | null;
  name: string;
  weightPct: number;
  children: SubcategoryIn[];
}

export interface CategoryTreeIn {
  groups: CategoryGroupIn[];
}
