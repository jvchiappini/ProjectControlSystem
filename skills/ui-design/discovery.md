<!-- generated from .control/prompts/ui-discovery.md by `update.py --build-manifest` -->

# UI discovery: archetypes and question bank

Loaded by `skills/ui-design.md` phase 2. Use the playbook to reason about
what the product needs, then ask only the questions the repository could
not answer. Every question carries the inferred default.

## Archetype playbooks

Each playbook lists sub-types (they change the design), must-haves
(missing ones go into the plan), and what makes it feel premium.

### Online store

- Sub-types and their character:
  - Fashion / apparel: image-led, editorial layouts, size guides, fit
    notes, model info, lookbooks.
  - Electronics / tech: spec tables, comparison, compatibility, warranty,
    reviews with detail, dense but clean.
  - Grocery / food: fast reorder, quantity steppers, delivery slots,
    dietary filters, substitutions.
  - Beauty / cosmetics: shade pickers, ingredients, routines, before/after.
  - Handmade / artisan: maker story, process photos, warmth, limited
    stock honesty.
  - Luxury: restraint, large imagery, slow reveal, very few elements.
  - Digital goods / courses / software: previews, license tiers, instant
    delivery, what's included.
  - Home / furniture: dimensions, materials, room views, swatches,
    delivery and assembly info.
  - Single-product / DTC: one long persuasive page, story, social proof.
- Must-haves: home with clear value and categories; search with
  suggestions; product listing with filters, sort and good empty result;
  product page with gallery (zoom), variants, price and stock, delivery
  and returns info near the buy button, reviews; cart (drawer or page)
  with editable quantities and totals; checkout with progress, guest
  option, address and payment, order summary; confirmation; account and
  order history; wishlist; trust signals (secure payment, returns
  policy, contact); footer with policies; 404 and error states.
- Premium signals: photography consistency, fast filters, sticky add to
  cart on mobile, honest stock and delivery dates, microinteraction on
  add to cart, thoughtful empty cart.

### SaaS / product landing

- Must-haves: hero that names the job done for whom; product visuals
  (real UI, not abstract blobs); how it works; use cases or audiences;
  proof (logos, case studies, quotes with names); pricing with a
  recommended plan and FAQ; security/compliance if B2B; clear sign-up.
- Premium signals: specific copy, real screenshots, varied section
  composition, one memorable visual idea.

### Dashboard / internal tool / admin

- Navigation (sidebar is the backbone): user/workspace switcher at the
  top of the sidebar or in the top bar, with avatar and a clear menu;
  links grouped by how often they are used in daily work; secondary items
  (settings, help) pinned at the bottom; obvious active state;
  collapsible to icons with tooltips; live count badges where something
  waits for the user.
- Density and hierarchy: unlike landing pages, a compact type scale,
  precise spacing and a strict grid that uses the screen; what matters
  most (key metrics, primary actions, current status) in the first
  viewport.
- Lists and tables: separation by space or subtle lines, not boxes;
  search, filter and sort built in; multi-select with bulk actions;
  sticky header, pagination or virtualization for long data; row click
  opens detail (drawer for a quick look, page for a deep one).
- Must-haves: a home that answers "what needs my attention"; detail
  views with breadcrumbs; forms with validation; global toasts; empty,
  loading (skeletons), error and permission states; consistent number
  and date formats.
- Premium signals: density with clarity, optimistic updates, keyboard
  shortcuts and a command palette, useful defaults, charts that answer a
  question. References: Linear, Vercel, Raycast, Stripe dashboard.

### Portfolio / personal / agency

- Must-haves: who and what in one glance; selected work with context
  (problem, role, result); about; contact.
- Premium signals: a strong personal visual idea, curated not
  exhaustive, case study storytelling.

### Editorial / blog / media

- Must-haves: readable article template (measure, rhythm, images,
  captions); index with hierarchy; categories/tags; author; related
  content; newsletter.
- Premium signals: typography first, art direction per story.

### Local business (restaurant, clinic, studio, gym)

- Must-haves: what, where, when (hours, map, address) above the fold on
  mobile; booking or order action; menu/services with prices; photos;
  reviews; contact.
- Premium signals: atmosphere through photography and type, one-tap
  actions (call, directions, book).

### Docs / developer portal

- Must-haves: search, navigation tree, copyable code, versioning,
  getting-started path, API reference layout.

### Mobile app UI

- Must-haves: platform conventions (navigation pattern, gestures, safe
  areas), onboarding, empty states, offline and permission states.

For other archetypes, build the same three lists by analogy before asking.

## Question bank

Pick at most 8 for round 1, highest design impact first. Rewrite each as
"I assume X because Y; correct?" when there is a basis for a default.

### Audience and goal
- Who is the main customer (age, context, expertise, device)?
- What is the one action that defines success (buy, sign up, book, contact)?
- Why do they choose this over alternatives (price, quality, story, speed)?

### Brand and personality
- Three adjectives the interface must feel like, and three it must never
  feel like? (offer sets, e.g. calm/premium/editorial,
  bold/young/energetic, warm/handmade/honest)
- Existing brand assets: logo, colors, fonts, guidelines?
- Two or three sites or apps you love the look of, and one you dislike?
- Light, dark, or both?

### Content reality
- Are there real photos (and of what quality), or do we need placeholders
  and an art direction for future shoots?
- Who writes the copy; is there a tone of voice?
- How many items/pages roughly (10 products vs 10,000 changes the UI)?

### Scope and constraints
- Which pages/features are in this version, which later?
- Languages, currencies, regions?
- Accessibility target (WCAG AA by default)?
- Performance or device constraints (low-end phones, slow networks)?
- Stack constraints: keep the current component library or free to choose?

### Store-specific
- What exactly is sold, and what is the price range?
- Variants (size, color, material), and is there a size or fit guide?
- Shipping zones, delivery times, returns policy to display?
- Payment methods; guest checkout allowed?
- Reviews, wishlist, accounts, discounts or gift cards?
- Who are the 2-3 competitors, and how should we look different?
