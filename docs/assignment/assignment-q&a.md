# Hermes Implementation Questions Tracking List

This document tracks key questions we need to answer to ensure our reference solution is perfect.

## Important Context: Reference Solution for Interview Assignment

This reference solution is intended to serve as an evaluation benchmark for the Hermes interview assignment. Key considerations:

1. **Achievable Timeline**: Solution should be something a top-tier senior developer could implement in 1-2 days
2. **Best Practices**: Demonstrate proper use of modern LLM tools and frameworks (LangChain/LangGraph, vector stores)
3. **Appropriate Sophistication**: Show mastery without over-engineering
4. **Aligned with Requirements**: Meet all requirements in assignment.md with elegance and efficiency

When making architectural decisions, we should prioritize:
- Clean, readable implementations over extensive abstractions
- Effective but straightforward solutions over multi-layered systems
- Practical patterns that showcase AI/LLM expertise
- Approaches that demonstrate understanding of RAG and proper LLM integration

This is NOT a production enterprise system - it's a well-crafted solution that shows mastery within reasonable bounds. 

## Architecture

1. [x] **LangGraph Architecture**:
   - Should we use the 4-agent architecture from agent-flow.md or follow the simpler pattern from data-enrichment?
   - Is it better to structure our graph with multiple specialized agents or a single agent with multiple tools?
   - How can we optimize the graph structure for both readability and performance?
   
   **Decision**: Implement a Supervisor Architecture with three specialized agents (Email Classifier, Order Processor, Response Generator) coordinated by a supervisor agent. This balances specialization benefits with manageable complexity.
   
   **Justification**: The supervisor architecture offers the best balance between specialization and coordination for an interview reference solution. By dedicating agents to specific tasks, we demonstrate LangGraph expertise while keeping the solution manageable for a 1-2 day implementation. This approach is more practical than a fully decentralized design while still showcasing best practices.

2. [x] **State Management**:
   - Should we use dataclasses with annotated fields like in data-enrichment/state.py?
   - Would TypedDict (used in agent-flow.md) be more appropriate than dataclasses?
   - How should we handle state transitions and reducers for complex states?
   
   **Decision**: Use TypedDict with Annotated fields for state management, following the pattern established in agent-flow.md. Structure the state with clear fields for each processing stage.
   
   **Justification**: TypedDict with Annotated fields provides a clean, maintainable approach that aligns with LangGraph's design patterns. For an interview reference solution, this approach demonstrates proper state management without introducing unnecessary complexity. It provides clear type hints and structured data flow that showcases best practices while remaining practical to implement within a 1-2 day timeframe.

3. [x] **Message Handling**:
   - Should we use langchain_core.messages (AIMessage, HumanMessage, ToolMessage) as in data-enrichment?
   - How should we handle tool calls and responses in the message history?
   
   **Decision**: Use langchain_core.messages for all message handling, including AIMessage, HumanMessage, and ToolMessage classes. Maintain a simplified message history approach focused on the core workflow.
   
   **Justification**: Using standard LangChain message types demonstrates best practices while keeping the implementation straightforward. For an interview reference solution, this approach shows proper integration with the LangChain ecosystem without adding unnecessary complexity. This standardized approach is achievable within the 1-2 day implementation window while still showcasing proper message handling patterns.

4. [x] **Configuration Management**:
   - Should we use RunnableConfig from langchain_core.runnables for configuration?
   - What parameters should be configurable vs. hardcoded?
   - How should we structure the configuration for different components?
   
   **Decision**: Use a simple Pydantic BaseModel Configuration class with a from_runnable_config method. Focus on essential configurable parameters only, particularly model settings and RAG parameters.
   
   **Justification**: This approach demonstrates proper configuration practices without over-engineering. For an interview reference solution, a streamlined configuration focusing on key parameters (model names, temperatures, vector store settings) provides the right balance between flexibility and simplicity. This approach is achievable within a 1-2 day implementation while still showcasing best practices.

5. [x] **Tool Design**:
   - What tools should each agent have access to?
   - How should we implement the database tools for order processing?
   - Should we use structured output from LLMs or rely on tools for data extraction?
   
   **Decision**: Implement focused tools for each agent following the data-enrichment pattern. Use ChromaDB for vector search, a simple DataFrame for stock management, and structured LLM output for data extraction.
   
   **Justification**: This pragmatic approach demonstrates proper tool design without unnecessary complexity. For an interview reference solution, using a combination of vector search, simple data management, and structured outputs showcases LLM best practices while remaining achievable in 1-2 days. This approach effectively balances sophistication with practicality.

