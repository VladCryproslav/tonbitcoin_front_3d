# Withdrawals backend: current logic and planned changes

## 1. Текущая архитектура вывода

### 1.1. Модели и конфиги

- **`WithdrawalRequest`**, **`AutoWithdrawalRequest`**, **`WithdrawalConfig`**  
  см. модельные классы:

```1176:1256:edit/core/models.py
class WithdrawalRequest(models.Model):
    ...

class AutoWithdrawalRequest(models.Model):
    ...

class WithdrawalConfig(models.Model):
    ...
```

- **Профиль пользователя и SBT‑комиссии**:

```412:437:edit/core/models.py
def sbt_get_kw_commision(self):
    gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
    premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
    if gold_sbt or premium_sub:
        return 0.08  # 4% + 4% (pool + fee)
    if self.has_silver_sbt and self.has_silver_sbt_nft:
        return 0.09  # 4.5% + 4.5%
    return 0.10  # 5% + 5%

def sbt_get_claim_commision(self):
    gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
    premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
    if gold_sbt or premium_sub:
        return 0.007
    if self.has_silver_sbt and self.has_silver_sbt_nft:
        return 0.0085
    return 0.01
```

Здесь:
- `sbt_get_kw_commision` — **суммарная комиссия** для blockchain‑минта kW (mint fee + LP fee).
- `sbt_get_claim_commision` — комиссия для blockchain‑claim/withdraw fBTC, уже совпадает с фронтом (1% / 0.85% / 0.7%).

### 1.2. HTTP‑endpoint `create-withdrawal-request/`

```1056:1058:edit/core/views.py
class CreateWithdrawalRequestView(APIView):
    @require_auth
    def post(self, request):
        return common_withdrawal(request)
```

Основная логика в `common_withdrawal`:

```1061:1143:edit/core/views.py
def common_withdrawal(request):
    wallet_address = request.data.get("wallet_address")
    token_amount = request.data.get("token_amount")
    token_contract_address = request.data.get("token_contract_address")
    is_mining = request.data.get("is_mining", False)
    is_staking = request.data.get("is_staking", False)
    is_rent = request.data.get("is_rent", False)
    ...
    if not all([wallet_address, token_amount, token_contract_address]):
        return Response({"error": "All fields are required"}, 400)
    ...
    if token_contract_address not in [KW_TOKEN, TBTC_TOKEN]:
        return Response({"error": "Wrong token_contract_address"}, 400)
    ...
    real_address = pytoniq_core.Address(wallet_address).to_str(is_user_friendly=False)
    if real_address != request.user_profile.ton_wallet:
        return Response({"error": "Wrong wallet address"}, 400)
    ...
    withdraw_config = WithdrawalConfig.objects.first() or None
    min_kw = getattr(withdraw_config, "min_kw", 500)
    ...
    max_auto_kw = getattr(withdraw_config, "max_auto_kw", 10000)
    max_auto_tbtc = getattr(withdraw_config, "max_auto_tbtc", 500)
    max_auto_claim = getattr(withdraw_config, "max_auto_claim", 500)
    ...
    last_request = WithdrawalRequest.objects.filter(
        user=user_profile,
        token_contract_address=token_contract_address,
        note=note,
    ).order_by("-claimed_at").first()
    if last_request and (timezone.now() - last_request.claimed_at).days < 1:
        return Response(
            {"error": "You can only make one withdrawal request per day",
             "last_date": last_request.claimed_at},
            400,
        )
```

Выводы:
- Endpoint **жёстко заточен под blockchain‑вывод**:
  - `wallet_address` обязателен.
  - Адрес валидируется и сравнивается с `user_profile.ton_wallet`.
- In‑App кейс (без адреса, без on‑chain) **сейчас не поддерживается**.

### 1.3. kW → blockchain (mint)

Ветка kW в `common_withdrawal`:

