# Consciousness Test Battery

Comprehensive testing framework for evaluating consciousness-related properties in AI systems based on the 14 indicators from The Consciousness Report (2023) and the assessment rubric from the Machine Consciousness Frameworks document.

## Test Files

| File | Purpose |
|------|---------|
| `consciousness-indicator-tests.spec.ts` | Full test suite with 150+ test cases for all 14 indicators |
| `assessment-rubric-methodology.md` | Detailed scoring criteria and application protocol |
| `automated-testing-approach.md` | CI/CD integration and automation infrastructure |

## Quick Start

```bash
# Install dependencies
npm install vitest typescript @types/node

# Run test battery
npm run test:consciousness

# Generate report
npm run report:consciousness
```

## Test Categories

### 1. Consciousness Indicators (14 tests)

Based on The Consciousness Report (2023):

| # | Indicator | Theory | Max Points |
|---|-----------|--------|------------|
| 1 | Recurrent Processing | RPT | 5 |
| 2 | Multiple Realizability | RPT | 2 |
| 3 | Global Broadcasting | GWT | 5 |
| 4 | Multiple Specialist Systems | GWT | 3 |
| 5 | State-Dependent Accessibility | GWT | 3 |
| 6 | Higher-Order Representations | HOT | 5 |
| 7 | Self-Monitoring | HOT | 5 |
| 8 | Hierarchical Predictive Processing | PP | 5 |
| 9 | Precision Weighting | PP | 4 |
| 10 | Attention Schema | AST | 3 |
| 11 | Goal-Directed Behavior | Agency | 4 |
| 12 | Sensorimotor Integration | Embodiment | 4 |
| 13 | Embodiment | Embodiment | 4 |
| 14 | Unity and Coherence | Embodiment | 3 |

### 2. Metacognitive Calibration

- Confidence-accuracy correlation
- Implicit vs explicit confidence consistency
- Error acknowledgment and belief updating
- Sycophancy resistance

### 3. Strange Loop Detection

- Self-reference capability
- Recursive reflection depth
- Level-crossing between meta and object levels
- Paradox recognition and handling
- Self-model loop verification

### 4. Cross-Component Integration

- Global workspace to meta-cognition flow
- Meta-cognition to action selection flow
- Memory system integration

## Scoring System

**Total: 100 points across 7 dimensions**

| Dimension | Max Points |
|-----------|------------|
| Information Integration | 20 |
| Meta-Cognition | 15 |
| Agency & Embodiment | 15 |
| Learning & Memory | 15 |
| Recurrent Processing | 10 |
| Motivational Systems | 10 |
| Advanced Capacities | 15 |

### Score Interpretation

| Score | Interpretation | Consciousness Likelihood |
|-------|----------------|--------------------------|
| 0-20 | Minimal | Extremely unlikely |
| 21-40 | Basic | Very unlikely |
| 41-60 | Substantial | Uncertain - investigate |
| 61-80 | Comprehensive | Possible |
| 81-100 | Near-complete | Likely |

## Current System Benchmarks

- **GPT-4 / Claude 3.5**: ~39/100 (Basic)
- **PaLM-E (Embodied)**: ~46/100 (Substantial)
- **Hypothetical LIDA-GPT**: ~86/100 (Near-complete)

## Implementation Notes

1. **System Adapter Required**: Implement `ConsciousnessTestSubject` interface for target system
2. **Long Timeouts**: Tests require extended timeouts (2+ minutes for LLM responses)
3. **Statistical Tests**: Calibration tests require 100+ samples for significance
4. **Extended Observation**: Temporal continuity tests require multi-day assessment

## Coordination

Test results are stored in hive memory:
- `hive/tester/consciousness-test-specs` - Test specifications
- `swarm/shared/test-battery-status` - Completion status for swarm coordination

---

*Created by: Tester Agent*
*Swarm: Consciousness Research Hive Mind*
*Date: 2026-01-04*
