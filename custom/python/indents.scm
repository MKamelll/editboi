; --- Immediate indent: line after these gets +1 level ---
[
  (if_statement)
  (for_statement)
  (while_statement)
  (try_statement)
  (function_definition)
  (class_definition)
  (with_statement)
  (match_statement)
  (case_clause)
] @indent.begin

; --- Bracket/paren alignment (hanging indent under an opening delimiter) ---
(argument_list) @indent.align
(parameters) @indent.align
(list) @indent.align
(dictionary) @indent.align
(set) @indent.align
(tuple) @indent.align
(parenthesized_expression) @indent.align

; --- Comprehensions/generators also open an indent scope ---
[
  (list_comprehension)
  (set_comprehension)
  (dictionary_comprehension)
  (generator_expression)
] @indent.begin

; --- Dedent-only statements ---
[
  (break_statement)
  (continue_statement)
  (return_statement)
  (raise_statement)
  (pass_statement)
] @indent.dedent_next

; --- Branch keywords: dedent this line to match its opener ---
[
 (elif_clause)
 (else_clause)
 (except_clause)
 (finally_clause)
 ] @indent.branch

(ERROR
  (identifier) @indent.error_branch
  ":")
