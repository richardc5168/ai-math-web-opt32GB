/**
 * Stripe Webhook + Checkout Session — Firebase Cloud Functions
 *
 * 部署步驟：
 *   1. cd functions && npm install
 *   2. 在 .env 或 Firebase Console 設定：
 *      - STRIPE_SECRET_KEY=sk_live_...
 *      - STRIPE_WEBHOOK_SECRET=whsec_...
 *   3. firebase deploy --only functions
 *   4. 在 Stripe Dashboard 設定 webhook endpoint:
 *      https://your-region-your-project.cloudfunctions.net/stripeWebhook
 *      Events: checkout.session.completed, customer.subscription.updated,
 *              customer.subscription.deleted
 *   5. 把 Cloud Function URL 填入 docs/shared/payment_provider.js 的 CHECKOUT_API_URL
 *
 * 安全：
 *   - Stripe secret key 只存在 server side (Cloud Function env)
 *   - Webhook 用 stripe.webhooks.constructEvent 做簽名驗證
 *   - CORS 只允許你的 GitHub Pages domain
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();
const db = admin.firestore();

// Stripe SDK — lazy init
let stripe;
function getStripe() {
  if (!stripe) {
    const key = process.env.STRIPE_SECRET_KEY || functions.config().stripe?.secret_key;
    if (!key) throw new Error('STRIPE_SECRET_KEY not configured');
    stripe = require('stripe')(key);
  }
  return stripe;
}

const WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET || '';

// Allowed origins for CORS
const ALLOWED_ORIGINS = [
  'https://richardc5168.github.io',
  'http://localhost:8000',
  'http://127.0.0.1:8000'
];

function setCors(req, res) {
  const origin = req.headers.origin || '';
  if (ALLOWED_ORIGINS.includes(origin)) {
    res.set('Access-Control-Allow-Origin', origin);
  }
  res.set('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
}

/**
 * createCheckoutSession — 前端呼叫此 API 建立 Stripe Checkout Session
 *
 * POST body: { price_id, customer_uid, customer_email, plan_type, billing_period, success_url, cancel_url }
 * Response: { sessionId }
 */
exports.createCheckoutSession = functions.https.onRequest(async (req, res) => {
  setCors(req, res);
  if (req.method === 'OPTIONS') { res.status(204).send(''); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

  try {
    const { price_id, customer_uid, customer_email, plan_type, billing_period, success_url, cancel_url } = req.body;

    if (!price_id) { res.status(400).json({ error: 'price_id required' }); return; }

    const s = getStripe();
    const sessionParams = {
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: price_id, quantity: 1 }],
      success_url: success_url || 'https://richardc5168.github.io/ai-math-web/docs/pricing/?checkout=success',
      cancel_url: cancel_url || 'https://richardc5168.github.io/ai-math-web/docs/pricing/?checkout=cancel',
      metadata: {
        customer_uid: customer_uid || '',
        plan_type: plan_type || 'standard',
        billing_period: billing_period || 'monthly'
      }
    };

    if (customer_email) {
      sessionParams.customer_email = customer_email;
    }

    const session = await s.checkout.sessions.create(sessionParams);
    res.json({ sessionId: session.id });

  } catch (err) {
    console.error('createCheckoutSession error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * stripeWebhook — Stripe 事件回調
 *
 * 處理事件：
 *   - checkout.session.completed → 開通訂閱
 *   - customer.subscription.updated → 更新狀態
 *   - customer.subscription.deleted → 取消訂閱
 */
exports.stripeWebhook = functions.https.onRequest(async (req, res) => {
  if (req.method !== 'POST') { res.status(405).send(''); return; }

  const sig = req.headers['stripe-signature'];
  let event;

  try {
    const s = getStripe();

    if (WEBHOOK_SECRET) {
      // Verify webhook signature
      event = s.webhooks.constructEvent(req.rawBody, sig, WEBHOOK_SECRET);
    } else {
      // Dev mode — no signature verification (NOT for production)
      event = req.body;
      console.warn('⚠️ Webhook signature verification disabled — set STRIPE_WEBHOOK_SECRET');
    }
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    res.status(400).send('Webhook Error: ' + err.message);
    return;
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const uid = session.metadata?.customer_uid;
        if (uid) {
          await db.collection('subscriptions').doc(uid).set({
            plan_type: session.metadata?.plan_type || 'standard',
            plan_status: 'paid_active',
            stripe_customer_id: session.customer,
            stripe_subscription_id: session.subscription,
            paid_start: new Date().toISOString(),
            expire_at: null, // Stripe manages renewal
            updated_at: new Date().toISOString()
          }, { merge: true });
          console.log(`✅ Subscription activated for ${uid}`);
        }
        break;
      }

      case 'customer.subscription.updated': {
        const sub = event.data.object;
        const customerRef = await db.collection('subscriptions')
          .where('stripe_subscription_id', '==', sub.id)
          .limit(1)
          .get();

        if (!customerRef.empty) {
          const doc = customerRef.docs[0];
          const status = sub.status === 'active' ? 'paid_active'
            : sub.status === 'trialing' ? 'trial'
            : sub.status === 'past_due' ? 'expired'
            : 'expired';
          await doc.ref.update({
            plan_status: status,
            updated_at: new Date().toISOString()
          });
          console.log(`🔄 Subscription updated: ${doc.id} → ${status}`);
        }
        break;
      }

      case 'customer.subscription.deleted': {
        const sub = event.data.object;
        const customerRef = await db.collection('subscriptions')
          .where('stripe_subscription_id', '==', sub.id)
          .limit(1)
          .get();

        if (!customerRef.empty) {
          const doc = customerRef.docs[0];
          await doc.ref.update({
            plan_status: 'expired',
            updated_at: new Date().toISOString()
          });
          console.log(`❌ Subscription cancelled: ${doc.id}`);
        }
        break;
      }

      default:
        console.log(`ℹ️ Unhandled event type: ${event.type}`);
    }

    res.json({ received: true });

  } catch (err) {
    console.error('Webhook processing error:', err);
    res.status(500).json({ error: 'Processing failed' });
  }
});
