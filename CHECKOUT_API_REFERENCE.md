# Quick Reference: Checkout System API

## Routes Summary

### Checkout Page
```
GET /checkout
├─ Requires: user_id in session
├─ Required data: session['cart'] with items
├─ Returns: checkout.html template
└─ Redirects to login if not authenticated
```

### Payment Page
```
GET /payment
├─ Requires: user_id in session
├─ Required data: session['cart'] with items, cards table with user's cards
├─ Returns: payment.html template with card options
└─ Redirects to login if not authenticated
```

### Process Payment
```
POST /process_payment
├─ Requires: user_id in session
├─ Expects JSON body: {"card_id": <int>}
├─ Database operations:
│  ├─ SELECT card balance
│  ├─ VALIDATE balance >= (total_amount)
│  ├─ UPDATE card balance
│  └─ CLEAR session['cart']
│
├─ Success response (200):
│  └─ {"status": "success", "message": "Төлем сәтті жасалды", 
│     "new_balance": <int>, "total_paid": <int>}
│
├─ Error responses:
│  ├─ 401: {"status": "error", "message": "Кіруіңіз қажет"}
│  ├─ 400: {"status": "error", "message": "Қаражатыңыз жеткіліксіз"}
│  └─ 404: {"status": "error", "message": "Карта табылмады"}
│
└─ Side effects:
   ├─ Card balance updated in database
   └─ Session cart cleared
```

## Database Schema

### Cards Table
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_name TEXT NOT NULL,           -- e.g., "Kaspi Gold"
    balance INTEGER NOT NULL,          -- in tenge (smallest unit)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Sample Data
```
user_id | card_name     | balance
--------|---------------|----------
1       | Kaspi Gold    | 4300000
1       | Halyk Bank    | 2100000
1       | BCC           | 650000
```

## Payment Calculation

```python
delivery_cost = 1500  # Fixed
cart_total = SUM(product.price * product.quantity for product in cart)
total_amount = cart_total + delivery_cost

# Example:
# Product 1: 925990 ₸ × 2 = 1851980 ₸
# Delivery: 1500 ₸
# Total: 1853480 ₸
```

## Session Structure

### Before Checkout
```python
session = {
    'user_id': 1,
    'user_name': 'Test User',
    'cart': {'1': 2, '2': 1}  # product_id -> quantity
}
```

### After Successful Payment
```python
session = {
    'user_id': 1,
    'user_name': 'Test User',
    'cart': {}  # Cleared
}
```

## Frontend JavaScript

### Card Selection Handler
```javascript
// When user selects a card
input.addEventListener('change', function(){
    const balance = parseInt(this.dataset.balance, 10);
    if(balance < totalAmount){
        balanceWarning.style.display = 'block';
        payButton.disabled = true;
    } else {
        balanceWarning.style.display = 'none';
        payButton.disabled = false;
    }
});
```

### Payment Submission
```javascript
fetch('/process_payment', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({card_id: cardId})
})
.then(r => r.json())
.then(data => {
    if(data.status === 'success'){
        // Payment successful
        // Redirect or show confirmation
    } else {
        // Show error message
        alert('Қате: ' + data.message);
    }
});
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Карта табылмады" | Invalid card_id or not user's card | Verify card exists and belongs to user |
| "Қаразатыңыз жеткіліксіз" | balance < total_amount | Use card with sufficient balance |
| 404 on checkout | Route not registered | Restart Flask server |
| Cart not cleared | Transaction not committed | Check conn.commit() in code |
| Cards not showing | No cards for user in DB | Insert test cards with correct user_id |

## Testing Commands

```bash
# Initialize fresh database
rm -f kazprice.db && sqlite3 kazprice.db < db_init.sql

# Run automated tests
python3 test_checkout.py

# Test with curl (get checkout page - requires session)
curl -X GET http://127.0.0.1:5000/checkout \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json"

# Test payment API
curl -X POST http://127.0.0.1:5000/process_payment \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"card_id": 1}'
```

## Response Examples

### Successful Payment
```json
{
    "status": "success",
    "message": "Төлем сәтті жасалды",
    "new_balance": 2446520,
    "total_paid": 1853480
}
```

### Insufficient Balance
```json
{
    "status": "error",
    "message": "Қаразатыңыз жеткіліксіз"
}
```

### Card Not Found
```json
{
    "status": "error",
    "message": "Карта табылмады"
}
```

## Performance Notes

- Delivery cost is hardcoded (no DB lookup)
- Card balance lookup is a single SELECT query
- Payment deduction uses single UPDATE query
- Session cart clearing is in-memory operation
- No N+1 queries (all product data fetched once)

## Audit Trail Recommendation

For production, add logging:
```python
import logging

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # ... existing code ...
    
    # Log transaction
    logging.info(f"Payment: user={user_id}, card={card_id}, amount={total_amount}, status=success")
```

