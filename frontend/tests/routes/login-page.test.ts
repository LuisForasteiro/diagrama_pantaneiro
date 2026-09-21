import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/svelte";
import { get } from "svelte/store";

vi.mock("$app/navigation", () => ({ goto: vi.fn() }));
vi.mock("$lib/api/auth", () => ({ login: vi.fn(), getCurrentUser: vi.fn() }));

import { goto } from "$app/navigation";
import { getCurrentUser, login } from "$lib/api/auth";
import LoginPage from "../../src/routes/(auth)/login/+page.svelte";
import { ApiError } from "../../src/lib/api/client";
import { authStore } from "../../src/lib/stores/auth";

async function submit(email = "a@b.c", password = "segredo123") {
  const { container } = render(LoginPage);
  await fireEvent.input(screen.getByLabelText("E-mail"), { target: { value: email } });
  await fireEvent.input(screen.getByLabelText("Senha"), { target: { value: password } });
  await fireEvent.submit(container.querySelector("form") as HTMLFormElement);
}

describe("login page", () => {
  beforeEach(() => {
    vi.mocked(goto).mockReset();
    vi.mocked(login).mockReset();
    vi.mocked(getCurrentUser).mockReset();
    authStore.logout();
  });

  it("shows a friendly message for bad credentials (400)", async () => {
    vi.mocked(login).mockRejectedValue(new ApiError(400, "login failed"));

    await submit();

    expect(await screen.findByText(/e-mail ou senha inválidos/)).toBeInTheDocument();
  });

  it("tells the user the backend is unreachable (status 0)", async () => {
    vi.mocked(login).mockRejectedValue(new ApiError(0, "não foi possível conectar ao servidor"));

    await submit();

    expect(await screen.findByText(/o backend está no ar\?/)).toBeInTheDocument();
  });

  it("rolls back the stored token when loading the user fails after login", async () => {
    vi.mocked(login).mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.mocked(getCurrentUser).mockRejectedValue(new ApiError(0, "não foi possível conectar ao servidor"));

    await submit();
    await screen.findByText(/o backend está no ar\?/);

    expect(get(authStore).token).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(goto).not.toHaveBeenCalled();
  });

  it("stores the session and goes home on success", async () => {
    const user = { id: "u1", email: "a@b.c", is_active: true, is_superuser: false, is_verified: true };
    vi.mocked(login).mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.mocked(getCurrentUser).mockResolvedValue(user);

    await submit();

    await vi.waitFor(() => expect(goto).toHaveBeenCalledWith("/home"));
    expect(get(authStore)).toEqual({ token: "tok", user });
  });
});
