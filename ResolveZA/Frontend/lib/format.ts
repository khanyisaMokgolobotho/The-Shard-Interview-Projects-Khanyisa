export function formatCurrency(amount: string, currency = "ZAR") {
  const numeric = Number(amount);
  if (Number.isNaN(numeric)) {
    return `${currency} ${amount}`;
  }

  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency,
  }).format(numeric);
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatStatusLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatCompactId(value: string) {
  return value.slice(0, 8);
}
