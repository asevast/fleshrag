# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-frontend.spec.js >> FleshRAG Frontend Tests >> send message in conversation
- Location: test-frontend.spec.js:126:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: apiRequestContext.post: Request context disposed.
Call log:
  - → POST http://localhost:8000/api/conversations/11/ask
    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/25.0
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - content-type: application/json
    - content-length: 40

```

# Page snapshot

```yaml
- generic [ref=e4]:
  - banner [ref=e5]:
    - generic [ref=e6]:
      - generic [ref=e7]:
        - generic [ref=e8]: FleshRAG MVP
        - heading "Multimodal workspace for search, grounded answers and operations" [level=1] [ref=e9]
        - paragraph [ref=e10]: Один экран для поиска, вопрос-ответа, библиотеки, диалогов и runtime-управления. Текущий shell приведён к фактическим backend endpoint'ам.
      - generic [ref=e11]:
        - generic [ref=e12]:
          - generic [ref=e13]: Search results
          - generic [ref=e14]: "0"
          - generic [ref=e15]: гибридный retrieval
        - generic [ref=e16]:
          - generic [ref=e17]: Ask mode
          - generic [ref=e18]: ready
          - generic [ref=e19]: grounded answer
        - generic [ref=e20]:
          - generic [ref=e21]: Dialogs
          - generic [ref=e22]: new
          - generic [ref=e23]: RAG history and export
  - navigation [ref=e24]:
    - button "Search Гибридный поиск по индексу" [ref=e25] [cursor=pointer]:
      - generic [ref=e26]: Search
      - generic [ref=e27]: Гибридный поиск по индексу
    - button "Ask Ответ с источниками и стримингом" [ref=e28] [cursor=pointer]:
      - generic [ref=e29]: Ask
      - generic [ref=e30]: Ответ с источниками и стримингом
    - button "Library Просмотр индексированных файлов" [ref=e31] [cursor=pointer]:
      - generic [ref=e32]: Library
      - generic [ref=e33]: Просмотр индексированных файлов
    - button "Dialogs История RAG-сессий" [ref=e34] [cursor=pointer]:
      - generic [ref=e35]: Dialogs
      - generic [ref=e36]: История RAG-сессий
    - button "Admin Провайдер, статус и бюджет" [ref=e37] [cursor=pointer]:
      - generic [ref=e38]: Admin
      - generic [ref=e39]: Провайдер, статус и бюджет
  - main [ref=e40]:
    - generic [ref=e41]:
      - generic [ref=e43]:
        - textbox "Введите запрос..." [ref=e44]
        - button "🔧" [ref=e45] [cursor=pointer]
        - button "Искать" [ref=e46] [cursor=pointer]
      - generic [ref=e48]:
        - generic [ref=e49]: Поиск пока пуст
        - generic [ref=e50]: Запустите запрос, чтобы получить релевантные фрагменты, файл и превью по клику.
