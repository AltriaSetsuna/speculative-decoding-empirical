import sys
import types
import unittest

sys.modules.setdefault("litellm", types.SimpleNamespace(completion=lambda *args, **kwargs: None))

from run_humaneval import normalize_completion


class NormalizeCompletionTest(unittest.TestCase):
    def test_markdown_function_body_continuation(self):
        completion = """Here is the solution:

```python
from typing import List

def filter_by_substring(strings: List[str], substring: str) -> List[str]:
    \"\"\"Repeated prompt docstring.\"\"\"
    return [s for s in strings if substring in s]
```
"""

        self.assertEqual(
            normalize_completion(completion, "filter_by_substring"),
            (
                "    from typing import List\n"
                "    return [s for s in strings if substring in s]\n"
            ),
        )


    def test_plain_body_is_unchanged(self):
        completion = "    return number - int(number)\n"

        self.assertEqual(normalize_completion(completion, "truncate_number"), completion)


if __name__ == "__main__":
    unittest.main()
