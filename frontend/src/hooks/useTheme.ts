import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem("reelvault-theme");
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* ignore */
  }
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("reelvault-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}
