/**
 * "Latest request wins" guard. Each `begin()` returns a checker that stays
 * true only until the next `begin()`, so responses of a superseded request
 * (e.g. switching portfolio A → B quickly) can be dropped instead of
 * overwriting fresher state.
 */
export function createLatestGuard(): { begin: () => () => boolean } {
  let generation = 0;
  return {
    begin() {
      generation += 1;
      const ticket = generation;
      return () => ticket === generation;
    },
  };
}
