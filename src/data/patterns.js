/**
 * Pattern taxonomy fixtures — the vocabulary the Intelligence loop
 * will eventually mine. Referenced by `creative.pattern_ids`.
 */

export const patterns = [
  { id: "pat_reduction", label: "Reduction", family: "offer", prevalence: 0.11, lift_index: 1.34 },
  { id: "pat_before_after", label: "Before / After", family: "proof", prevalence: 0.28, lift_index: 1.21 },
  { id: "pat_time_anchor", label: "Time anchor", family: "hook", prevalence: 0.19, lift_index: 1.17 },
  { id: "pat_substitution", label: "Substitution", family: "offer", prevalence: 0.07, lift_index: 1.28 },
  { id: "pat_benchmark_gap", label: "Benchmark gap", family: "hook", prevalence: 0.05, lift_index: 1.42 },
  { id: "pat_listicle", label: "Listicle", family: "structure", prevalence: 0.31, lift_index: 0.96 },
  { id: "pat_price_anchor", label: "Price anchor", family: "offer", prevalence: 0.24, lift_index: 1.09 },
  { id: "pat_myth_bust", label: "Myth bust", family: "hook", prevalence: 0.14, lift_index: 1.31 },
  { id: "pat_mechanism", label: "Mechanism reveal", family: "proof", prevalence: 0.16, lift_index: 1.26 },
  { id: "pat_demonstration", label: "Demonstration", family: "proof", prevalence: 0.37, lift_index: 1.15 },
  { id: "pat_blind_test", label: "Blind test", family: "proof", prevalence: 0.03, lift_index: 1.55 },
  { id: "pat_stress_test", label: "Stress test", family: "proof", prevalence: 0.06, lift_index: 1.38 },
  { id: "pat_contrarian", label: "Contrarian claim", family: "hook", prevalence: 0.09, lift_index: 1.47 },
  { id: "pat_expert_reaction", label: "Expert reaction", family: "credibility", prevalence: 0.12, lift_index: 1.33 },
  { id: "pat_social_proof", label: "Social proof", family: "credibility", prevalence: 0.44, lift_index: 1.04 },
  { id: "pat_risk_reversal", label: "Risk reversal", family: "offer", prevalence: 0.22, lift_index: 1.12 },
  { id: "pat_use_case_matrix", label: "Use-case matrix", family: "structure", prevalence: 0.04, lift_index: 1.08 },
  { id: "pat_cost_of_inaction", label: "Cost of inaction", family: "hook", prevalence: 0.08, lift_index: 1.29 },
  { id: "pat_narrative", label: "Narrative arc", family: "structure", prevalence: 0.17, lift_index: 1.23 },
  { id: "pat_education", label: "Education-first", family: "structure", prevalence: 0.26, lift_index: 1.06 },
  { id: "pat_comparison", label: "Direct comparison", family: "proof", prevalence: 0.13, lift_index: 1.19 },
  { id: "pat_haul", label: "Haul", family: "format", prevalence: 0.1, lift_index: 1.11 },
  { id: "pat_constraint_challenge", label: "Constraint challenge", family: "hook", prevalence: 0.05, lift_index: 1.36 },
  { id: "pat_unedited_demo", label: "Unedited demo", family: "proof", prevalence: 0.02, lift_index: 1.24 },
  { id: "pat_outcome_promise", label: "Outcome promise", family: "offer", prevalence: 0.33, lift_index: 1.02 },
  { id: "pat_radical_transparency", label: "Radical transparency", family: "credibility", prevalence: 0.03, lift_index: 1.44 },
]

export const patternsById = patterns.reduce((acc, p) => {
  acc[p.id] = p
  return acc
}, {})
