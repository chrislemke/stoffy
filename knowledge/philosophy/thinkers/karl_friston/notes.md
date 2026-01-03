---
thinker: "Karl J. Friston"
tags:
  - thinker
  - notes
---

# Notes on Karl J. Friston

Use this file to capture ongoing notes, insights, and reflections related to Friston's work and ideas.

## Reading Notes

### 2025-12-26 - Active Inference Book

**Key Insight**: The perception-action loop is not two separate processes but ONE process of active inference. To perceive IS to act (internally—updating beliefs), and to act IS to perceive (changing what you see). This dissolves the traditional perception/action boundary.

**Questions Raised**:
- Can the FEP explain consciousness, or just behavior? Where does qualia fit?
- Are Markov blankets observer-dependent (how we describe systems) or ontologically fundamental (real boundaries)?
- How do generative models arise in the first place? Is there a meta-FEP for model creation?
- What about organisms that seem to seek novelty, not minimize surprise? (Answer: epistemic value in expected free energy)

**Connection to My Thinking**:
- Edge-dynamics in Existentielle Potenzialität could be reframed as modes of free energy minimization
- An edge thickens when interaction reduces mutual surprise; dissolves when prediction error is unmanageable
- Markov blankets = nodes in graph ontology

---

### 2025-12-26 - The Mathematics

**Free Energy Decomposition**:
F = E_q[-log p(o,s)] - H[q(s)]
  = Energy (expected inaccuracy) - Entropy (expected uncertainty)

**Key Equations (Simplified)**:
1. Free Energy bound: F ≥ -log P(o) (surprisal)
2. Perception: argmin_q F (update beliefs about hidden states)
3. Action: argmin_a F (change observations to match predictions)

**Expected Free Energy** (for planning):
G = -E_q[log p(o|π)] - E_q[log p(s|o,π) - log q(s|π)]
  = Pragmatic value + Epistemic value

The epistemic value term explains curiosity—we're driven to reduce uncertainty, not just achieve goals.

---

### 2025-12-26 - Philosophical Implications

**Self as Markov Blanket**:
- This provides a formal, non-essentialist definition of identity
- A self is not a substance but a statistical boundary
- Selves can be nested (cells within organs within organisms within societies)

**Existence as Prediction**:
- To exist is to accurately predict one's sensory states
- Organisms are fundamentally models of their environment
- Death = failure of the model; complete surprise

**Determinism?**:
- If all behavior is free energy minimization, is there room for genuine choice?
- Active inference seems to support a sophisticated determinism
- But: The model parameters determine behavior, and these evolved/learned—is that freedom?

---

## Reflections

### 2025-12-26 - The Mathematical Elegance

Friston's framework is seductive in its elegance. One equation (minimize F) explains:
- Perception (update beliefs)
- Action (change world)
- Learning (update models)
- Attention (precision weighting)
- Development (model elaboration)
- Evolution (selection for good models)

This kind of unification is rare in science. It reminds me of how Maxwell unified electricity and magnetism, or how Darwin unified all biology.

### 2025-12-26 - Tension with Chater

The apparent tension between Friston and Chater is the most pressing issue for my project:

| Friston | Chater |
|---------|--------|
| Hierarchical generative models | No mental depths |
| Stable model parameters | Improvised beliefs |
| Prediction over time | Moment-to-moment construction |
| Hidden states | Surface is all there is |

**Possible resolution 1**: Different levels of description. Friston describes the computational mechanism; Chater describes the phenomenology. The brain has models (Friston), but we don't have introspective access to them (Chater).

**Possible resolution 2**: Models are themselves improvised. The "generative model" is not stored in fixed form but reconstructed each time it's deployed.

**Possible resolution 3**: "Depth" means different things. Friston's depth is computational hierarchy; Chater's depth is hidden mental contents (beliefs, desires). These might be independent.

This deserves a dedicated thought exploration.

---

### 2025-12-30 - Recent Developments (2024-2025)

**IAI TV Interview (2025)**: Friston described as "the world's most influential and highly cited neuroscientist." Explains how FEP unifies physics and psychology, explains agency and dreaming, and promises new ways to understand mental illness. Will appear at HowTheLightGetsIn London 2025 alongside Roger Penrose, Sabine Hossenfelder, John Gray.

**Psychology Today Interview (Feb 2025)**: Discussion of AI with genuine agency through active inference. Key quote: The generative model in active inference includes the consequences of action, which "endows AI with a minimal but authentic agency; in the sense agents can entertain counterfactual futures and select among them to act optimally."

**The Dissenter Podcast #1000 (Sept 2024)**: Comprehensive 3-hour discussion from physics to mind. Covers Markov blankets, internal and external states, blanket states, circular causality, and autonomous states. The 1000th episode milestone reflects Friston's significance.

**Cybernetics Society Talk (April 2024)**: "The Physics of Sentience" - addressed how we understand ourselves as sentient creatures and the principles that underwrite sentient behavior.

**Love and Philosophy Podcast (Dec 2024)**: Explored the concept of 'flow' and making right choices in a constantly changing world. Discussed how active inference provides a first-principles account of sentient behavior.

**Key Emerging Theme**: Friston increasingly frames FEP not just as neuroscience but as a bridge from physics to psychology—a formal account of sentience itself. The move from "brain theory" to "theory of sentient systems" is significant.

**Connection to My Project**: This expansion supports my thesis that FEP provides the formal apparatus for understanding existence itself, not just cognition. If FEP describes sentience, and sentience is a form of existence, then FEP may be the mathematics of being.

---

### 2025-12-30 - On the Notorious Difficulty

From Scott Alexander's "God Help Us, Let's Try To Understand Friston On Free Energy":
- At Columbia's psychiatry department, 15 researchers with PhDs in physics, statistics, and neuroscience spent 90 minutes on Friston's 2010 paper and failed to understand it
- There's an "entire not-understanding-Karl-Friston internet fandom" complete with parody Twitter accounts and Markov blanket memes
- Even friendly interpreters like Scott admit the writing is exceptionally opaque

**My Take**: This difficulty is both genuine and somewhat overstated. The mathematical formalism IS complex—variational Bayesian methods, random field theory, Lagrangian mechanics. But the core intuitions are surprisingly accessible:
1. Living things must predict their environment to survive
2. Prediction error drives both perception (update beliefs) and action (change world)
3. What counts as "you" is defined by what you can influence and sense

The gap between these intuitions and the mathematics is where the difficulty lies. Friston's contribution is formalizing what might otherwise remain vague phenomenology.

---

### 2025-12-30 - COVID-19 Modeling Digression

In 2020, Friston applied DCM to epidemiological modeling during the COVID-19 pandemic:
- Joined Independent SAGE (alternative to government SAGE)
- Applied systems biology approach to virus transmission dynamics
- Controversial: some epidemiologists criticized application of neuroimaging methods to public health

**Relevance**: Shows FEP/DCM as a general framework for any system with hidden states and observable outputs—not limited to brains. This supports the claim that FEP is a theory of "every thing" that persists as an identifiable entity.
