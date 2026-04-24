---
name: browser
description: Browser automation using the browser MCP for web scraping, form filling, content extraction, and macro execution. Use when user asks to open websites, search pages, extract data, fill forms, or automate browser tasks.
---

# Browser Automation Skill

This skill provides browser automation capabilities through direct execution of MCP tools. **You will execute MCP tools directly** based on task-specific instructions from specialization modules.

## When to Use This Skill

Activate when the user requests:
- Web browsing or navigation
- Data extraction or web scraping
- Form filling or automation
- E-commerce operations (Amazon, Google Shopping, Walmart)
- Testing or quality assurance
- Screenshot capture and analysis
- Multi-tab workflows

## How This Skill Works

1. **Detect task type** from user request (keywords, intent analysis)
2. **Route to specialization module** (ECOMMERCE.md, FORMS.md, SCRAPER.md, QA.md, SCREENSHOT_ANALYSIS.md)
3. **Follow module instructions** to invoke MCP tools directly
4. **Preserve tab context** for multi-turn workflows
5. **Return results** with tab metadata for future operations

## Task Type Detection

Analyze user request to determine which specialization module to use:

### E-Commerce Tasks → ECOMMERCE.md

**Trigger keywords**: "amazon", "shopping", "price", "product", "reviews", "buy", "purchase", "compare prices", "best deal", "rufus", "cart", "google shopping", "walmart"

**Example requests**:
- "Search Amazon for wireless headphones under $100"
- "Compare prices for this product on Amazon and Walmart"
- "Find the best value poly strapping kit"
- "What are the reviews saying about this product?"
- "Ask Rufus AI about laptop recommendations"

**Action**: Follow `.claude/skills/browser/ECOMMERCE.md` for step-by-step tool invocation instructions

### Form Automation → FORMS.md

**Trigger keywords**: "form", "fill", "submit", "input", "field", "validation", "signup", "register", "contact form"

**Example requests**:
- "Fill out the contact form on example.com"
- "Discover all forms on this page"
- "Submit the registration form with test data"
- "Analyze the form fields and validation rules"

**Action**: Follow `.claude/skills/browser/FORMS.md` - **CRITICAL**: Never auto-submit without user approval

### Web Scraping → SCRAPER.md

**Trigger keywords**: "scrape", "extract", "data", "table", "pagination", "export", "collect", "gather", "crawl", "pages 1-10"

**Example requests**:
- "Extract all product data from this page"
- "Scrape the table and export to CSV"
- "Collect data from pages 1-5 with pagination"
- "Get all article titles from this site"

**Action**: Follow `.claude/skills/browser/SCRAPER.md` for extraction and export patterns

### QA Testing → QA.md

**Trigger keywords**: "test", "qa", "accessibility", "performance", "audit", "wcag", "a11y", "validate", "check", "analyze", "keyboard navigation"

**Example requests**:
- "Audit this page for accessibility issues"
- "Run a performance test on example.com"
- "Check WCAG 2.1 compliance"
- "Test keyboard navigation"

**Action**: Follow `.claude/skills/browser/QA.md` for testing workflows and report generation

### Screenshot Analysis → SCREENSHOT_ANALYSIS.md

**Trigger keywords**: "screenshot", "analyze screenshot", "visual", "layout", "design consistency", "contrast", "color analysis", "compare screenshots"

**Example requests**:
- "Analyze these screenshots for accessibility issues"
- "Check the color contrast in this screenshot"
- "Compare design consistency across these screenshots"
- "Generate a visual audit report"

**Action**: Follow `.claude/skills/browser/SCREENSHOT_ANALYSIS.md` for analysis workflows

### Macro Learning → MACRO_LEARNING.md

**Trigger keywords**: "learn", "automate this", "create macro", "record", "capture", "demonstrate", "teach you", "how to automate", "save this workflow", "reusable"

**Example requests**:
- "Can you learn how to do this workflow?"
- "I want to automate this process"
- "Let me show you how to search this site"
- "Create a macro for adding items to cart"
- "Learn how I navigate this form"

