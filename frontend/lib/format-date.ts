function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

// 浏览器本地时区的日历日期，用于 date input 默认值；toISOString() 会给 UTC 日期，
// UTC+8 在本地 00:00-08:00 之间慢一天。
export function toLocalDateInputValue(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

// 浏览器本地时区的分钟级时间戳，用于面向用户的墙钟展示。
export function formatLocalDateTimeMinutes(date: Date): string {
  return `${toLocalDateInputValue(date)} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}
