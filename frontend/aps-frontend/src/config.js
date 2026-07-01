// URL del backend, configurabile tramite variabile d'ambiente VITE_API_URL
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Restituisce l'URL corretto per un'immagine:
 * - Se il path è già un URL completo (es. da Supabase Storage), lo usa direttamente
 * - Se è un path relativo (es. /static/...), aggiunge il prefisso del backend
 */
export function getImageUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return API_URL + path
}
