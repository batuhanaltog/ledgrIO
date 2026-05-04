export function todayMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
}
