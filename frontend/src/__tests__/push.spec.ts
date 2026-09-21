import { describe, expect, it } from 'vitest'
import { urlBase64ToUint8Array } from '../push'

describe('urlBase64ToUint8Array', () => {
  it('decodes a base64url string without padding', () => {
    // "Hello" is SGVsbG8 in base64url, which needs one '=' of padding added back.
    expect(Array.from(urlBase64ToUint8Array('SGVsbG8'))).toEqual([72, 101, 108, 108, 111])
  })

  it('translates the url-safe alphabet', () => {
    // 0xFB 0xFF decodes from "-_8" only if - and _ map to + and /.
    expect(Array.from(urlBase64ToUint8Array('-_8'))).toEqual([251, 255])
  })

  it('produces the 65 bytes of a real VAPID key', () => {
    const key =
      'BDqLMr7iwfPD5q5fZacIlJvPwlBLA-ojvGD_hc-nCBUKlIiIOHL3Dr0V4ydzfg9te0L6J1bWB_yOvXxc0-br970'
    const bytes = urlBase64ToUint8Array(key)
    expect(bytes).toHaveLength(65)
    expect(bytes[0]).toBe(4) // uncompressed EC point marker
  })
})
