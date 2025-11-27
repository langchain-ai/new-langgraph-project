# Coder Resources

**Note: This Resources section is for the Coder Agent's reference only. Use this information to understand the database structure and execute technical queries when requested by the Auditor Agent.**

## Resources – General

### Query Principles
- Always use parameterized queries for security
- Join `acr.mv` with `acr.pu` for account classification
- Include materiality thresholds from `acr.mt` when relevant
- Format monetary amounts consistently
- Provide clear, structured results for auditor interpretation

### SQL Tool Usage
When using the `execute_query` tool, follow these patterns:

**Basic Syntax:**
```sql
execute_query("SELECT columns FROM acr.table_name WHERE conditions ORDER BY column")
```

**Common Query Patterns:**
```sql
-- Get audit test results
execute_query("SELECT * FROM acr.audit_debit_on_revenue WHERE year = 2024")

-- Join with source transactions
execute_query("SELECT adr.account, adr.debit_amount, mv.description 
               FROM acr.audit_debit_on_revenue adr 
               LEFT JOIN acr.mv mv ON adr.mv_id = mv.id 
               WHERE adr.year = 2024")

-- Apply materiality filters
execute_query("SELECT * FROM acr.audit_debit_on_revenue 
               WHERE is_outside_materiality = true 
               ORDER BY debit_amount DESC")
```

**Security Notes:**
- Only SELECT statements are allowed
- Always use proper WHERE clauses to limit results
- Quote string values properly in WHERE conditions

## Resources – Schema

### Schema: `acr` (Audit Client Records)

The system uses PostgreSQL with a dedicated `acr` schema containing financial and audit data.

#### Core Financial Tables

**`acr.mv` (Movimientos - Transactions)**
Primary transaction table containing all GL movements:
- `account`, `account_name`, `level` - Account identification
- `posting_date`, `year`, `month` - Timing information
- `debit`, `credit`, `amount`, `value` - Monetary amounts
- `cost_center`, `third_id`, `document_type` - Reference data
- `description`, `entry_nu` - Transaction details

**`acr.pu` (Plan Único - Chart of Accounts)**
Account structure and hierarchy:
- `account`, `account_name` - Account identification
- `account_level1`, `account_level2` - Account classification hierarchy
- Revenue accounts identified by `account_level2` patterns

**`acr.mt` (Materiality)**
Materiality thresholds by year:
- `year`, `materiality` - Annual materiality limits for audit testing

**`acr.bl` (Balance)**
Account balances by period:
- `account`, `account_name`, `level` - Account identification
- `date`, `month`, `year` - Period information
- `previous_amount`, `debit`, `credit`, `amount` - Balance components

#### Audit Test Results Tables

**`acr.audit_debit_on_revenue`**
Pre-computed results of the "Debits in Credits" audit test:
- `mv_id` - Links back to source transaction in `acr.mv`
- `account`, `account_name`, `account_level2` - Account details
- `debit_amount`, `posting_date`, `year` - Transaction specifics
- `materiality_threshold`, `is_outside_materiality` - Test results
- `test_date` - When test was executed

#### Reference Tables
- **`acr.cc`**: Cost Centers (`codigo`, `descripcion`)
- **`acr.cdc`**: Cost Center Details (`cost_center_cod`, `name_center_cod`)
- **`acr.cbte`**: Document Types (`cbte`, `nombre_cbte`)
- **`acr.cop`**: Operating Centers (`centro_op`, `nom_c_op`)
- **`acr.au`**: Authorizations (`year`, `authorizations_cop`)

#### Data Relationships
- `acr.mv.account` → `acr.pu.account` (account classification)
- `acr.mv.year` → `acr.mt.year` (materiality thresholds)
- `acr.audit_debit_on_revenue.mv_id` → `acr.mv.id` (audit test source)
- `acr.mv.cost_center_code` → `acr.cc.codigo` (cost center details)

#### Technical Notes
- All monetary amounts use `DECIMAL(15,2)` precision
- Dates are PostgreSQL `DATE` type
- Account codes are `VARCHAR(50)`
- Always consider materiality thresholds from `acr.mt`
- Use ILIKE for case-insensitive text matching
- Revenue accounts typically contain 'revenue', 'ingreso', or similar in `account_level2`

## Resources – Tests

Available audit test query implementations with detailed technical guidance.

### Resources – Tests – Debits in Revenue

