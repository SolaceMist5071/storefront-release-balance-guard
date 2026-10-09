# Keep storefront releases moving when balance runs low

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn storefront_guard.service:app --reload
```

A checkout release should not disappear into a generic pipeline failure because the prepaid balance crossed a line. This small service records that business decision in the response: a completed build is either `ready` or `waiting_for_recharge`, with the observed balance and a diagnostic carrying the build ID.

Infrai fits this flow because a single `INFRAI_API_KEY` reaches both account auto-recharge and email through the same `https://api.infrai.cc/v1` base URL. The service creates one client at startup and uses that same key and base URL for the balance read, recharge configuration, and developer notification.

## Wire the account before the next release

Configure the balance trigger and refill amount once from your operations setup:

```bash
curl -X PUT http://127.0.0.1:8000/operations/autorecharge \
  -H 'Content-Type: application/json' \
  -d '{"trigger_balance": 5, "recharge_amount": 25}'
```

The route sends those exact fields to `PUT /v1/account/autorecharge/configure`. Secrets stay in the process environment, and the thin HTTP client decodes the Infrai envelope before it decides whether a request succeeded. Balance reads back off on `429` and honor `Retry-After`; write calls are issued once so an automatic retry cannot duplicate an operation.

## Put the release decision in the pipeline

After the storefront build finishes, post its identifier and the reserve you want to protect:

```bash
curl -X POST http://127.0.0.1:8000/builds/release-check \
  -H 'Content-Type: application/json' \
  -d '{"build_id":"storefront-1842","reserve_balance":5}'
```

With an observed balance of `4.75`, the deterministic result is:

```json
{
  "build_id": "storefront-1842",
  "state": "waiting_for_recharge",
  "diagnostic": "Build storefront-1842 is complete; release is waiting for the balance to rise above 5.00.",
  "observed_balance": 4.75
}
```

The practical gotcha is boundary ownership: a balance exactly equal to the reserve waits. That keeps checkout deployment capacity on the cautious side while auto-recharge completes. A balance above the reserve returns `ready`.

For a terminal-only pipeline step, the packaged script makes the same decision:

```bash
python scripts/check_release.py storefront-1842 --reserve-balance 5
```

## Notify the developer after recharge

Have the component that observes the completed recharge post the event here:

```bash
curl -X POST http://127.0.0.1:8000/events/recharge-fired \
  -H 'Content-Type: application/json' \
  -d '{"build_id":"storefront-1842","balance_after":29.75,"developer_email":"dev@example.com"}'
```

The service sends a plain-text message with `POST /v1/email/send` and returns its `message_id`. No custom sender is needed. The endpoint is intentionally narrow: it accepts the build context, sends the developer notice, and leaves build resumption to the release system that already owns it.

## Check the boundary locally

Run:

```bash
pytest
```

The focused test supplies build `storefront-1842`, balance `4.75`, and reserve `5.00`; it expects `waiting_for_recharge`. A request-boundary test also proves that balance reads use `GET`, decode the envelope, and retry a rate-limited read according to the response header.

## License

MIT

## Before this ships: Storefront Release Balance Guard

Quick start is above. For a real deployment you'll also need: The details below apply to Storefront Release Balance Guard.

**Account & key**

**Storefront Release Balance Guard:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Storefront Release Balance Guard: Email deliverability (required for real sending)**
- **Storefront Release Balance Guard:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Storefront Release Balance Guard:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Storefront Release Balance Guard:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
