# Checkout System - Architecture & Data Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ cart.html    │  │checkout.html │  │payment.html  │           │
│  │              │  │              │  │              │           │
│  │ "Төлеуге"    │  │ Delivery:    │  │ Card Selector│           │
│  │ өту button   │──│ 1500₸        │──│ Radio buttons│           │
│  │              │  │              │  │              │           │
│  │ Items + Qty  │  │ Total calc   │  │ Balance check│           │
│  │              │  │              │  │              │           │
│  │ Remove item  │  │ Edit address │  │ Payment fetch│           │
│  │              │  │              │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ▲                   ▲                  ▲                 │
│         │ session.cart      │ session.cart    │ POST JSON        │
│         │                   │                 │                 │
└─────────┼───────────────────┼─────────────────┼─────────────────┘
          │                   │                 │
          │                   │                 │ fetch('/process_payment')
          │                   │                 │
┌─────────▼───────────────────▼─────────────────▼─────────────────┐
│                         SERVER (Flask)                           │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐        │
│  │  /cart     │  │ /checkout  │  │ /payment            │        │
│  │ (GET)      │  │ (GET)      │  │ (GET)               │        │
│  │            │  │            │  │                     │        │
│  │ - Check    │  │ - Check    │  │ - Check user_id     │        │
│  │   cart     │  │   user_id  │  │ - Get user's cards  │        │
│  │ - Render   │  │ - Get cart │  │ - Calc total        │        │
│  │   items    │  │ - Get      │  │ - Render cards      │        │
│  │ - Session: │  │   products │  │ - Session: cart     │        │
│  │   cart     │  │ - Delivery │  │                     │        │
│  │            │  │   = 1500₸  │  └─────────────────────┘        │
│  │            │  │ - Calc     │                                 │
│  │            │  │   total    │   ┌─────────────────────┐       │
│  │            │  │ - Render   │   │ /process_payment    │       │
│  │            │  │   checkout │   │ (POST)              │       │
│  │            │  │ - Link to  │   │                     │       │
│  │            │  │   /payment │   │ Request: {card_id}  │       │
│  │            │  │            │   │                     │       │
│  │            │  │            │   │ 1. Get card         │       │
│  │            │  │            │   │ 2. Validate user    │       │
│  │            │  │            │   │ 3. Check balance    │       │
│  │            │  │            │   │ 4. IF OK:           │       │
│  │            │  │            │   │    - Deduct amount  │       │
│  │            │  │            │   │    - Clear cart     │       │
│  │            │  │            │   │    - Return success │       │
│  │            │  │            │   │ 5. IF ERROR:        │       │
│  │            │  │            │   │    - Return error   │       │
│  │            │  │            │   │    - Keep cart      │       │
│  │            │  │            │   │                     │       │
│  │            │  │            │   └─────────────────────┘       │
│  └────────────┘  └────────────┘                                 │
│                                                                   │
└────────────────────────────────────────────────────────────────────┘
          ▲                                           ▲
          │ SQL queries                              │ SQL queries
          │                                          │
┌─────────▼──────────────────────────────────────────▼──────────┐
│                       SQLite Database                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ users        │  │ products     │  │ cards               │  │
│  │              │  │              │  │                     │  │
│  │ id (PK)      │  │ id (PK)      │  │ id (PK)             │  │
│  │ name         │  │ name         │  │ user_id (FK)        │  │
│  │ email        │  │ color        │  │ card_name           │  │
│  │ password     │  │ storage      │  │ balance ◄───────┐   │  │
│  │ phone        │  │ image_url    │  │ created_at       │   │  │
│  │ address      │  │              │  │                 │   │  │
│  │              │  └──────────────┘  └─────────────────┼───┘  │
│  └──────────────┘                                       │       │
│         ▲                                               │       │
│         │ User registration                    UPDATED here    │
│         │ User authentication                        │       │
│         │                                            │       │
│  ┌──────┴──────────┐  ┌──────────────┐  ┌───────────┴──────┐ │
│  │ prices          │  │ stores       │  │ Reference        │ │
│  │                 │  │              │  │ Data:            │ │
│  │ id (PK)         │  │ id (PK)      │  │                  │ │
│  │ product_id (FK) │  │ name         │  │ Kaspi: 4.3M      │ │
│  │ store_id (FK)   │  │              │  │ Halyk: 2.1M      │ │
│  │ price ◄─────────┼──┘              │  │ BCC: 650k        │ │
│  │                 │                  │  │                  │ │
│  └─────────────────┘                  │  └──────────────────┘ │
│                                        │                       │
│  Product 1 = 925,990₸                  │                       │
│  Product 2 = 934,990₸                  │                       │
│                                        │                       │
└────────────────────────────────────────┴───────────────────────┘
```

## Payment Flow (Sequence Diagram)

```
User              Browser              Server              Database
  │                  │                   │                    │
  │ Click            │                   │                    │
  ├─"Төлеуге өту"───>│ GET /checkout     │                    │
  │                  ├──────────────────>│ Check user_id      │
  │                  │                   ├───────────────────>│
  │                  │                   │ Get cart items     │ SELECT products
  │                  │                   │ Get prices         │
  │                  │                   │ Calc total         │
  │                  │ return checkout   │                    │
  │                  │<──────────────────┤                    │
  │ View checkout    │                   │                    │
  │                  │                   │                    │
  │ Click            │                   │                    │
  ├─"Төлем          │ GET /payment       │                    │
  │ жасауға өту"──→  ├──────────────────>│ Check user_id      │
  │                  │                   ├───────────────────>│
  │                  │                   │ GET user's cards   │ SELECT cards
  │                  │                   │ Get card names/    │  WHERE user_id=?
  │                  │                   │ balances           │
  │                  │ return payment    │                    │
  │                  │<──────────────────┤                    │
  │ Select card      │                   │                    │
  │ Check balance    │ (JS local check)  │                    │
  │ Button enabled   │                   │                    │
  │                  │                   │                    │
  │ Click            │                   │                    │
  ├─"Төлеу"────────>│ POST /process_    │                    │
  │                  │ payment           ├──────────────────>│
  │                  │ {card_id: 1}      │ SELECT balance     │ SELECT card
  │                  │                   │ WHERE id=? AND     │  WHERE user_id=?
  │                  │                   │ user_id=?          │
  │ Processing...    │ [Loading state]   │                   │
  │                  │                   │ Validate:          │
  │                  │                   │ - Card exists ✓    │
  │                  │                   │ - Belongs to user ✓
  │                  │                   │ - balance >= total ✓
  │                  │                   │                    │
  │                  │                   ├───────────────────>│
  │                  │                   │ UPDATE cards       │ UPDATE cards
  │                  │                   │ balance -= total   │  SET balance=?
  │                  │                   │ COMMIT             │
  │                  │                   │<───────────────────┤
  │                  │ {status:          │                    │
  │                  │  "success"}       │ Clear session cart │
  │                  │<──────────────────┤                    │
  │ Success page     │                   │                    │
  │ Redirect /main   │ Redirect /main    │                    │
  │                  │<───────────────────                    │
  ├─────────────────>│                   │                    │
  │ View products    │ Render /main      │                    │
  │ Cart is empty    │<──────────────────┤                    │
  │                  │                   │                    │