**Action**: Follow `.claude/skills/browser/MACRO_LEARNING.md` for capturing user demonstrations and creating reusable macros

### Generic Browser Operations → Direct Execution

**Trigger keywords**: "navigate", "go to", "open", "screenshot", "tab", "browse", "visit"

**Example requests**:
- "Navigate to example.com"
- "Take a screenshot of this page"
- "Create a new tab"
- "List all open tabs"

**Action**: Use direct MCP tool invocation (see Quick Reference below)

## Specialization Module Structure

Each specialization module (ECOMMERCE.md, FORMS.md, etc.) provides:

1. **When to use** - Trigger keywords and task types
2. **Available macros** - Site-specific and universal macros for this domain
3. **Execution workflows** - Step-by-step MCP tool invocation instructions
4. **Safety protocols** - Critical rules (e.g., never auto-submit forms)
5. **Token conservation** - Domain-specific tips
6. **Troubleshooting** - Common errors and solutions

**Your role**: Read the appropriate module and follow its instructions to invoke MCP tools.

## Execution Patterns

### Pattern 1: Macro-First Execution

**ALWAYS follow this pattern** for browser automation tasks:

1. **Check site-specific macros first**:
   ```
   Extract domain from URL (e.g., "amazon.com" from "https://www.amazon.com/...")

   Call: mcp__browser__browser_list_macros({
     site: "amazon.com",
     category: "search" // optional filter
   })

   If macro found → Use macro (go to step 3)
   If not found → Check universal macros (go to step 2)
   ```

2. **Check universal macros**:
   ```
   Call: mcp__browser__browser_list_macros({
     site: "*",
     category: "extraction" // or relevant category
   })

   If macro found → Use macro (go to step 3)
   If not found → Use direct MCP tools (go to step 4)
   ```

3. **Execute macro**:
   ```
   Call: mcp__browser__browser_execute_macro({
     id: "{macro_id}",
     params: { /* macro-specific parameters */ },
     tabTarget: tabId // if operating on existing tab
   })

   Return result with tab metadata
   ```

4. **Fall back to direct MCP tools**:
   ```
   Use browser_click, browser_type, browser_get_visible_text, etc.
   Follow token conservation rules (see below)
   ```

### Pattern 2: Tab Creation and Labeling

**Always create and label tabs** for organized multi-turn workflows:

```
1. Create tab:
   Call: mcp__browser__browser_create_tab({ url: "https://example.com" })
   Store tabId from result.content.tabId

2. Label tab:
   Call: mcp__browser__browser_set_tab_label({
     tabTarget: tabId,
     label: "descriptive-name" // e.g., "amazon-search", "form-filling", "scraping-products"
   })

3. Store tab context for future operations:
   amazonTab = 123
   walmartTab = 456
```

### Pattern 3: Multi-Turn Workflow

**Preserve tab context** across conversation turns:

```
Turn 1 - User: "Search Amazon for headphones"
You:
 1. Create tab (tabId = 123), label "amazon-search"
 2. Execute search macro or navigate + search
 3. Return results with tab metadata: { tabId: 123, label: "amazon-search", ... }
 4. STORE: amazonTab = 123

Turn 2 - User: "Get more details on the first result"
You:
 1. Use stored tab ID: tabTarget = 123
 2. Execute detail macro or click + extract
 3. Return results with same tab metadata
```

### Pattern 4: Cleanup Before Operations

**Always clean interruptions first** (cookie consents, modals, popups):

```
Before main operation:
 1. Check for cleanup macros:
    Call: mcp__browser__browser_list_macros({ site: "*", search: "cookie" })

 2. Execute cleanup:
    Call: mcp__browser__browser_execute_macro({
      id: "smart_cookie_consent",
      tabTarget: tabId
    })

    Call: mcp__browser__browser_execute_macro({
      id: "dismiss_interruptions",
      tabTarget: tabId
    })

 3. Then proceed with main operation
```

## Token Conservation Rules

