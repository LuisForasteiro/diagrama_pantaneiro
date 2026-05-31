export const CLASS_LABELS: Record<string, string> = {
  acoes_nacionais: "Ações Nacionais",
  acoes_internacionais: "Ações Internacionais",
  etfs_nacionais: "ETFs Nacionais",
  etfs_internacionais: "ETFs Internacionais",
  fundos_imobiliarios: "Fundos Imobiliários",
  reits: "REITs",
  criptomoedas: "Criptomoedas",
  rendafixa: "Renda Fixa",
  rendafixa_internacional: "Renda Fixa Internacional",
};

export const CLASS_ORDER: readonly string[] = [
  "acoes_nacionais",
  "acoes_internacionais",
  "etfs_nacionais",
  "etfs_internacionais",
  "fundos_imobiliarios",
  "reits",
  "criptomoedas",
  "rendafixa",
  "rendafixa_internacional",
] as const;

// Region/currency exposure — purely visual. The algorithm rebalances by
// class; this mapping powers the "exposição por região" panel on /home.
// Cripto stays as its own bucket (not folded into "internacional") so the
// user sees BRL vs USD vs crypto exposure separately.
export type Region = "nacional" | "internacional" | "cripto";

export const REGION_FOR_CLASS: Record<string, Region> = {
  acoes_nacionais: "nacional",
  etfs_nacionais: "nacional",
  fundos_imobiliarios: "nacional",
  rendafixa: "nacional",
  acoes_internacionais: "internacional",
  etfs_internacionais: "internacional",
  reits: "internacional",
  rendafixa_internacional: "internacional",
  criptomoedas: "cripto",
};

export const REGION_LABELS: Record<Region, string> = {
  nacional: "Nacional (R$)",
  internacional: "Internacional (dolarizado)",
  cripto: "Cripto",
};

export const REGION_COLOR: Record<Region, string> = {
  nacional: "#7eb360",       // verde cerradão
  internacional: "#e8822c",  // laranja tuiuiú
  cripto: "#4fa8b8",         // água do corixo
};

// Semantic class for display + algorithm consumption.
// effectiveClass overrides assetType when set (e.g. OBTC3 reclassified as crypto).
export function displayClass(p: {
  assetType: string;
  effectiveClass: string | null;
}): string {
  return p.effectiveClass ?? p.assetType;
}
