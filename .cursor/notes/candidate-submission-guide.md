# Candidate Submission Guide: AI Business Problems Assignment

## Overview
This guide outlines the recommended approach for completing the "Solve Business Problems with AI" assignment. Following these stages ensures a systematic, well-documented, and high-quality submission that addresses all evaluation criteria.

## Stage 1: Setup & Environment Preparation

### Initial Setup
- [x] Create `.cursor/notes` folder for project documentation
- [x] Initialize project with `uv` (Python package manager)
- [x] Set up basic `.cursor/rules` for consistent development practices
- [x] Configure OpenAI API access (custom base URL + provided key)
- [x] Set up version control (git) with meaningful commit messages

### Environment Configuration
- [ ] Install required dependencies: `openai`, `pandas`, `numpy`, `scikit-learn`, `chromadb` (or similar vector DB)
- [ ] Set up development tools: linting, formatting, type checking
- [ ] Create basic project structure following Python best practices
- [ ] Test API connectivity with simple "Hello World" call

### Success Criteria
- Environment runs without errors
- Can successfully call OpenAI API
- Can read data from Google Sheets
- Basic project structure is established

## Stage 2: Planning & Architecture Design

### Requirements Analysis
- [ ] Break down assignment requirements into specific, measurable tasks
- [ ] Identify key constraints (token limits, scalability to 100k+ products)
- [ ] Map requirements to evaluation criteria
- [ ] Create requirement traceability matrix

### Important Technical Decisions (ITDs)
Create ITD documents for major architectural choices:

#### ITD-001: Email Classification Strategy
- **Decision**: Rule-based vs. ML-based vs. LLM-based classification
- **Rationale**: LLM provides better context understanding for complex emails
- **Implementation**: Few-shot prompting with clear examples

#### ITD-002: RAG Architecture for Product Queries
- **Decision**: Vector database choice and embedding strategy
- **Rationale**: Need to handle 100k+ products without token limit issues
- **Implementation**: ChromaDB with OpenAI embeddings, semantic search

#### ITD-003: Stock Management Strategy
- **Decision**: In-memory vs. persistent stock tracking
- **Rationale**: Assignment scope suggests in-memory is sufficient
- **Implementation**: Pandas DataFrame with atomic updates

#### ITD-004: Response Generation Architecture
- **Decision**: Template-based vs. fully generative responses
- **Rationale**: Hybrid approach for consistency and flexibility
- **Implementation**: Structured prompts with dynamic content injection

### System Architecture
- [ ] Design component interaction diagram
- [ ] Define data flow between components
- [ ] Plan error handling and edge case strategies
- [ ] Design testing strategy (unit, integration, end-to-end)

## Stage 3: Implementation & Iterative Development

### Development Methodology: Plan-Doc-Code-Test Cycles

#### Cycle 1: Email Classification
- **Plan**: Create detailed implementation plan in notes
- **Doc**: Write component documentation and API contracts
- **Code**: Implement email classifier with proper error handling
- **Test**: Unit tests + manual validation with sample emails

#### Cycle 2: RAG System for Product Queries
- **Plan**: Vector store setup and query optimization strategy
- **Doc**: Document embedding strategy and retrieval logic
- **Code**: Implement vector store, embedding generation, semantic search
- **Test**: Test with various query types and edge cases

#### Cycle 3: Order Processing System
- **Plan**: Stock management and order fulfillment logic
- **Doc**: Document business rules and data validation
- **Code**: Implement order processing with stock updates
- **Test**: Test inventory edge cases and concurrent order scenarios

#### Cycle 4: Response Generation
- **Plan**: Response template design and tone adaptation
- **Doc**: Document prompting strategies and quality criteria
- **Code**: Implement response generators for both order and inquiry types
- **Test**: Evaluate response quality, tone, and completeness

### Code Quality Standards
- [ ] Type hints for all functions and classes
- [ ] Comprehensive docstrings (TSDoc style for consistency)
- [ ] Error handling for API failures, data issues, edge cases
- [ ] Logging for debugging and monitoring
- [ ] Code organization following SOLID principles

