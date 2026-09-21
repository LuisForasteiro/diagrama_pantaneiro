import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import { createRawSnippet, tick } from "svelte";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));

import { goto } from "$app/navigation";
import AppLayout from "../../src/routes/(app)/+layout.svelte";
import { authStore } from "../../src/lib/stores/auth";

const USER = { id: "u1", email: "a@b.c", is_active: true, is_superuser: false, is_verified: true };
const children = createRawSnippet(() => ({ render: () => "<p>conteúdo da página</p>" }));

describe("(app)/+layout.svelte", () => {
  beforeEach(() => {
    vi.mocked(goto).mockReset();
    authStore.login("tok", USER);
  });

  it("renders the page while the session is valid", async () => {
    render(AppLayout, { props: { children } });
    await tick();

    expect(screen.getByText("conteúdo da página")).toBeInTheDocument();
    expect(goto).not.toHaveBeenCalled();
  });

  it("navigates to /login when the token is cleared mid-session (e.g. a 401)", async () => {
    render(AppLayout, { props: { children } });
    await tick();

    authStore.logout();
    await tick();

    expect(goto).toHaveBeenCalledWith("/login", { replaceState: true });
  });
});
