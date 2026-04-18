import { writable } from "svelte/store";
import type { PortfolioOut } from "$lib/types/api";

const STORAGE_KEY = "active_portfolio_id";

interface PortfolioState {
  all: PortfolioOut[];
  activeId: string | null;
}

function readInitial(): PortfolioState {
  if (typeof localStorage === "undefined") return { all: [], activeId: null };
  return { all: [], activeId: localStorage.getItem(STORAGE_KEY) };
}

function createPortfolioStore() {
  const { subscribe, set, update } = writable<PortfolioState>(readInitial());

  return {
    subscribe,
    setAll(list: PortfolioOut[]) {
      update((s) => {
        // Active id validation: if the persisted id isn't in the returned list,
        // fall back to is_default (or first). Otherwise keep the user's choice.
        const ids = new Set(list.map((p) => p.id));
        let active = s.activeId && ids.has(s.activeId) ? s.activeId : null;
        if (active === null) {
          const def = list.find((p) => p.isDefault) ?? list[0] ?? null;
          active = def?.id ?? null;
          if (active !== null) localStorage.setItem(STORAGE_KEY, active);
        }
        return { all: list, activeId: active };
      });
    },
    setActive(id: string) {
      localStorage.setItem(STORAGE_KEY, id);
      update((s) => ({ ...s, activeId: id }));
    },
    reset() {
      localStorage.removeItem(STORAGE_KEY);
      set({ all: [], activeId: null });
    },
  };
}

export const portfolioStore = createPortfolioStore();
