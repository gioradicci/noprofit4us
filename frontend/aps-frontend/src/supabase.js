import { createClient } from '@supabase/supabase-js'

export const isInitialRecoveryLink = typeof window !== 'undefined' && (
  window.location.href.includes('type=recovery') ||
  window.location.hash.includes('type=recovery') ||
  window.location.search.includes('type=recovery')
)

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