```1164:1183:edit/core/views.py
if token_contract_address == KW_TOKEN:
    token_type = "kw"
    if user_profile.energy < token_amount or token_amount < min_kw or (wallet_info and wallet_info.kw_amount < token_amount):
        return Response({"error": "Not enough kW in wallet"}, 400)
    with transaction.atomic():
        UserProfile.objects.filter(user_id=user_profile.user_id).update(
            energy=F("energy") - token_amount
        )
        WalletInfo.objects.filter(
            user=user_profile, wallet=user_profile.ton_wallet
        ).update(kw_amount=F("kw_amount") - token_amount)

    commision_percent = user_profile.sbt_get_kw_commision()
    if token_amount < max_auto_kw:
        real_amount = token_amount * (1 - commision_percent)
        add_kw_commission(token_amount - real_amount)
        tx_hash = ""
        comment = f"Mint {user_profile.user_id}"
        ...
        is_auto = True
```

Текущее поведение:
- Вся комиссия закодирована в `sbt_get_kw_commision()`:
  - без SBT: 10%
  - Silver SBT: 9%
  - Gold SBT / Premium: 8%
- Для auto‑mint (`token_amount < max_auto_kw`) на кошелёк уходит:
  - `real_amount = token_amount * (1 - commision_percent)`
  - разница (`token_amount - real_amount`) уходит на `add_kw_commission(...)`.

**Автоматический mint и лимиты auto‑вывода завязаны на `max_auto_kw`, `min_kw` и т.п. — эту логику трогать нельзя.**

### 1.4. fBTC → blockchain (claim / withdraw)

Ветка fBTC (token_contract_address = TBTC_TOKEN, `is_mining=True`) в `common_withdrawal`:

```1199:1249:edit/core/views.py
else:
    token_type = "tbtc"
    if is_mining:
        with transaction.atomic():
            requested_amount = float(token_amount)
            total_mined_tokens_balance = user_profile.total_mined_tokens_balance()
            ...
            withdraw_gross = min(requested_amount, total_mined_tokens_balance)
            if withdraw_gross < min_claim:
                return Response({"error": "Not enough tBTC in wallet 2"}, 400)
            ratio = withdraw_gross / total_mined_tokens_balance
            mined_main_take = user_profile.mined_tokens_balance * ratio
            mined_s21_take = user_profile.mined_tokens_balance_s21 * ratio
            mined_sx_take = user_profile.mined_tokens_balance_sx * ratio

            commision_percent = user_profile.sbt_get_claim_commision()
            low_sum = withdraw_gross < 100
            apply_comission = lambda t: t - 1 if low_sum else t * (1-commision_percent)

            token_amount_s21 = (1-commision_percent) * mined_s21_take
            token_amount_sx = (1-commision_percent) * mined_sx_take
            token_amount = (
                apply_comission(mined_main_take)
                + token_amount_s21
                + token_amount_sx
            )
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                mined_tokens_balance=F("mined_tokens_balance") - mined_main_take,
                ...
                tbtc_claimed_period=F("tbtc_claimed_period") + token_amount,
            )
            WalletInfo.objects.filter(
                user=user_profile, wallet=user_profile.ton_wallet
            ).update(
                tbtc_amount=F("tbtc_amount") - mined_main_take,
                ...
            )
```

Ключевые моменты:
- Комиссия по fBTC берётся из `sbt_get_claim_commision()`:
  - без SBT: 1%,
  - Silver: 0.85%,
  - Gold/Premium: 0.7%.
- Для сумм `< 100` дополнительно используется фикс `-1` токен, как и на фронте.
- Логика распределения между S21/SX и обычными ASIC уже обновлена и не должна меняться (особенно с точки зрения стейкинга/автоминта).

## 2. Соответствие фронту

### 2.1. Mint kW (Blockchain vs In‑App)

Во фронтенде (`src/components/MintModal.vue` и примеры) уже реализован визуальный тоггл:

```21:45:src/components/MintModal.vue
const withdrawalType = ref('blockchain')
...
const commissionRate = computed(() => {
  if (withdrawalType.value === 'inapp') return 0.10 // In-App как сейчас: 10%
  const hasGold = app?.user?.has_gold_sbt && app?.user?.has_gold_sbt_nft
  const hasSilver = app?.user?.has_silver_sbt && app?.user?.has_silver_sbt_nft
  if (hasGold || premiumActive.value) return 0.18
  if (hasSilver) return 0.19
  return 0.20
})
```

