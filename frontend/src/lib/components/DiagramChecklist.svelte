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
  <div class="rounded border border-slate-200 bg-slate-50 p-4">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-sm font-semibold">
        Pontuação ({diagramType === "diagrama-do-cerrado"
          ? "Diagrama Pantaneiro"
          : diagramType === "investimentos-imobiliarios"
            ? "Investimentos Imobiliários"
            : "Diagrama de ETFs"})
      </h3>
      <span class="text-sm tabular-nums">
        <span class="text-slate-500">{yesCount}/{questions.length} sim ·</span>
        <strong
          class:text-emerald-700={computedStrength > 0}
          class:text-red-700={computedStrength < 0}
          class:text-slate-600={computedStrength === 0}
        >
          força {computedStrength > 0 ? "+" : ""}{computedStrength}
        </strong>
      </span>
    </div>

    {#if loading}
      <p class="text-sm text-slate-500">Carregando perguntas…</p>
    {:else if error}
      <p class="text-sm text-red-700">Erro: {error}</p>
    {:else if questions.length === 0}
      <p class="text-sm text-slate-500">Nenhuma pergunta cadastrada para este diagrama.</p>
    {:else}
      <ul class="space-y-2">
        {#each questions as q (q.id)}
          {@const ticked = responses.includes(q.id)}
          <li>
            <label class="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={ticked}
                onchange={(e) =>
                  toggle(q.id, (e.currentTarget as HTMLInputElement).checked)}
                class="mt-0.5"
              />
              <span>
                {#if q.criterias}<strong>{q.criterias}</strong>{/if}
                {#if q.questionText && q.questionText !== q.criterias}
                  <span class="text-slate-600">
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
