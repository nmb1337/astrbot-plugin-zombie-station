const bridge = window.AstrBotPluginPage;
const heading = document.getElementById("heading");
const notice = document.getElementById("notice");
const overview = document.getElementById("overview");
const groups = document.getElementById("groups");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setNotice(text, isError = false) {
  notice.textContent = text;
  notice.className = isError ? "error" : "success";
}

function metric(label, value) {
  const card = element("article", "metric");
  card.append(element("span", "label", label), element("strong", "value", value));
  return card;
}

function renderGroup(group, deckSize) {
  const card = element("article", "group-card");
  const progress = Math.round((group.drawn / deckSize) * 100);
  const title = element("h2", "", `群 ${group.group_id} · 第 ${group.round} 局 / 第 ${group.day} 天`);
  const details = element("p", "details", `主持人：${group.host_name}｜已抽 ${group.drawn}｜剩余 ${group.remaining}｜玩家 ${group.player_count}`);
  const bar = element("div", "progress");
  const fill = element("span", "");
  fill.style.width = `${progress}%`;
  bar.append(fill);
  const ranking = element("ol", "ranking");
  for (const player of group.players) {
    ranking.append(element("li", "", `${player.name}：累计 ${player.total_opened} 包｜体力 ${player.stamina}｜今日 ${player.opened_today}`));
  }
  if (!group.players.length) ranking.append(element("li", "", "尚无人开包"));
  card.append(title, details, bar, ranking);
  return card;
}

function render(stats) {
  overview.replaceChildren(
    metric("卡池", `${stats.deck_size} 张`),
    metric("卡池来源", stats.cards_source),
    metric("进行中群局", `${stats.groups.length} 个`),
  );
  groups.replaceChildren();
  if (!stats.groups.length) {
    groups.append(element("p", "empty", "暂无进行中的群局。请在 QQ 群发送“驿站 开局”。"));
    return;
  }
  for (const group of stats.groups) groups.append(renderGroup(group, stats.deck_size));
}

async function loadStats() {
  setNotice("正在读取统计…");
  try {
    render(await bridge.apiGet("stats"));
    setNotice("统计已刷新。");
  } catch (error) {
    setNotice(`读取失败：${error.message}`, true);
  }
}

async function importCards() {
  const file = document.getElementById("file").files[0];
  if (!file) return setNotice("请先选择 CSV 或 XLSX 卡牌表。", true);
  if (!window.confirm("导入会清空全部群局，确定继续吗？")) return;
  setNotice("正在上传并校验 1200 张卡牌…");
  try {
    const result = await bridge.upload("cards/import", file);
    setNotice(`已导入 ${result.imported} 张卡牌，所有群局已清空。`);
    await loadStats();
  } catch (error) {
    setNotice(`导入失败：${error.message}`, true);
  }
}

await bridge.ready();
function updateLocale() {
  const title = bridge.t("pages.dashboard.title", "末日快递驿站");
  document.title = title;
  heading.textContent = title;
}
updateLocale();
bridge.onContext(updateLocale);
document.getElementById("refresh").addEventListener("click", loadStats);
document.getElementById("import").addEventListener("click", importCards);
await loadStats();
