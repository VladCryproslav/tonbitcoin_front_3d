import { createI18n } from 'vue-i18n'
import en from '../locales/en'
import uk from '../locales/uk'
import ru from '../locales/ru'

// List of CIS language codes that should use 'ru'
const cisLanguages = ['ru', 'uk', 'be', 'kk', 'uz', 'tg', 'ky', 'az', 'hy', 'tk']

function customRule(choice, choicesLength) {
  if (+choice == 0) {
    return 0;
  }
  const teen = +choice >= 11 && +choice <= 19;
  const lastDigit = +choice % 10;
  if (lastDigit == 1 && !teen) {
    return 1;
  }
  if (lastDigit >= 2 && lastDigit <= 4 && !teen) {
    return 2;
  }
  return choicesLength < 4 ? 2 : 3;
}

const getLocale = () => {
  // Check localStorage first
  const storedLocale = localStorage.getItem('locale')
  if (storedLocale && ['en', 'ru', 'uk'].includes(storedLocale)) {
    return storedLocale
  }

  // Get language from Telegram or default to 'en'
  const telegramLocale = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || 'ru'

  // Set 'ru' for CIS languages, otherwise 'en'
  const selectedLocale = cisLanguages.includes(telegramLocale) ? 'ru' : 'en'

  // Save selected locale to localStorage
  localStorage.setItem('locale', selectedLocale)
  return selectedLocale
}

const i18n = createI18n({
  legacy: false,
  locale: getLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    ru,
    uk,
  },
  pluralRules: {
    en: customRule,
    ru: customRule,
    uk: customRule,
  },
})

export default i18n