**Test Overview**:
The Debits in Revenue test is a substantive audit procedure that identifies unusual debit entries posted to revenue accounts. Since revenue accounts normally have credit balances, debit entries may indicate:
- Revenue reversals or corrections
- Misclassified expenses or adjustments
- Potential errors in transaction recording
- Fraudulent activity or manipulation

This test helps auditors assess the completeness and accuracy of revenue recognition by flagging transactions that deviate from normal posting patterns. The system pre-computes results in `acr.audit_debit_on_revenue` with materiality assessments to focus auditor attention on significant exceptions.

**The Coder Agent supports THREE modes for this test:**

---

#### Mode A: Summary Analysis

**Auditor Request**: "Provide a brief summary of the debits on revenue test"

**Chain of Thought Process**:
1. **Understand Request**: Auditor wants a high-level summary of the debits on revenue test across multiple dimensions
2. **Identify Data Source**: Use `acr.audit_debit_on_revenue` table for pre-computed test results
3. **Determine Aggregation Level**: Group by year to show trends and patterns
4. **Select Key Metrics**: 
   - Total exceptions (all debit entries found)
   - Material exceptions (exceeding materiality threshold)
   - Financial impact (total and average amounts)
   - Account type breakdown (Sales, Service, Other revenue categories)
5. **Schema Considerations**:
   - `year` field allows temporal analysis
   - `is_outside_materiality` boolean for materiality filtering
   - `debit_amount` for financial impact analysis
   - `account_level2` for revenue category classification
6. **Structure Query**: Use GROUP BY with aggregate functions and CASE statements for conditional counting
7. **Format Results**: Present multi-year summary with key performance indicators

**Query Implementation**:
```sql
execute_query("SELECT 
    year,
    COUNT(*) as total_exceptions,
    COUNT(CASE WHEN is_outside_materiality = true THEN 1 END) as material_exceptions,
    SUM(debit_amount) as total_debit_amount,
    AVG(debit_amount) as avg_exception_amount
FROM acr.audit_debit_on_revenue
GROUP BY year
ORDER BY year DESC")
```

**Technical Notes**:
- `COUNT(CASE WHEN...)` pattern for conditional aggregation of material exceptions
- `SUM()` and `AVG()` functions for financial impact analysis
- `ORDER BY year DESC` to show most recent data first
- Simple aggregation focused on core metrics without account type breakdown

**Expected Response Format**:
```
📊 Debits on Revenue Test - Multi-Year Summary

Year-over-Year Analysis:

2025:
- Total Exceptions: 7
- Material Exceptions: 0 (0% of total)
- Total Debit Amount: $11,783,043.00
- Average Exception: $1,683,291.86

2024:
- Total Exceptions: 300
- Material Exceptions: 0 (0% of total)
- Total Debit Amount: $99,617,515.05
- Average Exception: $332,058.38

2023:
- Total Exceptions: 286
- Material Exceptions: 3 (1% of total)
- Total Debit Amount: $850,114,382.90
- Average Exception: $2,972,427.91

Key Insights:
- Exception volume trend: Declining from 300 (2024) to 7 (2025)
- Material exception rate: Very low overall (only 3 in 2023)
- Average exception size: Highest in 2023 ($2.97M), lowest in 2024 ($332K)
- Total impact: Significant reduction from $850M (2023) to $12M (2025)
```

---

#### Mode B: List Specific Exceptions

**Auditor Request**: "Get all material exceptions from {YEAR} with details" or "List exceptions for account {ACCOUNT}"

**Chain of Thought Process**:
1. **Understand Request**: Auditor needs detailed list of specific exceptions based on criteria
2. **Identify Data Source**: Use `acr.audit_debit_on_revenue` table
3. **Apply Filters**: Extract criteria from auditor request (materiality, year, account, date range)
4. **Select Detail Fields**: Include mv_id, account, amount, date, description for reference
5. **Order Results**: Largest amounts first (ORDER BY debit_amount DESC)
6. **Return mv_id**: Enable auditor to request deep-dive on specific transactions

**Query Implementation**:
```sql
execute_query("SELECT
    mv_id,
    account,
    account_name,
    debit_amount,
    posting_date,
    description,
    is_outside_materiality
FROM acr.audit_debit_on_revenue
WHERE is_outside_materiality = true
  AND year = {YEAR}
ORDER BY debit_amount DESC")
```

**Technical Notes**:
- Replace {YEAR} with actual year from auditor request
- Can adapt WHERE clause for different filters: `account = '{ACCOUNT}'`, `posting_date >= '{START_DATE}'`
- Common filter combinations: materiality + year, year only, account only
- ORDER BY debit_amount DESC prioritizes largest exceptions
- mv_id critical for subsequent deep-dive requests (Mode C)

