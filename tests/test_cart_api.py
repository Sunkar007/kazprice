from app import app

with app.test_client() as c:
    # prepare a cart with two items
    with c.session_transaction() as sess:
        sess['cart'] = {'11': 2, '22': 1}

    # update product 11 -> 0 (should remove it)
    r = c.post('/update_cart_quantity', json={'product_id': 11, 'quantity': 0})
    print('/update_cart_quantity 11->0 ->', r.status_code, r.get_json())

    # remove 22 using remove_from_cart
    r2 = c.post('/remove_from_cart/22')
    print('/remove_from_cart/22 ->', r2.status_code, r2.get_json())

    # clear cart
    r3 = c.post('/clear_cart')
    print('/clear_cart ->', r3.status_code, r3.get_json())
