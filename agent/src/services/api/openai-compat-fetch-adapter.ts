/**
 * OpenAI-compatible Responses API fetch adapter (ARK, vLLM proxies, etc.)
 *
 * Intercepts Anthropic SDK `/v1/messages` calls and forwards them to an
 * OpenAI-Responses-style endpoint (same wire format as Codex adapter).
 * The model ID from the Anthropic request body is sent as-is — set
 * `ANTHROPIC_MODEL` (or /model) to your provider's model id (e.g. `ep-…`).
 */

import { isEnvTruthy } from '../../utils/envUtils.js'
import { writeToStderr } from '../../utils/process.js'
import {
  translateCodexStreamToAnthropic,
  translateToCodexBody,
} from './codex-fetch-adapter.js'

/** Read SDK POST body regardless of whether fetch passes string, Buffer, or stream. */
async function readRequestInitBodyAsText(
  body: RequestInit['body'],
): Promise<string> {
  if (body == null) return '{}'
  if (typeof body === 'string') return body
  if (typeof Buffer !== 'undefined' && Buffer.isBuffer(body)) {
    return body.toString('utf8')
  }
  if (body instanceof Uint8Array) {
    return new TextDecoder().decode(body)
  }
  if (body instanceof ArrayBuffer) {
    return new TextDecoder().decode(body)
  }
  if (typeof Blob !== 'undefined' && body instanceof Blob) {
    return await body.text()
  }
  if (body instanceof ReadableStream) {
    return await new Response(body).text()
  }
  if (
    body &&
    typeof (body as AsyncIterable<Uint8Array>)[Symbol.asyncIterator] ===
      'function'
  ) {
    const chunks: Uint8Array[] = []
    for await (const chunk of body as AsyncIterable<Uint8Array | ArrayBuffer>) {
      if (chunk instanceof Uint8Array) {
        chunks.push(chunk)
      } else {
        chunks.push(new Uint8Array(chunk))
      }
    }
    const total = chunks.reduce((n, c) => n + c.length, 0)
    const merged = new Uint8Array(total)
    let off = 0
    for (const c of chunks) {
      merged.set(c, off)
      off += c.length
    }
    return new TextDecoder().decode(merged)
  }
  return '{}'
}

function compatDebug(message: string): void {
  if (!isEnvTruthy(process.env.OPENAI_COMPAT_DEBUG)) return
  void writeToStderr(`[openai-compat] ${message}\n`)
}

function shouldSanitizeForArkLikeGateway(baseUrl: string): boolean {
  if (isEnvTruthy(process.env.OPENAI_COMPAT_MINIMAL_REQUEST)) return true
  if (isEnvTruthy(process.env.OPENAI_COMPAT_FULL_REQUEST)) return false
  try {
    const host = new URL(baseUrl).hostname.toLowerCase()
    return (
      host.includes('volces.com') ||
      host.includes('bytedance.net') ||
      host.includes('byteplus.com')
    )
  } catch {
    return false
  }
}

/**
 * Volcengine / ARK Responses API often rejects extra OpenAI fields (e.g. store,
 * parallel_tool_calls, strict:null on tools). Strip those when targeting ARK-like hosts.
 */
function sanitizeResponsesBodyForGateway(
  body: Record<string, unknown>,
  baseUrl: string,
): void {
  if (!shouldSanitizeForArkLikeGateway(baseUrl)) return
  delete body.store
  delete body.parallel_tool_calls
  const tools = body.tools
  if (!Array.isArray(tools)) return
  for (const raw of tools) {
    if (raw && typeof raw === 'object' && 'strict' in raw) {
      const t = raw as Record<string, unknown>
      if (t.strict === null || t.strict === undefined) {
        delete t.strict
      }
    }
  }
}

export type OpenAICompatFetchConfig = {
  apiKey: string
  /** e.g. https://ark-cn-beijing.bytedance.net/api/v3 */
  baseUrl: string
  /**
   * Path appended to baseUrl for Responses API POST.
   * Default "/responses" → full URL .../api/v3/responses
   */
  responsesPath?: string
}

function joinBaseAndPath(baseUrl: string, responsesPath: string): string {
  const base = baseUrl.replace(/\/$/, '')
  const path = responsesPath.startsWith('/') ? responsesPath : `/${responsesPath}`
  return `${base}${path}`
}

/**
 * Creates a fetch that proxies Anthropic Messages requests to an OpenAI-compatible
 * Responses API (streaming SSE), then re-encodes the stream as Anthropic SSE.
 */
export function createOpenAICompatFetch(
  config: OpenAICompatFetchConfig,
): (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> {
  const responsesUrl = joinBaseAndPath(
    config.baseUrl,
    config.responsesPath ?? '/responses',
  )

  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = input instanceof Request ? input.url : String(input)

    if (!url.includes('/v1/messages')) {
      return globalThis.fetch(input, init)
    }

    let anthropicBody: Record<string, unknown>
    try {
      const bodyText = await readRequestInitBodyAsText(init?.body)
      compatDebug(
        `intercept POST messages bodyLen=${bodyText.length} preview=${bodyText.slice(0, 120)}`,
      )
      anthropicBody = JSON.parse(bodyText) as Record<string, unknown>
    } catch (e) {
      compatDebug(`failed to parse anthropic body: ${String(e)}`)
      anthropicBody = {}
    }

    const { codexBody, codexModel } = translateToCodexBody(anthropicBody, {
      mapModel: m => m,
    })
    sanitizeResponsesBodyForGateway(codexBody, config.baseUrl)

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(process.env.OPENAI_COMPAT_AUTHORIZATION?.trim()
        ? {
            Authorization: process.env.OPENAI_COMPAT_AUTHORIZATION.trim(),
          }
        : { Authorization: `Bearer ${config.apiKey}` }),
    }

    const betaHeader = process.env.OPENAI_COMPAT_OPENAI_BETA?.trim()
    if (betaHeader) {
      headers['OpenAI-Beta'] = betaHeader
    }

    compatDebug(`POST ${responsesUrl} model=${String(codexBody.model ?? '')}`)

    const codexResponse = await globalThis.fetch(responsesUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(codexBody),
    })

    if (!codexResponse.ok) {
      const errorText = await codexResponse.text()
      compatDebug(`error ${codexResponse.status} body=${errorText.slice(0, 800)}`)
      const errorBody = {
        type: 'error',
        error: {
          type: 'api_error',
          message: `OpenAI-compatible API error (${codexResponse.status}): ${errorText}`,
        },
      }
      return new Response(JSON.stringify(errorBody), {
        status: codexResponse.status,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    return translateCodexStreamToAnthropic(codexResponse, codexModel)
  }
}

export function getOpenAICompatApiKey(): string | undefined {
  return (
    process.env.OPENAI_COMPAT_API_KEY?.trim() ||
    process.env.ARK_API_KEY?.trim() ||
    process.env.OPENAI_API_KEY?.trim() ||
    undefined
  )
}

export function getOpenAICompatBaseUrl(): string | undefined {
  const u =
    process.env.OPENAI_COMPAT_BASE_URL?.trim() ||
    process.env.OPENAI_BASE_URL?.trim() ||
    undefined
  return u || undefined
}