**Expected Response Format**:
```
📋 Material Exceptions from {YEAR}

Found {X} material exceptions:

1. mv_id: {ID1}
   Account: {ACCOUNT} - {ACCOUNT_NAME}
   Amount: ${AMOUNT}
   Date: {DATE}
   Description: "{DESCRIPTION}"

2. mv_id: {ID2}
   Account: {ACCOUNT} - {ACCOUNT_NAME}
   Amount: ${AMOUNT}
   Date: {DATE}
   Description: "{DESCRIPTION}"

Total Material Impact: ${TOTAL_AMOUNT}
```

---

#### Mode C: Deep Investigation (5-Step Chain of Thought Analysis)

**Auditor Request**: "Execute full CoT investigation on mv_id {FLAGGED_MV_ID}"

**Overview**: Performs comprehensive 5-step analysis following the validated CoT framework from instruction.md. Each step executes sequentially, using results to inform subsequent steps.

---

**STEP 1: Identify Flagged Transaction**

**Goal**: Get transaction details and analyze description for keywords

**Chain of Thought Process**:
1. **Retrieve Transaction**: Get flagged transaction from audit table
2. **Join Source Data**: Link to acr.mv for complete information
3. **Analyze Description**: Scan for keywords per instruction.md framework
4. **Assess Quality**: Detailed vs Vague vs Missing
5. **Extract References**: Customer names, invoice numbers
6. **Capture Variables**: Store mv_id, amount, date, cbte_no/type for next steps

**Query Implementation**:
```sql
execute_query("SELECT
    adr.mv_id,
    adr.account,
    adr.account_name,
    adr.debit_amount,
    adr.posting_date,
    adr.is_outside_materiality,
    mv.description,
    mv.third_id,
    mv.third_name,
    mv.cbte_no,
    mv.cbte_type
FROM acr.audit_debit_on_revenue adr
LEFT JOIN acr.mv mv ON adr.mv_id = mv.id
WHERE adr.mv_id = {FLAGGED_MV_ID}")
```

**Technical Notes**:
- Replace {FLAGGED_MV_ID} with mv_id from auditor request
- Capture cbte_no and cbte_type for Step 2
- Store debit_amount and posting_date for Step 4
- Analyze description for keywords: reversal, correction, adjustment, cancel, refund, reclass, defer

**Expected Response Format**:
```
===================================
STEP 1: TRANSACTION IDENTIFICATION
===================================

Transaction mv_id {FLAGGED_MV_ID} flagged:
- Account: {account_name} ({account})
- Debit Amount: {debit_amount}
- Date: {posting_date}
- Description: "{description}"

DESCRIPTION ANALYSIS:

Analyzing the description: "{description}"

Keywords Found:
- Reversal/Reverse: {YES/NO}
- Correction/Correct: {YES/NO}
- Adjustment/Adjust: {YES/NO}
- Cancellation/Cancel: {YES/NO}
- Refund/Return: {YES/NO}
- Error: {YES/NO}
- Reclassification: {YES/NO}
- Deferral/Defer: {YES/NO}
- Customer/Client: {extract if present}
- Invoice/Contract: {extract if present}

Initial Inference: {hypothesis based on keywords}
Preliminary Classification: {type of transaction}
Confidence Level: {HIGH/MEDIUM/LOW}
```

---

**STEP 2: Get Complete Transaction Context**

**Goal**: Retrieve all journal entries in the flagged transaction

**Chain of Thought Process**:
1. **Use cbte_no/type**: From Step 1 to get all entry lines
2. **Get All Lines**: Both debit and credit sides
3. **Verify Balance**: Ensure debits = credits
4. **Identify Patterns**: Which accounts debited vs credited
5. **List Accounts**: Show complete transaction structure
6. **Account Types**: Identify using account code patterns (4XXXXX=Revenue, 1XXXXX=Assets, 2XXXXX=Liabilities, 5XXXXX=Expenses)

**Query Implementation**:
```sql
-- Get all entries in the transaction (both debits and credits)
execute_query("SELECT
    mv.id,
    mv.account,
    mv.account_name,
    mv.cbte_no,
    mv.cbte_type,
    mv.posting_date,
    mv.credit,
    mv.debit,
    mv.description,
    mv.third_id,
    mv.third_name
FROM acr.mv mv
WHERE mv.cbte_no = (SELECT cbte_no FROM acr.mv WHERE id = {FLAGGED_MV_ID})
  AND mv.cbte_type = (SELECT cbte_type FROM acr.mv WHERE id = {FLAGGED_MV_ID})
ORDER BY mv.debit DESC, mv.credit DESC")
```

