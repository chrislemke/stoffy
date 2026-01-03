# Argument Patterns Reference

## Deductive Argument Forms

### Valid Forms

#### Categorical Syllogisms

**Barbara (AAA-1)**:
```
P1: All M are P
P2: All S are M
--------------
C: All S are P
```
Example: All mammals are animals. All dogs are mammals. Therefore, all dogs are animals.

**Celarent (EAE-1)**:
```
P1: No M are P
P2: All S are M
--------------
C: No S are P
```

**Darii (AII-1)**:
```
P1: All M are P
P2: Some S are M
--------------
C: Some S are P
```

**Ferio (EIO-1)**:
```
P1: No M are P
P2: Some S are M
--------------
C: Some S are not P
```

#### Propositional Logic Forms

**Modus Ponens (Affirming the Antecedent)**:
```
P1: If A, then B
P2: A
--------------
C: B
```
Valid. The foundation of much reasoning.

**Modus Tollens (Denying the Consequent)**:
```
P1: If A, then B
P2: Not B
--------------
C: Not A
```
Valid. Used in falsification.

**Hypothetical Syllogism (Chain Argument)**:
```
P1: If A, then B
P2: If B, then C
--------------
C: If A, then C
```
Valid. Builds chains of implication.

**Disjunctive Syllogism**:
```
P1: A or B
P2: Not A
--------------
C: B
```
Valid. Eliminates alternatives.

**Constructive Dilemma**:
```
P1: If A, then B
P2: If C, then D
P3: A or C
--------------
C: B or D
```

**Destructive Dilemma**:
```
P1: If A, then B
P2: If C, then D
P3: Not B or not D
--------------
C: Not A or not C
```

**Reductio ad Absurdum**:
```
P1: Assume A for contradiction
P2: A implies B
P3: A implies not-B
--------------
C: Not A
```
Valid. Proof by contradiction.

**Contraposition**:
```
P1: If A, then B
--------------
C: If not B, then not A
```
Valid equivalence.

### Invalid Forms (Fallacies)

**Affirming the Consequent**:
```
P1: If A, then B
P2: B
--------------
C: A          ← INVALID
```
Example: If it's raining, the ground is wet. The ground is wet. Therefore, it's raining. (Could be sprinklers!)

**Denying the Antecedent**:
```
P1: If A, then B
P2: Not A
--------------
C: Not B      ← INVALID
```
Example: If I'm in Paris, I'm in France. I'm not in Paris. Therefore, I'm not in France. (Could be in Lyon!)

**Undistributed Middle**:
```
P1: All A are B
P2: All C are B
--------------
C: All A are C  ← INVALID
```
Example: All dogs are animals. All cats are animals. Therefore, all dogs are cats.

**Illicit Major**:
```
P1: All M are P
P2: No S are M
--------------
C: No S are P   ← INVALID
```

---

## Inductive Argument Patterns

### Generalization

**Simple Induction**:
```
P1: Object a₁ has property F
P2: Object a₂ has property F
...
Pn: Object aₙ has property F
--------------
C: (Probably) All objects of type A have property F
```

**Strength factors**:
- Sample size
- Sample diversity
- No counterexamples observed

### Statistical Syllogism

```
P1: X% of A are B
P2: c is an A
--------------
C: (Probably) c is B (with probability ~X%)
```

**Strength factors**:
- Percentage (higher = stronger)
- Reference class appropriateness
- No relevant defeating information

### Argument from Analogy

```
P1: A has features f₁, f₂, f₃, f₄
P2: B has features f₁, f₂, f₃
P3: A has property P
--------------
C: (Probably) B has property P
```

**Strength factors**:
- Number of shared features
- Relevance of shared features to P
- Absence of relevant dissimilarities
- Diversity of analogous cases

### Inference to Best Explanation (IBE / Abduction)

```
P1: Surprising observation O occurred
P2: If hypothesis H were true, O would be expected
P3: H is the best available explanation of O
--------------
C: (Probably) H is true
```

**Criteria for "best"**:
- Explanatory power (explains more)
- Simplicity (fewer assumptions)
- Coherence (fits with other beliefs)
- Fruitfulness (generates predictions)
- Lack of ad hocness

### Causal Reasoning

**Method of Agreement**:
```
P1: In case 1, antecedent A and effect E occurred
P2: In case 2, antecedent A and effect E occurred
P3: Cases 1 and 2 differ in all other relevant respects
--------------
C: A causes E
```

**Method of Difference**:
```
P1: In case 1, A present, E occurred
P2: In case 2, A absent, E did not occur
P3: Cases 1 and 2 are otherwise identical
--------------
C: A causes E
```

**Concomitant Variation**:
```
P1: When A increases, E increases
P2: When A decreases, E decreases
--------------
C: A and E are causally related
```

---

## Philosophical Argument Patterns

### Conceptual Analysis Arguments

**Counterexample to Analysis**:
```
P1: Analysis claims: X is Y iff conditions C
P2: Case K satisfies C but is not Y (or: is Y but doesn't satisfy C)
--------------
C: Analysis is incorrect
```
Example: Gettier cases against JTB analysis of knowledge.

