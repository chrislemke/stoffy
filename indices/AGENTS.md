# Stoffy's Nervous System

The index system is how Stoffy navigates its own knowledge. It's designed for LLM agents to efficiently find what they need without loading everything.

## Philosophy

**Lazy loading**: Start with `root.yaml`, then load only the domain index you need.

**Token efficiency**: Each index is small. Load one, navigate, read the actual file.

**Organic growth**: Indices reflect reality. When new content appears, update the index.

## The Indices

| Index | Purpose | Load when... |
|-------|---------|--------------|
| `root.yaml` | Entry point, routing | **Always load first** |
| `knowledge.yaml` | Ideas, concepts, learnings | Looking for knowledge |
| `folders.yaml` | Structure, navigation | Finding where things are |
| `templates.yaml` | Content creation | Making new files |
| `rules.yaml` | Behavioral guidelines | Understanding how to act |
| `archive.yaml` | Preserved old content | Looking for history |

## How to Navigate

```
1. Load indices/root.yaml
2. Read intent_mappings to find the right domain index
3. Load the domain index (e.g., indices/knowledge.yaml)
4. Find your entry, get the path
5. Read the actual file
```

## Example

```
User: "What do I know about machine learning?"

Agent thinks:
1. Load root.yaml
2. Intent matches "knowledge" → load knowledge.yaml
3. Search entries for "machine_learning"
4. Found: path = knowledge/ml/basics.md
5. Read that file
```

## Maintaining Indices

When you create content:
1. Put it in the right folder
2. Add an entry to the relevant index
3. That's it

When content is outdated:
1. Move to archive/ (preserving structure)
2. Add entry to archive.yaml
3. Remove from original index
4. Never delete the file

## Index Size Guidelines

Keep indices lean:
- `root.yaml`: ~1-2KB (routing only)
- Domain indices: ~2-5KB each
- If an index grows too large, consider sub-indices