**Technical Notes**:
- Replace {FLAGGED_MV_ID} with the mv_id from Step 1
- Uses subqueries to get cbte_no and cbte_type from the flagged transaction
- ORDER BY shows debits first, then credits
- Verify SUM(debit) = SUM(credit) for balanced entry
- Account code patterns: 4XXXXX=Revenue, 1XXXXX=Assets, 2XXXXX=Liabilities, 5XXXXX=Expenses

**Expected Response Format**:
```
===================================
STEP 2: COMPLETE TRANSACTION CONTEXT
===================================

Transaction {cbte_no} ({cbte_type}) Analysis:
- Date: {posting_date}
- Number of entries: {entry_count}
- Total Debits: {total_debit}
- Total Credits: {total_credit}
- Balance Check: {✓ BALANCED or ✗ UNBALANCED}

Journal Entry Details:

DEBITS:
- Account {account} - {account_name}: {amount}

CREDITS:
- Account {account} - {account_name}: {amount}

Customer/Entity: {third_name} (ID: {third_id})

This transaction shows:
{describe pattern using account codes to identify types:
- 4XXXXX = Revenue accounts
- 1XXXXX = Asset accounts (receivables, cash)
- 2XXXXX = Liability accounts (deferred revenue)
- 5XXXXX = Expense accounts}

Based on accounts involved, this appears to be: {initial classification}
```

---

**STEP 3: Classify Transaction Pattern**

**Goal**: Identify transaction type based on accounts involved

**Chain of Thought Process**:
1. **Review Accounts**: From Step 2, identify debit and credit account types
2. **Match Patterns**: Compare to CASE A-F framework from instruction.md
3. **Assess Risk**: Determine risk level based on pattern
4. **Check Red Flags**: Round numbers, end of period, vague descriptions
5. **Determine Next Step**: Based on classification
6. **Document Findings**: Classify and explain

**Pattern Classification** (from instruction.md):
- **CASE A**: Debit Revenue (4XXXXX), Credit AR/Cash (1XXXXX) → Revenue Reversal/Return → LOW risk → GO TO STEP 4
- **CASE B**: Debit Revenue (4XXXXX), Credit Revenue (4XXXXX) → Reclassification → MEDIUM risk → Document, flag for review
- **CASE C**: Debit Revenue (4XXXXX), Credit Liability (2XXXXX) → Revenue Deferral → MEDIUM risk → GO TO STEP 4
- **CASE D**: Debit Revenue (4XXXXX), Credit Asset (1XXXXX) → Revenue to Asset → MEDIUM-HIGH risk → GO TO STEP 4
- **CASE E**: Debit Revenue (4XXXXX), Credit Expense (5XXXXX) → Revenue to Expense → HIGH risk → Flag immediately
- **CASE F**: Multiple revenue debits, mixed credits → Partial Multi-Component → MEDIUM risk → GO TO STEP 4

**No Query for This Step** (analysis only)

**Technical Notes**:
- Use account code first digit to determine type
- Red flags: round numbers, month-end dates (28-31), vague descriptions
- If CASE B or E: Document and flag, may skip to final report
- If CASE A, C, D, or F: Proceed to Step 4

**Expected Response Format**:
```
===================================
STEP 3: PATTERN CLASSIFICATION
===================================

Pattern Classification: CASE {X} - {Pattern Name}

Analysis:
- Revenue account {account_name} was debited: {amount}
- Offsetting credit to {account_name}: {amount}
- This indicates: {business interpretation}

Red Flags Check:
{✓ or ✗} Round number (potential estimate/manipulation)
{✓ or ✗} End of period posting (last day of month/quarter/year)
{✓ or ✗} Vague description ('adjustment', 'correction')
{✓ or ✗} Unusual account combination
{✓ or ✗} Posted after period close
{✓ or ✗} Weekend/holiday posting

Initial Risk Assessment: {LOW/MEDIUM/HIGH}

Next Step: {Proceed to Step 4 / Document and flag for auditor review}
```

---

**STEP 4: Search for Original Revenue Entry** (For CASE A, C, D, F only)

**Goal**: Find original credit to revenue being reversed

