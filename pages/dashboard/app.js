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

function staminaInput(value) {
  const input = document.createElement("input");
  input.type = "number";
  input.min = "1";
  input.step = "1";
  input.value = String(value);
  input.setAttribute("aria-label", "每日体力");
  return input;
}

async function savePlayerStamina(groupId, playerId, dailyStamina) {
  if (!playerId.trim()) return setNotice("请输入玩家 QQ 号。", true);
  if (!Number.isInteger(dailyStamina) || dailyStamina < 1) {
    return setNotice("每日体力必须是大于 0 的整数。", true);
  }
  setNotice("正在保存玩家体力…");
  try {
    await bridge.apiPost("players/stamina", {
      group_id: groupId,
      player_id: playerId.trim(),
      daily_stamina: dailyStamina,
    });
    setNotice(`已保存 ${playerId} 的每日体力上限。`);
    await loadStats();
  } catch (error) {
    setNotice(`保存失败：${error.message}`, true);
  }
}

function playerRow(groupId, player) {
  const row = element("li", "player-row");
  row.append(element("span", "player-summary", `${player.name}：累计 ${player.total_opened} 包｜体力 ${player.stamina}/${player.daily_stamina}｜今日 ${player.opened_today}`));
  const controls = element("div", "stamina-controls");
  const input = staminaInput(player.daily_stamina);
  const button = element("button", "secondary", "保存上限");
  button.type = "button";
  button.addEventListener("click", () => savePlayerStamina(groupId, player.player_id ?? player.id ?? player.name, Number(input.value)));
  controls.append(input, button);
  row.append(controls);
  return row;
}

function newPlayerForm(group) {
  const form = element("form", "new-player-form");
  const title = element("strong", "", "预设玩家体力");
  const playerId = document.createElement("input");
  playerId.type = "text";
  playerId.placeholder = "QQ 号";
  playerId.setAttribute("aria-label", "QQ 号");
  const dailyStamina = staminaInput(10);
  const submit = element("button", "secondary", "新增或覆盖");
  submit.type = "submit";
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await savePlayerStamina(group.group_id, playerId.value, Number(dailyStamina.value));
  });
  form.append(title, playerId, dailyStamina, submit);
  return form;
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
  for (const player of group.players) ranking.append(playerRow(group.group_id, player));
  if (!group.players.length) ranking.append(element("li", "", "尚无人开包；可先在下方预设玩家体力。"));
  card.append(title, details, bar, ranking, newPlayerForm(group));
  return card;
}

function render(stats) {
  overview.replaceChildren(
    metric("运行版本", `v${stats.plugin_version || "未知"}`),
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

async function loadStats(showNotice = true) {
  if (showNotice) setNotice("正在读取统计…");
  try {
    const stats = await bridge.apiGet("stats");
    render(stats);
    if (showNotice) setNotice("统计已刷新。");
    return stats;
  } catch (error) {
    const message = error?.message || "未知错误";
    setNotice(`读取失败：${message}`, true);
    throw error;
  }
}

async function importCards() {
  const file = document.getElementById("file").files[0];
  if (!file) return setNotice("请先选择 CSV 或 XLSX 卡牌表。", true);
  setNotice("正在上传并校验卡牌表…");
  try {
    const result = await bridge.upload("cards/import", file);
    const stats = await loadStats(false);
    if (stats.deck_size !== result.imported || stats.cards_source !== result.source) {
      throw new Error("上传接口返回成功，但回读卡池与导入结果不一致");
    }
    setNotice(`已导入 ${result.imported} 张卡牌，当前卡池来源：${stats.cards_source}。`);
  } catch (error) {
    console.error("Card table import failed:", error);
    const message = error?.message || "未知错误";
    setNotice(`导入失败：${message}。请在 AstrBot Trace 中搜索“驿站卡牌表导入”。`, true);
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
