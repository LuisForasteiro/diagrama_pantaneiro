<script lang="ts">
  import { onMount } from "svelte";
  import {
    listDiagramQuestions,
    createDiagramQuestion,
    updateDiagramQuestion,
    deleteDiagramQuestion,
  } from "$lib/api/diagram";
  import Panel from "$lib/components/Panel.svelte";
  import Topbar from "$lib/components/Topbar.svelte";
  import type { DiagramQuestionOut } from "$lib/types/api";

  let questions = $state<DiagramQuestionOut[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let busyId = $state<string | null>(null);

  let editingId = $state<string | null>(null);
  let editCriterias = $state("");
  let editText = $state("");

  let addingFor = $state<string | null>(null);
  let newCriterias = $state("");
  let newText = $state("");

  async function load() {
    loading = true;
    error = null;
    try {
      questions = await listDiagramQuestions();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  onMount(load);

  let cerrado = $derived(
    questions.filter((q) => q.diagramType === "diagrama-do-cerrado"),
  );
  let imobiliarios = $derived(
    questions.filter((q) => q.diagramType === "investimentos-imobiliarios"),
  );
  let etfs = $derived(
    questions.filter((q) => q.diagramType === "diagrama-etfs"),
  );

  function startEdit(q: DiagramQuestionOut) {
    editingId = q.id;
    editCriterias = q.criterias;
    editText = q.questionText;
  }

  function cancelEdit() {
    editingId = null;
  }

  async function saveEdit(id: string) {
    busyId = id;
    error = null;
    try {
      await updateDiagramQuestion(id, {
        criterias: editCriterias,
        questionText: editText,
      });
      editingId = null;
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busyId = null;
    }
  }

  async function remove(q: DiagramQuestionOut) {
    if (
      !confirm(
        `Deletar "${q.criterias || q.questionText}"?\n\n` +
          `Isso rebalanceia a força de todas as ações: N diminui em 1 e ` +
          `qualquer resposta "sim" para esta pergunta é removida. Esta ação ` +
          `não pode ser desfeita.`,
      )
    )
      return;
    busyId = q.id;
    error = null;
    try {
      await deleteDiagramQuestion(q.id);
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busyId = null;
    }
  }

  function startAdd(diagramType: string) {
    addingFor = diagramType;
    newCriterias = "";
    newText = "";
  }

  function cancelAdd() {
    addingFor = null;
  }

  async function submitAdd(diagramType: string) {
    if (!newText.trim()) {
      error = "O texto da pergunta é obrigatório";
      return;
    }
    busyId = "new";
    error = null;
    try {
      await createDiagramQuestion({
        diagramType,
        criterias: newCriterias,
        questionText: newText,
      });
      addingFor = null;
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busyId = null;
    }
  }

  const BANKS = [
    {
      type: "diagrama-do-cerrado",
      label: "── diagrama_pantaneiro ──",
      subtitle: "Ações nacionais + internacionais",
    },
    {
      type: "investimentos-imobiliarios",
      label: "── investimentos_imobiliários ──",
      subtitle: "FIIs + REITs",
    },
    {
      type: "diagrama-etfs",
      label: "── diagrama_etfs ──",
      subtitle: "ETFs nacionais + internacionais",
    },
  ];
</script>

<section class="pant-wrap">
  <Topbar subtitle="diagrama">
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
    {/snippet}
  </Topbar>

  <Panel delay={0}>
    <p class="intro">
      <span class="pant-prompt">»</span> força =
      <code class="formula">2 × sim − N</code>.
      adicionar ou deletar uma pergunta recalcula a força de todas as ações
      naquele diagrama.
    </p>
  </Panel>

  {#if error}
    <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
  {/if}

  {#if loading}
    <p class="pant-loading"><span class="pant-blink">█</span> carregando perguntas</p>
  {:else}
    <div class="banks">
      {#each BANKS as bank, i (bank.type)}
        {@const list = bank.type === "diagrama-do-cerrado"
          ? cerrado
          : bank.type === "investimentos-imobiliarios"
            ? imobiliarios
            : etfs}
        <Panel title={bank.label} sub="{bank.subtitle} · {list.length} perguntas" delay={120 + i * 80}>
          {#snippet actions()}
            {#if addingFor !== bank.type}
              <button type="button" class="pant-btn pant-btn-accent" onclick={() => startAdd(bank.type)}>
                + adicionar
              </button>
            {/if}
          {/snippet}

          <ol class="qlist">
            {#each list as q (q.id)}
              <li class="qrow">
                {#if editingId === q.id}
                  <div class="edit-form">
                    <input
                      type="text"
                      bind:value={editCriterias}
                      placeholder="rótulo curto (ex: ROE)"
                      class="pant-input"
                    />
                    <textarea
                      bind:value={editText}
                      rows="2"
                      placeholder="pergunta completa"
                      class="pant-input"
                    ></textarea>
                    <div class="pant-form-actions">
                      <button
                        type="button"
                        disabled={busyId === q.id}
                        onclick={() => saveEdit(q.id)}
                        class="pant-btn pant-btn-accent"
                      >
                        {busyId === q.id ? "…" : "salvar"}
                      </button>
                      <button type="button" onclick={cancelEdit} class="pant-btn">
                        cancelar
                      </button>
                    </div>
                  </div>
                {:else}
                  <div class="qrow-view">
                    <span class="qrow-text">
                      <span class="pant-prompt">›</span>
                      {#if q.criterias}<strong class="qcrit">{q.criterias}</strong>{/if}
                      {#if q.questionText && q.questionText !== q.criterias}
                        <span class="ink-dim">
                          {q.criterias ? " — " : ""}{q.questionText}
                        </span>
                      {/if}
                    </span>
                    <span class="qrow-actions">
                      <button type="button" onclick={() => startEdit(q)} class="pant-btn">
                        editar
                      </button>
                      <button
                        type="button"
                        disabled={busyId === q.id}
                        onclick={() => remove(q)}
                        class="pant-btn pant-btn-danger"
                      >
                        × deletar
                      </button>
                    </span>
                  </div>
                {/if}
              </li>
            {/each}
          </ol>

          {#if addingFor === bank.type}
            <div class="add-form">
              <span class="pant-label-text">── nova pergunta ──</span>
              <input
                type="text"
                bind:value={newCriterias}
                placeholder="rótulo curto (opcional, ex: P/L)"
                class="pant-input"
              />
              <textarea
                bind:value={newText}
                rows="2"
                placeholder="pergunta completa"
                class="pant-input"
              ></textarea>
              <div class="pant-form-actions">
                <button
                  type="button"
                  disabled={busyId === "new"}
                  onclick={() => submitAdd(bank.type)}
                  class="pant-btn pant-btn-accent"
                >
                  {busyId === "new" ? "…" : "adicionar"}
                </button>
                <button type="button" onclick={cancelAdd} class="pant-btn">
                  cancelar
                </button>
              </div>
            </div>
          {/if}
        </Panel>
      {/each}
    </div>

    <p class="footer">
      <span class="pant-prompt">»</span>
      <span class="ink-dim">
        atenção: adicionar ou deletar perguntas desloca a força de todas as
        ações do diagrama — confira o painel/posições após edições em massa.
      </span>
    </p>
  {/if}
</section>

<style>
  .intro {
    margin: 0;
    font-size: 13px;
    color: var(--ink-dim);
  }
  .formula {
    background: var(--surface-raised);
    border: 1px solid var(--hairline);
    padding: 1px 6px;
    color: var(--accent);
    font-family: inherit;
    font-size: 12px;
  }

  .banks {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0;
  }
  @media (min-width: 1100px) {
    .banks { grid-template-columns: repeat(2, 1fr); gap: 20px; }
  }

  .qlist { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .qrow {
    border: 1px solid var(--hairline);
    padding: 8px 10px;
    background: var(--surface-raised);
    font-size: 12px;
  }
  .qrow-view {
    display: flex;
    gap: 10px;
    justify-content: space-between;
    align-items: flex-start;
  }
  .qrow-text { flex: 1; line-height: 1.5; }
  .qcrit { color: var(--ink); }
  .qrow-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .edit-form { display: grid; gap: 6px; }
  .add-form {
    margin-top: 14px;
    padding: 12px;
    background: var(--surface-raised);
    border: 1px solid var(--hairline-strong);
    display: grid;
    gap: 6px;
  }

  .footer {
    margin-top: 16px;
    font-size: 12px;
  }
</style>
