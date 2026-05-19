import { AxiosError } from 'axios'

import { axiosInstance } from './mutator'

type ReportKind = 'course' | 'program'

interface DownloadReportPdfOptions {
  kind: ReportKind
  id: number
  termId?: number
  fallbackFilename: string
}

const getFilenameFromDisposition = (contentDisposition: unknown): string | null => {
  if (typeof contentDisposition !== 'string') return null

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].replace(/"/g, ''))
  }

  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return filenameMatch?.[1] ?? null
}

const getReportErrorMessage = async (data: unknown): Promise<string | null> => {
  if (data instanceof Blob && data.type.includes('application/json')) {
    try {
      const json = JSON.parse(await data.text()) as { detail?: unknown; error?: unknown }
      const message = json.detail ?? json.error
      return typeof message === 'string' ? message : null
    } catch {
      return null
    }
  }

  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const message = (data as { detail?: unknown }).detail
    return typeof message === 'string' ? message : null
  }

  return null
}

export const downloadReportPdf = async ({
  kind,
  id,
  termId,
  fallbackFilename,
}: DownloadReportPdfOptions): Promise<void> => {
  const url = kind === 'course'
    ? `/api/core/courses/${id}/report/`
    : `/api/core/programs/${id}/report/`

  try {
    const response = await axiosInstance.get<Blob>(url, {
      params: kind === 'program' && termId ? { term: termId } : undefined,
      responseType: 'blob',
    })

    const blob = new Blob([response.data], { type: 'application/pdf' })
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = getFilenameFromDisposition(response.headers['content-disposition']) ?? fallbackFilename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
  } catch (error) {
    if (error instanceof AxiosError) {
      const message = await getReportErrorMessage(error.response?.data)
      throw new Error(message ?? 'Failed to generate report.')
    }
    throw error
  }
}