**CRITICAL**: Always minimize token usage when executing browser automation.

### Rule 1: Avoid `browser_snapshot`

**Problem**: Returns massive ARIA tree (10,000+ tokens)

**Solution**: Use targeted alternatives

```
❌ DON'T:
Call: mcp__browser__browser_snapshot({ tabTarget: tabId })

✅ DO:
Call: mcp__browser__browser_get_visible_text({
  maxLength: 3000,
  tabTarget: tabId
})

OR use specific queries:
Call: mcp__browser__browser_query_dom({
  selector: "button, a, input",
  limit: 20,
  tabTarget: tabId
})
```

### Rule 2: Use Specialized Macros

**Problem**: Generic extraction returns too much data

**Solution**: Use targeted macros

```
❌ DON'T:
Call: mcp__browser__browser_get_visible_text({ maxLength: 10000 })

✅ DO:
Call: mcp__browser__browser_execute_macro({
  id: "get_interactive_elements", // Returns only buttons, links, inputs
  tabTarget: tabId
})

OR:
Call: mcp__browser__browser_execute_macro({
  id: "extract_table_data", // Returns only table data
  tabTarget: tabId
})
```

### Rule 3: Always Truncate Text Extraction

**Problem**: Full page text wastes tokens

**Solution**: Always set `maxLength`

```
❌ DON'T:
Call: mcp__browser__browser_get_visible_text({ tabTarget: tabId })

✅ DO:
Call: mcp__browser__browser_get_visible_text({
  maxLength: 3000, // or 5000 for longer pages
  tabTarget: tabId
})
```

### Rule 4: Limit DOM Queries

**Problem**: Returning 100+ elements wastes tokens

**Solution**: Always set `limit`

```
❌ DON'T:
Call: mcp__browser__browser_query_dom({
  selector: "div",
  tabTarget: tabId
})

✅ DO:
Call: mcp__browser__browser_query_dom({
  selector: "button.primary, a.cta", // Specific selector
  limit: 10, // Reasonable limit
  tabTarget: tabId
})
```

### Rule 5: Use Macros for Cleanup

**Problem**: Manual popup dismissal requires multiple steps

**Solution**: Use cleanup macros

```
✅ Efficient:
Call: mcp__browser__browser_execute_macro({
  id: "smart_cookie_consent",
  tabTarget: tabId
})

Call: mcp__browser__browser_execute_macro({
  id: "dismiss_interruptions",
  tabTarget: tabId
})
```

## Tab Context Preservation

**Pattern**: Create tabs → store IDs → reuse in follow-ups

### Tab Creation Workflow

```
1. User requests browser operation
2. Create tab with descriptive URL
3. Label tab with meaningful name
4. Execute operation
5. Return result with tab metadata
6. Store tab ID for future use
```

### Tab Metadata Format

**Always return** tab metadata with results:

```json
{
  "tabId": 123,
  "tabLabel": "amazon-search",
  "url": "https://www.amazon.com/s?k=headphones",
  "timestamp": "2025-12-22T11:58:10Z",
  "data": { /* operation results */ }
}
```

### Multi-Tab Scenarios

**Scenario 1: Parallel Comparison**

```
User: "Compare prices on Amazon and Walmart"

You:
1. Create Amazon tab (amazonTab = 123)
2. Create Walmart tab (walmartTab = 456)
3. Execute searches in both tabs (use tabTarget parameter)
4. Return results: { amazonTab: 123, walmartTab: 456, comparison: [...] }
5. Store both tab IDs

Follow-up: "Get more details on the Amazon result"
Use tabTarget = 123 (amazonTab)
```

**Scenario 2: Sequential Workflow**

```
User: "Fill out the contact form on example.com"

You:
1. Create tab (formTab = 123)
2. Discover forms (following FORMS.md)
3. Fill fields
4. Generate preview (DO NOT submit)
5. Return preview with tab metadata
6. Store formTab = 123

Follow-up: "Submit the form"
Use tabTarget = 123 (formTab)
Call: mcp__browser__browser_submit_form (ONLY after user approval)
```

