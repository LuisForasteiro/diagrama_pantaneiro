export const CLASS_LABELS: Record<string, string> = {
  acoes_nacionais: "Ações Nacionais",
  acoes_internacionais: "Ações Internacionais",
  fundos_imobiliarios: "Fundos Imobiliários",
  reits: "REITs",
  criptomoedas: "Criptomoedas",
  rendafixa: "Renda Fixa",
  rendafixa_internacional: "Renda Fixa Internacional",
};

export const CLASS_ORDER: readonly string[] = [
  "acoes_nacionais",
  "acoes_internacionais",
  "fundos_imobiliarios",
  "reits",
  "criptomoedas",
  "rendafixa",
  "rendafixa_internacional",
] as const;
