```markdown
# fleshrag Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `fleshrag` Python repository. You will learn about file naming, import/export styles, commit message conventions, and testing patterns. This guide helps maintain consistency and efficiency when contributing to or extending the codebase.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `myModule.py`, `dataProcessor.py`

### Import Style
- Use **relative imports** within the project.
  - Example:
    ```python
    from .utils import helperFunction
    ```

### Export Style
- Use **default exports** (i.e., define the main class or function intended for use at the top level).
  - Example:
    ```python
    # In myModule.py
    def mainFunction():
        pass
    ```

### Commit Messages
- Follow **conventional commit** patterns.
- Use the `fix` prefix for bug fixes.
- Keep commit messages concise (average length: ~57 characters).
  - Example:
    ```
    fix: handle edge case in dataProcessor for empty input
    ```

## Workflows

### Fixing a Bug
**Trigger:** When you need to resolve a bug in the codebase  
**Command:** `/fix-bug`

1. Identify the bug and the affected module.
2. Create a new branch for the fix.
3. Apply the fix using camelCase file naming and relative imports as needed.
4. Write a commit message starting with `fix:`, describing the change.
5. Push your branch and open a pull request.

### Adding a New Module
**Trigger:** When introducing new functionality  
**Command:** `/add-module`

1. Create a new Python file using camelCase naming.
2. Implement the module, using relative imports for dependencies.
3. Export the main function or class as the default export.
4. Add or update tests as needed.
5. Commit your changes with a descriptive message.

## Testing Patterns

- **Framework:** Unknown (not detected)
- **Test file pattern:** `*.test.ts` (suggests some TypeScript testing, possibly for related tooling or scripts)
- Write tests in files ending with `.test.ts`.
- Place test files alongside the modules they test or in a dedicated test directory.

  Example:
  ```
  myModule.test.ts
  ```

## Commands
| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /fix-bug     | Guide for fixing a bug in the codebase       |
| /add-module  | Steps to add a new module to the repository  |
```
