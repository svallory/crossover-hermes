# Sample Markdown for Jupyter Conversion

This is a sample markdown file that demonstrates how the conversion to Jupyter notebook works.

## Regular Markdown Content

- Lists
- And formatting
- Will be preserved

## Code Blocks That Become Code Cells

This code block uses triple backticks and will become a code cell:

```python
import pandas as pd

# This is a Python code block
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': ['a', 'b', 'c']
})
print(df)
```

## Code Blocks That Remain as Markdown

This code block uses triple tildes and will remain as part of the markdown:

~~~python
# This code will NOT be executed
# It will remain as a code block in the markdown
import numpy as np
print("This won't run")
~~~

## Another Code Cell

```python
# Another Python code block
x = 10
y = 20
print(f"Sum: {x + y}")
``` 