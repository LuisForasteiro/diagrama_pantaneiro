import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

vi.mock("$lib/api/targets", () => ({
  listPresets: vi.fn(async () => []),
  updateTargets: vi.fn(async (body) => body.targets),
  createPreset: vi.fn(async (body) => ({
    id: "p-new",
    name: body.name,
    values: body.values,
    createdAt: new Date().toISOString(),
  })),
  deletePreset: vi.fn(async () => undefined),
}));

import EditTargetsModal from "../../src/lib/components/EditTargetsModal.svelte";
import { listPresets } from "../../src/lib/api/targets";

const SEEDED = [
  { id: "t1", assetType: "acoes_nacionais", targetPercentage: 55 },
  { id: "t2", assetType: "acoes_internacionais", targetPercentage: 5 },
  { id: "t3", assetType: "fundos_imobiliarios", targetPercentage: 0 },
  { id: "t4", assetType: "reits", targetPercentage: 0 },
  { id: "t5", assetType: "criptomoedas", targetPercentage: 20 },
  { id: "t6", assetType: "rendafixa", targetPercentage: 20 },
  { id: "t7", assetType: "rendafixa_internacional", targetPercentage: 0 },
];

describe("EditTargetsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listPresets as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it("shows total 100% / 100% initially with seeded values", async () => {
    render(EditTargetsModal, {
      initialTargets: SEEDED,
      onsaved: () => {},
      onclose: () => {},
    });
    const total = await screen.findByTestId("total-indicator");
    expect(total).toHaveTextContent("Total: 100% / 100%");
  });

  it("disables Save when sum differs from 100", async () => {
    render(EditTargetsModal, {
      initialTargets: SEEDED,
      onsaved: () => {},
      onclose: () => {},
    });

    const fii = await screen.findByTestId("target-input-fundos_imobiliarios");
    await fireEvent.input(fii, { target: { value: "15" } });

    const save = screen.getByTestId("save-button") as HTMLButtonElement;
    expect(save.disabled).toBe(true);

    const total = screen.getByTestId("total-indicator");
    expect(total).toHaveTextContent("Total: 115% / 100%");
  });

  it("enables Save when total equals 100 after rebalancing", async () => {
    render(EditTargetsModal, {
      initialTargets: SEEDED,
      onsaved: () => {},
      onclose: () => {},
    });

    await fireEvent.input(
      await screen.findByTestId("target-input-acoes_nacionais"),
      { target: { value: "40" } }
    );
    await fireEvent.input(
      screen.getByTestId("target-input-fundos_imobiliarios"),
      { target: { value: "15" } }
    );

    const save = screen.getByTestId("save-button") as HTMLButtonElement;
    expect(save.disabled).toBe(false);
  });

  it("clicking a preset chip fills the inputs", async () => {
    (listPresets as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: "p1",
        name: "Agressivo",
        values: {
          acoes_nacionais: 70,
          acoes_internacionais: 10,
          fundos_imobiliarios: 5,
          reits: 5,
          criptomoedas: 5,
          rendafixa: 5,
          rendafixa_internacional: 0,
        },
        createdAt: "2026-04-17T00:00:00Z",
      },
    ]);

    render(EditTargetsModal, {
      initialTargets: SEEDED,
      onsaved: () => {},
      onclose: () => {},
    });

    const chip = await screen.findByRole("button", { name: "Agressivo" });
    await fireEvent.click(chip);

    const an = screen.getByTestId("target-input-acoes_nacionais") as HTMLInputElement;
    expect(an.value).toBe("70");
  });
});
