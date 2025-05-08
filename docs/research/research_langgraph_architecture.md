# Research: LangGraph Architecture

## Question
Should we use the 4-agent architecture from agent-flow.md or follow the simpler pattern from data-enrichment? Is it better to structure our graph with multiple specialized agents or a single agent with multiple tools?

## Research Notes

### Data-Enrichment Example Architecture
The data-enrichment example uses a simpler architecture with a single agent that has access to multiple tools. It defines:
- A main agent model that makes decisions
- Tools for searching and scraping websites
- A reflection mechanism to validate outputs
- A state management system using dataclasses

The architecture is implemented as a graph with nodes for:
- call_agent_model (main decision-making)
- reflect (validation)
- tools (execution of search and scrape functionality)

The flow is controlled by conditional routing based on the agent's decisions.

### 4-Agent Architecture from agent-flow.md
The 4-agent architecture proposes specialized agents:
1. Email Analyzer Agent - Analyzes intent, extracts product references
2. Order Processor Agent - Processes orders, checks inventory
3. Inquiry Responder Agent - Generates detailed responses to inquiries
4. Response Composer Agent - Generates final customer responses

Each agent has specific responsibilities and tools, with a main processing flow coordinating between them.

### Current Best Practices from Web Research

#### Multi-Agent Architecture Patterns
According to the LangGraph documentation and expert blogs, there are several common multi-agent architecture patterns:

1. **Single Agent with Multiple Tools**: Simpler architecture, easier to maintain, with one LLM making decisions about which tools to use.

2. **Supervisor Architecture**: Multiple agents coordinated by a supervisor agent that routes tasks to specialized agents.

3. **Network Architecture**: Each agent can communicate with every other agent in a many-to-many pattern.

4. **Hierarchical Architecture**: Teams of agents managed by supervisors, with a top-level supervisor managing the teams.

5. **Custom Workflow Architecture**: Predefined flow between agents, either deterministic or with dynamic routing.

#### Considerations for Choosing an Architecture

From "LLM Architectures in Action" (Medium article):

**Single-Agent Strengths:**
- Low complexity and easier maintenance
- No inter-agent coordination needed
- Potentially lighter compute footprint

**Single-Agent Weaknesses:**
- Struggles with complex or dynamic tasks
- Limited specialization capabilities
- Risk of tool-overload confusion

**Multi-Agent Strengths:**
- Better handling of complex and dynamic tasks
- Parallel processing for efficiency 
- Can use smaller, specialized models for specific tasks

**Multi-Agent Weaknesses:**
- Increased system complexity
- Requires robust interaction management
- Higher resource demands with more agents

#### Recent Evolution in LangGraph
According to the Dev.to article "AI Agents Architecture, Actors and Microservices," LangGraph is moving toward a "multi-actor" approach that focuses on stateful, actor-based applications. This aligns with treating each agent as an actor with specific responsibilities.

#### Communication Between Agents
The LangGraph documentation highlights important considerations for agent communication:
- Whether agents communicate via graph state or tool calls
- How to handle different state schemas between agents
- Whether to share the full history or only final results between agents

### Email Classification and Customer Service Architectures

From reviewing several real-world implementations of email classification and customer service systems:

1. **Email-Sorter (GitHub)**: Uses CrewAI to create a team of agents that receive, classify, search, and reply to emails.

2. **LangGraph Email Automation (GitHub)**: Uses a multi-agent architecture with specialized agents for:
   - Email classification/categorization
   - Response generation using RAG for product inquiries
   - Quality assurance before sending

3. **AI Email Automation Blog**: Describes a three-component system:
   - Email parser for detection and classification
   - Response generator using GPT-4
   - Email sender with formatting and signature

4. **Galileo AI's Agent Architecture Guide**: Emphasizes the importance of perception, reasoning, and action modules in agent design, with feedback loops for continuous improvement.

5. **Databricks AI Agent Systems**: Advocates for modular design with components for:
   - Input and output formatting
   - Data foundation (vector database)
   - Deterministic processing (functions/tools)
   - General reasoning
   - Domain reasoning
   - Evaluation 

## Decision
For the Hermes project, we should implement a **Supervisor Architecture** with specialized agents similar to the 4-agent architecture from agent-flow.md, but with some modifications to simplify implementation and maintenance.

## Justification
The Hermes project involves complex email processing with distinct phases (classification, order processing, inquiry handling, and response generation) that benefit from specialization. However, implementing all four agents with equal complexity would increase development time and maintenance costs.

Our approach will use a supervisor agent coordinating three specialized agents:
1. **Email Classifier Agent** - Combines email analysis and intent detection
2. **Order Processor Agent** - Handles order verification and stock management
3. **Response Generator Agent** - Creates context-aware responses for both inquiries and orders

This approach balances the benefits of multi-agent architecture (specialization, better handling of complex tasks) while mitigating its weaknesses (reduced complexity compared to a full 4-agent system).

The communication between agents will be through shared state via a well-defined schema, and we'll implement reflection mechanisms for quality assurance. We'll use dataclasses for state management as demonstrated in the data-enrichment example, which provides a clear, strongly typed interface between agents.

This architecture also scales well with the expected large product catalog (100,000+ products) as the specialized agents can efficiently handle their specific tasks without overwhelming the entire system. The RAG implementation for product inquiries can be contained within the Response Generator agent, allowing for independent optimization. 