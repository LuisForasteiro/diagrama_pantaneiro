import { beforeEach, describe, expect, it } from "vitest";
import { get } from "svelte/store";

import { authStore } from "../../src/lib/stores/auth";

describe("authStore", () => {
  beforeEach(() => {
    localStorage.clear();
    authStore.logout();
  });

  it("starts unauthenticated", () => {
    const state = get(authStore);
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
  });

  it("login sets token and user", () => {
    authStore.login("tok-123", { id: "u1", email: "a@b.c" });
    const state = get(authStore);
    expect(state.token).toBe("tok-123");
    expect(state.user?.email).toBe("a@b.c");
  });

  it("persists token to localStorage on login", () => {
    authStore.login("tok-xyz", { id: "u1", email: "a@b.c" });
    expect(localStorage.getItem("auth_token")).toBe("tok-xyz");
  });

  it("logout clears token and localStorage", () => {
    authStore.login("tok-xyz", { id: "u1", email: "a@b.c" });
    authStore.logout();
    expect(get(authStore).token).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
  });
});
