# Ship Tomorrow — 90-minute morning checklist

The code is ready. These are the things only you can do (account creation, paid services, or UI clicks). Total time: **~90 minutes**.

## 1. Stripe Payment Link — 15 min

1. Go to https://dashboard.stripe.com/payment-links/create
2. Create product:
   - **Name:** Meridian — Lifetime Pro Access
   - **Description:** Lifetime price-lock for the first 50 customers. When V1 ships, you keep Pro tier forever — daily digest, unlimited labs, paper-anchored outreach drafter, GitHub & affiliation signals. No subscription, no questions.
   - **Price:** $99 one-time
3. Click **Create payment link**
4. Copy the URL (looks like `https://buy.stripe.com/xxx`)
5. Paste it into `docs/index.html` — search for `REPLACE_WITH_YOUR_PAYMENT_LINK` and replace
6. Push: `git add docs/index.html && git commit -m "Add Stripe payment link" && git push`

## 2. Email capture (Tally — easiest, free) — 10 min

1. Go to https://tally.so → sign up (no credit card)
2. Create new form, single email field, label: "Get the daily digest"
3. After save, click **Share** → copy the embed code (looks like `<iframe src="https://tally.so/...">`)
4. Open `docs/index.html`, find the `<form action="https://formspree.io/f/REPLACE_ME"...>` block
5. Replace the entire `<form>...</form>` with your Tally `<iframe>`
6. Push.

(Alternative: real Formspree account at https://formspree.io — same flow, replace `REPLACE_ME` with your form ID.)

## 3. Custom domain — 30 min

1. Go to https://dash.cloudflare.com/?to=/:account/domains/register
2. Search `meridian.so` (or `meridian.app`, `meridian.dev`, `getmeridian.com`)
3. Buy the cheapest available (~$9–15/yr at-cost on Cloudflare)
4. Once registered, in Cloudflare DNS for that domain, add:
   ```
   Type: CNAME    Name: @    Target: altanapps.github.io    Proxied: ON
   Type: CNAME    Name: www  Target: altanapps.github.io    Proxied: ON
   ```
5. In your repo Settings → Pages → Custom domain, enter `meridian.so` (or whatever you bought). HTTPS gets re-issued automatically.
6. Update README.md and `docs/index.html` to point to the new domain.

## 4. Pin the repo — 1 min

1. Go to https://github.com/altanapps
2. Click "Customize your pins" near the top
3. Check the box for `frontier-scout`
4. Save

## 5. Deploy the Flask dashboard (optional but big) — 30 min

If you want strangers to actually use the dashboard (not just see the screenshot):

```bash
# Sign up at https://railway.app (free $5/mo credit)
# Or https://fly.io (free starter)

# From the project root:
brew install flyctl                       # one-time
fly auth signup                           # opens browser
fly launch                                # follow prompts; pick "Yes" to existing Procfile
fly secrets set ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
fly secrets set MERIDIAN_PASSWORD=meridian2026   # or whatever you want
fly deploy
```

Wait ~2 minutes. You get a URL like `meridian-app.fly.dev`. Test it in incognito with username `anything` and password `meridian2026`.

Then update the landing page nav: replace `Get early access ↓` link with `Try the dashboard ↗` pointing to the Fly URL. Add a small note: *"Password: meridian2026"*.

If you skip this, the landing page still works — visitors join the waitlist, you build V1 with proper auth later.

## 6. The tweet — 15 min

After 1–4 are done, post the reply tweet to your 56K-view post:

```
Built it. Day-one finding from the tool:

Yarin Gal (Oxford OATML — runs ~30 PhDs, top-5 European ML PI) lists 
Apple as a co-affiliation on his 2026 papers. No press release, no 
Twitter bio change, no LinkedIn update.

The paper says it. Most VCs aren't reading paper affiliations.

Step 6 of last week's thread, now working as code:
https://meridian.so

Two-week dogfood starts now.
```

Attach: dashboard screenshot showing the Yarin Gal signal at score 9/10.

Best time: **Tuesday or Wednesday at 13:00 UTC / 08:00 ET**.

Block the next 60 minutes for replies. Twitter rewards engagement velocity hard.

## 7. Pre-DM 4 people — 10 min before posting

DM Illia, Avichal, Anand, Enis the link 1 hour before posting publicly:

> About to post this in an hour — anything wrong? <link>

Primes them to engage on launch, signals the algorithm fast.

---

## Done. Now wait 48 hours.

Decision rubric:

| Outcome | Move |
|---|---|
| 5+ Stripe purchases | Build V1 (auth, hosted, multi-user). 5 days. |
| 50+ waitlist sign-ups, 0 purchases | Strong interest, weak willingness to pay. Re-think pricing or audience. |
| <20K views on the reply | Audience didn't fit. Stop. Use it personally. Try a different angle in 2 weeks. |