ALTERNATIVE: Insufficient Balance

User              Browser              Server              Database
  │                  │                   │                    │
  │ Select card      │                   │                    │
  ├─(JS runs balance check, shows warning, button disabled)     │
  │                  │                   │                    │
  │ Can't click      │                   │                    │
  │ "Төлеу" button   │                   │                    │
  │                  │                   │                    │

OR if JS disabled:

  │ Click            │                   │                    │
  ├─"Төлеу"────────>│ POST /process_    │                    │
  │                  │ payment           ├──────────────────>│
  │                  │ {card_id: 1}      │ SELECT balance     │ SELECT card
  │                  │                   │                    │
  │ Error message    │ {status: "error", │ balance < total ✗  │
  │ "Қаражатыңыз    │  message: "..."}  │                    │
  │  жеткіліксіз"}   │<──────────────────┤ NO UPDATE         │
  │                  │ 400 Bad Request   │ Return error       │
  │ Cart intact      │                   │                    │
  │ Try again        │                   │                    │
  │                  │                   │                    │
```

## Data Flow - Successful Payment

```
Session State Changes:
┌─────────────────────────────────────────────────────────┐
│ BEFORE:                                                 │
│ session = {                                             │
│   'user_id': 1,                                        │
│   'cart': {'1': 2}  ← 2 units of product 1            │
│ }                                                       │
│                                                         │
│ POST /process_payment with card_id=1                  │
│                       ↓                                │
│ Database Update:                                       │
│ UPDATE cards SET balance = 2446520 WHERE id=1         │
│ (was 4300000, deducted 1853480)                       │
│                       ↓                                │
│ AFTER:                                                 │
│ session = {                                            │
│   'user_id': 1,                                       │
│   'cart': {}  ← CLEARED                               │
│ }                                                      │
└─────────────────────────────────────────────────────────┘

Response to Client:
{
  "status": "success",
  "message": "Төлем сәтті жасалды",
  "new_balance": 2446520,
  "total_paid": 1853480
}

Client Action:
window.location.href = '/main'  ← Redirect to main page
```

## Data Calculation Example

```
Cart Contents:
├─ Product 1 (iPhone 17 Orange)
│  ├─ Unit Price: 925,990₸
│  ├─ Quantity: 2
│  └─ Subtotal: 1,851,980₸
│
├─ Delivery
│  └─ Fixed Cost: 1,500₸
│
└─ TOTAL: 1,853,480₸

Card Balance Validation:
Selected Card: Kaspi Gold
Available: 4,300,000₸
Required: 1,853,480₸
Status: ✓ APPROVED (balance > total)

After Payment:
New Balance = 4,300,000 - 1,853,480 = 2,446,520₸
```

## Error Handling Tree

```
POST /process_payment
│
├─ Check user_id
│  ├─ NOT FOUND → 401 Unauthorized
│  │             "Кіруіңіз қажет"
│  │
│  └─ FOUND → Continue
│
├─ Check cart
│  ├─ EMPTY → 400 Bad Request
│  │          "Себет бос"
│  │
│  └─ NOT EMPTY → Continue
│
├─ Validate card_id parameter
│  ├─ MISSING → 400 Bad Request
│  │            "Картасын таңдаңыз"
│  │
│  └─ PROVIDED → Continue
│
├─ Query card from database
│  ├─ NOT FOUND → 404 Not Found
│  │              "Карта табылмады"
│  │
│  ├─ DOESN'T BELONG TO USER → 404 Not Found
│  │                            "Карта табылмады"
│  │
│  └─ FOUND & BELONGS TO USER → Continue
│
├─ Validate balance
│  ├─ balance < total_amount → 400 Bad Request
│  │                           "Қаражатыңыз жеткіліксіз"
│  │                           (NO DATABASE UPDATE)
│  │
│  └─ balance >= total_amount → Continue
│
├─ Update database
│  ├─ UPDATE cards balance
│  ├─ COMMIT transaction
│  └─ Clear session cart
│
└─ Return 200 OK
   {
     "status": "success",
     "message": "Төлем сәтті жасалды",
     "new_balance": <new_value>,
     "total_paid": <amount>
   }
```