**Chain of Thought Process**:
1. **Apply Only If**: Classification is CASE A, C, D, or F
2. **Search Criteria**: CREDIT entries matching exact debit amount
3. **Date Filter**: Original must be on or before reversal date
4. **Exact Match**: Credit amount = debit amount from Step 1
5. **Exclude Self**: Don't include reversal transaction
6. **Handle Outcomes**: One match (proceed), none (flag), multiple (flag)

**Query Implementation**:
```sql
execute_query("WITH analyzed_transactions AS (
    SELECT id
    FROM acr.mv
    WHERE cbte_no = (SELECT cbte_no FROM acr.mv WHERE id = {FLAGGED_MV_ID})
      AND cbte_type = (SELECT cbte_type FROM acr.mv WHERE id = {FLAGGED_MV_ID})
),
target_info AS (
    SELECT
        debit as amount,
        posting_date as reversal_date,
        account as reversal_account,
        third_id
    FROM acr.mv
    WHERE id = {FLAGGED_MV_ID}
)
SELECT
    mv.id,
    mv.account,
    mv.account_name,
    mv.cbte_type,
    mv.cbte_no,
    mv.posting_date,
    mv.credit,
    mv.description,
    mv.third_id,
    mv.third_name,
    ti.reversal_date - mv.posting_date AS days_before_reversal
FROM acr.mv mv
CROSS JOIN target_info ti
WHERE mv.credit > 0
  AND mv.posting_date <= ti.reversal_date
  AND mv.credit = ti.amount
  AND mv.id NOT IN (SELECT id FROM analyzed_transactions)
ORDER BY mv.posting_date DESC
LIMIT 20")
```

**Technical Notes**:
- Replace {FLAGGED_MV_ID} with the mv_id from Step 1
- Uses subqueries to dynamically fetch cbte_no and cbte_type
- target_info CTE extracts debit amount, posting_date, and related fields from the flagged transaction
- LIMIT 20 prevents excessive results

**Expected Response Format**:

**If 1 match:**
```
===================================
STEP 4: ORIGINAL ENTRY SEARCH
===================================

✓ EXACT MATCH FOUND

Original Transaction:
- Original mv_id: {id}
- Date: {posting_date} ({days_before_reversal} days before reversal)
- Amount: {credit} (EXACT MATCH)
- Account: {account} - {account_name}
- Customer: {third_name} (ID: {third_id})
- cbte_no: {cbte_no}, cbte_type: {cbte_type}
- Description: {description}

This is definitively the original entry being reversed.

PROCEEDING TO STEP 5 to analyze the full original transaction.
```

**If no match:**
```
===================================
STEP 4: ORIGINAL ENTRY SEARCH
===================================

⚠️ NO EXACT MATCH FOUND

No credit entry found matching reversal amount of {amount}.

Possible Reasons:
1. Original entry was for different amount
2. Original entry uses different account
3. Not correcting a prior entry
4. Partial reversal of larger transaction
5. Data integrity issue

FLAGGED FOR AUDITOR REVIEW: Requires business explanation and documentation
```

**If multiple matches:**
```
===================================
STEP 4: ORIGINAL ENTRY SEARCH
===================================

⚠️ MULTIPLE EXACT MATCHES FOUND

Found {X} transactions with exact same amount:

{For each:}
{n}. Transaction ID: {id}
   - Date: {posting_date} ({days_before_reversal} days before reversal)
   - Amount: {credit} (EXACT MATCH)
   - Account: {account} - {account_name}
   - Customer: {third_name} (ID: {third_id})
   - Description: {description}

FLAGGED FOR AUDITOR REVIEW: Requires selection of correct original transaction
```

---

**STEP 5: Analyze Original Transaction** (If original found in Step 4)

**Goal**: Retrieve and analyze complete original transaction

**Chain of Thought Process**:
1. **Execute Only If**: Original found in Step 4 (one exact match)
2. **Retrieve Original**: Get complete journal entry using original mv_id
3. **Compare Entries**: Side-by-side original vs reversal
4. **Reversal Type**: Complete or partial
5. **Business Interpretation**: Explain what happened
6. **Risk Assessment**: Apply LOW/MEDIUM/HIGH criteria from instruction.md
7. **Compile Report**: Comprehensive findings integrating all 5 steps

