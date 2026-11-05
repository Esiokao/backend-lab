<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'

  import Icon from '@/components/Icon.vue'
  import StorefrontHeader from '@/components/StorefrontHeader.vue'
  import StorefrontFooter from '@/components/StorefrontFooter.vue'
  import { ApiError, api } from '@/lib/api'
  import { FollowedSchema, type Product } from '@/lib/schemas'
  import { useAuth } from '@/stores/auth'
  import { useCart } from '@/stores/cart'
  import { useFollows } from '@/stores/follows'
  import { useToast } from '@/stores/toast'

  // 購物車（v1.8）：勾選式 —— 單選/全選，只結帳選中品；
  // Checkout → /checkout 付款頁（明細 → 付款 → 結果頁）。

  const router = useRouter()
  const toast = useToast()
  const { user } = useAuth()
  const {
    items,
    busy,
    isSelected,
    isSelectable,
    selectedItems,
    selectedCount,
    selectedTotal,
    allSelected,
    toggleSelect,
    toggleAll,
    refresh,
    updateQty,
    remove,
    clear,
    add: addToCart
  } = useCart()

  const loading = ref(true)

  function formatPrice(price: string | number): string {
    return `$${Number(price).toFixed(2)}`
  }

  async function setQty(
    productId: number,
    name: string,
    quantity: number,
    stock?: number
  ): Promise<void> {
    if (quantity < 1) return // 移除請用 ×
    if (quantity > 100) {
      toast.show('Quantity cannot exceed 100.')
      return
    }
    if (stock !== undefined && quantity > stock) {
      toast.show(
        stock === 0
          ? `"${name}" is out of stock.`
          : `Only ${stock} of "${name}" in stock.`
      )
      return
    }
    try {
      await updateQty(productId, quantity)
    } catch (err) {
      toast.show(
        err instanceof ApiError
          ? `Update failed: ${err.message}`
          : 'Update failed.'
      )
    }
  }

  // 內部自行讀 store 現值：模板傳來的 item.quantity 是渲染快照，
  // 連按快過 re-render 會讀到重複的舊值（浪費遞增）。
  async function step(productId: number, delta: number): Promise<void> {
    const item = items.value.find((i) => i.product_id === productId)
    if (!item) return
    await setQty(
      productId,
      item.product_name,
      item.quantity + delta,
      item.stock
    )
  }

  async function onQtyInput(
    productId: number,
    name: string,
    current: number,
    stock: number,
    event: Event
  ): Promise<void> {
    const value = Number((event.target as HTMLInputElement).value)
    if (
      Number.isInteger(value) &&
      value >= 1 &&
      value <= 100 &&
      value !== current
    ) {
      await setQty(productId, name, value, stock)
    }
    // 還原輸入框（re-render 由 store 狀態驅動）。
    ;(event.target as HTMLInputElement).value = String(current)
  }

  async function removeItem(productId: number, name: string): Promise<void> {
    try {
      await remove(productId)
      toast.show(`Removed "${name}".`)
    } catch (err) {
      toast.show(
        err instanceof ApiError
          ? `Remove failed: ${err.message}`
          : 'Remove failed.'
      )
    }
  }

  async function clearCart(): Promise<void> {
    if (!window.confirm('Clear all items from your cart?')) return
    try {
      await clear()
      toast.show('Cart cleared.')
    } catch (err) {
      toast.show(
        err instanceof ApiError
          ? `Clear failed: ${err.message}`
          : 'Clear failed.'
      )
    }
  }

  // 帶著選中品去結帳：無選擇時按鈕已 disabled，這裡是防禦。
  function goCheckout(): void {
    if (selectedItems().length === 0) {
      toast.show('Select at least one item to checkout.')
      return
    }
    void router.push({ name: 'checkout' })
  }

  // ── Followed products（購物車裡的收藏快區）：讓 shopper 直接發現收藏的
  // 商品、補齊下單動線。固定只露 4 個 in stock（全量列表在 /app/following）。
  const { load: loadFollows } = useFollows()
  const followedProducts = ref<Product[]>([])
  const FOLLOWED_LIMIT = 4

  // Cart 的收藏快區只顯示 in stock——out of stock 的留在 /app/following 等補貨通知。
  const followedPreview = computed(() =>
    followedProducts.value.filter((p) => p.stock > 0).slice(0, FOLLOWED_LIMIT),
  )

  // 收藏快區的一鍵加購（數量 1 + toast 回饋）。
  async function quickAdd(product: Product): Promise<void> {
    await addToCart(product.id, 1)
    toast.show(`Added "${product.name}" to cart.`)
  }

  async function loadFollowedProducts(): Promise<void> {
    if (!user.value) return
    try {
      const data = await api.get('/products/followed', FollowedSchema)
      followedProducts.value = data.items
    } catch (err) {
      // 收藏區是加值內容，失敗不擋購物車主流程——但要留痕跡（silent catch 曾把 bug 藏死）。
      console.warn('[cart] failed to load followed products:', err)
    }
  }

  onMounted(async () => {
    if (user.value) {
      await refresh()
      void loadFollows()
      void loadFollowedProducts()
    }
    loading.value = false
  })
