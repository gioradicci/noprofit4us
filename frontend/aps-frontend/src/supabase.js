import { createClient } from '@supabase/supabase-js'

export function checkUrlAuthError() {
  if (typeof window === 'undefined') return null
  const hash = window.location.hash ? window.location.hash.substring(1) : ''
  const search = window.location.search ? window.location.search.substring(1) : ''
  const hashParams = new URLSearchParams(hash)
  const searchParams = new URLSearchParams(search)

  const errorCode = hashParams.get('error_code') || searchParams.get('error_code')
  const error = hashParams.get('error') || searchParams.get('error')
  const errorDescription = hashParams.get('error_description') || searchParams.get('error_description')

  if (errorCode || error) {
    return {
      errorCode: errorCode || error,
      errorDescription: errorDescription ? decodeURIComponent(errorDescription.replace(/\+/g, ' ')) : null
    }
  }
  return null
}

export const isInitialRecoveryLink = typeof window !== 'undefined' && !checkUrlAuthError() && (
  window.location.href.includes('type=recovery') ||
  window.location.hash.includes('type=recovery') ||
  window.location.search.includes('type=recovery')
)


const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
