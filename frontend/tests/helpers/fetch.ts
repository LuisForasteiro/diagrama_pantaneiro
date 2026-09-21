import { vi } from "vitest";

/**
 * fetch mock that never resolves on its own — it only settles (rejecting with
 * an AbortError, like the real fetch) when the request's signal is aborted.
 * Simulates a backend that accepted the TCP connection but froze.
 */
export function hangingFetch() {
  return vi.fn(
    (_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal;
        if (!signal) return;
        const abort = () => reject(new DOMException("The operation was aborted.", "AbortError"));
        if (signal.aborted) abort();
        else signal.addEventListener("abort", abort, { once: true });
      }),
  );
}

/** Captures how a promise settled without awaiting it (safe with fake timers). */
export function track<T>(promise: Promise<T>) {
  const outcome: { settled: boolean; value?: T; error?: unknown } = { settled: false };
  promise.then(
    (value) => {
      outcome.settled = true;
      outcome.value = value;
    },
    (error: unknown) => {
      outcome.settled = true;
      outcome.error = error;
    },
  );
  return outcome;
}