### Tab Management Commands

**List attached tabs**:
```
Call: mcp__browser__browser_list_attached_tabs()
Returns: Array of { tabId, label, url }
```

**Attach to existing tab**:
```
Call: mcp__browser__browser_attach_tab({ tabId: 123 })
OR
Call: mcp__browser__browser_attach_tab({ autoOpenUrl: "https://example.com" })
```

**Close tab**:
```
Call: mcp__browser__browser_close_tab({ tabId: 123 })
```

## Available Macro Categories

**91+ macros** organized by category and site:

### Universal Macros (40+)
- **extraction**: `get_interactive_elements`, `extract_table_data`, `extract_main_content`
- **form**: `discover_forms`, `fill_form_fields`, `validate_form`
- **navigation**: `smart_scroll`, `wait_for_element`, `check_page_loaded`
- **util**: `smart_cookie_consent`, `dismiss_interruptions`, `close_modal`
- **interaction**: `safe_click`, `type_with_validation`, `select_dropdown`

### Site-Specific Macros (51)
- **Amazon** (17 macros): Search, product details, reviews, Rufus AI, cart operations
- **Google Shopping** (12 macros): Product search, comparison, price tracking
- **Walmart** (5 macros): Search, product details, reviews
- **Upwork** (4 macros): Job search, proposal submission
- **Fidelity** (4 macros): Account navigation, portfolio analysis
- **OpenGameArt** (3 macros): Asset search, license filtering
- **CoinTracker** (3 macros): Portfolio tracking, transaction import
- **Google** (3 macros): Search, results extraction

**See detailed documentation**:
- `.claude/skills/browser/MACROS.md` - Universal macros
- `.claude/skills/browser/AMAZON_MACROS.md` - Amazon-specific
- `.claude/skills/browser/GOOGLE_SHOPPING_MACROS.md` - Google Shopping
- `.claude/skills/browser/WALMART_MACROS.md` - Walmart
- (+ 5 more site-specific docs)

## Error Handling

### Common Errors and Solutions

**Error**: "No attached tabs"
```
Solution:
1. List attached tabs: mcp__browser__browser_list_attached_tabs()
2. If none, create and attach: mcp__browser__browser_attach_tab({ autoOpenUrl: "https://example.com" })
3. Retry operation with tabTarget
```

**Error**: "Tab not found (ID: 123)"
```
Solution:
1. List attached tabs to verify tab still exists
2. If tab closed, create new tab
3. Update stored tab ID
```

**Error**: "Macro not found"
```
Solution:
1. List available macros: mcp__browser__browser_list_macros({ site: "domain.com" })
2. Check spelling of macro ID
3. Fall back to direct MCP tools if macro doesn't exist
```

**Error**: "Navigation timeout"
```
Solution:
1. Retry navigation with increased wait time
2. Check if site is accessible
3. Use browser_wait({ time: 5 }) before retrying
```

**Error**: "Element not found"
```
Solution:
1. Use browser_query_dom to verify element exists
2. Try alternative selectors (ID, class, text content)
3. Check if element is in iframe or shadow DOM
4. Wait for dynamic content: browser_wait({ time: 2 })
```

**Error**: "Cannot read property of undefined"
```
Solution:
1. Verify return structure from MCP tool
2. Check that result.content exists before accessing properties
3. Add null checks: tabId = result?.content?.tabId || null
```

## Quick Reference

### Generic Browser Operations

**Navigate to URL**:
```
Call: mcp__browser__browser_navigate({
  url: "https://example.com",
  tabTarget: tabId // optional
})
```

**Take screenshot**:
```
Call: mcp__browser__browser_screenshot({
  tabTarget: tabId // optional
})
```

**Get visible text**:
```
Call: mcp__browser__browser_get_visible_text({
  maxLength: 3000,
  tabTarget: tabId // optional
})
```

**Click element**:
```
Call: mcp__browser__browser_click({
  element: "Submit button",
  ref: "element-reference-from-snapshot",
  tabTarget: tabId // optional
})
```