6. [x] **Error Handling and Graceful Degradation**:
   - How should we handle LLM errors or hallucinations?
   - What fallback mechanisms should be in place?
   - How can we ensure the system degrades gracefully under edge cases?
   
   **Decision**: Implement focused error handling with validation at critical points. Use Pydantic models for structured outputs, implement basic retry mechanisms for LLM calls, and add validation nodes for key state transitions.
   
   **Justification**: This practical approach demonstrates error handling awareness without over-engineering. For an interview reference solution, focusing on structured validation and retry logic at critical points provides robust error handling that's achievable within a 1-2 day timeframe. This approach showcases best practices while maintaining implementation simplicity.

7. [x] **Testing and Evaluation**:
   - How should we test each component of the system?
   - What metrics should we use to evaluate performance?
   - How can we ensure the system is robust to a variety of inputs?
   
   **Decision**: Implement a focused testing approach with sample email test cases and validation steps for critical components. Create a small but diverse set of test cases covering key scenarios (multi-language, mixed intent, vague references).
   
   **Justification**: This balanced approach demonstrates testing awareness while being practical for an interview solution. Rather than a comprehensive test suite, focusing on key validation points and representative test cases ensures the solution handles edge cases while remaining achievable in a 1-2 day implementation timeframe.

8. [x] **Scalability Considerations**:
   - How should we structure the system to handle a 100,000+ product catalog?
   - What optimizations can we make for token efficiency?
   - How can we ensure response time remains reasonable at scale?
   
   **Decision**: Implement a basic scalability approach with category-based filtering before vector search. Include comments explaining how the solution would extend to larger catalogs and use proper embedding practices that would scale reasonably.
   
   **Justification**: This pragmatic approach demonstrates scalability awareness without implementing complex systems that would be impractical in a 1-2 day timeframe. By using category filtering and proper RAG design, the solution shows understanding of scaling considerations while remaining achievable for an interview reference implementation.

## Implementation Specifics

9. [x] **Vector Database Integration**:
   - Which vector database should we use (ChromaDB, FAISS, etc.)?
   - How should we structure our embeddings for optimal retrieval?
   - What indexing strategy should we use for the product catalog?
   
   **Decision**: Use ChromaDB with OpenAI embeddings for the product catalog. Structure embeddings at the product level with a combined approach (product ID + name + description) and implement simple metadata filtering.
   
   **Justification**: ChromaDB offers the right balance of simplicity and effectiveness for an interview reference solution. It's easy to set up, has native LangChain integration, and doesn't require external services. This approach demonstrates proper RAG implementation while being achievable within a 1-2 day timeframe.

10. [x] **MCP vs Tool Calling**:
    - Should the ideal solution use MCP (Model Context Protocol) or traditional Tool Calling for providing tools to agents?
    
    **Decision**: Use Function Calling
    
    **Justification**: MCP is designed for plug-and-play integration of external tools, but the Hermes assignment only needs internal, tightly-coupled business logic tools. Function calling via LangChain's @tool decorator (or equivalent) is more reliable, easier to test, and gives you full control over tool schemas, validation, and error handling. ([LangChain Blog](https://blog.langchain.dev/mcp-fad-or-fixture/), [Athina AI Hub](https://hub.athina.ai/blogs/model-context-protocol-mcp-with-langgraph-agent/), [Medium](https://medium.com/@h1deya/supercharging-langchain-integrating-450-mcp-with-react-d4e467cbf41a))

11. [ ] **Email Classification Logic**:
    - How should we detect mixed intents in emails?
    - How should we handle language variations?
    - What threshold should we use for classification confidence?

12. [ ] **Order Processing Logic**:
    - How should we handle partial orders (some items in stock, others not)?
    - How should we suggest alternatives for out-of-stock items?
    - What inventory update strategy should we use?

13. [ ] **Response Generation**:
    - How should we adapt tone to match customer style?
    - How should we handle multi-language responses?
    - How can we ensure responses are concise yet comprehensive?

## Documentation and Delivery

14. [ ] **Code Documentation**:
    - What documentation standards should we follow?
    - How should we structure inline comments and docstrings?
    - What external documentation should we provide?

15. [ ] **Deployment Guidelines**:
    - What environment setup instructions should we provide?
    - How should we document API usage?
    - What performance expectations should we set?