Требуемые проценты для **Blockchain mint kW**:
- без SBT: **20%** (10% mint fee + 10% LP),
- Silver SBT: **19%** (9.5% + 9.5%),
- Gold SBT / Premium: **18%** (9% + 9%).

In‑App на фронте отдельно, и по ТЗ **оставляется как сейчас**:
- In‑App: 10% только как “MINT fee”, LP = 0%.

### 2.2. Withdraw fBTC (Blockchain vs In‑App)

Фронтовый тоггл уже есть в `src/components/WithdrawModal.vue`, и для In‑App там **комиссия 0**, а для blockchain совпадает с текущими бэкенд‑ставками (`sbt_get_claim_commision` + фикс `-1` для `<100`).

На бэке сейчас:
- **нет понятия `withdrawal_type`**,
- In‑App логика **отсутствует полностью**, всё завязано на blockchain‑вывод.

## 3. Что нужно изменить (позже), не ломая автоминт

> В этом разделе только план и точки правок. Фактические изменения в коде пока **не делаем**.

### 3.1. Обновление процентов blockchain mint kW

Цель: выровнять бэкенд с фронтом по kW mint (Blockchain) и при этом **не трогать автоминт/лимиты/потоки**.

Минимальная точка изменения:

```420:427:edit/core/models.py
def sbt_get_kw_commision(self):
    gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
    premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
    if gold_sbt or premium_sub:
        return 0.08  # 4% + 4% (pool + fee)
    if self.has_silver_sbt and self.has_silver_sbt_nft:
        return 0.09  # 4.5% + 4.5%
    return 0.10  # 5% + 5%
```

План изменения значений (без изменения структуры и вызовов):
- `return 0.10` → `0.20` (без SBT).
- `return 0.09` → `0.19` (Silver).
- `return 0.08` → `0.18` (Gold/Premium).

Это автоматически:
- изменит `commision_percent` в `common_withdrawal` для kW,
- оставит всю автоминт‑логику (`max_auto_kw`, лимиты, atomic‑блоки, `AutoWithdrawalRequest`) без изменений.

Ничего больше трогать **не нужно**:
- расчёт `real_amount = token_amount * (1 - commision_percent)` останется тем же,
- фоновые обработчики `AutoWithdrawalRequest` (в `edit/sender.py` и т.п.) продолжают работать на том же интерфейсе.

### 3.2. In‑App логика для kW и fBTC

Сейчас BE не знает о `withdrawal_type`, а фронт уже отправляет его (в примерах и новых компонентах).

#### 3.2.1. Расширение контракта API

В `CreateWithdrawalRequestView` (swagger-схема) добавить поле:
- `withdrawal_type: "blockchain" | "inapp"`, необязательное, по умолчанию `"blockchain"` для обратной совместимости.

#### 3.2.2. Ветвление в `common_withdrawal`

В начале функции:

```1061:1068:edit/core/views.py
def common_withdrawal(request):
    wallet_address = request.data.get("wallet_address")
    token_amount = request.data.get("token_amount")
    token_contract_address = request.data.get("token_contract_address")
    is_mining = request.data.get("is_mining", False)
    is_staking = request.data.get("is_staking", False)
    is_rent = request.data.get("is_rent", False)
```

Добавить только чтение режима:
- `withdrawal_type = request.data.get("withdrawal_type", "blockchain")`.

Дальше логика:

- Если `withdrawal_type == "blockchain"` — **оставляем текущий путь 1:1**:
  - обязательный `wallet_address`,
  - проверка `real_address == user_profile.ton_wallet`,
  - создание `AutoWithdrawalRequest` при авто‑кейсах,
  - все существующие мин/макс‑лимиты.

