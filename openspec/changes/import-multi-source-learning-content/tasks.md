## 1. Source Configuration

- [x] 1.1 Replace the single hard-coded course definition with explicit configurations for LangGraph, LangChain v1, and Deep Agents sources.
- [x] 1.2 Add source validation and Git-tracked-file discovery for the Deep Agents repository, including exclusions for dependencies, caches, workspaces, logs, and generated files.
- [x] 1.3 Preserve the existing 13 LangGraph document IDs and add metadata for chapters 14 and 15.

## 2. Content Import and Link Resolution

- [x] 2.1 Implement namespaced document ID generation so repeated filenames across Deep Agents topics cannot collide.
- [x] 2.2 Generalize relative Markdown link resolution for sibling documents, cross-source documents, fragments, examples, and upstream source files.
- [x] 2.3 Make unresolved relative links fail with the source file and original target in the error message.
- [x] 2.4 Generate collection and document manifest entries with stable order, section, source URL, and collection metadata.

## 3. Example Source Publishing

- [x] 3.1 Copy allowed tracked teaching source files to `public/examples` using the same namespace as document IDs.
- [x] 3.2 Generate `resources` entries that link each document to its local example source and retain upstream repository links.
- [x] 3.3 Ensure missing or disallowed example resources fail content validation before Astro build.

## 4. Content and Build Validation

- [x] 4.1 Extend import tests for all three source configurations, missing sources, duplicate IDs, and preserved legacy routes.
- [x] 4.2 Extend link rewriting tests for cross-topic documents, fragments, local example resources, external URLs, and unsupported relative links.
- [x] 4.3 Extend manifest and asset validation to cover generated example resources and allowed file extensions.
- [x] 4.4 Run `npm test`, `npm run assets:check`, and `npm run build`; verify all existing and new collection routes are generated.

## 5. Documentation and Refresh Workflow

- [x] 5.1 Update `README.md` with the three source directories, repository URLs, import command, filtering rules, and non-execution safety boundary.
- [x] 5.2 Document how to refresh content from local source checkouts and how to inspect example code from the site.
- [x] 5.3 Record the generated collection names, source revision assumptions, and any known upstream-link limitations.
