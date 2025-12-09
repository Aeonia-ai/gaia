## Gemini Verification Process

My verification process follows a systematic, code-first approach for each document:

1.  **Locate the Document**: I start by finding the exact file path of the document to ensure I'm working with the correct version.

2.  **Identify Core Claims**: I read the document to identify its key architectural claims, implementation details, and procedural instructions.

3.  **Verify Against Code**: I then dive into the codebase to find evidence that supports or refutes these claims. This involves:
    *   **Searching for Files**: Using `glob` and `search_file_content` to find relevant files, configuration settings, and code snippets.
    *   **Reading Code**: Analyzing the implementation in key files (e.g., `main.py` for services, specific modules for business logic) to understand how the system actually works.
    *   **Checking Configurations**: Examining `docker-compose.yml`, `.env` files, and other configurations to verify environment-specific claims.
    *   **Reviewing Migrations**: Checking database migration scripts in the `migrations/` directory to verify database schemas.

4.  **Append Verification Status**: Once I have a clear picture, I append a `Verification Status` section to the end of the markdown document. This section includes:
    *   A "Verified By" and date stamp.
    *   A bulleted list of the core claims.
    *   For each claim, a status (**Verified**, **Partially Verified**, **Incorrect**, **Outdated**, or **Missing**).
    *   Specific code references (file paths and sometimes line numbers) that serve as evidence.
    *   A concluding summary of the document's accuracy.

5.  **Update the Index**: Finally, I update the main index file (`docs/+docs.md`) to reflect the verification status of the document, ensuring a centralized overview of the documentation's health.