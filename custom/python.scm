(assignment
 left: (identifier) @variable.declaration)

((identifier) @variable.builtin
 (#any-of? @variable.builtin "self" "cls"))

[
 "and"
 "in"
 "is"
 "not"
 "or"
 "is not"
 "not in"
] @operator.keyword
