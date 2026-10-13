<!-- page: 1 -->
# Propositions and truth values
Illustrative practice notes created for the offline software demo. These are not official Waterloo slides.
A proposition is a statement assigned exactly one of two truth values, true (T) or false (F), in classical propositional logic. We use p and q for propositions.

<!-- page: 2 -->
# Negation, conjunction, and disjunction
Negation: not p, written ¬p, reverses the truth value of p.
Conjunction: p ∧ q is true exactly when both p and q are true.
Inclusive disjunction: p ∨ q is true when at least one of p or q is true, including when both are true.

<!-- page: 3 -->
# Truth tables
For two distinct variables p and q, enumerate (T,T), (T,F), (F,T), (F,F).
Example: construct the truth table of ¬(p ∧ q). First compute p ∧ q, then negate that result. The final column is F,T,T,T.

<!-- page: 4 -->
# Logical equivalence
Two formulas are logically equivalent if their truth values agree for every assignment of truth values to their variables. We write A ≡ B for equivalence of formulas A and B. Checking a single matching row does not establish equivalence.

<!-- page: 5 -->
# De Morgan's law
¬(p ∧ q) ≡ ¬p ∨ ¬q. To verify this equivalence, build both truth-table columns over the same four assignments. Each final column is F,T,T,T.

<!-- page: 6 -->
# Counterexamples
One assignment where formulas differ disproves equivalence.
Example: ¬(p ∧ q) is not equivalent to ¬p ∧ ¬q. At p=T and q=F, the first is true but the second is false.
