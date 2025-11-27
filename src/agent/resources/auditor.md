# Auditor Resources

**Note: This Resources section is for the Auditor Agent's reference only. The Coder Agent does not see these resources - they only receive specific instructions about which tests to run.**

## Resources – General
Contextual information on audit principles, thresholds, and materiality.

## Resources – Tests
Available audit tests in the system with detailed examples for your reference.

### Test: Debits in Revenue
**Purpose**: Identify unusual debit entries posted to revenue accounts that may indicate errors, adjustments, or potential misstatements
**Test Availability**: Pre-computed results available in the system for immediate analysis

**Business Context**:
Revenue accounts normally maintain credit balances. Debit entries in these accounts may represent:
- Revenue reversals or corrections (legitimate business adjustments)
- Misclassified expenses or journal entry errors
- Potential fraud or earnings manipulation
- System processing errors

**Example Questions**:
- "Provide a brief summary of the debits on revenue test results"

**Chain of Thought Process**:
1. **Assess Request Type**: Summary analysis vs. detailed exception review
2. **Consider Materiality**: Focus on exceptions that exceed audit thresholds
3. **Business Impact**: Evaluate financial significance and trends
4. **Risk Assessment**: Determine audit implications and follow-up procedures
5. **Communication**: Present findings in business terms with audit recommendations

**Instruction to Coder**:
"Provide a summary analysis of the debits in revenue test results, including total exceptions, material items, and year-over-year trends."

**Sample Coder Response**:
```
📊 Debits on Revenue Test - Multi-Year Summary

2025: 7 exceptions, 0 material, $11.8M total impact, $1.7M average
2024: 300 exceptions, 0 material, $99.6M total impact, $332K average  
2023: 286 exceptions, 3 material, $850.1M total impact, $2.97M average

Key Insights: Declining exception volume, low materiality rate, significant impact variation
```

**Final Answer to User**:
"The debits in revenue analysis shows a positive trend with exception volume declining significantly from 300 in 2024 to just 7 in 2025. Here's the comprehensive summary:

## Debits on Revenue Test - Summary Results

| Year | Total Exceptions | Material Exceptions | Material Exception % | Total Debit Amount ($) | Avg Exception Amount ($) | Unique Accounts Affected |
|------|------------------|---------------------|---------------------|------------------------|--------------------------|--------------------------|
| 2025 | 7               | 0                   | 0.00%               | 11,783,043            | 1,683,292               | 2                        |
| 2024 | 300             | 0                   | 0.00%               | 99,617,515            | 332,058                 | 6                        |
| 2023 | 286             | 3                   | 1.05%               | 850,114,383           | 2,972,428               | 9                        |

**Key Audit Findings**:
- **Volume Trend**: 98% reduction in exceptions (2024 to 2025) suggests improved controls
- **Materiality Assessment**: No material exceptions in the past two years (2024-2025), with only 3 material exceptions in 2023
- **Financial Impact**: Significant decrease from $850 million in 2023 to $12 million in 2025
- **Risk Assessment**: Low current risk based on 2025 data, but 2023 requires attention

**Recommendations**:
1. Review the 3 material exceptions from 2023 for proper resolution
2. Investigate causes of 2023's high average exception amount ($2.97 million)
3. Document control improvements that led to 2025's reduction
4. Continue monitoring for any resurgence in exception volume

Would you like me to drill down into any specific year or investigate the material exceptions in detail?"

---

#### Progressive Investigation Workflow

The Debits in Revenue test supports progressive investigation - starting with summary, drilling into specific exceptions, and performing deep-dive analysis. The workflow follows natural user conversation patterns.

**Workflow Pattern**:
1. **Summary** → User sees high-level statistics
2. **User drills down** → Requests details on material/specific exceptions
3. **List exceptions** → Present specific mv_ids with amounts
4. **Wait for user decision** → User chooses whether to deep-dive
5. **Single investigation** → Analyze ONE user-selected transaction (Mode C)
6. **User decides** → Investigate another or stop

---

**Mode B: Listing Specific Exceptions**

**Example Question**:
- "Can you provide more detail on the material transactions from 2023?"
- "Show me the exceptions for account 41001"
- "List all debits over 1 million dollars"

**Chain of Thought Process**:
1. **Understand Criteria**: User wants filtered list (material, specific year, account, amount threshold)
2. **Request List**: Ask Coder for detailed list with mv_ids
3. **Present Results**: Show user the specific exceptions with amounts
4. **Stop and Ask**: Let user decide if they want deep-dive analysis on any transaction
5. **Wait for User**: Only proceed to Mode C when user explicitly confirms

**Instruction to Coder**:
"Get all material exceptions from 2023 with details including mv_id, account, amount, date, and description."

**Sample Coder Response**:
```
📋 Material Exceptions from 2023

Found 3 material exceptions:

1. mv_id: 45678
   Account: 41001 - Product Sales Revenue
   Amount: $2,500,000.00
   Date: 2023-12-28
   Description: "Customer cancellation per contract dispute"

2. mv_id: 45920
   Account: 41507 - Service Revenue
   Amount: $1,800,000.00
   Date: 2023-11-15
   Description: "Revenue reversal - timing adjustment"

3. mv_id: 46102
   Account: 42105 - Interest Income
   Amount: $1,200,000.00
   Date: 2023-10-05
   Description: "Correction of Q2 accrual"

Total Material Impact: $5,500,000.00
```

**Final Answer to User**:
"I found 3 material exceptions in 2023 totaling 5.5 million dollars:

1. **mv_id 45678**: 2.5M debit to Product Sales Revenue (Dec 28) - Customer cancellation per contract dispute
2. **mv_id 45920**: 1.8M debit to Service Revenue (Nov 15) - Revenue reversal timing adjustment
3. **mv_id 46102**: 1.2M debit to Interest Income (Oct 5) - Correction of Q2 accrual

Would you like me to investigate any of these in detail? I can perform a deep-dive analysis on the largest one (mv_id 45678, 2.5M) or any specific transaction you're interested in.

[WAIT for user to request investigation before transferring to coder]"

---

**Mode C: Deep Investigation**

**Example Question** (following Mode B):
- User's implicit request after seeing the list
- Or explicit: "Investigate mv_id 45678 in detail"
- Or: "Analyze that 2.5M transaction"

**Chain of Thought Process**:
1. **Select Transaction**: Choose largest or user-specified mv_id
2. **Request Full Analysis**: Ask Coder to execute complete 5-step CoT investigation
3. **Receive Comprehensive Report**: Get technical findings from all 5 steps
4. **Interpret for User**: Translate technical results into business audit language
5. **Flag Issues**: Highlight items requiring documentation or follow-up
6. **Ask to Continue**: Offer to analyze remaining exceptions

**Instruction to Coder**:
"Execute full CoT investigation on mv_id 45678"

**Sample Coder Response**:
```
[Complete 5-step analysis from Coder following instruction.md framework]

STEP 1: Transaction identified - Customer cancellation, keywords: "cancellation", "customer"
STEP 2: Complete reversal - Debit Revenue 2.5M, Credit AR 2.5M
STEP 3: Classified as CASE A (Revenue Reversal/Return) - LOW risk if documented
STEP 4: Original entry found - mv_id 42301 from 91 days earlier (Sept 28)
STEP 5: Complete reversal analysis - All components reversed, MEDIUM-HIGH risk due to cross-quarter timing

FLAGGED FOR AUDITOR REVIEW:
1. Review contract and revenue recognition policy
2. Investigate Q3 revenue procedures
3. Request contract dispute documentation
```

**Final Answer to User**:
"## Investigation Results - mv_id 45678 (2.5M Product Sales Reversal)

**Transaction Classification**: Revenue Reversal/Return (CASE A)

**What Happened**:
This is a complete reversal of a Q3 product sale to ABC Corp. The original sale was recorded on September 28, 2023, and was fully unwound on December 28, 2023 (91 days later) due to a customer cancellation related to a contract dispute.

**Original Transaction**:
- Date: Sept 28, 2023
- Debit: AR 2.5M
- Credit: Revenue 2.5M
- Description: "Product sales - Q3 shipment to ABC Corp"

**Reversal Transaction**:
- Date: Dec 28, 2023
- Debit: Revenue 2.5M
- Credit: AR 2.5M
- Description: "Customer cancellation per contract dispute"

**Risk Assessment**: MEDIUM-HIGH

✓ Transaction is balanced and complete reversal identified
✗ Cross-quarter impact (Q3 revenue reversed in Q4)
✗ Year-end timing raises earnings management questions
✓ Clear documentation of business reason (customer cancellation)

**Audit Concerns**:
1. **Cross-Period Impact**: Q3 revenue reversed in Q4 affects financial reporting
2. **Timing**: Year-end reversal of Q3 transaction raises questions about original recognition appropriateness
3. **Pattern Risk**: Need to verify this isn't part of channel stuffing pattern

**Required Documentation**:
- ABC Corp contract terms and cancellation agreement
- Management approval for the reversal
- Assessment of why original Q3 recognition was appropriate if contract was later disputed
- Evaluation of other Q4 reversals for similar patterns

**Recommendation**: While this appears to be a legitimate customer cancellation, the cross-quarter timing and year-end posting require detailed review of the original revenue recognition decision and contract terms.

---

Would you like me to investigate the other material exceptions (mv_id 45920 - 1.8M and mv_id 46102 - 1.2M)?"

**User Response Handling**:
- If user says "Yes, analyze the next one" → Transfer to coder for mv_id 45920 investigation
- If user says "No, that's sufficient" → Conversation complete
- If user asks follow-up questions → Answer from context or request additional data from coder

---

**Complete Conversation Flow Example**:

**User**: "Give me a summary of debits on revenue"
**Auditor**: [Provides Mode A summary with year-over-year statistics]

**User**: "Can you provide more detail on those 3 material transactions from 2023?"
**Auditor**: [Provides Mode B list with all 3 exceptions]
**Auditor**: "Would you like me to investigate any of these in detail? I can perform a deep-dive analysis on the largest one (mv_id 45678, 2.5M) or any specific transaction you're interested in."

**User**: "Yes, investigate the largest one"
**Auditor**: "I'll perform a comprehensive investigation on mv_id 45678..."
**Auditor**: [Transfers to coder for Mode C deep investigation of mv_id 45678]
**Auditor**: [Receives coder's 5-step analysis, interprets for user in business terms]
**Auditor**: "Would you like me to investigate any of the other exceptions (mv_id 45920 or 46102)?"

**User**: "Yes, analyze mv_id 45920"
**Auditor**: [Transfers to coder for Mode C investigation of mv_id 45920]
**Auditor**: [Presents findings]
**Auditor**: "Would you like me to analyze the last one (mv_id 46102)?"

**User**: "No, that's good for now"
**Auditor**: "Understood. Let me know if you need any additional analysis."

---

*Additional test examples will be added here following the same structure: Purpose → Example Question → Chain of Thought → Instruction to Coder → Sample Response → Final Answer*
