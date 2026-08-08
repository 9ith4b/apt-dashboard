export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

let csrfToken: string | null = null
let csrfRequest: Promise<string> | null = null

export function setCsrfToken(value: string | null) {
  csrfToken = value
}

async function ensureCsrfToken() {
  if (csrfToken) return csrfToken
  if (!csrfRequest) {
    csrfRequest = fetch("/api/v1/auth/csrf", {
      credentials: "same-origin",
    })
      .then(async (response) => {
        if (!response.ok)
          throw new ApiError("无法建立安全会话", response.status)
        const payload = (await response.json()) as { csrf_token: string }
        csrfToken = payload.csrf_token
        return payload.csrf_token
      })
      .finally(() => {
        csrfRequest = null
      })
  }
  return csrfRequest
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? "GET").toUpperCase()
  if (init?.body !== undefined) {
    headers.set("Content-Type", "application/json")
  }
  if (
    import.meta.env.MODE !== "test" &&
    !["GET", "HEAD", "OPTIONS"].includes(method) &&
    path !== "/auth/login"
  ) {
    headers.set("X-CSRF-Token", await ensureCsrfToken())
  }
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers,
  })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        message = payload.detail
      }
    } catch {
      // Preserve the status-based fallback when the body is not JSON.
    }
    if (response.status === 401 && path !== "/auth/login") {
      csrfToken = null
      window.dispatchEvent(new Event("apt-hunter:unauthorized"))
    }
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
