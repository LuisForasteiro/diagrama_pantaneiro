import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";

const pageState = vi.hoisted(() => ({
  status: 503,
  error: { message: "servidor indisponível" } as { message: string } | null,
}));
vi.mock("$app/state", () => ({ page: pageState }));

import ErrorPage from "../../src/routes/+error.svelte";

describe("+error.svelte", () => {
  beforeEach(() => {
    pageState.status = 503;
    pageState.error = { message: "servidor indisponível" };
  });

  it("shows the status and the error message", () => {
    render(ErrorPage);

    expect(screen.getByText(/503/)).toBeInTheDocument();
    expect(screen.getByText(/servidor indisponível/)).toBeInTheDocument();
  });

  it("offers retry and a way back to the login", () => {
    render(ErrorPage);

    expect(screen.getByRole("button", { name: /tentar novamente/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ir para o login/ })).toHaveAttribute("href", "/login");
  });

  it("uses a friendly message for unknown routes (404)", () => {
    pageState.status = 404;
    pageState.error = { message: "Not Found" };

    render(ErrorPage);

    expect(screen.getByText(/página não encontrada/)).toBeInTheDocument();
  });
});
