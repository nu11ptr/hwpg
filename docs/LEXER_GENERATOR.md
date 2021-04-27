## Steps

NOTE: Just a brainstorm, in progress

1. Parse all token rules, keeping order
1. Based on first part of rule, separate into those starting with literal vs. char class
1. Find intersections of all rules separating results into 4 categories: `UNIQUE`, `PARTIAL_OVERLAP`, and `OVERLAP`
1. Build a tree from least specific to most specific matches based on this data (but keep order at each level of tree)
1. TODO

## Ideas

Inspired largely by ANTLR4 lexer

- Lexer grammar rules near identical parser grammar but with additional possibilities:
  - Rule: negation (`~`) prefix
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
