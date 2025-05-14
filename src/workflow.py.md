### Visualize the Workflow Graph

```python {cell}
from IPython.display import display
from langgraph.graph.graph import StateGraph

workflow = create_hermes_workflow()
display(workflow)
```