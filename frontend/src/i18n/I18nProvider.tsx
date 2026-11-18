import React, { createContext, useContext, useState } from "react";
import {
  AuthDictionary,
  LocaleCode,
  enAuthDictionary,
  guAuthDictionary,
} from "./dictionaries";

interface I18nContextValue {
  locale: LocaleCode;
  setLocale: (next: LocaleCode) => void;
  toggleLocale: () => void;
  t: AuthDictionary;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export const I18nProvider: React.FC<{
  initialLocale?: LocaleCode;
  children: React.ReactNode;
}> = ({ initialLocale = "en", children }) => {
  const [locale, setLocale] = useState<LocaleCode>(initialLocale);
  const toggleLocale = () => setLocale((prev) => (prev === "en" ? "gu" : "en"));
  const t = locale === "gu" ? guAuthDictionary : enAuthDictionary;

  return (
    <I18nContext.Provider value={{ locale, setLocale, toggleLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
