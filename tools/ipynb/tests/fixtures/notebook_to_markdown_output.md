```python {cell}
# This is a regular Python code cell
import numpy as np
import matplotlib.pyplot as plt

# Regular comments stay with the code
x = np.linspace(0, 10, 100)
y = np.sin(x)

```

# Markdown Cell
This is a markdown cell with some formatting:
- Item 1
- Item 2

And math: $y = sin(x)$


```python {cell}


# Another code cell
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')

# This comment stays with the code
plt.grid(True)

```

## Results
The graph above shows a sine wave plotted from 0 to 10.


```python {cell}


# Final code cell
print("Maximum value:", np.max(y))
print("Minimum value:", np.min(y)) 
```

