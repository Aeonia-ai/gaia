# 020 - MVP Migration: From Dictionaries to Classes

**Status:** Proposed
**Version:** 1.0
**Purpose:** This document describes the process of migrating the file-based MVP from a simple, dictionary-based approach to a more robust, class-based design.

## 1. The Two Approaches

For the initial implementation of the file-based MVP, there are two possible approaches:

*   **Dictionary-Based Approach:** This approach involves loading the JSON files from the KB directly into Python dictionaries and manipulating the dictionaries directly. This is a quick way to get a prototype up and running, but it can quickly become difficult to manage as the complexity of the system grows.
*   **Class-Based Approach:** This approach involves creating a set of Python classes that represent the core concepts of the simulation (e.g., `SimObject`, `PlayerState`). These classes are responsible for loading, managing, and saving the data from the KB. This approach is more structured, maintainable, and scalable.

While the dictionary-based approach might be tempting for a quick start, we strongly recommend migrating to the class-based approach as soon as possible.

## 2. Benefits of the Class-Based Approach

*   **Structure and Maintainability:** Classes provide a clear structure for the code, making it easier to understand, maintain, and extend.
*   **Encapsulation:** Classes encapsulate the logic for interacting with the data, which makes the code more robust and less prone to errors.
*   **Type Safety:** Classes allow for type hinting and static analysis, which can help to catch errors early in the development process.
*   **Future-Proofing:** A class-based design will make the future migration to a database much easier.

## 3. Step-by-Step Migration Guide

Here is a step-by-step guide for migrating from a dictionary-based approach to a class-based approach.

### Step 1: Define the Class Structure

The first step is to define the class structure in the `app/services/kb/simulation/` directory, as described in the `000-mvp-file-based-design.md` document.

### Step 2: Refactor the Data Loading Logic

The next step is to refactor the data loading logic to use the new classes.

**Before (Dictionary-Based):**

```python
def load_instance(instance_file):
    with open(instance_file, 'r') as f:
        return json.load(f)

instance_dict = load_instance('items/dream_bottle_1.json')
```

**After (Class-Based):**

```python
# in app/services/kb/simulation/instances.py
class ItemInstance(ObjectInstance):
    @classmethod
    def load(cls, instance_file, template):
        with open(instance_file, 'r') as f:
            data = json.load(f)
        return cls(data, template)

# in the application code
item_template = Gaia.Simulation.ItemTemplate.from_kb("wylding-woods/items/dream_bottle")
instance_obj = Gaia.Simulation.ItemInstance.load('items/dream_bottle_1.json', item_template)
```

### Step 3: Refactor the Business Logic

The final step is to refactor the business logic to use the new class methods instead of directly manipulating the dictionaries.

**Before (Dictionary-Based):**

```python
def collect_item(instance_dict, user_id):
    instance_dict['state']['collected_by'] = user_id
    # ... save the dictionary to the file ...
```

**After (Class-Based):**

```python
# in app/services/kb/simulation/instances.py
class ItemInstance(ObjectInstance):
    def collect(self, user_id):
        self.state['collected_by'] = user_id
        self.save()

# in the application code
instance_obj.collect(user_id)
```

By following these steps, you can smoothly migrate from a simple, dictionary-based prototype to a robust and maintainable class-based design.