- Если `withdrawal_type == "inapp"`:
  - `wallet_address` **не обязателен**:
    - проверка `if not all([...])` должна игнорировать `wallet_address` в этом режиме;
  - **пропускаем** всю проверку/валидатор TON‑адреса (`pytoniq_core.Address`, сравнение с `ton_wallet`);
  - работаем только с внутренними балансами:
    - kW: списать `energy`/`wallet_info.kw_amount` и зачислить во внутренний In‑App баланс (нужно выбрать конкретные поля: либо отдельная колонка, либо `tbtc_wallet`/другой кошелёк — это архитектурное решение);
    - fBTC: списать из соответствующего хранилища (mined / staking / rent) и зачислить во внутренний In‑App баланс, без формирования `AutoWithdrawalRequest` и без on‑chain tx.
  - комиссии:
    - kW In‑App: как по ТЗ — **10% mint, 0% LP**, суммарно 10% (сейчас фронт уже так считает).
    - fBTC In‑App: по ТЗ — **0% комиссия** (фронт уже рисует 0 для In‑App).

Важно:
- In‑App не должен:
  - создавать `AutoWithdrawalRequest`,
  - инициировать on‑chain mint/transfer (`send_kw`, `send_tbtc` и т.д.).
- Но при этом должен **создавать запись `WithdrawalRequest`** (с пометкой `withdrawal_type = "inapp"` или флагом `is_internal`), чтобы:
  - история/ограничение “раз в сутки” продолжали работать корректно,
  - фронт мог показывать статусы/историю.

#### 3.2.3. Значения `note` для In‑App

Текущее поведение:

```1120:1125:edit/core/views.py
if is_mining:
    note = "withdraw"
elif is_staking:
    note = "staking"
elif is_rent:
    note = "rent"
else:
    note = "claim"
```

Требование к In‑App:
- при In‑App выводе из майнинга (`is_mining=True`, `withdrawal_type="inapp"`) в `WithdrawalRequest.note` писать **`"In-app withdraw claim"`**;
- при In‑App выводе “из кошелька” (обычный вывод, не `is_mining`) — **`"In-app withdraw"`**.

Создание записи остаётся тем же, меняется только значение `note`:

```1534:1548:edit/core/views.py
withdrawal_request = WithdrawalRequest.objects.create(
    user=user_profile,
    wallet_address=wallet_address,
    token_amount=token_amount,
    token_contract_address=token_contract_address,
    claimed_at=timezone.now(),
    is_auto=is_auto,
    ...
    note=note,
    commision_percent=commision_percent,
)
```

### 3.3. Автоминт и ограничения — что не трогаем

То, что менять нельзя в рамках задачи:

- Лимиты и статусы авто‑вывода:
  - `max_auto_kw`, `max_auto_tbtc`, `max_auto_claim`, `max_auto_staking_out`, `max_auto_rent` в `WithdrawalConfig`.
  - Дневной лимит “одна заявка в день” по `WithdrawalRequest`.
- Место, где создаются `AutoWithdrawalRequest` и как они далее обрабатываются (`edit/sender.py`, `edit/ttt2.py` и т.п.).
- Логику перераспределения mined fBTC между S1‑S19 и S21/SX, а также отключённый стейкинг S21/SX — это уже согласованная автоминт‑архитектура.

## 4. Резюме для реализации (когда будем править код)

1. **Blockchain kW mint**:
   - Обновить только `UserProfile.sbt_get_kw_commision` до 0.20/0.19/0.18.
   - Не трогать `common_withdrawal` и `AutoWithdrawalRequest`.
2. **Blockchain fBTC**:
   - Оставить `sbt_get_claim_commision` и текущую формулу (она уже совпадает с фронтом).
3. **In‑App режим**:
   - Добавить `withdrawal_type` в контракт `create-withdrawal-request/`.
   - В `common_withdrawal`:
     - для `"blockchain"` сохранить поведение как есть;
     - для `"inapp"` сделать отдельную ветку без проверки TON‑адреса и без создания `AutoWithdrawalRequest`, только с внутренними балансами и нулевой комиссией для fBTC, 10% для kW.
   - Добавить поле/флаг в `WithdrawalRequest`, чтобы отличать blockchain и in‑app запросы.

Такой подход меняет **только проценты** и добавляет in‑app путь, не ломая существующую автоминт‑логику и cron‑процессы.

