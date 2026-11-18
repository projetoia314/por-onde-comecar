async function loadData() {
  const files = ['dicionario', 'biblioteca', 'direitos', 'coletivos', 'midia'];
  const entries = await Promise.all(files.map(async name => {
    const res = await fetch(`data/${name}.json`);
    return [name, await res.json()];
  }));
  return Object.fromEntries(entries);
}

loadData().then(DATA => {
  const appMain = document.getElementById('appMain');
  appMain.innerHTML = `<section class="p-6 rounded-2xl bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800">
    <h1 class="text-2xl font-bold mb-2">Portal carregado via JSON</h1>
    <p class="text-sm text-stone-600 dark:text-stone-400">Itens carregados: ${DATA.dicionario.length} verbetes, ${DATA.biblioteca.length} obras, ${DATA.coletivos.length} coletivos e ${DATA.midia.length} canais de mídia.</p>
  </section>`;
});
