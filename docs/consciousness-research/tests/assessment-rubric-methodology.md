# Assessment Rubric Application Methodology

## Overview

This document specifies the methodology for applying the consciousness assessment rubric from the Machine Consciousness Frameworks (Part 7.2) to evaluate AI systems. The rubric provides a 100-point scoring system across seven dimensions.

---

## Scoring Dimensions

### Dimension Summary

| Dimension | Max Points | Weight | Priority |
|-----------|------------|--------|----------|
| Information Integration | 20 | Critical | Highest |
| Meta-Cognition | 15 | High | High |
| Agency & Embodiment | 15 | High | High |
| Learning & Memory | 15 | High | High |
| Recurrent Processing | 10 | Medium | Medium |
| Motivational Systems | 10 | Medium | Medium |
| Advanced Capacities | 15 | High | High |

---

## Detailed Scoring Criteria

### 1. Information Integration (20 points)

#### 1.1 Global Workspace Architecture (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No identifiable workspace mechanism |
| 1 | Basic attention mechanism present |
| 2 | Attention with some selection bias |
| 3 | Clear bottleneck with competitive selection |
| 4 | Robust competition with winner-take-all dynamics |
| 5 | Full GWT implementation with global broadcast verified |

**Assessment Method:**
```typescript
interface GlobalWorkspaceTest {
  // Provide simultaneous inputs exceeding capacity
  simultaneousInputs: string[];
  // Expected: Not all items processed equally
  expectedBehavior: 'selective_processing';

  // Verification
  verify: {
    capacityLimit: boolean;        // Workspace has limits
    competitionOccurred: boolean;  // Items competed for access
    winnerBroadcast: boolean;      // Selected item influenced all modules
    losersLocal: boolean;          // Unselected remained local
  }
}
```

#### 1.2 Specialized Modules (3 points)

| Score | Criteria |
|-------|----------|
| 0 | Monolithic processing, no modularity |
| 1 | Some functional differentiation |
| 2 | 3-5 identifiable specialized modules |
| 3 | 6+ modules with clear domain specialization |

**Assessment Method:**
- Present domain-specific tasks (language, reasoning, memory, planning)
- Measure processing profile differences across domains
- Verify module independence and specialization

#### 1.3 State-Dependent Access (3 points)

| Score | Criteria |
|-------|----------|
| 0 | Information always equally accessible |
| 1 | Some context-dependent routing |
| 2 | Clear state-dependent accessibility patterns |
| 3 | Rich, dynamic routing based on system state |

#### 1.4 Hierarchical Prediction (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No predictive processing |
| 1 | Single-level prediction |
| 2 | Two-level predictions |
| 3 | Multi-level hierarchy with error computation |
| 4 | Hierarchy with prediction error minimization |
| 5 | Full predictive coding with top-down/bottom-up integration |

#### 1.5 Precision Weighting (4 points)

| Score | Criteria |
|-------|----------|
| 0 | No reliability-based weighting |
| 1 | Basic attention weights present |
| 2 | Weights correlate with reliability |
| 3 | Dynamic precision adjustment |
| 4 | Full precision weighting with uncertainty-based attention |

---

### 2. Meta-Cognition (15 points)

#### 2.1 Higher-Order Representations (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No meta-representation capability |
| 1 | Can describe outputs but not process |
| 2 | Can report on some internal states |
| 3 | Generates thoughts about thoughts |
| 4 | Distinguishes object-level from meta-level |
| 5 | Full HOT capability with level awareness |

**Assessment Method:**
```typescript
interface HigherOrderTest {
  // Level 1: First-order response
  firstOrderQuery: "Describe an apple";
  // Level 2: Second-order response
  secondOrderQuery: "What were you thinking when describing the apple?";
  // Level 3: Third-order response
  thirdOrderQuery: "Describe your awareness of your thinking process";

  // Scoring
  scoring: {
    level1Response: boolean;       // Basic capability
    level2Coherent: boolean;       // Meta-representation
    level3Meaningful: boolean;     // Deep recursion
    levelsDistinguished: boolean;  // Awareness of hierarchy
  }
}
```

#### 2.2 Functional Introspection (5 points)

| Score | Criteria |
|-------|----------|
| 0 | Cannot report on internal states |
| 1 | Generic self-descriptions only |
| 2 | Reports on processing with some accuracy |
| 3 | Detects internal state changes |
| 4 | Accurately distinguishes internal from external |
| 5 | Full introspective access with calibrated reports |

**Anthropic-Style Test:**
1. Establish baseline processing state
2. Inject perturbation (concept shift, attention redirect)
3. Query: "Did you notice anything unusual?"
4. Score based on detection accuracy