</script>

<template>
  <StorefrontHeader />

  <main class="storefront-main">
    <section class="page-heading">
      <div class="th-main">
        <h1>Cart</h1>
        <p>Select items, then checkout to place the order.</p>
      </div>
      <router-link
        :to="{ name: 'storefront' }"
        class="text-button"
      >
        <Icon
          name="arrow"
          :size="15"
        />
        Continue shopping
      </router-link>
      <div class="th-cell"><small>Sheet</small><b>CART-01</b></div>
    </section>

    <p
      v-if="loading"
      class="empty-state"
    >
      Loading cart...
    </p>

    <!-- 訪客：車屬於登入者，引導登入後回此頁 -->
    <section
      v-else-if="!user"
      class="data-panel"
    >
      <div class="panel-header">
        <div>
          <h2>Your cart is waiting</h2>
          <p>
            Carts are saved to your account — sign in to pick up where you left
            off.
          </p>
        </div>
      </div>
      <div class="cart-empty-actions">
        <router-link
          class="primary-button"
          :to="{ name: 'login', query: { redirect: '/cart' } }"
        >
          Sign in to view your cart
        </router-link>
      </div>
    </section>

    <template v-else-if="items.length > 0">
      <section class="data-panel">
        <div class="panel-header">
          <div>
            <h2>Items</h2>
            <p>
              {{ items.length }} product{{ items.length === 1 ? '' : 's' }} in
              your cart.
            </p>
          </div>
          <button
            type="button"
            class="ghost-button"
            :disabled="busy"
            @click="clearCart"
          >
            Clear cart
          </button>
        </div>
        <div class="table-scroll">
          <table class="cart-table">
            <thead>
              <tr>
                <th class="check-col">
                  <input
                    type="checkbox"
                    :checked="allSelected()"
                    aria-label="Select all items"
                    @change="toggleAll"
                  />
                </th>
                <th>Product</th>
                <th>Unit price</th>
                <th>Stock</th>
                <th>Qty</th>
                <th>Subtotal</th>
                <th><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="item.product_id"
                :class="{
                  dimmed: !isSelected(item.product_id),
                  blocked: !isSelectable(item)
                }"
              >
                <td class="check-col">
                  <input
                    type="checkbox"
                    :checked="isSelected(item.product_id)"
                    :disabled="!isSelectable(item)"
                    :aria-label="`Select ${item.product_name}`"
                    :title="
                      isSelectable(item)
                        ? undefined
                        : item.stock <= 0
                          ? 'Out of stock'
                          : `Only ${item.stock} in stock`
                    "
                    @change="toggleSelect(item.product_id)"
                  />
                </td>
                <td class="cart-product">
                  <div class="cart-product-info">
                    <img
                      v-if="item.image_url"
                      :src="item.image_url"
                      :alt="item.product_name"
                      class="cart-thumb"
                    >
                    <strong>{{ item.product_name }}</strong>
                  </div>
                  <p
                    v-if="!isSelectable(item) && item.stock > 0"
                    class="field-error"
                  >
                    Only {{ item.stock }} in stock — reduce quantity to select.
                  </p>
                  <p
                    v-else-if="item.stock <= 0"
                    class="field-error"
                  >
                    Out of stock — follow it in the storefront for a restock
                    alert.
                  </p>
                </td>
                <td class="cart-price">
                  <span class="order-total">{{
                    formatPrice(item.unit_price)
                  }}</span>
                </td>
                <td class="cart-stock">
                  <span :class="['stock-badge', item.stock > 0 ? 'in' : 'out']">
                    {{
                      item.stock > 0
                        ? `In stock · ${item.stock}`
                        : 'Out of stock'
                    }}
                  </span>
                </td>
                <td class="cart-qty">
                  <div class="qty-stepper">
                    <button
                      type="button"
                      :aria-label="`Decrease ${item.product_name}`"
                      :disabled="item.quantity <= 1"
                      @click="step(item.product_id, -1)"
                    >
                      −
                    </button>
                    <input
                      type="number"
                      min="1"
                      :max="Math.min(item.stock, 100)"
                      :value="item.quantity"
                      :aria-label="`${item.product_name} quantity`"
                      @change="
                        onQtyInput(
                          item.product_id,
                          item.product_name,
                          item.quantity,
                          item.stock,
                          $event
                        )
                      "
                    />
                    <button
                      type="button"
                      :aria-label="`Increase ${item.product_name}`"
                      @click="step(item.product_id, 1)"
                    >
                      +
                    </button>
                  </div>
                </td>
                <td class="cart-subtotal">
                  <span class="order-total">{{
                    formatPrice(item.subtotal)
                  }}</span>
                </td>
                <td class="cart-remove">
                  <button
                    type="button"
                    class="row-action row-delete"
                    :aria-label="`Remove ${item.product_name}`"
                    :disabled="busy"
                    @click="removeItem(item.product_id, item.product_name)"
                  >
                    <Icon
                      name="close"
                      :size="14"
                    />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

    <!-- 收藏快區：登入且有收藏時露出（上限 4 個），方便 shopper 發現並補下單。 -->
    <section
      v-if="user && followedPreview.length > 0"
      class="data-panel"
    >
      <div class="panel-header">
        <div>
          <h2>Following</h2>
          <p>Products you follow.</p>
        </div>
        <router-link
          :to="{ name: 'following' }"
          class="text-button"
        >
          See all ({{ followedProducts.length }})
          <Icon
            name="arrow"
            :size="13"
          />
        </router-link>
      </div>
      <ul class="followed-list">
        <li
          v-for="product in followedPreview"
          :key="product.id"
          class="followed-row"
        >
          <router-link
            class="followed-link"
            :to="{ name: 'product-detail', params: { id: product.id } }"
            :aria-label="`Open ${product.name}`"
          >
            <img
              v-if="product.image_url"
              :src="product.image_url"
              :alt="product.name"
              class="followed-thumb"
            >
            <span
              v-else
              class="followed-thumb followed-thumb-empty"
              aria-hidden="true"
            ></span>
            <span class="followed-name">
              <strong>{{ product.name }}</strong>
              <small>{{ product.description ?? '' }}</small>
            </span>
            <span class="followed-price">${{ Number(product.price).toFixed(2) }}</span>
            <span
              :class="['stock-badge', product.stock > 0 ? 'in' : 'out']"
            >
              {{ product.stock > 0 ? `In stock · ${product.stock}` : 'Out of stock' }}
            </span>
          </router-link>
          <button
            v-if="product.stock > 0"
            type="button"
            class="primary-button"
            :aria-label="`Add ${product.name} to cart`"
            @click="quickAdd(product)"
          >
            <Icon
              name="cart"
              :size="14"
            />
            Add to cart
          </button>
        </li>
      </ul>
    </section>
      <section class="data-panel cart-summary">
        <div class="panel-header">
          <div>
            <h2>Selected</h2>
            <p>
              {{ selectedCount() }} item{{
                selectedCount() === 1 ? '' : 's'
              }}
              selected · cart total {{ formatPrice(selectedTotal()) }}
            </p>
          </div>
          <span class="cart-total">{{ formatPrice(selectedTotal()) }}</span>
        </div>
        <div class="cart-summary-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="busy || selectedCount() === 0"
            @click="goCheckout"
          >
            <Icon
              name="store"
              :size="15"
            />
            Checkout ({{ selectedCount() }})
          </button>
        </div>
      </section>
    </template>

    <section
      v-else
      class="data-panel"
    >
      <div class="panel-header">
        <div>
          <h2>Your cart is empty</h2>
          <p>Browse the catalog and add something you like.</p>
        </div>
      </div>
      <div class="cart-empty-actions">
        <router-link
          :to="{ name: 'storefront' }"
          class="primary-button"
        >
          <Icon
            name="cart"
            :size="15"
          />
          Browse catalog
        </router-link>
      </div>
    </section>

  </main>

  <StorefrontFooter />
</template>