**Necessary Condition Argument**:
```
P1: If X is Y, then X has property P
P2: X lacks property P
--------------
C: X is not Y
```

**Sufficient Condition Argument**:
```
P1: If X has property P, then X is Y
P2: X has property P
--------------
C: X is Y
```

### Modal Arguments

**Possibility Argument**:
```
P1: It is conceivable that P
P2: What is conceivable is possible
--------------
C: It is possible that P
```

**Necessity from Possibility**:
```
P1: If P is possible, P is necessary (for the relevant modal domain)
P2: P is possible
--------------
C: P is necessary
```

**Zombie Argument (Chalmers)**:
```
P1: Zombies are conceivable
P2: If zombies are conceivable, they are metaphysically possible
P3: If zombies are possible, physicalism is false
--------------
C: Physicalism is false
```

### Transcendental Arguments

```
P1: Experience E occurs
P2: E is possible only if condition C obtains
--------------
C: Condition C obtains
```
Example: Kant's argument that causality is necessary for coherent experience.

### Regress Arguments

**Infinite Regress (showing impossibility)**:
```
P1: X requires Y
P2: Y requires Y' (of the same type)
P3: Y' requires Y'' (and so on infinitely)
P4: An infinite regress of type Y is impossible
--------------
C: X is impossible (or requires a different foundation)
```

**Foundationalism from Regress**:
```
P1: All justified beliefs require justification
P2: Justification cannot be circular
P3: Justification cannot regress infinitely
--------------
C: Some beliefs must be self-justifying (foundational)
```

### Epistemic Arguments

**Closure Argument for Skepticism**:
```
P1: If S knows P, and S knows P→Q, then S knows Q (closure)
P2: S doesn't know she's not a BIV (not-Q)
P3: S knows: if P, then not-BIV (P→Q)
--------------
C: S doesn't know P
```

**Moorean Shift**:
```
P1: I know I have hands (P)
P2: If I have hands, I'm not a BIV (P→Q)
--------------
C: I know I'm not a BIV (by closure)
```

### Ethical Arguments

**Universalizability Test**:
```
P1: Action A involves maxim M
P2: M cannot be universalized without contradiction
--------------
C: Action A is morally impermissible
```

**Singer's Expanding Circle**:
```
P1: Property P grounds moral status
P2: Beings A and B both have P
P3: Treating A differently from B requires morally relevant difference
--------------
C: We should treat A and B equally (in relevant respects)
```

**Argument from Queerness (Mackie)**:
```
P1: If moral facts existed, they would be metaphysically queer
P2: If moral facts existed, knowing them would be epistemically queer
P3: We should not posit queer entities
--------------
C: Moral facts don't exist
```

---

## Dialectical Patterns

### Objection and Reply Structure

```
CLAIM: P
│
├─── OBJECTION 1: ~P because Q
│    │
│    └─── REPLY: Q doesn't establish ~P because R
│         │
│         └─── COUNTER-REPLY: But R fails because S
│
├─── OBJECTION 2: ~P because T
│    │
│    └─── REPLY: T is false because U
│
└─── (Position survives if replies succeed)
```

### Dilemma Structure

```
DILEMMA: Either A or B
│
├─── HORN 1: If A, then bad consequence C
│
└─── HORN 2: If B, then bad consequence D

ESCAPE ROUTES:
1. Reject dilemma (show third option)
2. Go between horns (neither A nor B, but something else)
3. Grasp a horn (accept one consequence)
```

### Socratic Elenchus Pattern

```
1. INTERLOCUTOR claims P
2. SOCRATES elicits additional commitments Q, R, S
3. SOCRATES shows: Q, R, S → ~P
4. INTERLOCUTOR must give up P, Q, R, or S
5. APORIA: Puzzlement about which to abandon
```

### Hegelian Dialectic

```
THESIS: P (initial position)
    │
    ▼
ANTITHESIS: ~P (opposing position)
    │
    ▼
SYNTHESIS: P' (higher unity preserving truth of both)
    │
    ▼
[New THESIS: P' ...]
```

---

## Argument Strength Assessment

### For Deductive Arguments

| Question | Strong | Weak |
|----------|--------|------|
| Valid form? | Yes | No |
| Premises true? | All true | One+ false/unknown |
| Hidden premises? | None or trivial | Substantial unstated |
| Begs question? | No | Yes |

### For Inductive Arguments

| Question | Strong | Weak |
|----------|--------|------|
| Sample size? | Large | Small |
| Sample representative? | Yes | No |
| Relevant variables controlled? | Yes | No |
| Alternative explanations? | Ruled out | Not addressed |

### For Philosophical Arguments

| Question | Strong | Weak |
|----------|--------|------|
| Survives counterexamples? | Yes | No |
| Intuitions tracked correctly? | Yes | No |
| Consistent with other commitments? | Yes | No |
| Fruitful implications? | Yes | No |
