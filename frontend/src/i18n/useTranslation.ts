import { useContext } from 'react'
import { I18nContext } from './I18nContext'

export function useTranslation() {
  return useContext(I18nContext)
}
