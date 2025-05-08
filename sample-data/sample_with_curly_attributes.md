# Sample with Curly Brace Attributes

This file demonstrates the use of curly brace attributes in markdown code blocks.

## Regular Python Cell

```python
# This is a regular Python cell
x = 5
print(f"x = {x}")
```

## JavaScript Cell with {cell} Attribute

JavaScript code would normally be included as a markdown code block, but with the {cell} attribute it becomes a code cell:

```javascript {cell}
// This JavaScript code will become a code cell
let message = "Hello, world!";
console.log(message);
```

## JavaScript with explicit cell=true

```javascript {cell=true}
// This JavaScript code will become a code cell with explicit true value
let numbers = [1, 2, 3, 4, 5];
numbers.forEach(n => console.log(n * 2));
```

## JavaScript with quoted cell value

```javascript {cell="true"}
// This JavaScript code will become a code cell with quoted true value
document.addEventListener('DOMContentLoaded', () => {
  console.log('Document loaded');
});
```

## Regular JavaScript (as markdown)

This JavaScript code doesn't have the {cell} attribute, so it stays as markdown:

```javascript
// This will remain a markdown code block
let x = 10;
console.log(x);
```

## Bash with Cell Attribute

```bash {cell}
# This will become a code cell even though it's bash
echo "Hello from bash"
ls -la
```

## Complex Attributes

The parser supports complex attribute formats:

```python {cell class="important"}
# The parser will see the "cell" keyword and make this a code cell
# Other attributes could be used for metadata in the future
import matplotlib.pyplot as plt
plt.plot([1, 2, 3, 4])
plt.show()
``` 