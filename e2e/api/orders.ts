// API wrapper：造資料的語意化封裝。
// 原則：測試檔只說「我要一筆訂單」，不說「先查商品再 POST 之後檢查 200」——
// 這些步驟知識集中在一處，改契約時只改這裡。
import type { APIRequestContext } from '@playwright/test'

export type CreatedOrder = { id: number; user_id: number }

/** 用已登入的 client 下單。商品用種子名稱查詢（名字是契約，id 不是）。 */
export async function createOrder(
  shopper: APIRequestContext,
  productName = 'E2E Widget A'
): Promise<CreatedOrder> {
  const products = await (
    await shopper.get(`/api/products?q=${productName}`)
  ).json()

  if (products.length === 0) {
    throw new Error(
      `seeded product "${productName}" should exist (did setup run?)`
    )
  }

  const res = await shopper.post('/api/orders', {
    data: { items: [{ product_id: products[0].id, quantity: 1 }] }
  })

  const body = await res.text()
  if (res.status() !== 200) {
    throw new Error(`create order failed: ${res.status()} ${body}`)
  }

  const order = JSON.parse(body)
  return { id: order.id, user_id: order.user_id }
}

/** 付款：模擬付款（demo 端點），把訂單推進到 pending（已付款待出貨）。
 *  真實 UI 流程的終點是 pending 而非 created——造資料要貼近真實流程時用這個。 */
export async function payOrder(
  shopper: APIRequestContext,
  orderId: number
): Promise<void> {
  const res = await shopper.post(`/api/orders/${orderId}/pay`, {})
  const body = await res.text()
  if (res.status() !== 200) {
    throw new Error(`pay order failed: ${res.status()} ${body}`)
  }
}
