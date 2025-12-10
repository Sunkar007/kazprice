# Bank Cards Functionality Implementation

## Overview
Full virtual "Bank Cards" system added to the Flask KazPrice project. Users can:
- Add and save multiple virtual bank cards with masked card numbers
- Pay for orders using saved cards with balance validation
- View card balances on their profile
- See order history with payment details

---

## 1. Database Schema

### New Tables

#### `bank_cards` table
```sql
CREATE TABLE bank_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_name TEXT NOT NULL,           -- e.g., "Kaspi Gold", "Halyk Bank"
    card_number TEXT NOT NULL,         -- Masked version (e.g., "**** 1234")
    balance INTEGER NOT NULL,          -- Virtual balance in tenge
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

#### `order_history` table
```sql
CREATE TABLE order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount INTEGER NOT NULL,     -- Amount paid
    card_id INTEGER,                   -- Which card was used
    card_name TEXT,                    -- Card name at time of purchase
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (card_id) REFERENCES bank_cards (id)
);
```

### Sample Data
The system includes initial sample cards for testing:
```sql
INSERT INTO bank_cards (user_id, card_name, card_number, balance)
VALUES
(1, 'Kaspi Gold', '**** 4300', 4300000),
(1, 'Halyk Bank', '**** 2100', 2100000);
```

---

## 2. Backend Routes (app.py)

### `/profile` — Display Bank Cards
**Method**: GET  
**Description**: Updated to show user's saved bank cards with:
- Card name
- Masked card number
- Current balance
- Creation date
- "Add Card" button

**Route Handler**:
```python
@app.route('/profile')
def profile():
    # Fetches user data + all bank_cards for current user
    # Passes to profile.html template
```

### `/add_card` — Add New Card
**Methods**: GET, POST

**GET**: Display form with fields:
- Card Name (text)
- Card Number (text, normalized to digits)
- Initial Balance (number)

**POST**: 
- Validates input:
  - Card name required
  - Card number must have ≥4 digits
  - Balance must be non-negative integer
- Masks card number to "**** XXXX" (last 4 digits only)
- Inserts into `bank_cards` table
- Redirects to `/profile` with success message

**Route Handler**:
```python
@app.route('/add_card', methods=['GET', 'POST'])
def add_card():
    # Form validation + masking logic
    # INSERT INTO bank_cards with masked number
```

### `/payment` — Select Card for Payment
**Method**: GET  
**Description**: Updated to load all user's `bank_cards` and display as radio button options with:
- Card name
- Masked number
- Available balance
- Balance validation message if insufficient

**Route Handler**:
```python
@app.route('/payment')
def payment():
    # SELECT card_name, card_number, balance FROM bank_cards
    # Pass to payment.html for selection
```

### `/process_payment` — Deduct & Record Payment
**Method**: POST (AJAX)  
**Description**: 
- Validates card selection
- Checks balance >= total_amount
- Deducts from card balance
- Records order in `order_history`
- Clears session cart
- Returns JSON response

**Logic**:
1. Get total = cart_total + delivery_cost
2. SELECT balance from bank_cards WHERE id = card_id
3. IF balance < total: return error
4. UPDATE bank_cards SET balance = balance - total
5. INSERT INTO order_history (payment record)
6. Clear session['cart']
7. Return success JSON

---

## 3. Templates

### `profile.html` (Updated)
Added new "Банк карттар" (Bank Cards) section with:
- List of user's saved cards (name, masked number, balance)
- "Карта қосу" (Add Card) button linking to `/add_card`
- Existing profile controls preserved (Edit Profile, Logout)

**Structure**:
```html
<!-- Bank Cards Section -->
<div class="card p-3 shadow-sm">
  <h5>Банк карттар</h5>
  <!-- List of bank_cards with balance -->
  <!-- Add Card button -->
