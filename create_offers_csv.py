#!/usr/bin/env python3
"""Script to create emails-for-offers.csv with comprehensive test data."""

import csv

# Define all the email data
emails_data = [
    ["email_id", "subject", "message", "classification", "expected_behavior"],
    [
        "E024",
        "Beach Bag BOGO Deal",
        "Hi! I saw that you have a buy one get one 50% off deal on the CBG9876 Canvas Beach Bag. My sister and I are planning a beach vacation next month and we both need new beach bags. Can I order 2 of them to take advantage of this promotion? Thanks, Sarah",
        "order",
        "Should process order for 2 beach bags with BOGO 50% discount applied (total: $36 instead of $48)",
    ],
    [
        "E025",
        "Question about Quilted Tote Sale",
        "Good morning, I'm interested in the QTP5432 Quilted Tote that's on sale for 25% off. Is this a limited-time offer? How long will this promotion last? I'm considering it for work but want to make sure I don't miss the discount. Thank you!",
        "inquiry",
        "Should answer questions about the 25% discount promotion and encourage purchase",
    ],
    [
        "E026",
        "Tailored Suit Bundle Deal Order",
        "Hello, I need a new suit for job interviews and I noticed your TLR5432 Tailored Suit has a special deal where I get the full suit for the price of just the blazer. This sounds perfect for my budget! Please process an order for 1 suit. My name is Michael and this would really help me land my dream job. Thanks!",
        "order",
        "Should process order for tailored suit with bundle discount applied (50% off total price)",
    ],
    [
        "E027",
        "Plaid Vest and Shirt Combo Question",
        "Hey there, I'm looking at the PLV8765 Plaid Flannel Vest and I see there's a promotion where I can get a matching plaid shirt at 50% off if I buy the vest. What's the product ID for the matching shirt? I want to make sure I get the right combination. Also, do they come in the same size? Thanks, Jake",
        "inquiry",
        "Should provide information about the matching plaid shirt (PLD9876) and explain the bundle promotion",
    ],
    [
        "E028",
        "Floral Dress 20% Off Order",
        "Hi, I absolutely love the FLD9876 Floral Maxi Dress and I see it's 20% off right now! Perfect timing since I have a garden party coming up next weekend. Please send me 1 dress. I'm so excited about this purchase and the discount makes it even better! Best regards, Emma",
        "order",
        "Should process order for floral dress with 20% discount applied",
    ],
    [
        "E029",
        "Bomber Jacket Free Beanie Inquiry",
        "Good afternoon, I'm interested in the BMX5432 Bomber Jacket for women. The description mentions that I get a free matching beanie with purchase - is this still available? What color options do you have for both the jacket and the beanie? I love getting free items with my purchases! Thank you, Lisa",
        "inquiry",
        "Should confirm free beanie offer and provide color options for both items",
    ],
    [
        "E030",
        "Two for One Dress Deal",
        "Hello! I'm organizing outfits for my girls' night outs and I noticed the KMN3210 Knit Mini Dress has a buy 2 get 1 free promotion. This is exactly what I need! Can I order 2 dresses to get the third one free? I want to make sure I understand the deal correctly before placing my order. Thanks so much, Rachel",
        "order",
        "Should process order for 2 knit dresses with 1 free dress included (total: $53 for 3 dresses)",
    ],
    [
        "E031",
        "Pregunta sobre Ofertas de Bolsos",
        "Hola, he visto que tienen ofertas especiales en algunas bolsas. ¿Podrían decirme cuáles son las promociones actuales en la categoría de bolsos? Estoy especialmente interesada en la CBG9876 y la QTP5432. ¿Estas ofertas están disponibles para envío internacional? Gracias, María",
        "inquiry",
        "Should respond in Spanish explaining bag promotions (BOGO for beach bag, 25% off quilted tote) and confirm international shipping",
    ],
    [
        "E032",
        "Vague Beach Bag Inquiry",
        "Hi there, I heard from a friend that you guys have some kind of deal on beach bags? I'm not sure what exactly but she said it was a really good offer. Could you tell me more about it? I might be interested in getting a couple for my family. Thanks!",
        "inquiry",
        "Should identify this refers to CBG9876 beach bag BOGO offer and explain the promotion details",
    ],
    [
        "E033",
        "Just the Vest Please",
        "Hello, I'd like to order the plaid flannel vest. I think the product code was something like PLV... 8765? Just the vest for now, thanks.",
        "order",
        "Should process order for PLV8765 vest only, but mention the available bundle promotion with matching shirt",
    ],
    [
        "E034",
        "Partial Bundle Order",
        "Hi, I want to order both the plaid vest PLV8765 and the matching shirt. I think there was some kind of combo deal? Please let me know the total cost. Thanks, Alex",
        "order",
        "Should process order for both PLV8765 vest and PLD9876 shirt with 50% discount on the shirt",
    ],
    [
        "E035",
        "Single Item from Bundle Inquiry",
        "Good morning, I'm interested in learning more about your plaid shirts. I saw one mentioned as part of a promotion with a vest? Could you tell me about the shirt itself and what the deal is? I might just want the shirt.",
        "inquiry",
        "Should explain the plaid shirt (PLD9876) and mention it's part of a bundle promotion with the vest, encouraging the bundle purchase",
    ],
    [
        "E036",
        "Confused About Dress Deal",
        "Hey, I'm looking at some dresses on your site and I think I saw something about a special offer on one of them? It was a knit dress I think? Can you help me figure out what the deal was?",
        "inquiry",
        "Should identify this refers to KMN3210 knit mini dress buy-2-get-1-free promotion and explain the details",
    ],
    [
        "E037",
        "One Beach Bag Only",
        "Hi, I just need one canvas beach bag for my upcoming trip. I think the product ID is CBG9876. How much would that be? Thanks!",
        "order",
        "Should process order for 1 beach bag at regular price but mention the BOGO promotion if they want 2",
    ],
    [
        "E038",
        "Jacket Without Beanie",
        "Hello, I'd like to purchase the women's bomber jacket BMX5432. Just the jacket please, I already have plenty of hats. What's the price?",
        "order",
        "Should process order for bomber jacket and mention the free beanie offer (even if customer doesn't want it)",
    ],
    [
        "E039",
        "Suit Inquiry Vague",
        "Hi, I'm job hunting and need a professional suit. I think I saw you had some kind of special pricing on suits? Could you tell me more about your suit options and any current deals?",
        "inquiry",
        "Should identify TLR5432 tailored suit and explain the bundle deal (full suit for blazer price)",
    ],
    [
        "E040",
        "Tote Bag Discount Question",
        "Good afternoon, I'm interested in a quilted tote bag for work. I believe there might be a discount available? Could you confirm the current price and any promotions? Thank you.",
        "inquiry",
        "Should confirm QTP5432 quilted tote has 25% off promotion and provide discounted price",
    ],
    [
        "E041",
        "Multiple Beach Bags Vague",
        "Hi, my family is going on vacation and we need several beach bags. I heard you might have a good deal if we buy more than one? What would be the best option for us?",
        "inquiry",
        "Should recommend CBG9876 beach bags with BOGO 50% off promotion for multiple bags",
    ],
    [
        "E042",
        "Dress for Party",
        "Hello! I need a dress for a garden party next month. I love floral patterns and I think I saw you had a maxi dress with some kind of special price? Could you help me find it?",
        "inquiry",
        "Should identify FLD9876 floral maxi dress with 20% off promotion and provide details",
    ],
    [
        "E043",
        "Wrong Product ID",
        "Hi, I want to order the beach bag with the special offer. I think the code is CBG9867? Or maybe CBG9876? Anyway, I want 2 of them for the deal. Thanks!",
        "order",
        "Should correct the product ID to CBG9876 and process order for 2 beach bags with BOGO promotion",
    ],
    [
        "E044",
        "Beanie Color Question",
        "Hi, I'm planning to buy the bomber jacket that comes with a free beanie. What colors are available for the beanie? I want to make sure it matches my style. The jacket code is BMX5432.",
        "inquiry",
        "Should explain the free beanie offer with BMX5432 bomber jacket and provide available beanie colors",
    ],
    [
        "E045",
        "Suit Components Question",
        "Hello, I'm interested in your tailored suit deal. Does the 'full suit for blazer price' include pants and jacket? Or are there other pieces included? Product TLR5432.",
        "inquiry",
        "Should explain what's included in the TLR5432 tailored suit bundle deal and confirm all components",
    ],
    [
        "E046",
        "International Shipping Dress",
        "Hi, I'm located in Canada and interested in the knit mini dress with the buy-2-get-1-free offer. Do you ship internationally and does the promotion apply? Product KMN3210.",
        "inquiry",
        "Should confirm international shipping availability and that the KMN3210 promotion applies to international orders",
    ],
    [
        "E047",
        "Price Check Multiple Items",
        "Good morning, could you give me the total cost for: 1 quilted tote bag, 1 floral dress, and 2 beach bags? I want to take advantage of any current promotions. Thanks!",
        "inquiry",
        "Should calculate total with all applicable promotions: QTP5432 (25% off), FLD9876 (20% off), CBG9876 (BOGO 50% off)",
    ],
    [
        "E048",
        "Gift Purchase Inquiry",
        "Hi, I'm buying gifts for my daughters. One wants a dress for parties and the other needs a work bag. I think both items might have promotions? Could you help me find the best deals?",
        "inquiry",
        "Should recommend FLD9876 dress (20% off) or KMN3210 dress (buy-2-get-1) and QTP5432 tote (25% off) based on needs",
    ],
]

# Write to CSV file
with open("data/emails-for-offers.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(emails_data)

print(f"Created emails-for-offers.csv with {len(emails_data)-1} test emails")
