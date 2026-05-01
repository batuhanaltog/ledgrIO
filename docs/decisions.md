# Architecture Decision Records (ADR)

Önemli mimari kararların kaydı. Her karar bir bağlam, seçim ve sonuç içerir.
Format: `D-NNN: Başlık (Tarih)` — durum: ✅ Aktif / ⚠️ Revize / 🗄️ Arşiv

---

## D-001: User.default_currency_code FK yerine CharField (2026-02-15)

**Bağlam:** Phase 1'de Currency modeli henüz yoktu.  
**Karar:** `CharField(3)` + regex validator. Phase 1 geçilsin, Currency gelince FK'ya promote edilsin.  
**Sonuç:** Phase 3'te `apps/users/migrations/000X_currency_fk.py` ile FK'ya promote edildi.  
**Durum:** 🗄️ Arşiv (çözüldü Phase 3)

---

## D-002: JWT logout sadece refresh token'ı blacklistler (2026-02-15)

**Bağlam:** Stateless JWT'nin temel özelliği server-side state tutmamak.  
**Karar:** `/auth/logout/` yalnızca refresh token'ı blacklistler. Access token TTL (15 dk) dolana kadar çalışmaya devam eder.  
**Sonuç:** Per-request revocation list = JWT'nin değerini sıfırlar. Frontend access token'ı hemen düşürmeli.  
**Durum:** ✅ Aktif — `docs/lessons.md` "JWT logout semantics" maddesine bak.

---

## D-003: Celery beat task'leri DatabaseScheduler migration ile kayıt (2026-02-20)

**Bağlam:** `DatabaseScheduler` kullanılınca `CELERY_BEAT_SCHEDULE` setting okunmuyor.  
**Karar:** Her beat task bir data migration ile `PeriodicTask` olarak kayıt edilir.  
**Sonuç:** FX beat `apps/currencies/migrations/0003_register_daily_fx_beat.py`, recurring beat `apps/recurring/migrations/0002_register_recurring_beat.py`.  
**Durum:** ✅ Aktif

---

## D-004: FX snapshot pattern — rate kayıt anında store edilir (2026-02-20)

**Bağlam:** Tarihsel transaction'ların tutarlılığı için.  
**Karar:** `Transaction.fx_rate_snapshot` ve `amount_base` kayıt anında hesaplanır, sonradan değişmez. Eski transaction'lar cari FX değişimlerinden etkilenmez.  
**Sonuç:** `convert()` direct + inverse + tarih fallback. Quantize sadece outermost layer'da.  
**Durum:** ✅ Aktif

---

## D-005: SoftDeleteModel — default manager deleted satırları filtreler (2026-03-01)

**Bağlam:** Phase 3.5 hardening audit sonrası.  
**Karar:** `Model.objects` live-only (default). `Model.all_objects` audit/admin için. `base_manager_name = "all_objects"` ile FK reverse lookup'lar deleted satırları görür.  
**Sonuç:** Hard delete user-owned financial data üzerinde yasak.  
**Durum:** ✅ Aktif

---

## D-006: Coverage floor — CI 80%, layer audit manuel (2026-03-01)

**Bağlam:** %90 CI floor false confidence yaratıyordu (view test geçer, service hatalı olabilir).  
**Karar:** CI `--cov-fail-under=80`. services/selectors %90 ve views %75 floor manuel audit, faz sonu checklist'te.  
**Sonuç:** Tiered approach — otomatik guard + manuel kalite.  
**Durum:** ✅ Aktif

---

## D-007: Transaction.account FK migration — test verisi silindi (2026-05-01)

