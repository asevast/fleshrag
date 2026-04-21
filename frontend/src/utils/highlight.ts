/**
 * Подсветка совпадений запроса в тексте
 */
export function highlightText(text: string, query: string): string {
  if (!query.trim()) return text
  
  // Экранируем спецсимволы для regex
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  
  return text.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>')
}

/**
 * Обрезка текста до нужной длины с сохранением границ слов
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  
  // Находим последнее полное слово перед обрезкой
  const truncated = text.slice(0, maxLength)
  const lastSpace = truncated.lastIndexOf(' ')
  
  return (lastSpace > 0 ? truncated.slice(0, lastSpace) : truncated) + '...'
}