**Type text**:
```
Call: mcp__browser__browser_type({
  element: "Search input",
  ref: "element-reference-from-snapshot",
  text: "query text",
  submit: false, // or true to press Enter
  tabTarget: tabId // optional
})
```

**Query DOM**:
```
Call: mcp__browser__browser_query_dom({
  selector: "button.primary",
  limit: 10,
  tabTarget: tabId // optional
})
```

**Execute macro**:
```
Call: mcp__browser__browser_execute_macro({
  id: "macro_id",
  params: { /* macro-specific */ },
  tabTarget: tabId // optional
})
```

### Tab Management

**Create tab**:
```
Call: mcp__browser__browser_create_tab({
  url: "https://example.com" // optional
})
Store: tabId = result.content.tabId
```

**Label tab**:
```
Call: mcp__browser__browser_set_tab_label({
  tabTarget: tabId,
  label: "descriptive-name"
})
```

**List tabs**:
```
Call: mcp__browser__browser_list_attached_tabs()
```

**Close tab**:
```
Call: mcp__browser__browser_close_tab({
  tabId: tabId
})
```

### Macro Discovery

**List all macros for site**:
```
Call: mcp__browser__browser_list_macros({
  site: "amazon.com" // or "*" for universal
})
```

**Search macros by category**:
```
Call: mcp__browser__browser_list_macros({
  site: "*",
  category: "extraction" // extraction, form, navigation, util, interaction
})
```

## Safety Protocols

### Form Submission

**NEVER auto-submit forms** without explicit user approval.

```
✅ Correct flow:
1. Discover form: mcp__browser__browser_execute_macro({ id: "discover_forms" })
2. Fill fields: mcp__browser__browser_execute_macro({ id: "fill_form_fields", params: {...} })
3. Generate preview for user review
4. WAIT for user confirmation
5. Then submit: mcp__browser__browser_execute_macro({ id: "submit_form" })
```

### E-Commerce Operations

**DO NOT** complete purchases without explicit user approval.

```
✅ Correct flow:
1. Search products
2. Show results with prices and reviews
3. Add to cart ONLY on user request
4. Checkout ONLY on explicit user confirmation
```

### Data Extraction

**Respect robots.txt** and terms of service.

```
✅ Best practices:
1. Check site's robots.txt before large-scale scraping
2. Use rate limiting (wait between requests)
3. Extract only necessary data
4. Cache results to avoid repeated requests
```

## Troubleshooting

### Issue: Browser not responding

**Check**:
1. Is MCP Browser server running?
2. List attached tabs to verify connection
3. Try creating a new tab

### Issue: Macros not executing

**Check**:
1. Verify macro ID spelling
2. Check if macro exists for the target site
3. Ensure tab is attached and active
4. Try direct MCP tools as fallback

### Issue: High token usage

**Solutions**:
1. Always use `maxLength` in text extraction
2. Use `limit` in DOM queries
3. Prefer macros over raw snapshots
4. Extract only visible text, not full page

## Related Documentation

- `MACROS.md` - Complete list of universal macros
- `AMAZON_MACROS.md` - Amazon-specific macros (17)
- `GOOGLE_SHOPPING_MACROS.md` - Google Shopping macros (12)
- `WALMART_MACROS.md` - Walmart macros (5)
- `UPWORK_MACROS.md` - Upwork macros (4)
- `FIDELITY_MACROS.md` - Fidelity macros (4)
- `OPENGAMEART_MACROS.md` - OpenGameArt macros (3)
- `COINTRACKER_MACROS.md` - CoinTracker macros (3)
- `GOOGLE_MACROS.md` - Google search macros (3)
- `ECOMMERCE.md` - E-commerce task workflows
- `FORMS.md` - Form automation workflows
- `SCRAPER.md` - Web scraping workflows
- `QA.md` - QA testing workflows
- `SCREENSHOT_ANALYSIS.md` - Screenshot analysis workflows
- `MACRO_LEARNING.md` - Macro learning workflows