```

# Test source

```ts
  29  | 
  30  |   test('search tab is active by default', async ({ page }) => {
  31  |     const searchSection = page.locator('section').first();
  32  |     await expect(searchSection).toBeVisible();
  33  |   });
  34  | 
  35  |   test('search bar is visible and editable', async ({ page }) => {
  36  |     const searchInput = page.locator('input[type="text"]').first();
  37  |     await expect(searchInput).toBeVisible();
  38  |     await searchInput.fill('test query');
  39  |     await expect(searchInput).toHaveValue('test query');
  40  |   });
  41  | 
  42  |   test('can switch to Ask tab', async ({ page }) => {
  43  |     await page.getByRole('button', { name: 'Ask' }).click();
  44  |     await expect(page.getByText('Ответ с источниками')).toBeVisible();
  45  |   });
  46  | 
  47  |   test('can switch to Library tab', async ({ page }) => {
  48  |     await page.getByRole('button', { name: 'Library' }).click();
  49  |     await expect(page.getByRole('heading', { name: 'Файлы' })).toBeVisible();
  50  |   });
  51  | 
  52  |   test('can switch to Admin tab', async ({ page }) => {
  53  |     await page.getByRole('button', { name: 'Admin' }).click();
  54  |     await expect(page.getByText('Admin Console')).toBeVisible();
  55  |   });
  56  | 
  57  |   test('health check via API', async ({ request }) => {
  58  |     const response = await request.get('http://localhost:8000/api/health');
  59  |     expect(response.status()).toBeLessThan(500);
  60  |     const data = await response.json();
  61  |     expect(data.status).toBe('healthy');
  62  |   });
  63  | 
  64  |   test('dialogs tab shows conversation interface', async ({ page }) => {
  65  |     await page.getByRole('button', { name: 'Dialogs' }).click();
  66  |     await page.waitForTimeout(3000);
  67  |     await expect(page.getByRole('heading', { name: 'Диалоги' })).toBeVisible();
  68  |   });
  69  | 
  70  |   // ============================================================
  71  |   // 1. SEARCH API TESTS
  72  |   // ============================================================
  73  |   test('search API handles embed-service error', async ({ request }) => {
  74  |     const response = await request.post('http://localhost:8000/api/search', {
  75  |       data: { query: 'docker', top_k: 5 }
  76  |     });
  77  |     expect(response.status()).toBeLessThan(503);
  78  |   });
  79  | 
  80  |   test('search via UI handles errors', async ({ page }) => {
  81  |     const searchInput = page.locator('input[type="text"]').first();
  82  |     await searchInput.fill('тест');
  83  |     await searchInput.press('Enter');
  84  |     await page.waitForTimeout(5000);
  85  |     const emptyState = page.getByText('Поиск пока пуст');
  86  |     await expect(emptyState).toBeVisible({ timeout: 10000 });
  87  |   });
  88  | 
  89  |   test('search handles empty query', async ({ request }) => {
  90  |     const response = await request.post('http://localhost:8000/api/search', {
  91  |       data: { query: '', top_k: 5 }
  92  |     });
  93  |     expect(response.status()).toBeLessThan(503);
  94  |   });
  95  | 
  96  |   // ============================================================
  97  |   // 2. ASK MODE (RAG) TESTS
  98  |   // ============================================================
  99  |   // test('ask mode UI accepts question', async ({ page }) => {
  100 |   //   // Skipped: textarea selector needs refinement
  101 |   //   test.skip();
  102 |   // });
  103 | 
  104 |   test('ask mode API handles embed error', async ({ request }) => {
  105 |     const response = await request.post('http://localhost:8000/api/ask', {
  106 |       data: { query: 'Что такое RAG?', top_k: 3 }
  107 |     });
  108 |     expect(response.status()).toBeLessThan(503);
  109 |   });
  110 | 
  111 |   // test('ask mode UI remains responsive', async ({ page }) => {
  112 |   //   // Skipped: textarea selector needs refinement
  113 |   //   test.skip();
  114 |   // });
  115 | 
  116 |   // ============================================================
  117 |   // 3. DIALOGS (CONVERSATIONS) TESTS
  118 |   // ============================================================
  119 |   test('create new conversation via API', async ({ request }) => {
  120 |     const response = await request.post('http://localhost:8000/api/conversations?title=Test Dialog');
  121 |     expect(response.ok()).toBeTruthy();
  122 |     const data = await response.json();
  123 |     expect(data).toHaveProperty('id');
  124 |   });
  125 | 
  126 |   test('send message in conversation', async ({ request }) => {
  127 |     const createRes = await request.post('http://localhost:8000/api/conversations?title=Msg Test');
  128 |     const { id } = await createRes.json();
> 129 |     const askRes = await request.post(`http://localhost:8000/api/conversations/${id}/ask`, {
      |                                  ^ Error: apiRequestContext.post: Request context disposed.
  130 |       data: { query: 'Привет!', stream: false }
  131 |     });
  132 |     expect(askRes.status()).toBeLessThan(503);
  133 |   });
  134 | 
  135 |   test('conversation history UI is visible', async ({ page }) => {
  136 |     await page.getByRole('button', { name: 'Dialogs' }).click();
  137 |     await page.waitForTimeout(5000);
  138 |     await expect(page.getByRole('heading', { name: 'Диалоги' })).toBeVisible();
  139 |     const newButton = page.getByText('+ Новый');
  140 |     await expect(newButton).toBeVisible();
  141 |   });
  142 | 
  143 |   test('delete conversation via API', async ({ request }) => {
  144 |     const createRes = await request.post('http://localhost:8000/api/conversations?title=Delete Test');
  145 |     const { id } = await createRes.json();
  146 |     const deleteRes = await request.delete(`http://localhost:8000/api/conversations/${id}`);
  147 |     expect(deleteRes.ok()).toBeTruthy();
  148 |   });
  149 | 
  150 |   // ============================================================
  151 |   // 4. FILE PREVIEW TESTS
  152 |   // ============================================================
  153 |   test('file preview API handles missing file', async ({ request }) => {
  154 |     const previewRes = await request.get(
  155 |       'http://localhost:8000/api/files/preview?path=/nonexistent/file.txt'
  156 |     );
  157 |     expect(previewRes.status()).toBe(404);
  158 |   });
  159 | 
  160 |   test('file browser displays indexed files', async ({ page }) => {
  161 |     await page.getByRole('button', { name: 'Library' }).click();
  162 |     await page.waitForTimeout(5000);
  163 |     await expect(page.getByRole('heading', { name: 'Файлы' })).toBeVisible();
  164 |     const filterControls = page.getByPlaceholder('Поиск по пути...');
  165 |     await expect(filterControls).toBeVisible();
  166 |   });
  167 | 
  168 |   test('file preview modal opens on click', async ({ page }) => {
  169 |     await page.getByRole('button', { name: 'Library' }).click();
  170 |     await page.waitForTimeout(5000);
  171 |     const firstFileCard = page.locator('[class*="border"]').first();
  172 |     const isVisible = await firstFileCard.isVisible().catch(() => false);
  173 |     if (isVisible) {
  174 |       await firstFileCard.click();
  175 |       await page.waitForTimeout(3000);
  176 |       await page.keyboard.press('Escape');
  177 |     }
  178 |   });
  179 | 
  180 |   test('file type filter works', async ({ page }) => {
  181 |     await page.getByRole('button', { name: 'Library' }).click();
  182 |     await page.waitForTimeout(3000);
  183 |     const typeSelect = page.locator('select').nth(1);
  184 |     await typeSelect.selectOption('pdf');
  185 |     await page.waitForTimeout(2000);
  186 |     const noFilesText = await page.getByText('Нет файлов').isVisible().catch(() => false);
  187 |     expect(noFilesText || true).toBeTruthy();
  188 |   });
  189 | 
  190 |   // ============================================================
  191 |   // 5. ADMIN PANEL TESTS
  192 |   // ============================================================
  193 |   test('admin panel shows all sections', async ({ page }) => {
  194 |     await page.getByRole('button', { name: 'Admin' }).click();
  195 |     await page.waitForTimeout(5000);
  196 |     await expect(page.getByText('Budget overview')).toBeVisible();
  197 |     await expect(page.getByText('Runtime models')).toBeVisible();
  198 |     await expect(page.getByText('Index health')).toBeVisible();
  199 |   });
  200 | 
  201 |   test('admin panel shows index stats', async ({ page }) => {
  202 |     await page.getByRole('button', { name: 'Admin' }).click();
  203 |     await page.waitForTimeout(5000);
  204 |     await expect(page.getByText('Index health')).toBeVisible();
  205 |     await expect(page.getByText('Total', { exact: true })).toBeVisible();
  206 |   });
  207 | 
  208 |   test('admin panel refresh works', async ({ page }) => {
  209 |     await page.getByRole('button', { name: 'Admin' }).click();
  210 |     await page.waitForTimeout(5000);
  211 |     const refreshButton = page.getByRole('button', { name: 'Refresh' });
  212 |     await refreshButton.click();
  213 |     await page.waitForTimeout(3000);
  214 |     await expect(refreshButton).toBeEnabled();
  215 |   });
  216 | 
  217 |   test('admin panel test connection', async ({ page }) => {
  218 |     await page.getByRole('button', { name: 'Admin' }).click();
  219 |     await page.waitForTimeout(5000);
  220 |     const testButton = page.getByRole('button', { name: 'Test connection' });
  221 |     await testButton.click();
  222 |     await page.waitForTimeout(10000);
  223 |     const isDisabled = await testButton.isDisabled();
  224 |     expect(isDisabled).toBeFalsy();
  225 |   });
  226 | 
  227 |   test('admin panel reindex button exists', async ({ page }) => {
  228 |     await page.getByRole('button', { name: 'Admin' }).click();
  229 |     await page.waitForTimeout(5000);
```