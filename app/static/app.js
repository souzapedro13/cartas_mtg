const EXAMPLE_DECK = "https://www.mtggoldfish.com/archetype/pauper-blue-terror-2b4f6710-ccb2-4660-b5f9-ea85c8875ec5#paper";

const form = document.querySelector("#analysis-form");
const urlInput = document.querySelector("#deck-url");
const shippingInput = document.querySelector("#shipping");
const submitButton = document.querySelector("#submit-button");
const loading = document.querySelector("#loading");
const loadingMessage = document.querySelector("#loading-message");
const errorBox = document.querySelector("#error");
const errorMessage = document.querySelector("#error-message");
const results = document.querySelector("#results");
const cardsGrid = document.querySelector("#cards-grid");
const cardSearch = document.querySelector("#card-search");
const emptySearch = document.querySelector("#empty-search");

const loadingMessages = [
  "Lendo a lista de cartas no MTGGoldfish…",
  "Consultando referências de preço no Brasil…",
  "Calculando quantidades e subtotais…",
  "Convertendo a estimativa internacional…",
  "Preparando a comparação final…",
];

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const usd = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD" });
let currentCards = [];
let loadingTimer;

function moneyBRL(value) {
  return brl.format(Number(value || 0));
}

function moneyUSD(value) {
  return usd.format(Number(value || 0)).replace("US$", "US$");
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function startLoading() {
  let index = 0;
  loadingMessage.textContent = loadingMessages[index];
  loading.hidden = false;
  errorBox.hidden = true;
  results.hidden = true;
  submitButton.disabled = true;
  loadingTimer = window.setInterval(() => {
    index = (index + 1) % loadingMessages.length;
    loadingMessage.textContent = loadingMessages[index];
  }, 2800);
  loading.scrollIntoView({ behavior: "smooth", block: "center" });
}

function stopLoading() {
  window.clearInterval(loadingTimer);
  loading.hidden = true;
  submitButton.disabled = false;
}

function showError(message) {
  errorMessage.textContent = message;
  errorBox.hidden = false;
  errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function validateDeckUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && (parsed.hostname === "mtggoldfish.com" || parsed.hostname.endsWith(".mtggoldfish.com"));
  } catch {
    return false;
  }
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function createCard(card) {
  const article = createElement("article", "mtg-card");
  article.dataset.search = `${card.nome || ""} ${card.nome_pt || ""}`.toLocaleLowerCase("pt-BR");

  const art = createElement("div", "card-art");
  const placeholder = createElement("div", "card-art-placeholder", "✦");
  art.append(placeholder);

  if (card.imagem) {
    const image = document.createElement("img");
    image.src = card.imagem;
    image.alt = `Carta ${card.nome}`;
    image.loading = "lazy";
    image.addEventListener("load", () => { placeholder.hidden = true; });
    image.addEventListener("error", () => { image.remove(); placeholder.hidden = false; });
    art.append(image);
  }

  art.append(createElement("span", "quantity-badge", `${card.quantidade_total}x`));

  const body = createElement("div", "card-body");
  const name = createElement("div", "card-name");
  name.append(createElement("strong", "", card.nome));
  name.append(createElement("small", "", card.nome_pt || card.ligamagic?.edicao_referencia || "Nome em português indisponível"));
  body.append(name);

  if (card.status === "ok" && card.ligamagic && card.subtotal) {
    const prices = createElement("div", "card-prices");
    [
      ["Mín.", card.ligamagic.preco_minimo],
      ["Médio", card.ligamagic.preco_medio],
      ["Máx.", card.ligamagic.preco_maximo],
    ].forEach(([label, value]) => {
      const item = document.createElement("div");
      item.append(createElement("span", "", label));
      item.append(createElement("strong", "", moneyBRL(value)));
      prices.append(item);
    });
    body.append(prices);

    const subtotal = createElement("div", "card-subtotal");
    subtotal.append(createElement("span", "", "Subtotal mínimo"));
    subtotal.append(createElement("strong", "", moneyBRL(card.subtotal.minimo)));
    body.append(subtotal);
  } else {
    body.append(createElement("div", "card-unavailable", "Cotação brasileira indisponível"));
  }

  article.append(art, body);
  return article;
}

function renderCards(cards) {
  currentCards = cards;
  cardsGrid.replaceChildren(...cards.map(createCard));
  emptySearch.hidden = cards.length !== 0;
}

function renderNotices(notices) {
  const container = document.querySelector("#notices");
  const title = createElement("strong", "", "Notas importantes");
  const list = document.createElement("ul");
  notices.forEach((notice) => list.append(createElement("li", "", notice)));
  container.replaceChildren(title, list);
}

function renderResult(data) {
  const totalCards = data.deck.main_deck_cartas + data.deck.sideboard_cartas;
  setText("#deck-name", data.deck.nome || "Deck sem nome");
  setText("#deck-format", data.deck.formato || "Formato não informado");
  setText("#deck-count", `${totalCards} cartas · ${data.deck.main_deck_cartas} main / ${data.deck.sideboard_cartas} side`);
  document.querySelector("#source-link").href = data.deck.url;

  setText("#brazil-min", moneyBRL(data.brasil.total_minimo_brl));
  setText("#brazil-average", moneyBRL(data.brasil.total_medio_brl));
  setText("#brazil-max", moneyBRL(data.brasil.total_maximo_brl));
  setText("#quoted-cards", `${data.brasil.cartas_com_cotacao} nomes cotados · ${data.brasil.cartas_sem_cotacao} sem cotação`);
  setText("#import-total", moneyBRL(data.importacao.total_brl));
  setText("#import-detail", `${moneyUSD(data.importacao.total_usd)} com frete`);
  setText("#exchange-rate", `US$ 1 = ${moneyBRL(data.importacao.cotacao_usd_brl)}`);
  setText("#deck-usd", moneyUSD(data.importacao.deck_usd));
  setText("#shipping-usd", moneyUSD(data.importacao.frete_usd));
  setText("#import-total-secondary", moneyBRL(data.importacao.total_brl));

  const verdictCard = document.querySelector("#verdict-card");
  verdictCard.classList.remove("is-import", "is-partial");
  const cheaper = data.comparacao.mais_barato;
  const isImport = cheaper === "importacao";
  const isTie = cheaper === "empate";
  if (isImport) verdictCard.classList.add("is-import");
  if (!data.comparacao.confiavel) verdictCard.classList.add("is-partial");

  setText("#verdict-kicker", isTie ? "Estimativas equivalentes" : "Melhor estimativa");
  setText("#verdict-title", isTie ? "Valores praticamente iguais" : isImport ? "Importar ficou mais barato" : "Comprar no Brasil ficou mais barato");
  setText("#verdict-description", data.comparacao.observacao || (isTie
    ? "A diferença entre as duas estimativas é mínima."
    : isImport
      ? "A estimativa internacional, com o frete informado, apresentou o menor valor."
      : "O menor preço brasileiro encontrado apresentou o menor valor total."));
  setText("#verdict-difference", moneyBRL(data.comparacao.diferenca_brl));

  const brazilValue = Number(data.brasil.total_minimo_brl || 0);
  const importValue = Number(data.importacao.total_brl || 0);
  const scale = Math.max(brazilValue, importValue, 1);
  document.querySelector("#bar-brazil").style.width = `${Math.max(4, (brazilValue / scale) * 100)}%`;
  document.querySelector("#bar-import").style.width = `${Math.max(4, (importValue / scale) * 100)}%`;
  setText("#bar-brazil-value", moneyBRL(brazilValue));
  setText("#bar-import-value", moneyBRL(importValue));
  setText("#comparison-note", data.comparacao.confiavel
    ? "Comparação baseada no menor preço brasileiro válido para cada carta."
    : data.comparacao.observacao || "Comparação parcial por existirem cartas sem cotação.");

  renderCards(data.cartas);
  renderNotices([...data.avisos, data.importacao.aviso]);
  cardSearch.value = "";
  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const deckUrl = urlInput.value.trim();
  const shipping = Number(shippingInput.value);

  if (!validateDeckUrl(deckUrl)) {
    showError("Informe um link HTTPS válido do MTGGoldfish.");
    urlInput.focus();
    return;
  }
  if (!Number.isFinite(shipping) || shipping < 0) {
    showError("O frete precisa ser um valor igual ou maior que zero.");
    shippingInput.focus();
    return;
  }

  startLoading();
  try {
    const query = new URLSearchParams({ url: deckUrl, frete_usd: String(shipping) });
    const response = await fetch(`/analisar-deck?${query.toString()}`, { headers: { Accept: "application/json" } });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `A análise retornou o código ${response.status}.`);
    renderResult(payload);
  } catch (error) {
    showError(error.message || "Ocorreu um erro inesperado. Tente novamente em instantes.");
  } finally {
    stopLoading();
  }
});

document.querySelector("#example-button").addEventListener("click", () => {
  urlInput.value = EXAMPLE_DECK;
  urlInput.focus();
});

document.querySelector("#dismiss-error").addEventListener("click", () => { errorBox.hidden = true; });

document.querySelector("#new-analysis").addEventListener("click", () => {
  results.hidden = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
  window.setTimeout(() => urlInput.focus(), 450);
});

cardSearch.addEventListener("input", () => {
  const search = cardSearch.value.trim().toLocaleLowerCase("pt-BR");
  let visible = 0;
  cardsGrid.querySelectorAll(".mtg-card").forEach((card) => {
    const matches = !search || card.dataset.search.includes(search);
    card.hidden = !matches;
    if (matches) visible += 1;
  });
  emptySearch.hidden = visible !== 0;
});
