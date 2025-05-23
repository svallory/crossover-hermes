# Sample Markdown with Corrected Attributes

This is a sample markdown file that demonstrates how the conversion to Jupyter notebook works.

## Regular Markdown Content

- Lists
- And formatting
- Will be preserved

## Code Blocks That Become Code Cells

This code block uses triple backticks with {cell} and will become a code cell:

```python {cell}
import pandas as pd

# This is a Python code block
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': ['a', 'b', 'c']
})
print(df)
```

## JavaScript Code Block Becoming a Cell

```javascript {cell}
// This JavaScript code will become a code cell
let message = "Hello, world!";
console.log(message);
```

## Regular Code Blocks Stay as Markdown

This code block doesn't have the {cell} attribute, so it stays as markdown:

```python
# This will NOT be executed
# It remains as a code block in the markdown
import numpy as np
print("This won't run")
```

## Code Blocks with Tildes Always Stay as Markdown

~~~python {cell}
# Even with {cell} attribute, tilde blocks stay as markdown
print("This won't run either")
~~~

## Bash Code Block with Cell Attribute

```bash {cell=true}
# This will become a code cell with the explicit attribute
echo "Hello from bash"
ls -la
``` 