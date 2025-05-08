# Sample with Code Block Attributes

This file demonstrates the use of code block attributes in markdown.

## Regular Python Cell

```python
# This is a regular Python cell
x = 5
print(f"x = {x}")
```

## JavaScript Cell with [cell] Attribute

JavaScript code would normally be included as a markdown code block, but with the [cell] attribute it becomes a code cell:

```javascript [cell]
// This JavaScript code will become a code cell
let message = "Hello, world!";
console.log(message);
```

## Regular JavaScript (as markdown)

This JavaScript code doesn't have the [cell] attribute, so it stays as markdown:

```javascript
// This will remain a markdown code block
let x = 10;
console.log(x);
```

## Bash with Cell Attribute

```bash [cell]
# This will become a code cell even though it's bash
echo "Hello from bash"
ls -la
```

## Complex Attributes

The parser supports more complex attribute formats:

```python [cell important=true]
# The parser will see the "cell" keyword and make this a code cell
# Other attributes are ignored for now but could be used for metadata
import matplotlib.pyplot as plt
plt.plot([1, 2, 3, 4])
plt.show()
``` 