<script lang="ts">
  import { onMount } from "svelte";
  import { listDiagramQuestions } from "$lib/api/diagram";
  import type { DiagramQuestionOut } from "$lib/types/api";

  interface Props {
    assetType: string;
    responses: string[];
    onchange: (ids: string[]) => void;
  }

  let { assetType, responses, onchange }: Props = $props();

  // Map asset type to its diagram (mirrors backend DIAGRAM_FOR_CLASS)
  function diagramFor(t: string): string | null {
    if (t === "acoes_nacionais" || t === "acoes_internacionais")
      return "diagrama-do-cerrado";
    if (t === "fundos_imobiliarios" || t === "reits")
      return "investimentos-imobiliarios";
    if (t === "etfs_nacionais" || t === "etfs_internacionais")
      return "diagrama-etfs";
    return null;
  }

  let diagramType = $derived(diagramFor(assetType));
  let questions = $state<DiagramQuestionOut[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Load questions whenever the relevant diagram changes.
  $effect(() => {
    const d = diagramType;
    if (!d) {
      questions = [];
      return;
    }
    loading = true;
    error = null;
    listDiagramQuestions(d)
      .then((qs) => {
        questions = qs;
        reconcileResponses(qs);
      })
      .catch((e) => {
        error = e instanceof Error ? e.message : String(e);
      })
      .finally(() => {
        loading = false;
      });
  });

  // Translate legacy AUVP external_ids in `responses` to local question UUIDs,
  // drop any IDs that match neither. Emits the cleaned list so form state and
  // the strength we save are consistent with what the user actually sees ticked.
  function reconcileResponses(qs: DiagramQuestionOut[]) {
    const byLocal = new Set(qs.map((q) => q.id));
    const byExternal = new Map(
      qs.filter((q) => q.externalId).map((q) => [q.externalId as string, q.id]),
    );
    const cleaned: string[] = [];
    for (const r of responses) {
      if (byLocal.has(r)) cleaned.push(r);
      else if (byExternal.has(r)) cleaned.push(byExternal.get(r)!);
    }
    // Dedup preserves order.
    const deduped = Array.from(new Set(cleaned));
    if (
      deduped.length !== responses.length ||
      deduped.some((v, i) => v !== responses[i])
    ) {
      onchange(deduped);
    }
  }

  let yesCount = $derived(
    questions.length > 0
      ? responses.filter((r) => questions.some((q) => q.id === r)).length
      : 0,
  );
  let computedStrength = $derived(
    questions.length > 0 ? 2 * yesCount - questions.length : 0,
  );

  function toggle(id: string, checked: boolean) {
    const next = checked
      ? Array.from(new Set([...responses, id]))
      : responses.filter((r) => r !== id);
    onchange(next);
  }
</script>

{#if diagramType}
  <div class="dc-panel">
    <div class="dc-head">
      <h3 class="dc-title">
        Pontuação ({diagramType === "diagrama-do-cerrado"
          ? "Diagrama Pantaneiro"
          : diagramType === "investimentos-imobiliarios"
            ? "Investimentos Imobiliários"
            : "Diagrama de ETFs"})
      </h3>
      <span class="dc-score pant-tab-nums">
        <span class="ink-muted">{yesCount}/{questions.length} sim ·</span>
        <strong
          class:ink-pos={computedStrength > 0}
          class:ink-neg={computedStrength < 0}
          class:ink-muted={computedStrength === 0}
        >
          força {computedStrength > 0 ? "+" : ""}{computedStrength}
        </strong>
      </span>
    </div>

    {#if loading}
      <p class="dc-msg"><span class="pant-blink">█</span> carregando perguntas…</p>
    {:else if error}
      <p class="dc-msg ink-neg">Erro: {error}</p>
    {:else if questions.length === 0}
      <p class="dc-msg ink-muted">Nenhuma pergunta cadastrada para este diagrama.</p>
    {:else}
      <ul class="dc-list">
        {#each questions as q (q.id)}
          {@const ticked = responses.includes(q.id)}
          <li>
            <label class="dc-item">
              <input
                type="checkbox"
                checked={ticked}
                onchange={(e) =>
                  toggle(q.id, (e.currentTarget as HTMLInputElement).checked)}
                class="dc-check"
              />
              <span>
                {#if q.criterias}<strong class="dc-crit">{q.criterias}</strong>{/if}
                {#if q.questionText && q.questionText !== q.criterias}
                  <span class="ink-dim">
                    {q.criterias ? " — " : ""}{q.questionText}
                  </span>
                {/if}
              </span>
            </label>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
{/if}

<style>
  .dc-panel {
    border: 1px solid var(--hairline);
    background: var(--surface-raised);
    padding: 14px 16px;
  }
  .dc-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .dc-title {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--ink);
  }
  .dc-score { font-size: 12px; }
  .dc-msg { font-size: 12px; margin: 0; color: var(--ink-dim); }
  .dc-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 8px;
  }
  .dc-item {
    display: flex;
    cursor: pointer;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    line-height: 1.5;
    color: var(--ink-dim);
  }
  .dc-item:hover .dc-crit { color: var(--accent); }
  .dc-check {
    margin-top: 2px;
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    cursor: pointer;
  }
  .dc-crit { color: var(--ink); }
</style>