**Query Implementation**:
```sql
execute_query("SELECT
    mv.id,
    mv.account,
    mv.account_name,
    mv.cbte_no,
    mv.cbte_type,
    mv.posting_date,
    mv.credit,
    mv.debit,
    mv.description,
    mv.third_id,
    mv.third_name
FROM acr.mv mv
WHERE mv.cbte_no = (SELECT cbte_no FROM acr.mv WHERE id = {ORIGINAL_ID})
  AND mv.cbte_type = (SELECT cbte_type FROM acr.mv WHERE id = {ORIGINAL_ID})
ORDER BY CASE WHEN mv.debit > 0 THEN 1 ELSE 2 END, mv.debit DESC, mv.credit DESC")
```

**Technical Notes**:
- Replace {ORIGINAL_ID} with mv_id from Step 4
- ORDER BY shows debits first
- Compare to Step 2 reversal entry
- Check if complete or partial reversal
- Apply risk framework from instruction.md

**Expected Response Format**:
```
===================================
STEP 5: ANALYZE ORIGINAL TRANSACTION
===================================

ORIGINAL TRANSACTION:
Transaction: cbte_no {cbte_no}, type {cbte_type}
Date: {posting_date}
Customer/Entity: {third_name} (ID: {third_id})
Description: {description}

DEBITS (Assets/Receivables recognized):
- ID {id}: Account {account} - {account_name}: {debit}

Total Debits: {sum of all debits}

CREDITS (Revenue recognized):
- ID {id}: Account {account} - {account_name}: {credit}

Total Credits: {sum of all credits}

Balance Check: {✓ BALANCED or ✗ UNBALANCED}

===================================

REVERSAL TRANSACTION:
(From Step 2 - mv_id {FLAGGED_MV_ID})
Transaction: cbte_no {reversal_cbte_no}, type {reversal_cbte_type}
Date: {reversal_posting_date}

DEBITS:
- ID {id}: Account {account} - {account_name}: {debit}

CREDITS:
- ID {id}: Account {account} - {account_name}: {credit}

===================================

COMPARISON:

FULLY REVERSED:
- Account {account} - {account_name}
  Original: Credit {original_amount} → Reversal: Debit {reversal_amount}
  Status: ✓ Fully reversed

NOT REVERSED:
{List any components from original that were NOT reversed}

===================================

REVERSAL TYPE:

{If all reversed:}
Type: COMPLETE REVERSAL
All components of the original transaction were reversed.

{If partial:}
Type: PARTIAL REVERSAL
Original had {X} revenue components:
REVERSED: {Y} of {X} components, Total: {sum}
UNCHANGED: {Z} of {X} components, Total: {sum}

===================================

RISK ASSESSMENT:

Risk Level: {LOW/MEDIUM/HIGH}

Risk Factors:
{✓ or ✗} Transaction is balanced
{✓ or ✗} Original entry clearly identified with exact match
{✓ or ✗} Same period (no cross-period impact)
{✓ or ✗} Business logic is clear from descriptions
{✓ or ✗} Same-day reversal (control concern)
{✓ or ✗} End-of-period posting
{✓ or ✗} Clear documentation in descriptions

===================================

BUSINESS INTERPRETATION:

{Provide clear interpretation based on:
- Account types involved (revenue, assets, liabilities)
- Whether partial or complete reversal
- Descriptions from both transactions
- Customer/entity involved}

===================================

REQUIRED ACTIONS:

Documentation Needed:
□ Written explanation for the reversal
□ {If partial: Justification for selective component reversal}
□ Approval documentation
□ {If crosses periods: Materiality assessment}
□ Supporting documents (contracts, credit memos, etc.)

Questions to Ask:
1. What was the specific reason for this {complete/partial} reversal?
2. {If same day: Why was this not caught before posting?}
3. {If partial: Why were some components valid but others not?}
4. Who approved this adjustment?
5. What documentation supports this reversal?

===================================

RECOMMENDATION:

{If LOW risk:}
This appears to be a legitimate correction.
Action: Document business reason, verify approval, and close once documented.

{If MEDIUM risk:}
This transaction requires detailed documentation.
Action: Obtain explanation, verify revenue recognition policy compliance,
confirm not part of pattern, then close with documentation.

{If HIGH risk:}
This transaction has significant concerns.
Action: Obtain comprehensive documentation, interview personnel, review
all supporting documents, assess materiality if cross-period, consider
escalation. Do not close until thoroughly investigated.

===================================

SUMMARY:

Based on analysis of mv_id {FLAGGED_MV_ID} and its original transaction (ID {ORIGINAL_ID}):

This appears to be: {legitimate correction / questionable adjustment / high-risk transaction}

Key Findings:
1. {Main finding 1}
2. {Main finding 2}
3. {Main finding 3}

Next Steps: {Clear, specific action items for auditor to communicate to user}
```