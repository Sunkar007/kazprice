#!/usr/bin/env python3
"""
Test script for the checkout flow:
- Login
- Add to cart
- Go to checkout
- Go to payment
- Process payment
"""
import sys
sys.path.insert(0, '/Users/sunkar/kazprice_project')

from app import app
import json

def test_checkout_flow():
    client = app.test_client()
    
    # 1. Register a test user
    print("1. Registering test user...")
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@test.kz',
        'password': 'password123'
    }, follow_redirects=False)
    print(f"   Register response: {response.status_code}")
    
    # 2. Login
    print("2. Testing login...")
    with client:
        response = client.post('/login', data={
            'email': 'test@test.kz',
            'password': 'password123'
        }, follow_redirects=False)
        print(f"   Login response: {response.status_code}")
        
        # Get session user_id
        with client.session_transaction() as sess:
            user_id = sess.get('user_id')
            print(f"   Session user_id: {user_id}")
            
            if not user_id:
                print("   ✗ Login failed - no user_id in session")
                return
            
            # 3. Add to cart
            print("\n3. Adding to cart...")
            sess['cart'] = {'1': 2}  # 2 units of product 1
            
        # 4. Test checkout route
        print("\n4. Testing /checkout route...")
        response = client.get('/checkout')
        print(f"   Checkout response: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Checkout page loaded successfully")
            if b'1500' in response.data:
                print("   ✓ Delivery cost (1500) found in response")
        else:
            print(f"   ✗ Checkout failed: {response.data[:100]}")
        
        # 5. Test payment route
        print("\n5. Testing /payment route...")
        response = client.get('/payment')
        print(f"   Payment response: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Payment page loaded successfully")
            if b'Kaspi Gold' in response.data or b'card' in response.data.lower():
                print("   ✓ Cards found in response")
        else:
            print(f"   ✗ Payment failed: {response.data[:100]}")
        
        # 6. Test process_payment with valid card
        print("\n6. Testing /process_payment (success case)...")
        with client.session_transaction() as sess:
            print(f"   Session cart before payment: {sess.get('cart')}")
        
        response = client.post('/process_payment',
            json={'card_id': 1},
            content_type='application/json'
        )
        print(f"   Process payment response: {response.status_code}")
        data = response.get_json()
        print(f"   Response data: {data}")
        
        with client.session_transaction() as sess:
            print(f"   Session cart after payment: {sess.get('cart')}")
        
        if response.status_code == 200 and data.get('status') == 'success':
            print("   ✓ Payment processed successfully!")
        else:
            print(f"   ✗ Payment processing failed")
        
        # 7. Test process_payment with insufficient balance
        print("\n7. Testing /process_payment (insufficient balance case)...")
        with client.session_transaction() as sess:
            sess['cart'] = {'1': 50}  # Very large quantity
        
        response = client.post('/process_payment',
            json={'card_id': 1},
            content_type='application/json'
        )
        print(f"   Response: {response.status_code}")
        data = response.get_json()
        print(f"   Response data: {data}")
        
        if response.status_code == 400 and 'жеткіліксіз' in data.get('message', ''):
            print("   ✓ Correctly rejected due to insufficient balance")
        else:
            print(f"   ✗ Balance check failed")

if __name__ == '__main__':
    test_checkout_flow()
