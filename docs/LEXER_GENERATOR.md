## Steps

NOTE: Just a brainstorm, in progress (many details still need to be worked out)

NOTE 2: One limitation of this method is that it is assumed there are no overlaps in the first part of the rule for those that start with a char class range. Since designed for programming languages, these rules are assumed to be for things like identifiers and thus get there own function. Due to this and lack of backtracking, there is now way to tokenize different tokens starting with the same char class range. This is not an issue for rules starting with a string literal or individual chars in a class as these are typically tokenized as part of a single large switch/if block.

1. Parse all token rules, keeping their order
1. Based on first part of rule, separate by those starting with a string literal and individual chars in a class (set 1) vs. those with a char class range (set 2)
   1. This is done for each `mode` independently
1. Find all entries in set 1 (literals and char sets) and try to see how many of them would match the set 2 char class ranges (ie. `"skip"` would match `[a-z]*`)
   1. For each that does, it is flagged a keyword and separated into a third set
1. Take all the entries in set 1 and build a tree such that any partially conflicting entries (longer literals) are are a child of the shorter literals (ie. `>=` is a child of `>`)
1. Generate the lexer as such:
   1. Generate an enum value for each token and name per the grammar
   1. Generate a map of keywords to tokens
   1. Create a new function per rule in set 2
      1. If the rule can match keywords, substitute keyword token from map if found
   1. Create a new function for each `mode` (not including the default)
      1. It will mimic the main `NextToken` function we will create for default
   1. Create `NextToken` function with these sections in this order:
      1. Process all `mode` functions (if in that mode)
      1. Enter skip loop for all skipped tokens
         1. Generate a switch/if block for all tokens (TODO: What if char class ranges?)
      1. Process any functions for tokens in set 2
      1. Generate primary if/switch block
         1. Create entries for all set 1 entries

## Ideas

Inspired largely by ANTLR4 lexer

- Lexer grammar rules near identical parser grammar but with additional possibilities:
  - Rule: negation (`~`) prefix
    - TODO: Illegal in first position?
  - Rule: `->` = action
  - Rule: `.` = any char
  - Rule `[a-z0-9_]` = character class
  - Top Level: `mode` keyword
- Fragments based on leading underscore (ie. \_DIGIT)
- One or more actions following `->` at end of rule:

  - `skip` = skip this token an move on to next
  - `empty` = don't capture data, just the token itself

- Possible future actions:
  - `capture(<group_num>)` = capture partial data based on numbering of innner groups (`(` and `)`)
  - `push_mode(<mode_name>)` = switch lexer mode
  - `pop_mode` = switch back to previous lexer mode
  - `channel(<channel_name>)` = send token to alternate channel (FUTURE)
    - Allow channels to be optionally be turned off (equiv of `skip`) at runtime
    - Allow access lexer channels during AST generation (so we can do things like keep comments on AST nodes)
      `replace(<TOKEN_NAME>)`, `append(<TOKEN_NAME>)`, `prepend(<TOKEN_NAME>)` = replace, append, or prepend respectively the given token
