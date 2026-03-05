/**
 * Cloudflare Worker — ramsrinivasan.in API
 * Routes:
 *   GET    /api/blogs              → all published blogs ordered by sort_order (public)
 *   GET    /api/blogs/:slug        → single blog by slug (public)
 *   POST   /api/blogs              → create blog (admin only)
 *   PUT    /api/blogs/:id          → update blog (admin only)
 *   DELETE /api/blogs/:id          → delete blog (admin only)
 *   GET    /api/admin/blogs        → all blogs inc drafts (admin only)
 *   PUT    /api/admin/blogs/reorder → bulk update sort_order (admin only)
 *   POST   /api/messages           → submit contact/subscribe message (public)
 *   GET    /api/admin/messages     → all messages (admin only)
 *   PUT    /api/admin/messages/:id → mark read (admin only)
 *   DELETE /api/admin/messages/:id → delete message (admin only)
 *   POST   /api/auth/login         → login → returns token
 *
 * GA4: G-ZH170NH9GW is stored as ga_id on every post (default).
 * The blog post page reads post.ga_id and injects the gtag script automatically.
 */

const CORS_ORIGIN  = 'https://ramsrinivasan.github.io';
const DEFAULT_GA   = 'G-ZH170NH9GW';

function cors(origin) {
  return {
    'Access-Control-Allow-Origin':  origin || CORS_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age':       '86400',
  };
}
function json(data, status = 200, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors(origin) },
  });
}
function err(msg, status = 400, origin) {
  return json({ error: msg }, status, origin);
}

// ── JWT (HMAC-SHA256) ─────────────────────────────────────────────────────
async function signToken(payload, secret) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const data  = btoa(JSON.stringify(payload));
  const sig   = await crypto.subtle.sign('HMAC', key, enc.encode(data));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return `${data}.${sigB64}`;
}

async function verifyToken(token, secret) {
  try {
    const [data, sigB64] = token.split('.');
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']
    );
    const sig   = Uint8Array.from(atob(sigB64), c => c.charCodeAt(0));
    const valid = await crypto.subtle.verify('HMAC', key, sig, enc.encode(data));
    if (!valid) return null;
    const payload = JSON.parse(atob(data));
    if (payload.exp && Date.now() > payload.exp) return null;
    return payload;
  } catch { return null; }
}

async function requireAuth(request, env) {
  const auth  = request.headers.get('Authorization') || '';
  const token = auth.replace('Bearer ', '').trim();
  if (!token) return null;
  return await verifyToken(token, env.JWT_SECRET);
}

