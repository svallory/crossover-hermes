# Products with Actual Promotional Benefits

This document lists products that offer tangible benefits to customers through promotions, as opposed to urgency marketing tactics that create psychological pressure without providing actual advantages.

## Distinction
- **Promotional Benefits**: Discounts, free items, bundle deals, BOGO offers
- **Urgency Marketing**: "Limited stock", "Hurry", "Only a few left" (no actual benefit)

## Products with Promotional Benefits

### 1. CBG9876 - Canvas Beach Bag
- **Price**: $24
- **Category**: Bags
- **Description**: Pack your essentials in style with our canvas beach bag. Spacious and durable, this bag features a nautical-inspired print and interior pockets for organization. Perfectly sized for a day at the beach or a weekend getaway.
- **Promotion Text**: "Buy one, get one 50% off!"
- **Promotion Type**: BOGO Discount

```python
PromotionSpec(
    conditions=PromotionConditions(
        min_quantity=2,
        product_ids=["CBG9876"]
    ),
    effects=PromotionEffects(
        apply_discount=ApplyDiscount(
            to_product_id="CBG9876",
            type="percentage",
            amount=50.0,
            apply_to="second_item"
        )
    )
)
```

### 2. QTP5432 - Quilted Tote
- **Price**: $29
- **Category**: Bags
- **Description**: Carry your essentials in style with our quilted tote bag. This spacious bag features a classic quilted design, multiple interior pockets, and sturdy handles. A chic and practical choice for work, travel, or everyday use.
- **Promotion Text**: "Limited-time sale - get 25% off!"
- **Promotion Type**: Percentage Discount

```python
PromotionSpec(
    conditions=PromotionConditions(
        product_ids=["QTP5432"]
    ),
    effects=PromotionEffects(
        apply_discount=ApplyDiscount(
            to_product_id="QTP5432",
            type="percentage",
            amount=25.0
        )
    )
)
```

### 3. TLR5432 - Tailored Suit
- **Price**: $55
- **Category**: Men's Clothing
- **Description**: Exude confidence and professionalism with our tailored suit. Crafted from premium wool, this suit features a sleek, modern fit and impeccable tailoring. Perfect for important meetings, job interviews, or formal events.
- **Promotion Text**: "Limited-time sale - get the full suit for the price of the blazer!"
- **Promotion Type**: Bundle Deal

```python
PromotionSpec(
    conditions=PromotionConditions(
        product_ids=["TLR5432"]
    ),
    effects=PromotionEffects(
        apply_discount=ApplyDiscount(
            to_product_id="TLR5432",
            type="percentage",
            amount=50.0  # Assuming blazer is ~50% of suit price
        )
    )
)
```

### 4. PLV8765 - Plaid Flannel Vest
- **Price**: $42
- **Category**: Men's Clothing
- **Description**: Layer up with our plaid flannel vest. This cozy vest features a classic plaid pattern and is crafted from soft, warm flannel. Perfect for adding a touch of ruggedness to your casual or outdoor looks.
- **Promotion Text**: "Buy one, get a matching plaid shirt at 50% off!"
- **Promotion Type**: Bundle Discount

```python
PromotionSpec(
    conditions=PromotionConditions(
        product_combination=["PLV8765", "PLD9876"]  # Assuming PLD9876 is the matching plaid shirt
    ),
    effects=PromotionEffects(
        apply_discount=ApplyDiscount(
            to_product_id="PLD9876",
            type="percentage",
            amount=50.0
        )
    )
)
```

### 5. FLD9876 - Floral Maxi Dress
- **Price**: $56
- **Category**: Women's Clothing
- **Description**: Embrace the blooming season with our floral maxi dress. This breezy, lightweight dress features a vibrant floral pattern and a flattering silhouette that flows gracefully with every step. Perfect for garden parties, beach vacations, or romantic evenings.
- **Promotion Text**: "Act now and get 20% off!"
- **Promotion Type**: Percentage Discount

```python
PromotionSpec(
    conditions=PromotionConditions(
        product_ids=["FLD9876"]
    ),
    effects=PromotionEffects(
        apply_discount=ApplyDiscount(
            to_product_id="FLD9876",
            type="percentage",
            amount=20.0
        )
    )
)
```

### 6. BMX5432 - Bomber Jacket (Women's)
- **Price**: $62.99
- **Category**: Women's Clothing
- **Description**: Channel your inner rebel with our bomber jacket. Crafted from soft, lightweight material, this jacket features a classic bomber silhouette and a trendy, cropped length. Perfect for layering or making a statement on its own.
- **Promotion Text**: "Buy now and get a free matching beanie!"
- **Promotion Type**: Free Item

```python
PromotionSpec(
    conditions=PromotionConditions(
        product_ids=["BMX5432"]
    ),
    effects=PromotionEffects(
        free_items=1,
        free_item_id="CHN0987"  # Assuming this is a matching beanie
    )
)
```

### 7. KMN3210 - Knit Mini Dress
- **Price**: $53
- **Category**: Women's Clothing
- **Description**: Effortless and chic, our knit mini dress is a must-have for your wardrobe. Crafted from a soft, stretchy knit material, this form-fitting dress features a flattering silhouette and a trendy, mini length. Perfect for date nights, girls' nights out, or dressing up or down.
- **Promotion Text**: "Limited-time sale - get two for the price of one!"
- **Promotion Type**: BOGO Free

```python
PromotionSpec(
    conditions=PromotionConditions(
        min_quantity=2,
        product_ids=["KMN3210"]
    ),
    effects=PromotionEffects(
        free_items=1,
        free_item_id="KMN3210"
    )
)
```

## Summary

**7 products** offer actual promotional benefits to customers:
- **3 products** with percentage discounts (20-25% off)
- **2 products** with BOGO deals (50% off second item, or buy 2 get 1 free)
- **1 product** with a free item offer
- **1 product** with a bundle deal

These promotions provide tangible value to customers, unlike urgency marketing tactics that only create psychological pressure without offering actual benefits.