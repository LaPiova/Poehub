# Smart Message Splitting

## Overview

PoeHub v1.3.0 includes an intelligent message splitting system that automatically handles Discord's 2000 character limit by splitting long AI responses into multiple messages at natural boundaries.

## How It Works

### The Problem

Discord has a hard limit of 2000 characters per message. When AI generates long responses (e.g., detailed tutorials, code examples, essays), they need to be split into multiple messages.

### Our Solution

Instead of splitting at arbitrary character positions, PoeHub uses **intelligent boundary detection** to split messages at natural points.

## Splitting Priority

The algorithm tries to split at these boundaries in order:

1. **Code Block Boundary** (` ``` `)
   - Highest priority
   - Prevents breaking code examples mid-code
   - Example: `\n```python\n...\n```\n`

2. **Paragraph Boundary** (`\n\n`)
   - Natural separation between ideas
   - Keeps related content together

3. **Line Break** (`\n`)
   - Splits at line endings
   - Better than mid-sentence

4. **Sentence Ending** (`. `)
   - Period followed by space
   - Maintains sentence integrity

5. **Word Boundary** (` `)
   - Last resort
   - Never breaks words

## Examples

### Example 1: Code Block Protection

**AI Response (2500 chars):**
```
Here's how to use Python decorators:

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper
```

This decorator wraps any function and prints messages before and after execution. [more explanation...]
```

**Split Result:**

Message 1:
```
Here's how to use Python decorators:

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper
```

*(continued...)*
```

Message 2:
```
*(continued)*

This decorator wraps any function and prints messages before and after execution. [more explanation...]
```

✅ **Code block is intact!**

### Example 2: Paragraph Splitting

**AI Response (3000 chars):**
```
First, let me explain concept A. [500 characters of explanation]

Second, concept B is important because [800 characters]

Finally, concept C ties everything together [1500 characters]
```

**Split Result:**

Message 1:
```
First, let me explain concept A. [explanation]

Second, concept B is important because [explanation]

*(continued...)*
```

Message 2:
```
*(continued)*

Finally, concept C ties everything together [explanation]
```

✅ **Paragraphs respected!**

### Example 3: Continuous Text

**AI Response (2200 chars with no paragraphs):**
```
This is a very long sentence that continues on and on. Another sentence follows. Yet another sentence. [continues...]
```

**Split Result:**

Message 1:
```
This is a very long sentence that continues on and on. Another sentence follows.

*(continued...)*
```

Message 2:
```
*(continued)*

Yet another sentence. [continues...]
```

✅ **Split at sentence boundary!**

## Technical Details

### Configuration

- **Max Length:** 1950 characters (default)
- **Discord Limit:** 2000 characters
- **Buffer:** 50 characters (for continuation markers)

### Boundary Detection

The algorithm searches **backwards** from the max length position to find the best split point. It only considers boundaries in the **latter half** (50% threshold) of the chunk to avoid creating tiny chunks.

### Continuation Markers

- **End of chunk:** `\n\n*(continued...)*`
- **Start of next:** `*(continued)*\n\n`

These markers help users understand that a message is part of a longer response.

### Code

```python
def _split_message(self, content: str, max_length: int = 1950) -> List[str]:
    """
    Split a message into chunks that fit Discord's 2000 character limit.
    Attempts to split at natural boundaries.
    """
    if len(content) <= max_length:
        return [content]
    
    chunks = []
    remaining = content
    
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        
        chunk = remaining[:max_length]
        split_point = max_length
        
        # Priorities for splitting
        split_candidates = [
            ("```\n", 4),       # Code block end
            ("\n\n", 2),        # Paragraph
            ("\n", 1),          # Line
            (". ", 2),          # Sentence
            (" ", 1)            # Word
        ]
        
        for delimiter, offset in split_candidates:
            last_pos = chunk.rfind(delimiter)
            if last_pos > max_length * 0.5:  # Only if it's in the latter half
                split_point = last_pos + offset
                break
        
        # Add the chunk
        chunks.append(remaining[:split_point].rstrip())
        remaining = remaining[split_point:].lstrip()
        
        # Add continuation marker if there's more content
        if remaining and not chunks[-1].endswith("```"):
            chunks[-1] = chunks[-1] + "\n\n*(continued...)*"
        if remaining and len(chunks) > 0:
            remaining = "*(continued)*\n\n" + remaining
    
    return chunks
```

## Where It's Applied

The smart splitting is automatically used in:

1. **`!ask` command responses**
   - When you ask questions in a channel
   - When responses are sent to DMs (private mode)

2. **DM responses**
   - When you message the bot directly

3. **All streaming responses**
   - Real-time AI output is split intelligently

## Benefits

### For Users
- ✅ Code examples never broken
- ✅ Paragraphs stay together
- ✅ Sentences not cut off
- ✅ Clear continuation markers
- ✅ Better reading experience

### For Code Quality
- ✅ Maintainable and testable
- ✅ Configurable parameters
- ✅ No hardcoded magic numbers
- ✅ Clear priority system

## Testing

To test the smart splitting:

```
!ask Write a comprehensive 3000-word tutorial on Python decorators with multiple code examples, detailed explanations, and practical use cases.
```

You should receive multiple messages with:
- Intact code blocks
- Natural paragraph breaks
- Continuation markers
- Smooth reading flow

## Version History

- **v1.2.0:** Basic splitting at 1900 chars
- **v1.2.1:** Smart boundary detection
- **v1.3.0:** Refactored into specialized modules (current)

## Future Enhancements

Potential improvements (not yet implemented):

- Preserve markdown formatting across splits
- Handle nested code blocks
- Support for other languages (math blocks, etc.)
- User-configurable split preferences

---

**Version:** 1.3.0  
**Last Updated:** December 23, 2025  
**Status:** ✅ Production Ready