// ── Helpers ───────────────────────────────────────────────────────────────
function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function makeSlug(t) {
  return t.toLowerCase().trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function dbToPost(row) {
  return {
    id:           row.id,
    title:        row.title,
    slug:         row.slug,
    description:  row.description,
    content:      row.content,
    tags:         JSON.parse(row.tags || '[]'),
    featuredImage: row.featured_image,
    status:       row.status,
    publishDate:  row.publish_date,
    createdAt:    row.created_at,
    updatedAt:    row.updated_at,
    customUrl:    row.custom_url,
    sortOrder:    row.sort_order ?? 0,
    // GA is always set — default is G-ZH170NH9GW
    gaId:         row.ga_id || DEFAULT_GA,
  };
}

// ── ROUTER ────────────────────────────────────────────────────────────────
export default {
  async fetch(request, env) {
    const url    = new URL(request.url);
    const path   = url.pathname;
    const method = request.method;
    const origin = request.headers.get('Origin') || CORS_ORIGIN;

    // Preflight
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    // ── AUTH ─────────────────────────────────────────────────────────────
    if (method === 'POST' && path === '/api/auth/login') {
      const body = await request.json().catch(() => ({}));
      if (body.email === env.ADMIN_EMAIL && body.password === env.ADMIN_PASSWORD) {
        const token = await signToken(
          { email: body.email, exp: Date.now() + 7 * 86400000 },
          env.JWT_SECRET
        );
        return json({ token }, 200, origin);
      }
      return err('Invalid credentials', 401, origin);
    }

    // ── PUBLIC: GET all published blogs ──────────────────────────────────
    // Order: sort_order ASC (0 = top), then publish_date DESC as tiebreaker
    if (method === 'GET' && path === '/api/blogs') {
      const { results } = await env.DB.prepare(
        `SELECT * FROM blogs
         WHERE status = 'published'
         ORDER BY
           CASE WHEN sort_order = 0 THEN 1 ELSE 0 END,
           sort_order ASC,
           publish_date DESC,
           created_at DESC`
      ).all();
      return json(results.map(dbToPost), 200, origin);
    }

    // ── PUBLIC: GET single blog by slug ──────────────────────────────────
    const slugMatch = path.match(/^\/api\/blogs\/([^/]+)$/);
    if (method === 'GET' && slugMatch) {
      const slug = decodeURIComponent(slugMatch[1]);
      const post = await env.DB.prepare(
        `SELECT * FROM blogs WHERE slug = ? AND status = 'published'`
      ).bind(slug).first();
      if (!post) return err('Not found', 404, origin);
      return json(dbToPost(post), 200, origin);
    }

    // ── PUBLIC: POST message ──────────────────────────────────────────────
    if (method === 'POST' && path === '/api/messages') {
      const body = await request.json().catch(() => ({}));
      const { name, email, message, type } = body;
      if (!name || !email) return err('Name and email required', 400, origin);
      const id = uid();
      await env.DB.prepare(
        `INSERT INTO messages (id, name, email, message, type, status, created_at)
         VALUES (?, ?, ?, ?, ?, 'unread', ?)`
      ).bind(id, name, email, message || '', type || 'contact', new Date().toISOString()).run();
      return json({ ok: true, id }, 201, origin);
    }

    // ── ADMIN ROUTES (require auth) ───────────────────────────────────────
    const user = await requireAuth(request, env);
    if (!user) return err('Unauthorized', 401, origin);

    // GET all blogs for admin (inc drafts), ordered by sort_order
    if (method === 'GET' && path === '/api/admin/blogs') {
      const { results } = await env.DB.prepare(
        `SELECT * FROM blogs
         ORDER BY
           CASE WHEN sort_order = 0 THEN 1 ELSE 0 END,
           sort_order ASC,
           created_at DESC`
      ).all();
      return json(results.map(dbToPost), 200, origin);
    }

    // PUT /api/admin/blogs/reorder — bulk update sort_order
    // Body: [{ id: "xxx", sortOrder: 1 }, { id: "yyy", sortOrder: 2 }, ...]
    if (method === 'PUT' && path === '/api/admin/blogs/reorder') {
      const body = await request.json().catch(() => ([]));
      if (!Array.isArray(body)) return err('Expected array', 400, origin);
      // Use a batch of updates
      const stmts = body.map(item =>
        env.DB.prepare(`UPDATE blogs SET sort_order = ? WHERE id = ?`)
          .bind(item.sortOrder, item.id)
      );
      await env.DB.batch(stmts);
      return json({ ok: true, updated: body.length }, 200, origin);
    }

    // POST create blog
    if (method === 'POST' && path === '/api/blogs') {
      const body = await request.json().catch(() => ({}));
      if (!body.title || !body.content) return err('Title and content required', 400, origin);
      const id   = uid();
      const slug = body.slug || makeSlug(body.title);
      const now  = new Date().toISOString();

      // Auto sort_order: put new posts at the bottom (max + 1)
      const maxRow = await env.DB.prepare(
        `SELECT MAX(sort_order) as mx FROM blogs`
      ).first();
      const nextOrder = ((maxRow?.mx) || 0) + 1;

      await env.DB.prepare(
        `INSERT INTO blogs
           (id, title, slug, description, content, tags, featured_image,
            status, publish_date, created_at, updated_at, custom_url, sort_order, ga_id)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).bind(
        id, body.title, slug,
        body.description || '',
        body.content,
        JSON.stringify(body.tags || []),
        body.featuredImage || '',
        body.status || 'draft',
        body.status === 'published' ? (body.publishDate || now) : null,
        now, now,
        body.customUrl || '',
        nextOrder,
        DEFAULT_GA   // GA always defaults to G-ZH170NH9GW
      ).run();
      return json({ ok: true, id, slug }, 201, origin);
    }

    // PUT update blog
    const blogIdMatch = path.match(/^\/api\/blogs\/([^/]+)$/);
    if (method === 'PUT' && blogIdMatch) {
      const id       = blogIdMatch[1];
      const body     = await request.json().catch(() => ({}));
      const existing = await env.DB.prepare(`SELECT * FROM blogs WHERE id = ?`).bind(id).first();
      if (!existing) return err('Not found', 404, origin);
      const now = new Date().toISOString();
      await env.DB.prepare(
        `UPDATE blogs
         SET title=?, slug=?, description=?, content=?, tags=?,
             featured_image=?, status=?, publish_date=?, updated_at=?,
             custom_url=?, sort_order=?, ga_id=?
         WHERE id=?`
      ).bind(
        body.title            || existing.title,
        body.slug             || existing.slug,
        body.description      ?? existing.description,
        body.content          ?? existing.content,
        JSON.stringify(body.tags || JSON.parse(existing.tags || '[]')),
        body.featuredImage    ?? existing.featured_image,
        body.status           || existing.status,
        body.status === 'published'
          ? (body.publishDate || existing.publish_date || now)
          : existing.publish_date,
        now,
        body.customUrl        ?? existing.custom_url,
        body.sortOrder        ?? existing.sort_order ?? 0,
        existing.ga_id        || DEFAULT_GA,   // GA never changes — always default
        id
      ).run();
      return json({ ok: true }, 200, origin);
    }

    // DELETE blog
    if (method === 'DELETE' && blogIdMatch) {
      const id = blogIdMatch[1];
      await env.DB.prepare(`DELETE FROM blogs WHERE id = ?`).bind(id).run();
      return json({ ok: true }, 200, origin);
    }

    // GET all messages for admin
    if (method === 'GET' && path === '/api/admin/messages') {
      const { results } = await env.DB.prepare(
        `SELECT * FROM messages ORDER BY created_at DESC`
      ).all();
      return json(results, 200, origin);
    }

    // PUT mark message read
    const msgMatch = path.match(/^\/api\/admin\/messages\/([^/]+)$/);
    if (method === 'PUT' && msgMatch) {
      const id = msgMatch[1];
      await env.DB.prepare(`UPDATE messages SET status='read' WHERE id=?`).bind(id).run();
      return json({ ok: true }, 200, origin);
    }

    // DELETE message
    if (method === 'DELETE' && msgMatch) {
      const id = msgMatch[1];
      await env.DB.prepare(`DELETE FROM messages WHERE id=?`).bind(id).run();
      return json({ ok: true }, 200, origin);
    }

    return err('Not found', 404, origin);
  }
};
