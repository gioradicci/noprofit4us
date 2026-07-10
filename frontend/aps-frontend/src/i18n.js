import { createI18n } from 'vue-i18n'
import it from './locales/it.json'
import en from './locales/en.json'

const savedLanguage = localStorage.getItem('lang') || 'it'

const i18n = createI18n({
  legacy: false, // Disabilita la modalità legacy per usare Composition API
  locale: savedLanguage,
  fallbackLocale: 'it',
  globalInjection: true, // Inietta $t in tutti i template
  messages: {
    it,
    en
  }
})

export default i18n
