export const STORAGE_KEY = "renovation_daily_feedback_v1";

export function loadFeedback() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveFeedback(entries) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function clearFeedback() {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function appendFeedback(entry) {
  const entries = loadFeedback();
  const nextEntries = [...entries, entry];
  saveFeedback(nextEntries);
  return nextEntries;
}

export function buildLatestActionMap(entries) {
  return entries.reduce((acc, entry) => {
    if (entry.action === "like" || entry.action === "favorite" || entry.action === "dislike") {
      acc[entry.item_id] = entry.action;
    }
    return acc;
  }, {});
}

export function exportFeedback(entries) {
  const content = entries.map((entry) => JSON.stringify(entry)).join("\n");
  const blob = new Blob([content], {
    type: "application/x-ndjson;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "local-actions-export.jsonl";
  link.click();
  URL.revokeObjectURL(url);
}

export function buildFeedbackEntry(reportId, itemId, action, position, platform) {
  return {
    time: new Date().toISOString(),
    report_id: reportId,
    item_id: itemId,
    action,
    source: "daily_report",
    meta: {
      position,
      platform,
    },
  };
}
