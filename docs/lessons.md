# Solo-Dev Lessons Learned

Bilinçli trade-off'lar ve öğrenilen dersler. **Bu dosyadaki kararlar değiştirilmeden önce sorulmalı** — çoğu kasıtlı seçimdir.

---

## Docker & Infrastructure

- **Multi-service single image:** `backend`, `celery_worker`, `celery_beat` tek `ledgrio-backend:latest` image'ını paylaşır. Her servise ayrı `build:` bloku koyma — stale image bug'ı çıkar (`ModuleNotFoundError: environ`). `image:` ile referansla.
- **Health endpoint from day one:** Container healthcheck + smoke test tek satır. İlk fazdan kur.
- **Celery deprecation:** `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True` set et.
- **Custom User model timing:** `AUTH_USER_MODEL` ilk `migrate`'ten önce set edilmeli. Sonradan eklemek `InconsistentMigrationHistory` çıkarır. Dev fix: `docker compose down -v`.
- **Celery beat + DatabaseScheduler:** `CELERY_BEAT_SCHEDULE` setting `DatabaseScheduler` ile okunmaz. Beat task'lerini data migration ile kayıt et (bkz. `apps/currencies/migrations/0003_register_daily_fx_beat.py`). Migration dependency olarak `django_celery_beat`'in son migration'ını ekle.

## Django ORM & Models

- **Historical models in migrations:** `apps.get_model()` tarihi model döner, custom manager yok. `.objects.all()` kullan, `all_objects` çalışmaz.
- **SoftDeleteModel contract:** `Model.objects` deleted satırları filtreler. Admin/audit/restore için `Model.all_objects`. `base_manager_name = "all_objects"` set et — FK reverse lookup'lar (cascade) deleted satırları görsün.
- **UnorderedObjectListWarning:** Her list view'da explicit `.order_by()` zorunlu. Pagination'da sessiz bozulma olur.
- **`python -c` + Django ORM:** Container içinde Django setup çalışmaz. `python manage.py shell -c "..."` kullan.
- **django-stubs model resolution:** Model definition `models.py`'da olmalı. Başka modülde tanımlanırsa `.objects` `attr-defined` hatası verir.

## Auth & Security

- **JWT logout semantics:** `/auth/logout/` sadece **refresh token**'ı blacklistler. Access token TTL (15 dk) dolana kadar çalışır. Bu bilinçli trade-off — stateless JWT değerini korumak için. Frontend access token'ı hemen düşürmeli.
- **Email normalization:** `normalize_email`'i override et — hem local hem domain lowercase. Aksi halde `Bob@LEDGR.IO` ile login 401 atar.
- **django-ratelimit + DRF 429:** `Ratelimited` exception `PermissionDenied` subclass'ı, DRF default 403 render eder. `drf_exception_handler`'da intercept edip 429 + `RATE_LIMITED` envelope döndür.
- **SECRET_KEY:** Default kaldırıldı. `DJANGO_SECRET_KEY` env var yoksa container fail-fast. CI'da synthetic secret olarak commit SHA kullan.
- **Password reset enumeration:** Request endpoint her zaman 200 döner — kullanıcı bulunamasa bile. Enumerate önlemek için tasarım gereği.

## Financial Precision

