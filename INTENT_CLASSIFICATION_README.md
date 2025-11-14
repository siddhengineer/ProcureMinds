# Email Intent Classification System

PEP8-compliant LangGraph node for email intent classification with OpenAI and keyword fallback.

## Architecture

### 1. Schemas (`app/schemas/intent.py`)
- **EmailIntent**: Enum for intent categories (QUOTATION, QUOTATION_QUERIES, CASUAL)
- **EmailInput**: Input validation schema
- **IntentClassificationResult**: Structured classification output
- **IntentNodeState**: LangGraph node state schema

### 2. Service Layer (`app/services/intent.py`)
- **IntentClassifier**: Core classification logic
  - OpenAI GPT-4o-mini for intelligent classification
  - Keyword-based fallback system
  - 15+ quotation keywords, 7+ query keywords, 10+ casual keywords
  - Returns structured `IntentClassificationResult`

### 3. LangGraph Node (`app/workflows/intent_node.py`)
- **IntentClassificationNode**: LangGraph-compatible node
  - `classify_intent()`: Main async node function
  - `route_based_on_intent()`: Router for conditional edges
  - Error handling with graceful fallback

### 4. Workflow Integration (`app/workflows/email_workflow.py`)
- **EmailProcessingWorkflow**: Complete LangGraph workflow
  - Intent classification → Routing → Processing → Final output
  - Conditional routing based on intent
  - Quotation processing node (ready for implementation)
  - Query processing node (reserved for future)

## Usage

### Standalone Classification
```python
from app.services.intent import classify_email_intent

result = classify_email_intent(
    email_content="Can you send me a quote for 100 units?",
    subject="Pricing Request"
)

print(result.intent)           # EmailIntent.QUOTATION
print(result.confidence)       # "high"
print(result.method)           # "openai"
print(result.should_process)   # True
```

### LangGraph Workflow
```python
from app.workflows.email_workflow import EmailProcessingWorkflow

workflow = EmailProcessingWorkflow()

result = await workflow.execute(
    email_content="We need a quotation for 500 units",
    subject="RFQ - Model X",
    sender="buyer@company.com"
)

print(result['intent'])        # "quotation"
print(result['processed'])     # True
```

### Custom Node Integration
```python
from langgraph.graph import StateGraph, END
from app.workflows.intent_node import IntentClassificationNode, EmailWorkflowState

# Create your workflow
workflow = StateGraph(EmailWorkflowState)
intent_node = IntentClassificationNode()

# Add intent classification node
workflow.add_node("classify", intent_node.classify_intent)

# Add conditional routing
workflow.add_conditional_edges(
    "classify",
    intent_node.route_based_on_intent,
    {
        "quotation_processing": "process_quotation",
        "query_processing": "process_query",
        "end": END
    }
)
```

## Intent Categories

### QUOTATION (Processed)
Emails requesting pricing, quotes, estimates, proposals, or discussing purchase/procurement.
- **Keywords**: quote, quotation, pricing, price, cost, estimate, proposal, bid, rate, budget, purchase, order, buy, procurement, RFQ
- **Action**: Passed to quotation processing node

### QUOTATION_QUERIES (Reserved)
Follow-up questions or clarifications about existing quotations.
- **Keywords**: follow-up, question about, clarification, regarding quote, previous quote
- **Action**: Reserved for future implementation

### CASUAL (Ignored)
General greetings, thank you messages, casual conversation, or unrelated content.
- **Keywords**: hello, hi, hey, greetings, thanks, thank you, regards, cheers
- **Action**: Routed to end, not processed

## Classification Flow

1. **Empty Check**: Returns CASUAL for empty emails
2. **OpenAI Classification**: Primary method using GPT-4o-mini
3. **Keyword Fallback**: If OpenAI fails, uses regex pattern matching
4. **Ultimate Fallback**: Returns CASUAL with low confidence

## Configuration

### Environment Variables
```env
OPENAI_API_KEY=sk-or-v1-your-api-key-here
```

### OpenAI Settings
- **Model**: gpt-4o-mini (cost-effective)
- **Temperature**: 0.1 (consistent classification)
- **Max Tokens**: 10 (single word response)

## PEP8 Compliance

- ✅ Type hints on all functions
- ✅ Docstrings following Google style
- ✅ Line length < 79 characters
- ✅ Proper imports organization
- ✅ Snake_case naming convention
- ✅ Class and function documentation
- ✅ Structured error handling

## Testing

Run the example workflow:
```bash
python example_intent_workflow.py
```

## Next Steps

1. Implement quotation processing logic in `quotation_processing_node()`
2. Add query processing for QUOTATION_QUERIES intent
3. Integrate with email fetching service
4. Add logging and monitoring
5. Create unit tests for classification accuracy