### Continuous Validation
- [ ] Run tests after each implementation cycle
- [ ] Validate outputs match expected format exactly
- [ ] Check token usage to stay within limits
- [ ] Verify scalability considerations are addressed

## Stage 4: Integration Testing & Validation

### End-to-End Testing
- [ ] Test complete pipeline with assignment dataset
- [ ] Validate all output sheets have correct format and data
- [ ] Test edge cases: out-of-stock items, ambiguous emails, complex queries
- [ ] Performance testing with larger datasets

### Quality Assurance
- [ ] Cross-validate classifications with manual review
- [ ] Test response quality across different email types
- [ ] Verify business logic correctness (stock updates, order fulfillment)
- [ ] Ensure professional tone in all generated responses

### Compliance Verification
- [ ] Confirm all evaluation criteria are addressed
- [ ] Verify output format matches requirements exactly
- [ ] Test with both provided and edge-case data
- [ ] Document how advanced AI techniques (RAG, vector stores) are used

## Stage 5: Presentation & Documentation

### Jupyter Notebook Creation
The notebook should be a **showcase**, not the implementation. Code lives in the repository.

#### Structure:
1. **Executive Summary** (2-3 sentences)
2. **Key Implementation Highlights** (bullet points addressing evaluation criteria)
   - Advanced AI Techniques Used
   - RAG Implementation Details
   - Scalability Solutions
   - Tone Adaptation Examples
3. **Architecture Overview** (diagram + brief explanation)
4. **Code Repository Integration** (clone and import)
5. **Demonstration** (run with assignment data)
6. **Results Analysis** (sample outputs with explanations)
7. **Technical Decisions** (brief summary of key ITDs)

### Documentation Standards
- [ ] README with clear setup and usage instructions
- [ ] API documentation for all public interfaces
- [ ] Architecture decision records (ADRs) for major choices
- [ ] Test coverage report and quality metrics
- [ ] Performance benchmarks and token usage analysis

## Stage 6: Development Log & Reflection

### Development Log Format
Track progress with brief, dated entries:

```
2024-01-15: Setup complete, API connectivity verified
2024-01-15: ITD-001 completed - chose LLM-based classification
2024-01-16: Email classifier implemented, 95% accuracy on test set
2024-01-16: RAG system designed, ChromaDB integration complete
2024-01-17: Product query system handles 10k+ products efficiently
2024-01-17: Order processing with stock management implemented
2024-01-18: Response generation tuned for professional tone
2024-01-18: Integration tests pass, all outputs format-compliant
2024-01-19: Jupyter presentation notebook finalized
```

### Reflection Points
- [ ] What worked well in the approach?
- [ ] What challenges were encountered and how were they solved?
- [ ] How do the technical decisions align with evaluation criteria?
- [ ] What would be done differently in a production environment?

## Additional Considerations

### Performance & Scalability
- [ ] Token usage optimization strategies
- [ ] Caching mechanisms for repeated queries
- [ ] Batch processing capabilities
- [ ] Memory management for large datasets

### Error Handling & Robustness
- [ ] API timeout and retry logic
- [ ] Data validation and sanitization
- [ ] Graceful degradation strategies
- [ ] Comprehensive logging for debugging

### Professional Development Practices
- [ ] Version control with meaningful commits
- [ ] Code review checklist
- [ ] Dependency management and pinning
- [ ] Security considerations (API key handling)

## Success Metrics

### Technical Excellence
- All tests pass with >95% coverage
- Code follows Python best practices and style guidelines
- Performance meets scalability requirements
- Error handling covers all identified edge cases

### Assignment Compliance
- All required outputs generated in correct format
- Advanced AI techniques clearly demonstrated
- Professional tone achieved in all responses
- Evaluation criteria explicitly addressed

### Presentation Quality
- Clear, concise documentation
- Working demonstration with assignment data
- Technical decisions justified and explained
- Code organization facilitates understanding

---

**Remember**: This assignment evaluates AI/LLM expertise, not traditional programming skills. Focus on demonstrating advanced AI techniques, thoughtful prompting strategies, and practical solutions to real-world business problems.