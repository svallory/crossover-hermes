# Vector Store Semantic Search Analysis

This note summarizes the results of semantic search tests performed on the product vector store. The similarity scores represent L2 distance (lower is better, 0.0 is a perfect match). The vector store uses OpenAI embeddings.

## Test Scenarios and Results:

---

### Query: 'Leather Bifold Wallet'
- **Notes**: Exact name match
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['LTH0976']`
- **Search Results (Top 5)**:
  1. `LTH0976` - 'Leather Bifold Wallet', Score: 0.4659 (EXPECTED)
  2. `SWL2345` - 'Sleek Wallet', Score: 0.8767
  3. `LTH1098` - 'Leather Backpack', Score: 1.0517
  4. `LTH2109` - 'Leather Messenger Bag', Score: 1.0533
  5. `LTH5432` - 'Leather Tote', Score: 1.1590

---

### Query: 'Vibrant Tote bag'
- **Notes**: Exact name with 'bag' suffix
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['VBT2345']`
- **Search Results (Top 5)**:
  1. `VBT2345` - 'Vibrant Tote', Score: 0.4308 (EXPECTED)
  2. `QTP5432` - 'Quilted Tote', Score: 0.9242
  3. `LTH5432` - 'Leather Tote', Score: 0.9774
  4. `SDE2345` - 'Saddle Bag', Score: 1.1055
  5. `CBG9876` - 'Canvas Beach Bag', Score: 1.1448

---

### Query: 'Infinity Scarves'
- **Notes**: Plural query vs. singular product name
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['SFT1098']`
- **Search Results (Top 5)**:
  1. `SFT1098` - 'Infinity Scarf', Score: 0.6082 (EXPECTED)
  2. `VSC6789` - 'Versatile Scarf', Score: 0.9168
  3. `CSH1098` - 'Cozy Shawl', Score: 1.2243
  4. `PTR9876` - 'Patterned Tie', Score: 1.2755
  5. `FNK9876` - 'Fair Isle Sweater', Score: 1.3614

---

### Query: 'leather briefcase'
- **Notes**: Key User Scenario: 'leather briefcase'. Expect LTH2109 (Leather Messenger Bag) as a candidate.
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['LTH2109', 'LTH1098', 'LTH5432']`
- **Search Results (Top 5)**:
  1. `LTH2109` - 'Leather Messenger Bag', Score: 0.7777 (EXPECTED)
     - *Specific log: 'Leather Messenger Bag' (LTH2109) score for 'leather briefcase': 0.7777*
  2. `LTH1098` - 'Leather Backpack', Score: 0.8054 (EXPECTED)
  3. `LTH0976` - 'Leather Bifold Wallet', Score: 0.8960
  4. `LTH5432` - 'Leather Tote', Score: 0.9718 (EXPECTED)
  5. `SBP4567` - 'Sleek Backpack', Score: 1.1450

---

### Query: 'messenger bag'
- **Notes**: Specific query: 'messenger bag'
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['LTH2109']`
- **Search Results (Top 5)**:
  1. `LTH2109` - 'Leather Messenger Bag', Score: 0.7146 (EXPECTED)
  2. `CCB6789` - 'Chic Crossbody', Score: 0.9986
  3. `SDE2345` - 'Saddle Bag', Score: 1.0219
  4. `QTP5432` - 'Quilted Tote', Score: 1.0549
  5. `LTH1098` - 'Leather Backpack', Score: 1.0750

---

### Query: 'messenger bag or briefcase style options'
- **Notes**: Query from email E012
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['LTH2109', 'LTH1098', 'LTH5432']`
- **Search Results (Top 5)**:
  1. `LTH2109` - 'Leather Messenger Bag', Score: 0.8126 (EXPECTED)
  2. `LTH1098` - 'Leather Backpack', Score: 1.0358 (EXPECTED)
  3. `SBP4567` - 'Sleek Backpack', Score: 1.0389
  4. `CCB6789` - 'Chic Crossbody', Score: 1.0603
  5. `QTP5432` - 'Quilted Tote', Score: 1.0882

---

### Query: 'a bag for work'
- **Notes**: Abstract query: 'a bag for work'
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['LTH2109', 'LTH5432', 'LTH1098', 'SBP4567']`
- **Search Results (Top 5)**:
  1. `LTH2109` - 'Leather Messenger Bag', Score: 0.9735 (EXPECTED)
  2. `QTP5432` - 'Quilted Tote', Score: 0.9999
  3. `LTH5432` - 'Leather Tote', Score: 1.0308 (EXPECTED)
  4. `LTH1098` - 'Leather Backpack', Score: 1.0402 (EXPECTED)
  5. `CCB6789` - 'Chic Crossbody', Score: 1.1304

---

### Query: 'slide sandals for men'
- **Notes**: Specific query from email E013
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['SLD7654']`
- **Search Results (Top 5)**:
  1. `SLD7654` - 'Slide Sandals', Score: 0.6784 (EXPECTED)
  2. `CLG4567` - 'Clog Sandals', Score: 0.8402
  3. `SND7654` - 'Strappy Sandals', Score: 0.8994
  4. `SLP7654` - 'Slip-on Sneakers', Score: 1.0824
  5. `MLR0123` - 'Mule Loafers', Score: 1.0981

---

### Query: 'delicious pizza recipe'
- **Notes**: Irrelevant query; expect no good matches or very high distance scores
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: None
- **Search Results (Top 5)**:
  1. `DLD0123` - 'Delightful Dress', Score: 1.5111
  2. `PTD3210` - 'Printed Tunic Dress', Score: 1.5560
  3. `CPJ2345` - 'Cozy Pajama Set', Score: 1.6135
  4. `FRP9876` - 'Fringe Poncho', Score: 1.6366
  5. `PTD8901` - 'Patchwork Denim Jacket', Score: 1.6386
- **Note**: Top score for irrelevant query 'delicious pizza recipe' was 1.5111. (Assertion: score > 0.6 passed)

---

### Query: 'Chunky Knit Beanie'
- **Notes**: Match English name (product CHN0987 was 'Gorro de punto grueso' in E009)
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['CHN0987']`
- **Search Results (Top 5)**:
  1. `CHN0987` - 'Chunky Knit Beanie', Score: 0.4311 (EXPECTED)
  2. `CLF2109` - 'Cable Knit Beanie', Score: 0.7894
  3. `CHN5432` - 'Chunky Knit Sweater', Score: 0.8083
  4. `SKR3210` - 'Ski Sweater', Score: 1.0273
  5. `SFT1098` - 'Infinity Scarf', Score: 1.0880

---

### Query: 'Saddle bag'
- **Notes**: Specific query from email E020
- **Algorithm**: OpenAI Embeddings (L2 Distance)
- **Expected Product IDs**: `['SDE2345']`
- **Search Results (Top 5)**:
  1. `SDE2345` - 'Saddle Bag', Score: 0.6600 (EXPECTED)
  2. `FRP6789` - 'Fringe Crossbody', Score: 1.0859
  3. `LTH2109` - 'Leather Messenger Bag', Score: 1.1163
  4. `QTP5432` - 'Quilted Tote', Score: 1.1368
  5. `CCB6789` - 'Chic Crossbody', Score: 1.1671

---