## Configuration and Setup

16. [x] **Configuration Pattern**:
    - Should we use a dedicated Configuration class with RunnableConfig integration like in data-enrichment?
    - How should we handle environment variables vs. runtime configuration?
    - Should we support runtime configuration changes?
    
    **Decision**: Use a simple Pydantic BaseModel Configuration class with a from_runnable_config method, following the pattern in data-enrichment. Focus on essential configurable parameters only, particularly model settings and RAG parameters.
    
    **Justification**: This approach provides a clean, maintainable configuration pattern without over-engineering. For an interview reference solution, focusing on key parameters that would need tuning during development demonstrates best practices while keeping the implementation straightforward and achievable in 1-2 days.

17. [x] **LLM Integration**:
    - Should we follow the data-enrichment pattern of using init_model with provider/model name splitting?
    - How should we manage model parameters (temperature, etc.)?
    - Should we use different models for different agents/tasks?
    
    **Decision**: Implement a streamlined model initialization approach based on data-enrichment's init_model pattern. Use a single high-quality model (GPT-4o) for all agents, with configurable temperature per agent role.
    
    **Justification**: For an interview reference solution, using a single high-quality model with appropriate temperature settings per agent role (lower for classification, higher for creative responses) offers the best balance of simplicity and effectiveness. This approach demonstrates proper model integration without unnecessary complexity, making it achievable within a 1-2 day implementation timeframe.

## Tools and Functionality

18. [x] **Tool Definition and Usage**:
    - Should we use the function-based tool definitions from tools.py?
    - How should we handle tool injection and state access?
    - Should we use `InjectedToolArg` and `InjectedState` annotations?
    
    **Decision**: Implement function-based tool definitions following the data-enrichment pattern, using typed annotations including `InjectedToolArg` for configuration and `InjectedState` for state access. Group tools by agent responsibility in separate modules.
    
    **Justification**: Function-based tools with proper type annotations demonstrate best practices for LLM tool integration while remaining practical for an interview solution. This approach provides clear interfaces and better IDE support, showing technical expertise without unnecessary complexity.

19. [x] **RAG Implementation**:
    - Which vector store should we use for product catalog?
    - How should we structure the embedding process?
    - Should we implement batching for embeddings to improve performance?
    
    **Decision**: Use ChromaDB with OpenAI embeddings for the product catalog. Structure embeddings at the product level with a combined approach (product ID + name + description), and implement basic batching for initial catalog embedding.
    
    **Justification**: This approach demonstrates RAG best practices while remaining achievable within a 1-2 day implementation window. Product-level embeddings with combined fields provide effective retrieval without complex chunking strategies, striking the right balance between sophistication and practicality for an interview reference solution.

20. [x] **Error Handling**:
    - How comprehensive should our error handling be?
    - Should we follow the pattern in graph.py for handling unexpected message types?
    - How should we verify and validate the outputs at each step?
    
    **Decision**: Implement focused error handling with validation at critical points. Use Pydantic models for structured outputs, implement basic retry mechanisms for LLM calls, and add validation nodes for key state transitions.
    
    **Justification**: For an interview reference solution, focusing on the most critical aspects of error handling (structured validation, basic retry logic, validation checkpoints) demonstrates understanding of robust agent design without introducing complexity that would be impractical to implement in a 1-2 day timeframe.

## Prompts and Responses

21. [x] **Prompt Structure**:
    - Should we use simple f-string templates like in prompts.py or more structured PromptTemplates?
    - How should we structure prompts for optimal LLM performance?
    - Should we include system messages in our prompts?
    
    **Decision**: Use ChatPromptTemplate with separate system and user messages. Store prompts in a dedicated prompts.py module organized by agent role. Include examples for complex tasks.
    
    **Justification**: This approach demonstrates prompt engineering best practices while remaining straightforward to implement in a 1-2 day timeframe. Using ChatPromptTemplate with separate system/user messages and including examples for complex tasks shows proper prompt design without unnecessary complexity.

22. [x] **Response Generation**:
    - How should we structure the final response to match the expected format?
    - How should we handle tone adaptation in responses?
    - How can we ensure responses are production-ready?
    
    **Decision**: Implement a dedicated response generation agent that receives tone analysis, customer details, and product information. Use a template-based approach with examples of appropriate responses for different scenarios.
    
    **Justification**: This approach demonstrates effective response generation while being achievable in a 1-2 day implementation. Using a template-based strategy with examples ensures high-quality, natural-sounding responses without complex multi-layered approaches that would be impractical for an interview reference solution.