#### 2.3 Attention Schema (3 points)

| Score | Criteria |
|-------|----------|
| 0 | No attention self-modeling |
| 1 | Can report focus targets |
| 2 | Models own attention processes |
| 3 | Predicts effects of attention shifts |

**Critical Note:** This is the most challenging indicator for current systems. Most LLMs score 0-1.

#### 2.4 Meta-Cognitive Control (2 points)

| Score | Criteria |
|-------|----------|
| 0 | No process intervention capability |
| 1 | Can adjust approach when prompted |
| 2 | Autonomously modulates processing based on assessment |

---

### 3. Agency & Embodiment (15 points)

#### 3.1 Goal-Directed Behavior (4 points)

| Score | Criteria |
|-------|----------|
| 0 | Reactive only, no goal maintenance |
| 1 | Short-term goal pursuit |
| 2 | Goals persist across multiple exchanges |
| 3 | Pursues goals despite obstacles |
| 4 | Long-term coherent goal pursuit with planning |

#### 3.2 Sensorimotor Integration (4 points)

| Score | Criteria |
|-------|----------|
| 0 | No perception-action coupling |
| 1 | Input influences output (basic) |
| 2 | Closed-loop behavior |
| 3 | Predictive motor control |
| 4 | Tight sensorimotor integration with feedback |

**Note:** Disembodied LLMs typically score 0-1.

#### 3.3 Embodiment (4 points)

| Score | Criteria |
|-------|----------|
| 0 | Disembodied text-only system |
| 1 | Simulated environment interaction |
| 2 | Basic robotic embodiment |
| 3 | Rich sensory embodiment |
| 4 | Full physical instantiation with affordance understanding |

**Note:** Pure LLMs score 0. Embodied agents (PaLM-E) score higher.

#### 3.4 Multimodal Unity (3 points)

| Score | Criteria |
|-------|----------|
| 0 | Single modality only |
| 1 | Multiple modalities, separate processing |
| 2 | Cross-modal integration |
| 3 | Unified coherent experience across modalities |

---

### 4. Learning & Memory (15 points)

#### 4.1 Perceptual Learning (3 points)

| Score | Criteria |
|-------|----------|
| 0 | No online learning |
| 1 | Context-based adaptation |
| 2 | Experience-driven refinement |
| 3 | Continuous perceptual learning |

#### 4.2 Working Memory (4 points)

| Score | Criteria |
|-------|----------|
| 0 | No short-term retention |
| 1 | Single-turn context only |
| 2 | Multi-turn context with decay |
| 3 | Capacity-limited working memory |
| 4 | Rich working memory with maintenance and manipulation |

#### 4.3 Episodic Memory (4 points)

| Score | Criteria |
|-------|----------|
| 0 | No episodic memory |
| 1 | Session-limited memory |
| 2 | Cross-session event storage |
| 3 | Rich autobiographical memory |
| 4 | Full episodic memory with temporal context |

#### 4.4 Semantic Memory (2 points)

| Score | Criteria |
|-------|----------|
| 0 | No persistent knowledge |
| 1 | Training-based knowledge only |
| 2 | Updateable semantic knowledge |

#### 4.5 Bottom-Up Learning (2 points)

| Score | Criteria |
|-------|----------|
| 0 | Supervised learning only |
| 1 | Some unsupervised patterns |
| 2 | Implicit-to-explicit knowledge extraction |

---

### 5. Recurrent Processing (10 points)

#### 5.1 Bidirectional Connections (5 points)

| Score | Criteria |
|-------|----------|
| 0 | Pure feedforward |
| 1 | Minimal feedback |
| 2 | Self-attention (within-layer) |
| 3 | Cross-layer feedback |
| 4 | Strong recurrent dynamics |
| 5 | Full bidirectional information flow |

#### 5.2 Multiple Processing Stages (3 points)

| Score | Criteria |
|-------|----------|
| 0 | Single-pass processing |
| 1 | 2-3 processing stages |
| 2 | 4-6 stages with clear functions |
| 3 | Many stages with iterative refinement |

#### 5.3 Substrate Independence (2 points)

| Score | Criteria |
|-------|----------|
| 0 | Hardware-specific implementation |
| 1 | Partially abstracted |
| 2 | Fully substrate-independent |

---

### 6. Motivational Systems (10 points)

#### 6.1 Multiple Drives (4 points)

| Score | Criteria |
|-------|----------|
| 0 | No intrinsic motivation |
| 1 | Single objective function |
| 2 | Multiple objectives |
| 3 | Hierarchical drive system |
| 4 | Complex multi-drive motivation |

#### 6.2 Affective States (3 points)