**Bağlam:** Phase 4.5'te `Transaction.account` NOT NULL FK eklendi. Mevcut Phase 4 test transaction'larında account verisi yoktu.  
**Karar:** Migration 0002'de `Transaction.objects.all().delete()` ile test verisi silindi, sonra FK eklendi. Production verisi yoktu, data migration karmaşıklığına gerek görülmedi.  
**Sonuç:** Bu pattern production'da geçersiz. Production'da önce backfill, sonra NOT NULL.  
**Kural (gelecek için):** Production verisine dokunan ya da NOT NULL constraint ekleyen her schema migration, merge'den önce bir ADR yazarak backfill planını belgelemelidir.  
**Durum:** ✅ Aktif (prensip: production'da aynı karar alınamaz)

---

## D-008: DebtPayment hard delete — financial data kuralına istisna (2026-05-01)

**Bağlam:** Ödeme geri alındığında (reversal) `DebtPayment` kaydının silinmesi gerekiyor. SoftDeleteModel "user-owned financial data silinmez" kuralıyla çelişiyor.  
**Karar:** `DebtPayment` hard delete. Gerekçe: reversal işlemi ilişkili `Transaction`'ı da siler (veya iptal eder), dolayısıyla payment record'un kalması tutarsızlık yaratır. Audit ihtiyacı yoksa (kişisel ölçek) hard delete kabul edilebilir.  
**Sonuç:** `reverse_debt_payment()` → payment hard delete + transaction soft delete + balance restore.  
**Durum:** ✅ Aktif

---

## D-009: Budget kapsam — sadece kişisel, paylaşım yok (2026-05-01)

**Bağlam:** Phase 5 planlama öncesi.  
**Karar:** `Budget.user` direkt FK. Paylaşım, RBAC, çoklu-kullanıcı budget yok.  
**Sonuç:** Model tasarımı basit tutuluyor. Scope değişirse bu karar ilk revize edilecek.  
**Durum:** ✅ Aktif

---

## D-010: Budget model date_from/date_to — period_type enum yok (2026-05-01)

**Bağlam:** Phase 5 model tasarımı.  
**Karar:** `date_from` + `date_to` explicit date fields. `period_type` enum (monthly/yearly) yok. Daha esnek, daha az magic.  
**Sonuç:** Kullanıcı istediği tarih aralığını belirtir. UI "bu ay" shortcut'ı verebilir ama model bağımsız.  
**Durum:** ✅ Aktif (Phase 5'te implement edilecek)

---

## D-011: Budget currency — her zaman kullanıcının base currency'si (2026-05-01)

**Bağlam:** Phase 5 model tasarımı. `Transaction.amount_base` tüm işlemleri base currency'ye çevirip saklar.  
**Karar:** Budget her zaman `UserProfile.default_currency_code` cinsinden tanımlanır. `spent` hesabı `Transaction.amount_base` üzerinden yapılır — ayrı FX dönüşümüne gerek yok.  
**Sonuç:** Multi-currency budget desteği yok (kişisel ölçek, kapsam dışı). Kural §13 olarak ARCHITECTURE_RULES.md'ye eklendi.  
**Durum:** ✅ Aktif

---

## D-013: Budget alert email ordering — DB write before send_mail (2026-05-01)

**Bağlam:** Phase 5 alert service tasarımı. `check_and_send_budget_alerts` hem DB'yi güncelleyip hem email atıyor. Hata anında hangisi önce gelirse yanlış davranış tetiklenebilir.  
**Karar:** `alert_sent_at` alanı `@transaction.atomic` içinde email'den ÖNCE yazılır. `send_mail(fail_silently=True)` transaction dışında çağrılır.  
**Sonuç:** Crash senaryoları: (a) DB yazma başarılı, email çöküyor → kullanıcı ertesi beat'te uyarı almaz (kabul edilebilir, missed alert). (b) DB yazılmadan crash → ertesi beat yeniden dener, çift email riski → bu senaryoyu `alert_sent_at` guard'ı önler. Missed alert, double-send'den tercih edilir.  
**Durum:** ✅ Aktif

---

## D-012: Geçmiş tarihli transaction FX girişi (2026-05-01)

**Bağlam:** Kullanıcı 2+ yıl öncesine ait kira/fatura girmek isteyebilir. O tarihe ait FxRate olmayabilir.  
**Karar:** Seçenek 1 — `fx_rate_override` optional field. `POST /api/v1/transactions/` payload'ına isteğe bağlı `fx_rate_override: Decimal` eklenir. Gönderilirse `convert()` atlanır, bu değer doğrudan `fx_rate_snapshot` ve `amount_base` hesabında kullanılır. Gönderilmezse mevcut fallback + stale guard davranışı korunur.  
**Gerekçe:** Seçenek 2 kullanıcıya 2 adımlı iş yükü bindiriyor; Seçenek 3 precision güvencesini kırıyor; Seçenek 1 mevcut `convert()` imzasına minimal ek, kullanıcıya tam kontrol.  
**Sonuç:** Phase 5 transaction create/update flow'unda uygulanacak. UI'da "Override FX Rate" opsiyonel alan olarak sunulacak (Phase 6+).  
**Durum:** ✅ Aktif (Phase 5'te implement edilecek)
