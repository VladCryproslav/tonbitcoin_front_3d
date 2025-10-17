# Lottery API Documentation

## Endpoints

### 1. GET /lottery/data/
Получить данные о лотерее

**Response:**
```json
{
  "totalTickets": 150,
  "remainingTickets": 50,
  "isActive": true
}
```

### 2. GET /lottery/participants/
Получить список участников лотереи

**Response:**
```json
[
  {
    "id": 1,
    "username": "Vadim",
    "wallet_address": "UQD4XIdaIRt-42j4d6GIFj7....",
    "tickets_count": 20,
    "created_at": "2024-01-01T10:00:00Z"
  },
  {
    "id": 2,
    "username": "Alex",
    "wallet_address": "UQD4XIdaIRt-42j4d6GIFj7....",
    "tickets_count": 15,
    "created_at": "2024-01-01T11:00:00Z"
  }
]
```

### 3. POST /lottery/buy-ticket/
Купить билет лотереи

**Request:**
```json
{
  "wallet_address": "UQD4XIdaIRt-42j4d6GIFj7....",
  "transaction_hash": "abc123...",
  "amount": 0.01
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Ticket purchased successfully",
  "tickets_count": 21
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Lottery is not active"
}
```

## Database Schema

### Lottery Model
```python
class Lottery(models.Model):
    total_tickets = models.IntegerField(default=150)
    remaining_tickets = models.IntegerField(default=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### LotteryParticipant Model
```python
class LotteryParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    wallet_address = models.CharField(max_length=100)
    tickets_count = models.IntegerField(default=1)
    transaction_hash = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'wallet_address']
```

## Business Logic

1. **При покупке билета:**
   - Проверить активность лотереи
   - Проверить наличие оставшихся билетов
   - Найти существующего участника по wallet_address
   - Если участник существует - увеличить tickets_count
   - Если участник не существует - создать новую запись
   - Уменьшить remaining_tickets на 1
   - Если remaining_tickets = 0 - деактивировать лотерею

2. **Валидация:**
   - Проверить формат wallet_address
   - Проверить transaction_hash на уникальность
   - Проверить amount (должно быть 0.01 TON)

3. **Безопасность:**
   - Проверить подпись транзакции
   - Валидировать transaction_hash через TON API
   - Проверить что транзакция действительно поступила на указанный адрес