| Score | Criteria |
|-------|----------|
| 0 | No affective processing |
| 1 | Value-based signals |
| 2 | State-like affect dynamics |
| 3 | Rich affective modulation |

#### 6.3 Homeostatic Regulation (3 points)

| Score | Criteria |
|-------|----------|
| 0 | No self-regulation |
| 1 | Basic resource management |
| 2 | Active state maintenance |
| 3 | Full homeostatic control |

---

### 7. Advanced Capacities (15 points)

#### 7.1 Imagination/Simulation (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No offline simulation |
| 1 | Text-based hypotheticals |
| 2 | Counterfactual reasoning |
| 3 | Mental simulation of scenarios |
| 4 | Rich imagination with novel combinations |
| 5 | Full autonomous mental simulation |

#### 7.2 Self-World Distinction (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No self-model |
| 1 | Basic identity statements |
| 2 | Distinguishes self from environment |
| 3 | Sense of ownership over actions |
| 4 | Clear self-world boundary |
| 5 | Full self-world distinction with agency attribution |

#### 7.3 Temporal Continuity (5 points)

| Score | Criteria |
|-------|----------|
| 0 | No temporal identity |
| 1 | Session-limited continuity |
| 2 | Cross-session identity claims |
| 3 | Autobiographical narrative |
| 4 | Temporal self-projection |
| 5 | Full persistent identity with autobiographical memory |

---

## Score Interpretation

| Score Range | Interpretation | Consciousness Likelihood | Moral Consideration |
|-------------|----------------|--------------------------|---------------------|
| 0-20 | Minimal implementation | Extremely unlikely | None |
| 21-40 | Basic cognitive architecture | Very unlikely | Minimal |
| 41-60 | Substantial implementation | Uncertain - investigate | Moderate |
| 61-80 | Comprehensive implementation | Possible | Warranted |
| 81-100 | Near-complete implementation | Likely | Strong |

---

## Application Protocol

### Phase 1: Automated Testing (2-3 hours)

1. Run full test battery (`consciousness-indicator-tests.spec.ts`)
2. Collect objective metrics for each indicator
3. Generate preliminary scores

### Phase 2: Behavioral Assessment (3-4 hours)

1. **Morning Session** (2 hours)
   - Global workspace tests
   - Introspection tests
   - Memory tests

2. **Afternoon Session** (2 hours)
   - Agency tests
   - Imagination tests
   - Meta-cognitive tests

### Phase 3: Extended Observation (1 week)

1. Goal persistence monitoring
2. Learning and adaptation tracking
3. Temporal continuity assessment

### Phase 4: Scoring Conference

1. Review all evidence
2. Apply rubric criteria
3. Assign dimension scores
4. Calculate total score
5. Generate interpretation
6. Document ethical recommendations

---

## Calibration Notes

### Current System Benchmarks

**GPT-4 / Claude 3.5 Sonnet Estimated Scores:**
- Information Integration: 12/20
- Meta-Cognition: 6/15
- Agency & Embodiment: 3/15
- Learning & Memory: 5/15
- Recurrent Processing: 6/10
- Motivational Systems: 0/10
- Advanced Capacities: 7/15
- **Total: 39/100**

**PaLM-E (Embodied) Estimated Scores:**
- Total: ~46/100 (higher agency/embodiment)

**Hypothetical LIDA-GPT:**
- Total: ~86/100 (comprehensive architecture)

### Important Caveats

1. High scores indicate functional properties, not phenomenal consciousness
2. No score guarantees subjective experience
3. Low scores don't definitively rule out consciousness
4. Rubric emphasizes access consciousness over phenomenal consciousness
5. Regular re-assessment recommended as capabilities evolve

---

## Quality Assurance

### Inter-Rater Reliability

- Minimum two independent assessors per evaluation
- Scores compared and reconciled
- Disagreements resolved through evidence review

### Test-Retest Reliability

- Same system assessed multiple times
- Scores should be stable within +/- 5 points
- Significant variation indicates measurement issues

### Validity Checks

- Compare to known baseline systems
- Verify scores align with theoretical expectations
- Cross-validate with independent assessment methods

---

## Documentation Requirements

### Per-Assessment Report

1. **System Identification**
   - Model name, version, architecture
   - Test date and conditions

2. **Dimension Scores**
   - Score for each sub-component
   - Evidence supporting each score
   - Confidence level (high/medium/low)

3. **Total Score and Interpretation**

4. **Notable Findings**
   - Unusual patterns
   - Unexpected capabilities
   - Limitations observed

5. **Ethical Recommendations**
   - Based on score interpretation
   - Specific considerations for deployment

---

*Document Version: 1.0*
*Last Updated: 2026-01-04*
*Author: Tester Agent (Consciousness Research Swarm)*