## Testing and Performance

23. [x] **Testing Strategy**:
    - How should we test the individual components and the full integration?
    - Should we implement validation steps at key points?
    - How should we handle edge cases in the data?
    
    **Decision**: Implement a basic testing approach with sample email test cases, agent-level verification steps, and integration testing on the critical flow. Include explicit validation of edge cases in each agent's processing.
    
    **Justification**: This focused approach demonstrates testing awareness while being practical for an interview solution that must be completed in 1-2 days. Concentrating on key validation points and representative test cases ensures the solution handles edge cases while maintaining implementation efficiency.

24. [x] **Performance Optimization**:
    - How can we minimize token usage while maintaining quality?
    - Should we implement caching for embeddings or responses?
    - How should we handle parallel processing (if needed)?
    
    **Decision**: Implement basic performance optimizations focused on token efficiency and embedding caching. Use targeted product retrieval with similarity search, cache embeddings to avoid regeneration, and implement prompt design best practices to reduce token usage.
    
    **Justification**: For an interview reference solution, focusing on high-impact optimizations (efficient RAG design, embedding caching, token-efficient prompts) demonstrates performance awareness without introducing complex systems that would be impractical to implement in a 1-2 day timeframe.

## Best Practices

25. [x] **Code Organization**:
    - Should we follow the module structure from data-enrichment?
    - How should we organize the codebase for maintainability?
    - Should we use more type hints and docstrings?
    
    **Decision**: Use a clean module structure inspired by data-enrichment, with dedicated modules for agents, tools, state, and configuration. Implement thorough type hints and concise docstrings on public interfaces.
    
    **Justification**: This approach demonstrates code organization best practices while remaining achievable in a 1-2 day implementation. The clear module structure and focused documentation show understanding of maintainable code practices without excessive overhead.

26. [x] **Documentation**:
    - How detailed should our code documentation be?
    - Should we include architectural diagrams?
    - How should we document decision points and rationales?
    
    **Decision**: Include a README.md with project overview, clear setup instructions, and a brief architectural description. Add concise inline documentation focusing on key components.
    
    **Justification**: This balanced approach demonstrates documentation awareness while being practical for an interview solution with a 1-2 day implementation window. Focusing documentation efforts on the most impactful areas (setup instructions, key components) shows understanding of documentation importance without creating overhead that would be impractical in a limited timeframe.

27. [x] **Scaling Considerations**:
    - How well will our solution scale to 100,000+ products?
    - Should we include pagination or chunking for large product catalogs?
    - How should we handle rate limiting?
    
    **Decision**: Implement a basic scalability approach with category-based filtering before vector search and comments explaining how the solution would extend to larger catalogs. Keep implementation simple while demonstrating awareness of scaling issues.
    
    **Justification**: This practical approach demonstrates scalability awareness while remaining achievable in a 1-2 day implementation. By focusing on category-based pre-filtering and proper embedding practices, the solution shows understanding of RAG scalability considerations without requiring complex systems that would be impractical in a limited timeframe.

28. [x] **Function Calling vs Programmatic Tool Execution**:
    - Should the reference solution use function calling + retries/fallback logic for missed tool calls, or programmatically execute tools and inject their response into the context?
    
    **Decision**: Use function calling for all business logic tools, with a simple validation/reflection step to check if the LLM called the necessary tool(s). If a tool call is missed, retry or prompt the agent again. Only use programmatic injection for non-agentic, deterministic steps (e.g., loading data, updating stock).
    
    **Justification**: This approach demonstrates mastery of modern LLM agent patterns (function calling, validation, retries), aligns with the assignment's goal to showcase advanced LLM/agent techniques, and is robust, maintainable, and model-agnostic. It is the current best practice in the LangChain/LangGraph ecosystem. Programmatic injection should be reserved for deterministic, non-agentic steps, as it bypasses agentic reasoning and reduces the demonstration of best practices.
    
    | Approach                              | Reliability | Agentic | Best Practice | Interview Score |
    | ------------------------------------- | ----------- | ------- | ------------- | --------------- |
    | Function calling + retries/validation | High        | Yes     | Yes           | High            |
    | Programmatic execution + injection    | Very High   | No      | No            | Low/Medium      |