</div>
```

### `add_card.html` (New)
Form to add new virtual card with:
- **Card Name** input (Kaspi Gold, Halyk Bank, BCC, etc.)
- **Card Number** input (full digits, masked on save)
- **Balance** input (initial virtual funds)
- Validation messages (card name required, digits required, balance non-negative)
- Cancel / Add buttons

### `payment.html` (Updated)
Updated card selection to show:
- Card name
- **Masked number** (e.g., "**** 1234")
- Available balance
- Balance validation warning if insufficient
- Selected card name + masked number in right sidebar summary

---

## 4. Key Features

### Card Masking
- Full card number stored as masked version (e.g., "**** 1234")
- Only last 4 digits visible to user
- All card numbers automatically masked when saved

### Balance Validation
- Payment blocked if card balance < total order amount
- Clear error message shown: "Қаражатыңыз жеткіліксіз" (Insufficient funds)
- Balance check happens before payment processing

### Order Recording
- Each successful payment creates `order_history` entry:
  - user_id
  - total_amount paid
  - card_id used
  - card_name (snapshot)
  - created_at timestamp

### Database Migrations
- `ensure_user_columns()` function in app.py checks and creates tables on startup
- Automatically creates `bank_cards` and `order_history` tables if missing
- Ensures backward compatibility with existing databases

---

## 5. User Flow

### Adding a Card
1. User logs in → goes to Profile
2. Clicks "Карта қосу" (Add Card)
3. Fills form: name, full card number, initial balance
4. Submits → system masks number → saves to DB
5. Success message → redirects to Profile (card now visible)

### Paying with a Card
1. User adds items to cart → clicks "Төлеуге өту" (Checkout)
2. Reviews order → clicks "Төлем жасауға өту" (Proceed to Payment)
3. Selects saved card from radio buttons
4. System shows masked number + balance check
5. If balance sufficient → clicks "Төлеу" (Pay)
6. If balance insufficient → shows warning, Pay button disabled
7. On success → balance deducted → order recorded → redirects to main page

---

## 6. API / JSON Responses

### `/process_payment` Success Response
```json
{
  "status": "success",
  "message": "Төлем сәтті жасалды",
  "new_balance": 1500000,
  "total_paid": 2800000
}
```

### `/process_payment` Error Response
```json
{
  "status": "error",
  "message": "Қаражатыңыз жеткіліксіз"
}
```

---

## 7. Testing Checklist

✅ Bank cards table created with proper schema  
✅ Order history table created for payment recording  
✅ `/add_card` form validates card name, number, balance  
✅ Card number masked to "**** XXXX" on save  
✅ Profile displays all user cards with balances  
✅ Payment page loads all user cards as radio options  
✅ Balance validation prevents insufficient balance payments  
✅ `/process_payment` deducts balance and clears cart  
✅ Order history records each payment  
✅ All templates extend base.html and use Bootstrap classes  

---

## 8. Code Notes

### Backward Compatibility
- Legacy `cards` table preserved for existing installations
- New `bank_cards` table used for all new functionality
- `payment()` and `process_payment()` updated to use `bank_cards`

### Security Considerations
- Card numbers always masked (never stored in full)
- Balance deduction happens in single transaction
- User_id validated before allowing card operations
- AJAX payment requires JSON, no form injection risk

### Internationalization
- All user-facing text in Kazakh (with some Russian fallback)
- Template strings use Jinja2 filters for currency formatting

---

## 9. Files Modified

1. **db_init.sql** — Added bank_cards and order_history table creation + sample data
2. **app.py** — Added ensure_user_columns() migration logic + /add_card route + updated /profile, /payment, /process_payment
3. **templates/profile.html** — Added Bank Cards section with Add Card button
4. **templates/add_card.html** — NEW form template for adding cards
5. **templates/payment.html** — Updated to use bank_cards table + show masked numbers

---

## 10. Future Enhancements

- [ ] Delete card button on profile
- [ ] Edit card name / initial balance
- [ ] Export order history as CSV
- [ ] Card type icons (Visa, Mastercard, etc.)
- [ ] Card expiry tracking
- [ ] Transaction details page
- [ ] Refund logic

---

**Implementation Date**: December 11, 2025  
**Status**: ✅ Complete and tested