- **FX snapshot pattern:** `FxRate` rate kayıt anında store edilir, eski transaction'lar değişmez. `convert()` direct rate yoksa inverse dener; ikisi de yoksa en yakın tarihe fallback. Bu bilinçli mimari kararı (bkz. D-004).
- **Quantize sadece sonda:** `amount * raw_rate` sonrası tek 8dp quantize. `_lookup_rate` ham Decimal döner — mid-chain quantize = compounding rounding hatası.
- **Rounding standard:** `ROUND_HALF_EVEN` (banker's rounding) her yerde. `common/money.py:q()` tek giriş noktası.
- **`current_balance` hesaplama:** Account balance asla saklanmaz — `Subquery` annotation ile compute edilir. Stored derived value = tutarsızlık riski.

## Testing & Type Checking

- **mypy + Django:** `disallow_any_generics=false`, stub'sız paketler `[[tool.mypy.overrides]]` ile ignore. Sonrası temiz ve yönetilebilir.
- **factory-boy SelfAttribute:** Nested SubFactory'lerde user FK zinciri: `factory.SelfAttribute("..user")`.
- **Coverage tiered:** services/selectors %90, views %75, proje geneli %80 (CI enforce). Layer floor'lar faz sonu manuel audit.
- **Transaction.account FK migration:** Sadece test verisi vardı, wipe edildi. Production'da bu olmaz — migration planı gerekir.

## Serializer & API

- **CursorPagination + custom field:** Küçük enumerable tablolarda `PageNumberPagination` kullan. Default `CursorPagination` `created` field bekler → `FieldError`.
- **simplejwt + custom User:** `TokenObtainPairSerializer.username_field = User.USERNAME_FIELD` email login için yeterli, ekstra view gerekmez.
- **Email verification production:** Backend çalışıyor (token + endpoint + console mail). Production'a çıkmadan `EMAIL_BACKEND` Mailgun/Anymail'e çevrilmeli.

## Budget & Annotation Patterns

- **Case/When Subquery for nullable FK:** When a FK is nullable and `null` means "all" (e.g. `budget.category = null` → covers all categories), split the `spent` annotation into two `Case/When` branches: one `Subquery` for the category-filtered path, one for the unfiltered path. Both branches must include the same `filter(type="expense")` guard.
- **NullIf division guard on Decimal:** `ExpressionWrapper(F("spent") / F("amount"), ...)` will crash on `amount=0`. Use `NullIf(F("amount"), Value(Decimal("0")))` in the denominator. `usage_pct` annotation type is therefore `Decimal | None`, not `Decimal`.
- **`_UNSET` sentinel for PATCH nullable FK:** `data.pop("category_id", None)` cannot distinguish "client omitted field" from "client explicitly sent null." Use `_UNSET = object()` sentinel: `category_id = data.pop("category_id", _UNSET)` then `if category_id is not _UNSET: budget.category_id = category_id`. This allows explicit null (clear category) while ignoring absent field.
- **Quantize `fx_rate_snapshot` at both branches:** Pre-existing bug: `_compute_fx` stored the raw Decimal from `get_exchange_rate()` without quantizing. Fix: call `.quantize(QUANTIZE)` on the rate *before* computing `amount_base`, in both the `fx_rate_override` branch and the normal `convert()` branch.
- **Alert atomicity: DB write first, email second:** In `check_and_send_budget_alerts`, set `alert_sent_at` inside `@transaction.atomic` BEFORE calling `send_mail`. A crash after the DB commit = missed alert (user re-runs beat tomorrow). A crash before the DB commit = double-send on next run. The former is acceptable; the latter is not.

## Frontend (Phase 6+)

- **Tailwind `content: []` → sıfır CSS:** `tailwind.config.js` ilk oluşturulduğunda `content` dizisi boş gelir. Content glob'ları set edilmeden build alınırsa hiçbir utility class üretilmez — sayfa tamamen stilsiz görünür. Her yeni frontend projede `content: ["./index.html", "./src/**/*.{ts,tsx}"]` ilk adım olmalı.
- **Docker frontend dev workflow:** `docker-compose.yml`'de `frontend` servisi production build'ini `5173:80` üzerinde sunar ve dev portunu bloke eder. Hot-reload için: `docker compose stop frontend` + `cd frontend && npm run dev`. Docker rebuild sadece production deploy ya da nginx config değişikliğinde gerekli.

- **Brand tokens before components:** Tailwind config + CSS variables defined first, primitives themed against them. Reverse order produces hardcoded hexes that need a refactor when palette changes. (D-014)
- **Vite 8 + Vitest 2 type split:** `vite.config.ts` and `vitest.config.ts` must be separate files. The `test` key inside `defineConfig` from `vite` does not satisfy `UserConfigExport` — vitest provides its own `defineConfig` from `vitest/config`. Symptom: `TS2769 Object literal may only specify known properties, and 'test' does not exist`.
- **`@apply` cannot reference custom theme tokens defined later in the same file:** Tailwind 3 resolves `@apply bg-canvas` at PostCSS time, before `:root` CSS vars in `@layer base` are read. Use raw `background-color: rgb(var(--canvas))` for body styles; reserve `@apply` for primitives where the class is registered before use.
- **TS 6.x deprecates `baseUrl`:** Required even with `paths`. Add `"ignoreDeprecations": "6.0"` to silence — TS 7 will move to a different mechanism.
- **Refresh-queue is the right shape, not refresh-on-every-401:** Without a module-scoped promise guard, N concurrent 401s fire N refresh calls; the first one blacklists the refresh token and the rest 401-bounce the user to login. Single shared promise + `_retried` flag fixes both. (D-015)
- **Axios envelope flattening lives in one helper:** `parseApiError` returns `{type, status, message, fieldErrors}`. RHF integration is two lines (`setError(field, {type:"server", message})`); without this, every form re-implements DRF envelope parsing.
- **Logo SVG inline beats logo.png img:** Inline SVG component (`Logo` with `variant=full|mark|wordmark`) lets us recolor the wordmark via Tailwind classes for the dark brand panel. PNG would force a separate white-text logo asset.

## Process

- **Tamamlanmış faz = donmuş:** Bug fix haricinde tamamlanmış fazlar yeniden açılmaz. Yeni feature = yeni faz. Aksi halde "neredeyiz" sinyali bozulur.
- **Plan onayı ucuz, yanlış kod pahalı:** Her faz başında model şeması + endpoint listesi + service imzaları onaylanmadan kod yazılmaz.
- **`phase-N-start` tag'ini erken at:** Faz başında ilk iş `git tag phase-N-start`. Geç atılırsa ya da unutulursa rollback noktası kaybolur.
- **Diff review olmadan doc güncelleme yapılmaz:** "Dokümanları güncelle" dediğinde Claude'un nereye ne yazacağı belirsiz. Faz Bitiş Prompt'unda "önce diff göster" şartı kritik — yoksa Solo-Dev Tuzakları sessizce üzerine yazılabilir.
- **Bootstrap prompt sırası önemli:** ARCHITECTURE_RULES okunmadan plan yapılmaz. Sıra: CLAUDE.md Current State → decisions.md son kararlar → plan öner → onay al → implement.
- **Doküman güncellemeleri atomic commit olmalı:** Her faz sonu tek commit: `docs: complete phase N`. Tag: `git tag phase-N-complete`. Geri bakış için tarih damgası zorunlu.
- **"Tech Debt: None" inanılmaz görünüyor:** Her faz sonunda §11 index listesi, §5 precision helper'ları ve §14 response envelope eksik implementasyon için kontrol edilmeli. Gerçek "None" nadirdir.
- **Hard delete kararları ADR gerektirir:** `DebtPayment` gibi istisnalar önceden belgelenmeli. "Şimdilik hard delete yapalım" teknik borç değil, yanlış karardır — ADR yoksa merge edilmez.
- **Section numarası değişen her edit'te cross-reference tara:** `grep -rn "§N" docs/` komutuyla tüm dosyalardaki referanslar kontrol edilmeli. Renumbering tek dosyada yapılır, kırık referans başka dosyada sessizce kalır.
