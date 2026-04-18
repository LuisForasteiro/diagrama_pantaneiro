import { writable } from "svelte/store";
import { browser } from "$app/environment";

const KEY = "dp.privacy.masked";

function readInitial(): boolean {
  if (!browser) return false;
  return localStorage.getItem(KEY) === "1";
}

function create() {
  const { subscribe, set, update } = writable<boolean>(readInitial());
  return {
    subscribe,
    toggle: () =>
      update((v) => {
        const next = !v;
        if (browser) localStorage.setItem(KEY, next ? "1" : "0");
        return next;
      }),
    set: (v: boolean) => {
      if (browser) localStorage.setItem(KEY, v ? "1" : "0");
      set(v);
    },
  };
}

export const privacyStore = create();
